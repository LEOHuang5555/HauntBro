"""
Database ORM Session Management for ETL Operations
Provides secure database access using SQLAlchemy ORM instead of raw SQL
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Type, TypeVar, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete, and_, or_, func, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import logging
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from infrastructure.database.models import (
    Base, BronzeStory, BronzeStoryProcessing, SilverStory, SilverStoryChunks,
    GoldLayerMetrics, GoldStoryPerformance, User, UserFavorite, StoryRating,
    SearchInteraction, UserReadingBehavior, ScrapingPipelineMetrics
)
from etl.config.config import CONFIG

# Type variable for generic ORM operations
T = TypeVar('T', bound=Base)

logger = logging.getLogger(__name__)


class ETLDatabaseManager:
    """
    Secure database manager for ETL operations using SQLAlchemy ORM
    Replaces raw SQL queries with parameterized ORM operations
    """
    
    def __init__(self):
        """Initialize database manager with configuration"""
        self.db_config = CONFIG["database"]
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._connection_string = self._build_connection_string()
    
    def _build_connection_string(self) -> str:
        """Build secure database connection string"""
        return (
            f"postgresql+asyncpg://{self.db_config.username}:{self.db_config.password}@"
            f"{self.db_config.host}:{self.db_config.port}/{self.db_config.database}"
        )
    
    async def initialize(self) -> bool:
        """Initialize database engine and session factory"""
        try:
            self.engine = create_async_engine(
                self._connection_string,
                pool_size=self.db_config.min_connections,
                max_overflow=self.db_config.max_connections - self.db_config.min_connections,
                pool_pre_ping=True,
                echo=False  # Set to True for SQL debugging
            )
            
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            
            logger.info("✅ ETL Database manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic cleanup"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized - call initialize() first")
        
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def disconnect(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("🧹 Database connections closed")
    
    # =============================================================================
    # BRONZE LAYER OPERATIONS
    # =============================================================================
    
    async def get_unprocessed_bronze_stories(
        self, 
        limit: Optional[int] = None,
        min_content_length: int = 50
    ) -> List[BronzeStory]:
        """Get bronze stories that haven't been processed to silver layer"""
        async with self.get_session() as session:
            query = select(BronzeStory).where(
                and_(
                    BronzeStory.content.isnot(None),
                    func.length(BronzeStory.content) >= min_content_length
                )
            ).outerjoin(BronzeStoryProcessing).where(
                or_(
                    BronzeStoryProcessing.processing_status.is_(None),
                    BronzeStoryProcessing.processing_status.in_(['pending', 'failed']),
                    and_(
                        BronzeStoryProcessing.processing_status == 'failed',
                        BronzeStoryProcessing.retry_count < 3
                    )
                )
            ).outerjoin(SilverStoryChunks).where(
                SilverStoryChunks.story_id.is_(None)  # Not yet processed into chunks
            ).order_by(BronzeStory.scraped_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_bronze_story_by_id(self, story_id: str) -> Optional[BronzeStory]:
        """Get bronze story by ID"""
        async with self.get_session() as session:
            query = select(BronzeStory).where(BronzeStory.id == story_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    # =============================================================================
    # BRONZE STORY PROCESSING OPERATIONS
    # =============================================================================
    
    async def update_processing_status(
        self,
        story_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        etl_run_id: Optional[str] = None,
        quality_checks: Optional[Dict[str, Any]] = None
    ):
        """Update processing status for a bronze story using ORM"""
        async with self.get_session() as session:
            # Check if processing record exists
            existing = await session.execute(
                select(BronzeStoryProcessing).where(
                    BronzeStoryProcessing.story_id == story_id
                )
            )
            processing_record = existing.scalar_one_or_none()
            
            if processing_record:
                # Update existing record
                processing_record.processing_status = status
                processing_record.error_message = error_message
                processing_record.updated_at = datetime.now(timezone.utc)
                
                if etl_run_id:
                    processing_record.etl_run_id = etl_run_id
                
                if metadata:
                    # Merge metadata with existing
                    existing_metadata = processing_record.processing_metadata or {}
                    existing_metadata.update(metadata)
                    processing_record.processing_metadata = existing_metadata
                
                if quality_checks:
                    # Update quality checks
                    processing_record.quality_checks = quality_checks
                
                if status == 'failed':
                    processing_record.retry_count += 1
            else:
                # Create new record
                processing_record = BronzeStoryProcessing(
                    story_id=story_id,
                    processing_status=status,
                    processing_metadata=metadata,
                    quality_checks=quality_checks,
                    error_message=error_message,
                    etl_run_id=etl_run_id,
                    retry_count=1 if status == 'failed' else 0
                )
                session.add(processing_record)
    
    # =============================================================================
    # SILVER LAYER OPERATIONS
    # =============================================================================
    
    async def create_silver_story(
        self,
        bronze_story_id: str,
        title: str,
        cleaned_content: str,
        language_detected: str,
        word_count: int,
        tags: List[str] = None
    ) -> SilverStory:
        """Create silver story record using ORM"""
        async with self.get_session() as session:
            # Check if silver story already exists
            existing = await session.execute(
                select(SilverStory).where(
                    SilverStory.bronze_story_id == bronze_story_id
                )
            )
            silver_story = existing.scalar_one_or_none()
            
            # Get bronze story to copy author and post_date
            bronze_story_result = await session.execute(
                select(BronzeStory).where(BronzeStory.id == bronze_story_id)
            )
            bronze_story = bronze_story_result.scalar_one_or_none()
            
            if silver_story:
                # Update existing record
                silver_story.title = title
                silver_story.cleaned_content = cleaned_content
                silver_story.language_detected = language_detected
                silver_story.word_count = word_count
                silver_story.tags = tags or []
                silver_story.reading_time_minutes = max(1, word_count // 200)
                if bronze_story:
                    silver_story.author = bronze_story.author
                    silver_story.post_date = bronze_story.post_date
            else:
                # Create new record with fields that match the schema
                silver_story = SilverStory(
                    bronze_story_id=bronze_story_id,
                    title=title,
                    cleaned_content=cleaned_content,
                    language_detected=language_detected,
                    word_count=word_count,
                    author=bronze_story.author if bronze_story else None,
                    post_date=bronze_story.post_date if bronze_story else None,
                    tags=tags or [],  # Use provided tags or empty array
                    reading_time_minutes=max(1, word_count // 200)  # ~200 words per minute
                )
                session.add(silver_story)
            
            await session.flush()  # Flush to get the ID
            return silver_story
    
    async def create_silver_story_chunks(
        self,
        chunks_data: List[Dict[str, Any]],
        story_id: str
    ) -> List[SilverStoryChunks]:
        """Create silver story chunks using ORM batch operations - MVP schema"""
        async with self.get_session() as session:
            chunks = []
            
            for chunk_data in chunks_data:
                # Map to schema fields including embeddings
                chunk = SilverStoryChunks(
                    story_id=story_id,
                    chunk_text=chunk_data['chunk_text'],
                    chunk_order=chunk_data['chunk_order'],
                    chunk_type=chunk_data.get('chunk_type', 'body'),
                    
                    # Metrics fields
                    character_count=chunk_data.get('character_count', len(chunk_data['chunk_text'])),
                    word_count=chunk_data.get('word_count', len(chunk_data['chunk_text'].split())),
                    sentence_count=chunk_data.get('sentence_count', 0),
                    
                    # Extracted content
                    semantic_keywords=chunk_data.get('semantic_keywords', []),
                    
                    # Processing metadata
                    processing_language=chunk_data.get('processing_language', 'unknown'),
                    model_used=chunk_data.get('model_used', 'gpt-4o-mini'),
                    
                    # Embedding fields for semantic search
                    content_embedding=chunk_data.get('content_embedding'),
                    search_embedding=chunk_data.get('search_embedding'),
                )
                chunks.append(chunk)
                session.add(chunk)
            
            return chunks
    
    async def get_silver_story_chunks_by_story_id(self, story_id: str) -> List[SilverStoryChunks]:
        """Get all chunks for a specific story"""
        async with self.get_session() as session:
            query = select(SilverStoryChunks).where(
                SilverStoryChunks.story_id == story_id
            ).order_by(SilverStoryChunks.chunk_order)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    # =============================================================================
    # GOLD LAYER OPERATIONS
    # =============================================================================
    
    async def create_gold_layer_metrics(
        self,
        metric_type: str,
        metric_date: datetime,
        source_platform: str,
        metrics_data: Dict[str, Any],
        etl_run_id: str
    ) -> GoldLayerMetrics:
        """Create gold layer metrics record"""
        async with self.get_session() as session:
            metrics = GoldLayerMetrics(
                metric_type=metric_type,
                metric_date=metric_date,
                source_platform=source_platform,
                etl_run_id=etl_run_id,
                **metrics_data
            )
            session.add(metrics)
            await session.flush()
            return metrics
    
    # =============================================================================
    # UTILITY OPERATIONS
    # =============================================================================
    
    async def execute_raw_query(self, query: str, parameters: Dict[str, Any] = None) -> Any:
        """Execute raw SQL query when ORM is not sufficient (use sparingly)"""
        async with self.get_session() as session:
            result = await session.execute(text(query), parameters or {})
            return result
    
    async def get_table_count(self, model_class: Type[T]) -> int:
        """Get count of records in a table"""
        async with self.get_session() as session:
            result = await session.execute(select(func.count()).select_from(model_class))
            return result.scalar()
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
etl_db = ETLDatabaseManager()


# Convenience functions for common operations
async def get_unprocessed_stories(limit: Optional[int] = None) -> List[BronzeStory]:
    """Convenience function to get unprocessed stories"""
    return await etl_db.get_unprocessed_bronze_stories(limit=limit)


async def update_story_processing_status(
    story_id: str,
    status: str,
    metadata: Optional[Dict] = None,
    error_msg: Optional[str] = None,
    etl_run_id: Optional[str] = None,
    quality_checks: Optional[Dict] = None
):
    """Convenience function to update processing status"""
    await etl_db.update_processing_status(
        story_id=story_id,
        status=status,
        metadata=metadata,
        error_message=error_msg,
        etl_run_id=etl_run_id,
        quality_checks=quality_checks
    )


async def save_silver_data(
    bronze_story_id: str,
    story_data: Dict[str, Any],
    chunks_data: List[Dict[str, Any]]
) -> bool:
    """Convenience function to save complete silver layer data"""
    try:
        # Create silver story
        await etl_db.create_silver_story(
            bronze_story_id=bronze_story_id,
            **story_data
        )
        
        # Create silver chunks
        if chunks_data:
            await etl_db.create_silver_story_chunks(
                chunks_data=chunks_data,
                story_id=bronze_story_id
            )
        
        return True
    except Exception as e:
        logger.error(f"Failed to save silver data: {e}")
        return False
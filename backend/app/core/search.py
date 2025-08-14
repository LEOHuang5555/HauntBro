"""
Search service integrating with existing EmbeddingManager and database models
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
import json
import logging
import asyncio
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.models import (
    BronzeStory, SilverStory, SilverStoryChunks, SearchInteraction, 
    UserReadingBehavior, User
)
from etl.models.embedding_manager import EmbeddingManager
from monitoring.metrics_dashboard import MetricsCollector
from .base import BaseService, PaginatedResponse, TimestampMixin

logger = logging.getLogger(__name__)


class SearchService(BaseService, TimestampMixin):
    """Search service with hybrid keyword and semantic search capabilities"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.embedding_manager = None
        self.metrics_collector = MetricsCollector()
        
    async def initialize(self):
        """Initialize embedding manager"""
        if not self.embedding_manager:
            self.embedding_manager = EmbeddingManager()
            await self.embedding_manager.initialize()
    
    async def search_stories(
        self,
        query: str,
        user: Optional[User] = None,
        language: str = "auto",
        page: int = 1,
        per_page: int = 10,
        search_type: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Search stories using hybrid approach (keyword + semantic)
        
        Args:
            query: Search query
            user: Optional authenticated user
            language: Language hint (zh, en, auto) 
            page: Page number (1-based)
            per_page: Results per page
            search_type: Search type (keyword, semantic, hybrid)
        
        Returns:
            Search results with stories and metadata
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            await self.initialize()
            
            # Validate pagination
            offset, per_page = self._validate_pagination(page, per_page, 100)
            
            # Apply freemium restrictions
            if user:
                per_page = await self._apply_freemium_limits(user, per_page)
            
            results = []
            total_count = 0
            
            if search_type in ["keyword", "hybrid"]:
                # Keyword search
                keyword_results = await self._keyword_search(
                    query, language, offset, per_page
                )
                results.extend(keyword_results)
            
            if search_type in ["semantic", "hybrid"] and self.embedding_manager:
                # Semantic search
                semantic_results = await self._semantic_search(
                    query, language, offset, per_page
                )
                
                if search_type == "hybrid":
                    # Merge and rank results
                    results = await self._merge_search_results(
                        keyword_results, semantic_results
                    )
                else:
                    results = semantic_results
            
            # Get total count for pagination
            total_count = await self._get_total_search_count(query, language, search_type)
            
            # Format results
            formatted_results = await self._format_search_results(results)
            
            # Record search interaction
            if user:
                await self._record_search_interaction(
                    user, query, search_type, len(formatted_results), 
                    start_time
                )
            
            # Calculate metrics
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            
            # Record metrics
            await self.metrics_collector._record_metric(
                "search_query_count", 1.0, datetime.now(timezone.utc)
            )
            await self.metrics_collector._record_metric(
                "search_execution_time_ms", float(execution_time_ms), 
                datetime.now(timezone.utc)
            )
            
            response = PaginatedResponse.create(
                formatted_results, page, per_page, total_count, "results"
            )
            response["search_metadata"] = {
                "query": query,
                "language_detected": await self._detect_language(query),
                "search_type": search_type,
                "execution_time_ms": execution_time_ms,
                "results_count": len(formatted_results)
            }
            return response
            
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            execution_time_ms = int(
                (self.utc_now() - start_time).total_seconds() * 1000
            )
            
            response = PaginatedResponse.create([], page, per_page, 0, "results")
            response["search_metadata"] = {
                "query": query,
                "search_type": search_type,
                "execution_time_ms": execution_time_ms,
                "error": str(e)
            }
            return response
    
    async def _keyword_search(
        self, 
        query: str, 
        language: str, 
        offset: int, 
        limit: int
    ) -> List[Tuple]:
        """Perform keyword-based search"""
        try:
            # Build keyword search query
            search_terms = query.lower().split()
            
            # Search in bronze stories (title and content)
            stmt = (
                select(BronzeStory)
                .join(SilverStory, BronzeStory.id == SilverStory.bronze_story_id, isouter=True)
                .where(
                    or_(
                        func.lower(BronzeStory.title).contains(query.lower()),
                        func.lower(BronzeStory.content).contains(query.lower()),
                        and_(*[
                            or_(
                                func.lower(BronzeStory.title).contains(term),
                                func.lower(BronzeStory.content).contains(term)
                            ) for term in search_terms
                        ])
                    )
                )
                .offset(offset)
                .limit(limit)
                .order_by(BronzeStory.post_date.desc())
            )
            
            results = self.db.execute(stmt).scalars().all()
            return [(story, 1.0, "keyword") for story in results]
            
        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []
    
    async def _semantic_search(
        self, 
        query: str, 
        language: str, 
        offset: int, 
        limit: int
    ) -> List[Tuple]:
        """Perform semantic search using embeddings"""
        try:
            if not self.embedding_manager:
                return []
            
            # Generate query embedding
            embedding_result = await self.embedding_manager.generate_embeddings(
                text=query,
                search_text=query,
                language=language,
                strategy="speed_optimized"
            )
            
            if not embedding_result.success or not embedding_result.search_embedding:
                logger.warning("Failed to generate query embedding")
                return []
            
            query_embedding = embedding_result.search_embedding
            
            # Get story chunks with embeddings
            stmt = (
                select(SilverStoryChunks)
                .join(BronzeStory, SilverStoryChunks.story_id == BronzeStory.id)
                .where(SilverStoryChunks.search_embedding.isnot(None))
                .order_by(SilverStoryChunks.created_at.desc())
                .limit(1000)  # Limit for performance
            )
            
            chunks = self.db.execute(stmt).scalars().all()
            
            if not chunks:
                logger.info("No chunks with embeddings found")
                return []
            
            # Calculate similarities
            similarities = []
            for chunk in chunks:
                try:
                    chunk_embedding = json.loads(chunk.search_embedding)
                    similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                    similarities.append((chunk, similarity))
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Sort by similarity and get top results
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_chunks = similarities[offset:offset + limit]
            
            # Group by story and get unique stories
            story_scores = {}
            for chunk, similarity in top_chunks:
                story_id = chunk.story_id
                if story_id not in story_scores or similarity > story_scores[story_id][1]:
                    story_scores[story_id] = (chunk.bronze_story, similarity)
            
            # Convert to list and sort by score
            results = list(story_scores.values())
            results.sort(key=lambda x: x[1], reverse=True)
            
            return [(story, score, "semantic") for story, score in results]
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return float(dot_product / (norm1 * norm2))
        except Exception:
            return 0.0
    
    async def _merge_search_results(
        self, 
        keyword_results: List[Tuple], 
        semantic_results: List[Tuple]
    ) -> List[Tuple]:
        """Merge and rank keyword and semantic search results"""
        # Simple merging strategy: combine scores with weights
        keyword_weight = 0.4
        semantic_weight = 0.6
        
        all_results = {}
        
        # Add keyword results
        for story, score, source in keyword_results:
            story_id = story.id
            all_results[story_id] = {
                'story': story,
                'keyword_score': score,
                'semantic_score': 0.0,
                'sources': [source]
            }
        
        # Add semantic results
        for story, score, source in semantic_results:
            story_id = story.id
            if story_id in all_results:
                all_results[story_id]['semantic_score'] = score
                all_results[story_id]['sources'].append(source)
            else:
                all_results[story_id] = {
                    'story': story,
                    'keyword_score': 0.0,
                    'semantic_score': score,
                    'sources': [source]
                }
        
        # Calculate combined scores
        final_results = []
        for story_data in all_results.values():
            combined_score = (
                keyword_weight * story_data['keyword_score'] +
                semantic_weight * story_data['semantic_score']
            )
            final_results.append((
                story_data['story'], 
                combined_score, 
                "hybrid"
            ))
        
        # Sort by combined score
        final_results.sort(key=lambda x: x[1], reverse=True)
        return final_results
    
    async def _format_search_results(self, results: List[Tuple]) -> List[Dict[str, Any]]:
        """Format search results for API response"""
        formatted = []
        
        for story, score, source in results:
            try:
                # Get silver story data if available
                silver_stmt = select(SilverStory).where(
                    SilverStory.bronze_story_id == story.id
                )
                silver_story = self.db.execute(silver_stmt).scalar_one_or_none()
                
                formatted_result = {
                    "id": str(story.id),
                    "title": story.title or "Untitled",
                    "content": story.content[:500] + "..." if story.content and len(story.content) > 500 else story.content,
                    "author": story.author,
                    "source": story.source,
                    "post_date": story.post_date.isoformat() if story.post_date else None,
                    "search_score": round(score, 4),
                    "search_source": source,
                    "metadata": {
                        "word_count": silver_story.word_count if silver_story else None,
                        "reading_time_minutes": silver_story.reading_time_minutes if silver_story else None,
                        "language_detected": silver_story.language_detected if silver_story else None,
                        "tags": silver_story.tags if silver_story else []
                    }
                }
                
                formatted.append(formatted_result)
                
            except Exception as e:
                logger.warning(f"Error formatting search result: {e}")
                continue
        
        return formatted
    
    async def _apply_freemium_limits(self, user: User, per_page: int) -> int:
        """Apply freemium tier restrictions"""
        # For now, all users have the same limits
        # In a real implementation, you would check user.tier or similar
        max_results_free = 20
        return min(per_page, max_results_free)
    
    async def _detect_language(self, query: str) -> str:
        """Detect query language"""
        chinese_chars = len([c for c in query if '\u4e00' <= c <= '\u9fff'])
        total_chars = len(query.replace(' ', ''))
        
        if total_chars == 0:
            return 'auto'
        
        chinese_ratio = chinese_chars / total_chars
        return 'zh' if chinese_ratio > 0.3 else 'en'
    
    async def _get_total_search_count(
        self, 
        query: str, 
        language: str, 
        search_type: str
    ) -> int:
        """Get total count of search results for pagination"""
        try:
            search_terms = query.lower().split()
            
            stmt = (
                select(func.count(BronzeStory.id))
                .where(
                    or_(
                        func.lower(BronzeStory.title).contains(query.lower()),
                        func.lower(BronzeStory.content).contains(query.lower()),
                        and_(*[
                            or_(
                                func.lower(BronzeStory.title).contains(term),
                                func.lower(BronzeStory.content).contains(term)
                            ) for term in search_terms
                        ])
                    )
                )
            )
            
            result = self.db.execute(stmt).scalar()
            return result or 0
            
        except Exception as e:
            logger.error(f"Error getting search count: {e}")
            return 0
    
    async def _record_search_interaction(
        self,
        user: User,
        query: str,
        search_type: str,
        results_count: int,
        start_time: datetime
    ):
        """Record search interaction for analytics"""
        try:
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            
            interaction = SearchInteraction(
                user_id=user.id,
                query=query,
                search_type=search_type,
                results_count=results_count,
                execution_time_ms=execution_time_ms
            )
            
            self.db.add(interaction)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error recording search interaction: {e}")
            self.db.rollback()


# Dependency to get search service
from fastapi import Depends
from infrastructure.database.connection import get_db

def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    """Get search service instance"""
    return SearchService(db)
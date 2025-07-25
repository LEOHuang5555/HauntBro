"""
Silver Layer Processor - Language-Specific Processing
Integrates multi-language models for content cleaning, chunking, and embedding generation
"""

import asyncio
import asyncpg
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import sys
import unicodedata

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.processing.config import CONFIG
from etl.models.chinese_processor import ChineseProcessor, ChineseChunk
from etl.models.english_processor import EnglishProcessor, EnglishChunk
from etl.models.embedding_manager import EmbeddingManager
from etl.medallion.bronze_processor import BronzeProcessor
from infrastructure.database.models import BronzeStory, BronzeStoryProcessing, SilverStoryChunks

# Language detection
try:
    from langdetect import detect, LangDetectError
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


@dataclass
class SilverProcessingResult:
    """Result of silver layer processing"""
    success: bool
    story_id: str
    chunks_generated: int
    processing_time_ms: int
    model_cost: float
    language_detected: str
    quality_score: float
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class QualityValidationError(Exception):
    """Raised when content quality is below threshold"""
    def __init__(self, message: str, quality_score: float):
        super().__init__(message)
        self.quality_score = quality_score


class SilverProcessor:
    """
    Silver Layer Processor for language-specific content processing
    Handles Bronze → Silver transformation with multi-language support
    """
    
    def __init__(self):
        """Initialize silver processor with language-specific models"""
        self.pool = None
        self.db_config = CONFIG["database"]
        self.chunking_config = CONFIG["chunking"]
        
        # Language processors
        self.chinese_processor = ChineseProcessor()
        self.english_processor = EnglishProcessor()
        self.embedding_manager = EmbeddingManager()
        
        # Quality thresholds from config
        self.min_quality_score = self.chunking_config.min_quality_score
        self.max_chunks_per_story = self.chunking_config.max_chunks_per_story
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'chinese_stories': 0,
            'english_stories': 0,
            'mixed_stories': 0,
            'total_chunks': 0,
            'failed_stories': 0,
            'skipped_low_quality': 0,
            'total_cost': 0.0,
            'avg_processing_time': 0.0,
            'avg_quality_score': 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize all processors and database connections"""
        try:
            print("🚀 Initializing Silver Layer Processor...")
            
            # Initialize database connection pool
            self.pool = await asyncpg.create_pool(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.database,
                user=self.db_config.username,
                password=self.db_config.password,
                min_size=self.db_config.min_connections,
                max_size=self.db_config.max_connections,
                command_timeout=120  # Longer timeout for model operations
            )
            print("✅ Database connection pool created")
            
            # Initialize language processors
            print("Initializing Chinese processor (DeepSeek)...")
            chinese_initialized = await self.chinese_processor.initialize()
            
            print("Initializing English processor (LLaMA)...")
            english_initialized = await self.english_processor.initialize()
            
            print("Initializing Embedding Manager...")
            embedding_initialized = await self.embedding_manager.initialize()
            
            if not (chinese_initialized and english_initialized and embedding_initialized):
                print("⚠️  Some processors failed to initialize - continuing with available models")
            
            print("✅ Silver processor initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Silver processor initialization failed: {e}")
            return False
    
    async def disconnect(self):
        """Close all connections and cleanup resources"""
        if self.pool:
            await self.pool.close()
            print("Database connections closed")
        
        await self.chinese_processor.cleanup()
        await self.english_processor.cleanup()
        print("🧹 Silver processor resources cleaned up")
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of the text content
        Returns 'zh', 'en', 'mixed', or 'unknown'
        """
        if not text or len(text.strip()) < 10:
            return 'unknown'
        
        try:
            # Character-based detection first (more reliable for Chinese)
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            total_chars = len(text.replace(' ', ''))
            
            if total_chars == 0:
                return 'unknown'
            
            chinese_ratio = chinese_chars / total_chars
            
            if chinese_ratio > 0.5:
                return 'zh'  # Chinese dominant
            elif chinese_ratio < 0.1:
                # Use langdetect for non-Chinese text
                if LANGDETECT_AVAILABLE:
                    try:
                        detected = detect(text)
                        return 'en' if detected == 'en' else 'mixed'
                    except LangDetectError:
                        return 'en'  # Default to English if detection fails
                else:
                    return 'en'  # Default to English
            else:
                return 'mixed'  # Mixed language content
                
        except Exception as e:
            print(f"⚠️  Language detection failed: {e}")
            return 'unknown'
    
    def assess_content_quality(self, content: str, title: str = "", source: str = "") -> float:
        """
        Assess content quality for silver layer processing
        Returns quality score between 0.0 and 1.0
        """
        if not content:
            return 0.0
        
        score = 1.0
        
        # Length-based scoring
        content_length = len(content.strip())
        if content_length < 50:
            score *= 0.3  # Very short content
        elif content_length < 200:
            score *= 0.6  # Short content
        elif content_length > 50000:
            score *= 0.8  # Very long content might be spam
        
        # Structure assessment
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        if len(paragraphs) < 2:
            score *= 0.7  # Poor structure
        
        # Repetition check
        sentences = [s.strip() for s in content.replace('!', '.').replace('?', '.').split('.') if s.strip()]
        if len(sentences) > 3:
            unique_sentences = set(sentences)
            repetition_ratio = len(unique_sentences) / len(sentences)
            score *= max(0.5, repetition_ratio)
        
        # Character diversity (avoid spam/gibberish)
        unique_chars = len(set(content.lower()))
        char_diversity = unique_chars / max(len(content), 1)
        if char_diversity < 0.05:  # Very low diversity = likely spam
            score *= 0.3
        
        # Title relevance (basic check)
        if title and len(title.strip()) > 0:
            title_words = set(title.lower().split())
            content_words = set(content.lower().split())
            if title_words.intersection(content_words):
                score *= 1.1  # Bonus for title-content relevance
        
        # Source-specific adjustments
        if source == 'reddit_ghoststories':
            # Reddit posts often have formatting that affects quality
            if '[deleted]' in content or '[removed]' in content:
                score *= 0.1  # Deleted content
            if content.count('\n\n') > content.count('\n') * 0.3:
                score *= 1.05  # Well-formatted content bonus
        
        return round(min(1.0, max(0.0, score)), 3)
    
    async def get_unprocessed_stories(self, limit: int = 50) -> List[Dict]:
        """Get bronze stories that haven't been processed to silver layer"""
        query = """
        SELECT bs.id, bs.title, bs.content, bs.source, bs.source_url, 
               bs.author, bs.post_date, bs.scraped_at, bs.raw_metadata,
               bsp.processing_status, bsp.retry_count
        FROM bronze_stories bs
        LEFT JOIN bronze_story_processing bsp ON bs.id = bsp.story_id
        LEFT JOIN silver_story_chunks ssc ON bs.id = ssc.story_id
        WHERE (bsp.processing_status IS NULL OR bsp.processing_status IN ('pending', 'failed'))
        AND ssc.story_id IS NULL  -- Not yet processed into chunks
        AND LENGTH(bs.content) >= $1  -- Minimum content length
        AND bs.content IS NOT NULL
        AND (bsp.retry_count IS NULL OR bsp.retry_count < 3)  -- Limit retries
        ORDER BY bs.scraped_at DESC
        LIMIT $2
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, self.chunking_config.min_chunk_size, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Error fetching unprocessed stories: {e}")
            return []
    
    async def update_processing_status(self, story_id: str, status: str, metadata: Dict = None, error_msg: str = None):
        """Update processing status for a story"""
        query = """
        INSERT INTO bronze_story_processing (
            story_id, processing_status, processing_metadata, error_message, 
            retry_count, updated_at
        ) VALUES ($1, $2, $3, $4, 0, NOW())
        ON CONFLICT (story_id) DO UPDATE SET
            processing_status = $2,
            processing_metadata = COALESCE(bronze_story_processing.processing_metadata, '{}'::jsonb) || $3::jsonb,
            error_message = $4,
            retry_count = CASE WHEN $2 = 'failed' THEN bronze_story_processing.retry_count + 1 ELSE bronze_story_processing.retry_count END,
            updated_at = NOW()
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    story_id,
                    status,
                    json.dumps(metadata or {}),
                    error_msg
                )
        except Exception as e:
            print(f"❌ Error updating processing status: {e}")
    
    async def save_chunks_to_silver(self, chunks: List[Dict], story_id: str) -> bool:
        """Save processed chunks to silver_story_chunks table"""
        if not chunks:
            return True
        
        insert_query = """
        INSERT INTO silver_story_chunks (
            id, story_id, chunk_text, chunk_context, chunk_order, chunk_type,
            overlap_start, overlap_end, content_embedding, search_embedding,
            chunk_length, chunk_word_count, semantic_keywords,
            embedding_model, embedding_version, embedding_model_version,
            processing_language, chunk_quality_score, embedding_cost, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, NOW())
        ON CONFLICT (id) DO NOTHING  -- Avoid duplicates
        """
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for chunk in chunks:
                        await conn.execute(
                            insert_query,
                            chunk['id'],
                            story_id,
                            chunk['chunk_text'],
                            chunk['chunk_context'],
                            chunk['chunk_order'],
                            chunk['chunk_type'],
                            chunk.get('overlap_start', 0),
                            chunk.get('overlap_end', 0),
                            json.dumps(chunk.get('content_embedding', [])),  # Store as JSON for now
                            json.dumps(chunk.get('search_embedding', [])),   # Store as JSON for now
                            chunk['chunk_length'],
                            chunk['chunk_word_count'],
                            chunk.get('semantic_keywords', []),
                            chunk.get('embedding_model', 'unknown'),
                            chunk.get('embedding_version', '1.0'),
                            chunk.get('embedding_model_version', 'unknown'),
                            chunk.get('processing_language', 'unknown'),
                            chunk.get('chunk_quality_score', 0.0),
                            chunk.get('embedding_cost', 0.0)
                        )
            
            print(f"✅ Saved {len(chunks)} chunks to silver layer")
            return True
            
        except Exception as e:
            print(f"❌ Error saving chunks to silver layer: {e}")
            return False
    
    async def process_story(self, story_data: Dict, etl_run_id: str) -> SilverProcessingResult:
        """
        Process a single story through the silver layer pipeline
        
        Args:
            story_data: Bronze story data
            etl_run_id: ETL run identifier for tracking
            
        Returns:
            SilverProcessingResult with processing details
        """
        start_time = datetime.now()
        story_id = str(story_data['id'])
        
        try:
            # Update status to processing
            await self.update_processing_status(
                story_id, 'processing', 
                {'etl_run_id': etl_run_id, 'start_time': start_time.isoformat()}
            )
            
            # Extract story content
            title = story_data.get('title', '') or ''
            content = story_data.get('content', '') or ''
            source = story_data.get('source', '') or ''
            
            print(f"📖 Processing story: {title[:50]}... (ID: {story_id})")
            
            # Assess content quality
            quality_score = self.assess_content_quality(content, title, source)
            print(f"📊 Quality score: {quality_score}")
            
            if quality_score < self.min_quality_score:
                await self.update_processing_status(
                    story_id, 'skipped',
                    {
                        'reason': 'low_quality',
                        'quality_score': quality_score,
                        'min_threshold': self.min_quality_score
                    }
                )
                
                self.stats['skipped_low_quality'] += 1
                
                return SilverProcessingResult(
                    success=False,
                    story_id=story_id,
                    chunks_generated=0,
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    model_cost=0.0,
                    language_detected='unknown',
                    quality_score=quality_score,
                    error_message=f"Quality score {quality_score} below threshold {self.min_quality_score}"
                )
            
            # Detect language and route to appropriate processor
            language = self.detect_language(content)
            print(f"🌐 Language detected: {language}")
            
            # Process based on language
            chunks = []
            model_cost = 0.0
            processor_metadata = {}
            
            if language == 'zh':
                # Chinese processing with DeepSeek
                result = await self.chinese_processor.process_story(content, title)
                if result.success:
                    chunks = self._convert_chinese_chunks_to_dict(result.chunks, story_id)
                    model_cost = result.model_cost
                    processor_metadata = result.metadata
                    self.stats['chinese_stories'] += 1
                else:
                    raise Exception(f"Chinese processing failed: {result.error_message}")
                    
            elif language == 'en':
                # English processing with LLaMA
                result = await self.english_processor.process_story(content, title)
                if result.success:
                    chunks = self._convert_english_chunks_to_dict(result.chunks, story_id)
                    model_cost = result.model_cost
                    processor_metadata = result.metadata
                    self.stats['english_stories'] += 1
                else:
                    raise Exception(f"English processing failed: {result.error_message}")
                    
            elif language == 'mixed':
                # Mixed language - try both processors and choose best result
                print("🔄 Mixed language detected, trying both processors...")
                
                try:
                    # Try Chinese first (often has English mixed in)
                    zh_result = await self.chinese_processor.process_story(content, title)
                    if zh_result.success and len(zh_result.chunks) > 0:
                        chunks = self._convert_chinese_chunks_to_dict(zh_result.chunks, story_id)
                        model_cost = zh_result.model_cost
                        processor_metadata = zh_result.metadata
                        language = 'zh'  # Override detected language
                    else:
                        # Fallback to English processing
                        en_result = await self.english_processor.process_story(content, title)
                        if en_result.success:
                            chunks = self._convert_english_chunks_to_dict(en_result.chunks, story_id)
                            model_cost = en_result.model_cost
                            processor_metadata = en_result.metadata
                            language = 'en'  # Override detected language
                        else:
                            raise Exception("Both Chinese and English processing failed for mixed content")
                    
                    self.stats['mixed_stories'] += 1
                    
                except Exception as e:
                    raise Exception(f"Mixed language processing failed: {str(e)}")
            else:
                # Unknown language - default to English processing
                print("❓ Unknown language, defaulting to English processing...")
                result = await self.english_processor.process_story(content, title)
                if result.success:
                    chunks = self._convert_english_chunks_to_dict(result.chunks, story_id)
                    model_cost = result.model_cost
                    processor_metadata = result.metadata
                    language = 'en'
                    self.stats['english_stories'] += 1
                else:
                    raise Exception(f"Default English processing failed: {result.error_message}")
            
            # Validate chunk count
            if len(chunks) > self.max_chunks_per_story:
                print(f"⚠️  Too many chunks ({len(chunks)}), truncating to {self.max_chunks_per_story}")
                chunks = chunks[:self.max_chunks_per_story]
            
            # Generate embeddings for chunks
            embedding_cost = 0.0
            for chunk in chunks:
                try:
                    embedding_result = await self.embedding_manager.generate_embeddings(
                        chunk['chunk_text'],
                        chunk.get('chunk_context', ''),
                        language=language,
                        strategy='cost_optimized'
                    )
                    
                    if embedding_result.success:
                        chunk['content_embedding'] = embedding_result.content_embedding
                        chunk['search_embedding'] = embedding_result.search_embedding
                        chunk['embedding_model'] = embedding_result.model_used
                        chunk['embedding_cost'] = embedding_result.estimated_cost
                        embedding_cost += embedding_result.estimated_cost
                    else:
                        print(f"⚠️  Embedding failed for chunk {chunk['chunk_order']}: {embedding_result.error_message}")
                        chunk['content_embedding'] = []
                        chunk['search_embedding'] = []
                        chunk['embedding_cost'] = 0.0
                        
                except Exception as e:
                    print(f"❌ Error generating embeddings for chunk {chunk['chunk_order']}: {e}")
                    chunk['content_embedding'] = []
                    chunk['search_embedding'] = []
                    chunk['embedding_cost'] = 0.0
            
            total_cost = model_cost + embedding_cost
            
            # Save chunks to silver layer
            success = await self.save_chunks_to_silver(chunks, story_id)
            
            if success:
                # Update processing status to completed
                processing_metadata = {
                    'etl_run_id': etl_run_id,
                    'language_detected': language,
                    'quality_score': quality_score,
                    'chunks_generated': len(chunks),
                    'model_cost': model_cost,
                    'embedding_cost': embedding_cost,
                    'total_cost': total_cost,
                    'processor_metadata': processor_metadata,
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
                
                await self.update_processing_status(story_id, 'completed', processing_metadata)
                
                # Update statistics
                self.stats['total_processed'] += 1
                self.stats['total_chunks'] += len(chunks)
                self.stats['total_cost'] += total_cost
                self._update_average_stats(quality_score, start_time)
                
                processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                print(f"✅ Story processed: {len(chunks)} chunks, ${total_cost:.4f} cost ({processing_time_ms}ms)")
                
                return SilverProcessingResult(
                    success=True,
                    story_id=story_id,
                    chunks_generated=len(chunks),
                    processing_time_ms=processing_time_ms,
                    model_cost=total_cost,
                    language_detected=language,
                    quality_score=quality_score,
                    metadata={
                        'processor_used': f"{language}_processor",
                        'embedding_strategy': 'cost_optimized',
                        'chunks_truncated': len(chunks) == self.max_chunks_per_story
                    }
                )
            else:
                raise Exception("Failed to save chunks to silver layer")
                
        except Exception as e:
            error_msg = f"Silver processing failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Update error status
            await self.update_processing_status(
                story_id, 'failed',
                {'etl_run_id': etl_run_id, 'error_type': type(e).__name__},
                error_msg
            )
            
            self.stats['failed_stories'] += 1
            
            return SilverProcessingResult(
                success=False,
                story_id=story_id,
                chunks_generated=0,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                model_cost=0.0,
                language_detected='unknown',
                quality_score=0.0,
                error_message=error_msg
            )
    
    def _convert_chinese_chunks_to_dict(self, chunks: List[ChineseChunk], story_id: str) -> List[Dict]:
        """Convert Chinese chunks to database format"""
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                'id': str(uuid.uuid4()),
                'chunk_text': chunk.normalized_text,
                'chunk_context': chunk.original_text,  # Use original as context
                'chunk_order': chunk.chunk_order,
                'chunk_type': chunk.chunk_type,
                'chunk_length': chunk.character_count,
                'chunk_word_count': chunk.word_count,
                'semantic_keywords': chunk.semantic_keywords,
                'processing_language': 'zh',
                'chunk_quality_score': 0.8,  # Default quality for processed chunks
                'embedding_model_version': chunk.processing_metadata.get('model_used', 'deepseek-coder')
            }
            chunk_dicts.append(chunk_dict)
        return chunk_dicts
    
    def _convert_english_chunks_to_dict(self, chunks: List[EnglishChunk], story_id: str) -> List[Dict]:
        """Convert English chunks to database format"""
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                'id': str(uuid.uuid4()),
                'chunk_text': chunk.processed_text,
                'chunk_context': chunk.original_text,  # Use original as context
                'chunk_order': chunk.chunk_order,
                'chunk_type': chunk.chunk_type,
                'chunk_length': len(chunk.processed_text),
                'chunk_word_count': chunk.word_count,  
                'semantic_keywords': chunk.semantic_keywords,
                'processing_language': 'en',
                'chunk_quality_score': min(1.0, 0.7 + chunk.dialogue_ratio * 0.3),  # Quality bonus for dialogue
                'embedding_model_version': chunk.processing_metadata.get('model_used', 'llama3.2')
            }
            chunk_dicts.append(chunk_dict)
        return chunk_dicts
    
    def _update_average_stats(self, quality_score: float, start_time: datetime):
        """Update running averages for statistics"""
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Update average processing time
        total_processed = self.stats['total_processed']
        if total_processed > 1:
            self.stats['avg_processing_time'] = (
                (self.stats['avg_processing_time'] * (total_processed - 1) + processing_time) / total_processed
            )
        else:
            self.stats['avg_processing_time'] = processing_time
        
        # Update average quality score
        if total_processed > 1:
            self.stats['avg_quality_score'] = (
                (self.stats['avg_quality_score'] * (total_processed - 1) + quality_score) / total_processed
            )
        else:
            self.stats['avg_quality_score'] = quality_score
    
    async def process_batch(self, batch_size: int = 10, etl_run_id: str = None) -> Dict:
        """Process multiple stories in batch with controlled concurrency"""
        if etl_run_id is None:
            etl_run_id = f"silver_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        batch_start_time = datetime.now()
        
        try:
            # Get unprocessed stories
            stories = await self.get_unprocessed_stories(batch_size)
            
            if not stories:
                print("📭 No stories to process")
                return self.get_processing_stats()
            
            print(f"📚 Processing batch of {len(stories)} stories...")
            
            # Process stories with controlled concurrency (max 3 to avoid overwhelming models)
            semaphore = asyncio.Semaphore(3)
            
            async def process_with_semaphore(story):
                async with semaphore:
                    return await self.process_story(story, etl_run_id)
            
            # Process all stories concurrently
            tasks = [process_with_semaphore(story) for story in stories]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful = 0
            failed = 0
            skipped = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Story {i} failed with exception: {result}")
                    failed += 1
                elif isinstance(result, SilverProcessingResult):
                    if result.success:
                        successful += 1
                    elif "Quality score" in (result.error_message or ""):
                        skipped += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            
            batch_time = (datetime.now() - batch_start_time).total_seconds()
            
            print(f"📊 Batch complete: {successful} successful, {skipped} skipped, {failed} failed ({batch_time:.1f}s)")
            
            return self.get_processing_stats()
            
        except Exception as e:
            print(f"❌ Batch processing error: {e}")
            return {'error': str(e), 'stats': self.get_processing_stats()}
    
    def get_processing_stats(self) -> Dict:
        """Get comprehensive processing statistics"""
        return {
            'processor_type': 'silver_layer',
            'session_stats': self.stats,
            'language_breakdown': {
                'chinese': self.stats['chinese_stories'],
                'english': self.stats['english_stories'],
                'mixed': self.stats['mixed_stories']
            },
            'quality_metrics': {
                'avg_quality_score': self.stats['avg_quality_score'],
                'min_quality_threshold': self.min_quality_score,
                'skipped_low_quality': self.stats['skipped_low_quality']
            },
            'cost_metrics': {
                'total_cost': self.stats['total_cost'],
                'avg_cost_per_story': self.stats['total_cost'] / max(self.stats['total_processed'], 1),
                'avg_chunks_per_story': self.stats['total_chunks'] / max(self.stats['total_processed'], 1)
            },
            'performance_metrics': {
                'avg_processing_time_ms': self.stats['avg_processing_time'],
                'success_rate': self.stats['total_processed'] / max(
                    self.stats['total_processed'] + self.stats['failed_stories'], 1
                )
            }
        }


# CLI interface for testing
async def main():
    """Main CLI interface for testing silver processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Silver Layer Processor")
    parser.add_argument('--batch-size', type=int, default=5, help='Number of stories to process per batch')
    parser.add_argument('--etl-run-id', type=str, help='ETL run ID for tracking')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    parser.add_argument('--single-story', type=str, help='Process single story by ID')
    
    args = parser.parse_args()
    
    processor = SilverProcessor()
    
    try:
        await processor.initialize()
        
        if args.stats:
            stats = processor.get_processing_stats()
            print(f"📊 Processing Statistics: {json.dumps(stats, indent=2)}")
        
        if args.single_story:
            # Process single story (implement if needed)
            print(f"Single story processing not implemented yet")
        else:
            # Process batch
            etl_run_id = args.etl_run_id or f"cli_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            results = await processor.process_batch(args.batch_size, etl_run_id)
            
            print(f"\n📋 Batch Results:")
            print(json.dumps(results, indent=2))
            
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    except Exception as e:
        print(f"❌ Processor error: {e}")
    finally:
        await processor.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
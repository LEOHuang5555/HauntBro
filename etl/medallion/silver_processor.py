"""
Silver Layer Processor - Language-Specific Processing
Integrates multi-language models for content cleaning, chunking, and embedding generation
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import sys
import unicodedata
import re

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.config.config import CONFIG
from etl.processing.database_orm import etl_db, get_unprocessed_stories
from etl.models.chinese_processor import ChineseProcessor, ChineseChunk
from etl.models.english_processor import EnglishProcessor, EnglishChunk
from etl.models.embedding_manager import EmbeddingManager
from etl.medallion.bronze_processor import BronzeProcessor
from infrastructure.database.models import BronzeStory, BronzeStoryProcessing, SilverStoryChunks

from etl.models.utils import parse_title_tags, send_prompt_to_LLM

# Language detection
try:
    from langdetect import detect, LangDetectError
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


@dataclass
class SilverProcessingResult:
    """Result of silver layer processing (MVP - no cost tracking)"""
    success: bool
    story_id: str
    chunks_generated: int
    processing_time_ms: int
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
        self.db_manager = etl_db
        self.db_config = CONFIG["database"]
        self.chunking_config = CONFIG["chunking"]
        
        # Language processors
        self.chinese_processor = ChineseProcessor()
        self.english_processor = EnglishProcessor()
        self.embedding_manager = EmbeddingManager()
        
        # Quality thresholds from config
        self.min_quality_score = self.chunking_config.min_quality_score
        self.max_chunks_per_story = self.chunking_config.max_chunks_per_story
        
        # Processing statistics (MVP - no cost tracking)
        self.stats = {
            'total_processed': 0,
            'chinese_stories': 0,
            'english_stories': 0,
            'mixed_stories': 0,
            'total_chunks': 0,
            'failed_stories': 0,
            'skipped_low_quality': 0,
            'avg_processing_time': 0.0,
            'avg_quality_score': 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize all processors and database connections"""
        try:
            print("🚀 Initializing Silver Layer Processor...")
            
            # Initialize database ORM manager
            if not await self.db_manager.initialize():
                print("❌ Database ORM manager initialization failed")
                return False
            print("✅ Database ORM manager initialized")
            
            # Initialize language processors
            print("Initializing Chinese processor...")
            chinese_initialized = await self.chinese_processor.initialize()
            
            print("Initializing English processor...")
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
        await self.db_manager.disconnect()
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
        """Get bronze stories that haven't been processed to silver layer using ORM"""
        try:
            stories = await self.db_manager.get_unprocessed_bronze_stories(
                limit=limit,
                min_content_length=self.chunking_config.min_chunk_size
            )
            
            # Convert ORM objects to dictionaries for compatibility
            return [
                {
                    'id': str(story.id),
                    'title': story.title,
                    'content': story.content,
                    'source': story.source,
                    'source_url': story.source_url,
                    'author': story.author,
                    'post_date': story.post_date,
                    'scraped_at': story.scraped_at,
                    'raw_metadata': story.raw_metadata
                }
                for story in stories
            ]
        except Exception as e:
            print(f"❌ Error fetching unprocessed stories: {e}")
            return []
    
    async def update_processing_status(self, story_id: str, status: str, metadata: Dict = None, error_msg: str = None, etl_run_id: str = None, quality_checks: Dict = None):
        """Update processing status for a story using ORM"""
        try:
            await self.db_manager.update_processing_status(
                story_id=story_id,
                status=status,
                metadata=metadata,
                error_message=error_msg,
                etl_run_id=etl_run_id,
                quality_checks=quality_checks
            )
        except Exception as e:
            print(f"❌ Error updating processing status: {e}")
    
    async def save_story_to_silver(self, story_data: Dict, quality_score: float, language: str, metadata: Dict) -> bool:
        """Save processed story to silver_stories table using ORM"""
        try:
            story_id = str(story_data['id'])
            content = story_data.get('content', '')
            
            # Extract story-level tags from metadata
            tags = []
            if 'story_tags' in metadata:
                tags = metadata.get('story_tags', [])
            
            # Calculate language-aware word count
            word_count = self._calculate_word_count(content, language)
            
            # Map data to match updated database schema
            await self.db_manager.create_silver_story(
                bronze_story_id=story_id,
                title=story_data.get('title', ''),
                cleaned_content=content,
                language_detected=language,
                word_count=word_count,
                tags=tags
            )
            
            print(f"✅ Saved story to silver_stories table")
            return True
            
        except Exception as e:
            print(f"❌ Error saving story to silver layer: {e}")
            return False
    
    async def save_chunks_to_silver(self, chunks: List[Dict], story_id: str) -> bool:
        """Save processed chunks to silver_story_chunks table using ORM"""
        if not chunks:
            return True
        
        try:
            # Prepare chunks data for MVP schema ORM
            chunks_data = []
            for chunk in chunks:
                chunk_data = {
                    'chunk_text': chunk['chunk_text'],
                    'chunk_order': chunk['chunk_order'],
                    'chunk_type': chunk.get('chunk_type', 'body'),
                    'character_count': chunk.get('character_count', len(chunk['chunk_text'])),
                    'word_count': chunk.get('word_count', self._calculate_word_count(chunk['chunk_text'], chunk.get('processing_language', 'auto'))),
                    'sentence_count': chunk.get('sentence_count', 0),
                    'semantic_keywords': chunk.get('semantic_keywords', []),
                    'processing_language': chunk.get('processing_language', 'unknown'),
                    'model_used': chunk.get('model_used', 'gpt-4o-mini'),
                    'content_embedding': chunk.get('content_embedding', []), # chunk_text's embedding vector
                    'search_embedding': chunk.get('search_embedding', []), # semantic_keywords' embedding vector 
                }
                chunks_data.append(chunk_data)
            
            await self.db_manager.create_silver_story_chunks(
                chunks_data=chunks_data,
                story_id=story_id
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
                {'etl_run_id': etl_run_id, 'start_time': start_time.isoformat()},
                etl_run_id=etl_run_id
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
                    },
                    etl_run_id=etl_run_id
                )
                
                self.stats['skipped_low_quality'] += 1
                
                return SilverProcessingResult(
                    success=False,
                    story_id=story_id,
                    chunks_generated=0,
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    language_detected='unknown',
                    quality_score=quality_score,
                    error_message=f"Quality score {quality_score} below threshold {self.min_quality_score}"
                )
            
            # Detect language and route to appropriate processor
            language = self.detect_language(content)
            print(f"🌐 Language detected: {language}")
            
            # Process based on language
            chunks = []
            processor_metadata = {}
            
            if language == 'zh':
                # Chinese processing with gpt4o-mini
                result = await self.chinese_processor.process_story(content, title)
                if result.success:
                    chunks = self._convert_chinese_chunks_to_dict(result.chunks, story_id)
                    processor_metadata = result.metadata
                    self.stats['chinese_stories'] += 1
                else:
                    raise Exception(f"Chinese processing failed: {result.error_message}")
                    
            elif language == 'en':
                # English processing with gpt4o-mini
                result = await self.english_processor.process_story(content, title)
                if result.success:
                    chunks = self._convert_english_chunks_to_dict(result.chunks, story_id)
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
                        processor_metadata = zh_result.metadata
                        language = 'zh'  # Override detected language
                    else:
                        # Fallback to English processing
                        en_result = await self.english_processor.process_story(content, title)
                        if en_result.success:
                            chunks = self._convert_english_chunks_to_dict(en_result.chunks, story_id)
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
                    processor_metadata = result.metadata
                    print(processor_metadata)
                    language = 'en'
                    self.stats['english_stories'] += 1
                else:
                    raise Exception(f"Default English processing failed: {result.error_message}")
            
            # Validate chunk count
            if len(chunks) > self.max_chunks_per_story:
                print(f"⚠️  Too many chunks ({len(chunks)}), truncating to {self.max_chunks_per_story}")
                chunks = chunks[:self.max_chunks_per_story]
            
            # Generate embeddings for semantic search
            print("🚀 Generating embeddings for semantic search...")
            embeddings_success = await self._generate_embeddings_for_chunks(chunks)
            if embeddings_success:
                print("✅ Embeddings generated successfully")
            else:
                print("⚠️  Some embeddings failed to generate")
            
            # Generate story-level tags from full content analysis
            story_tags = await self._generate_story_tags(content, title, language)
            print(f"story_tags: {story_tags}")
            # Prepare metadata with tags for silver story
            story_metadata = dict(processor_metadata)
            story_metadata['story_tags'] = story_tags
            # Save story to silver_stories table first
            story_success = await self.save_story_to_silver(
                story_data, quality_score, language, story_metadata
            )
            
            # Save chunks to silver layer
            chunks_success = await self.save_chunks_to_silver(chunks, story_id)
            
            success = story_success and chunks_success
            
            if success:
                # Update processing status to completed
                processing_metadata = {
                    'etl_run_id': etl_run_id,
                    'language_detected': language,
                    'quality_score': quality_score,
                    'chunks_generated': len(chunks),
                    'story_tags': story_tags,
                    'processor_metadata': processor_metadata,
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
                    'word_count': self._calculate_word_count(story_data.get('content', ''), language),
                    'character_count': len(story_data.get('content', '')),
                    'embeddings_generated': embeddings_success
                }
                
                # Prepare quality checks data
                quality_checks = {
                    'content_quality_score': quality_score,
                    'min_quality_threshold': self.min_quality_score,
                    'quality_passed': quality_score >= self.min_quality_score,
                    'language_detection_confidence': 'high' if language in ['zh', 'en'] else 'low',
                    'chunking_success': len(chunks) > 0,
                    'chunks_count': len(chunks),
                    'avg_chunk_size': sum(len(chunk['chunk_text']) for chunk in chunks) / len(chunks) if chunks else 0,
                    'semantic_keywords_extracted': len(story_tags) > 0,
                    'processing_date': datetime.now(timezone.utc).isoformat()
                }
                
                await self.update_processing_status(
                    story_id, 'completed', processing_metadata, etl_run_id=etl_run_id, quality_checks=quality_checks
                )
                
                # Update statistics
                self.stats['total_processed'] += 1
                self.stats['total_chunks'] += len(chunks)
                self._update_average_stats(quality_score, start_time)
                
                processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                print(f"✅ Story processed: {len(chunks)} chunks ({processing_time_ms}ms)")
                
                return SilverProcessingResult(
                    success=True,
                    story_id=story_id,
                    chunks_generated=len(chunks),
                    processing_time_ms=processing_time_ms,
                    language_detected=language,
                    quality_score=quality_score,
                    metadata={
                        'processor_used': f"{language}_processor",
                        'embeddings_generated': embeddings_success,
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
                error_msg,
                etl_run_id=etl_run_id
            )
            
            self.stats['failed_stories'] += 1
            
            return SilverProcessingResult(
                success=False,
                story_id=story_id,
                chunks_generated=0,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                language_detected='unknown',
                quality_score=0.0,
                error_message=error_msg
            )
    
    def _convert_chinese_chunks_to_dict(self, chunks: List[ChineseChunk], story_id: str) -> List[Dict]:
        """Convert Chinese chunks to MVP database format"""
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                'chunk_text': chunk.normalized_text,
                'chunk_order': chunk.chunk_order,
                'chunk_type': chunk.chunk_type,
                'character_count': chunk.character_count,
                'word_count': chunk.word_count,
                'sentence_count': 0,  # Not applicable for Chinese text
                'semantic_keywords': chunk.semantic_keywords,
                'dialogue_ratio': 0.0,  # Not extracted for Chinese (budget optimization)
                'processing_language': 'zh',
                'model_used': chunk.processing_metadata.get('model_used', 'gpt-4o-mini')
            }
            chunk_dicts.append(chunk_dict)
        return chunk_dicts
    
    def _convert_english_chunks_to_dict(self, chunks: List[EnglishChunk], story_id: str) -> List[Dict]:
        """Convert English chunks to MVP database format"""
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                'chunk_text': chunk.normalized_text,
                'chunk_order': chunk.chunk_order,
                'chunk_type': chunk.chunk_type,
                'character_count': chunk.character_count,
                'word_count': chunk.word_count,
                'sentence_count': chunk.sentence_count,
                'semantic_keywords': chunk.semantic_keywords,
                'dialogue_ratio': chunk.dialogue_ratio,
                'processing_language': 'en',
                'model_used': chunk.processing_metadata.get('model_used', 'gpt-4o-mini')
            }
            chunk_dicts.append(chunk_dict)
        return chunk_dicts
    
    def _calculate_word_count(self, text: str, language: str) -> int:
        """Calculate language-aware word count"""
        if not text or not text.strip():
            return 0
        
        if language == 'zh':
            # For Chinese, use jieba for word segmentation if available
            if hasattr(self.chinese_processor, 'segment_chinese_text'):
                words = self.chinese_processor.segment_chinese_text(text)
                return len([w for w in words if w.strip()])
            else:
                # Fallback: count Chinese characters as approximate words
                chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
                # Estimate words (average 1.5-2 characters per word in Chinese)
                return max(1, int(chinese_chars / 1.7))
        else:
            # For English and other languages, split on whitespace
            return len(text.split())

    async def _generate_story_tags(self, content: str, title: str, language: str) -> List[str]:
        """Generate intelligent story-level tags with title parsing and LLM filtering."""
        try:
            tags = []

            # Step 1: Parse title-based tags
            if title:
                tags += parse_title_tags(title)

            # Step 2: Content-based keyword extraction
            if language == 'zh' and hasattr(self.chinese_processor, 'extract_keywords_tfidf'):
                tags += self.chinese_processor.extract_keywords_tfidf(content, max_keywords=10)
            elif language == 'en' and hasattr(self.english_processor, 'extract_keywords_nltk'):
                tags += self.english_processor.extract_keywords_nltk(content)
            else:
                tags += self._extract_tags_fallback(content, language)

            # Step 3: De-duplicate and cap
            tags = list(dict.fromkeys([t.strip() for t in tags if len(t.strip()) > 1]))[:20]
            # Skip LLM filtering if no tags found
            if not tags:
                return []

            # Step 4: Build filtering prompt based on language
            tags_str = ', '.join(tags)
            if language == 'zh':
                prompt = f"""請從以下標籤中挑選 3~7 個最能代表這篇故事主題的詞彙，
刪除無意義或重複的詞，只回傳一行以英文逗號分隔的詞彙清單，不需要其他解釋：

{tags_str}

範例輸出(一定要輸出繁體中文)：
無頭老師, 斧頭事件, 圖書館, 老師的頭, 夜路"""
            else:
                prompt = f"""From the following list of tags, please select 3 to 7 keywords that best represent the core theme of the story.
Remove any meaningless or redundant words.
Return only one line of keywords, separated by English commas.
Do not include any explanations or additional text.

Input tags:
{tags_str}

Example output (must be in english):
headless teacher, axe incident, library, teacher's head, walking at night"""

            # Step 5: LLM filtering
            filtered = await send_prompt_to_LLM(prompts=prompt, model_name=CONFIG['model'].english_model, temperature=0.1)
            final_tags = [tag.strip() for tag in re.split(r"[，,]", filtered) if len(tag.strip()) > 1]

            return final_tags[:10]

        except Exception as e:
            print(f"⚠️ Tag generation failed: {e}")
            return []


    
    def _extract_tags_fallback(self, content: str, language: str) -> List[str]:
        """Fallback tag extraction using simple analysis"""
        import re
        from collections import Counter
        
        if language == 'zh':
            # Chinese: extract 2-4 character words
            words = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
        else:
            # English: extract words 3+ characters
            words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Count frequencies and return top words
        word_freq = Counter(words)
        return [word for word, count in word_freq.most_common(10) if count >= 2]
    
    async def _generate_embeddings_for_chunks(self, chunks: List[Dict]) -> bool:
        """Generate embeddings for all chunks using the embedding manager"""
        try:
            if not self.embedding_manager:
                print("❌ Embedding manager not available")
                return False
            
            success_count = 0
            for chunk in chunks:
                chunk_text = chunk.get('chunk_text', '')
                if not chunk_text:
                    continue
                
                # Generate embeddings for the chunk
                embedding_result = await self.embedding_manager.generate_embeddings(
                    text=chunk_text,
                    search_text=chunk.get('semantic_keywords', []),
                    language=chunk.get('processing_language', 'auto'),
                    strategy='cost_optimized'
                )
                
                if embedding_result.success:
                    # Store embeddings in the chunk data
                    chunk['content_embedding'] = json.dumps(embedding_result.content_embedding) if embedding_result.content_embedding else None
                    chunk['search_embedding'] = json.dumps(embedding_result.search_embedding) if embedding_result.search_embedding else None
                    chunk['embedding_model'] = embedding_result.model_used
                    success_count += 1
                else:
                    print(f"⚠️  Failed to generate embedding for chunk {chunk.get('chunk_order', '?')}: {embedding_result.error_message}")
                    # Set empty embeddings to avoid database errors
                    chunk['content_embedding'] = None
                    chunk['search_embedding'] = None
                    chunk['embedding_model'] = None
            
            print(f"📊 Generated embeddings for {success_count}/{len(chunks)} chunks")
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            return False
    
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
        """Get comprehensive processing statistics (MVP - no cost tracking)"""
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
            'processing_metrics': {
                'avg_chunks_per_story': self.stats['total_chunks'] / max(self.stats['total_processed'], 1),
                'total_chunks_generated': self.stats['total_chunks']
            },
            'performance_metrics': {
                'avg_processing_time_ms': self.stats['avg_processing_time'],
                'success_rate': self.stats['total_processed'] / max(
                    self.stats['total_processed'] + self.stats['failed_stories'], 1
                )
            },
            'embedding_status': {
                'embeddings_enabled': True,
                'focus': 'chunking_and_embeddings'
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
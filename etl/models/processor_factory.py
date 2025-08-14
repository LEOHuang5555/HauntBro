"""
Language Processor Factory
Implements factory pattern for multi-language text processing
"""

import re
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime

# Language detection
try:
    from langdetect import detect, LangDetectError
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

from .chinese_processor import ChineseProcessor, ChineseChunk, ProcessingResult as ChineseResult
from .english_processor import EnglishProcessor, EnglishChunk, ProcessingResult as EnglishResult


@dataclass
class UnifiedChunk:
    """Unified chunk representation for all languages"""
    chunk_id: str
    original_text: str
    normalized_text: str
    chunk_order: int
    character_count: int
    word_count: int
    semantic_keywords: List[str]
    chunk_type: str
    language: str
    processing_metadata: Dict[str, Any]
    
    # Language-specific fields (optional)
    sentence_count: Optional[int] = None
    dialogue_ratio: Optional[float] = None


@dataclass
class UnifiedProcessingResult:
    """Unified processing result for all languages"""
    success: bool
    chunks: List[UnifiedChunk]
    processing_time_ms: int
    language: str
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class BaseLanguageProcessor(ABC):
    """Abstract base class for language processors"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the processor"""
        pass
    
    @abstractmethod
    async def process_story(self, story_text: str, title: str = "", metadata: Dict = None) -> UnifiedProcessingResult:
        """Process a story and return unified results"""
        pass
    
    @abstractmethod
    def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Cleanup resources"""
        pass


class ChineseProcessorAdapter(BaseLanguageProcessor):
    """Adapter for Chinese processor to conform to unified interface"""
    
    def __init__(self):
        self.processor = ChineseProcessor()
    
    async def initialize(self) -> bool:
        return await self.processor.initialize()
    
    async def process_story(self, story_text: str, title: str = "", metadata: Dict = None) -> UnifiedProcessingResult:
        result = await self.processor.process_story(story_text, title, metadata)
        
        # Convert to unified format
        unified_chunks = []
        for chunk in result.chunks:
            unified_chunk = UnifiedChunk(
                chunk_id=chunk.chunk_id,
                original_text=chunk.original_text,
                normalized_text=chunk.normalized_text,
                chunk_order=chunk.chunk_order,
                character_count=chunk.character_count,
                word_count=chunk.word_count,
                semantic_keywords=chunk.semantic_keywords,
                chunk_type=chunk.chunk_type,
                language='zh',
                processing_metadata=chunk.processing_metadata
            )
            unified_chunks.append(unified_chunk)
        
        return UnifiedProcessingResult(
            success=result.success,
            chunks=unified_chunks,
            processing_time_ms=result.processing_time_ms,
            language='zh',
            error_message=result.error_message,
            metadata=result.metadata
        )
    
    def get_processing_stats(self) -> Dict:
        return self.processor.get_processing_stats()
    
    async def cleanup(self):
        await self.processor.cleanup()


class EnglishProcessorAdapter(BaseLanguageProcessor):
    """Adapter for English processor to conform to unified interface"""
    
    def __init__(self):
        self.processor = EnglishProcessor()
    
    async def initialize(self) -> bool:
        return await self.processor.initialize()
    
    async def process_story(self, story_text: str, title: str = "", metadata: Dict = None) -> UnifiedProcessingResult:
        result = await self.processor.process_story(story_text, title, metadata)
        
        # Convert to unified format
        unified_chunks = []
        for chunk in result.chunks:
            unified_chunk = UnifiedChunk(
                chunk_id=chunk.chunk_id,
                original_text=chunk.original_text,
                normalized_text=chunk.normalized_text,
                chunk_order=chunk.chunk_order,
                character_count=chunk.character_count,
                word_count=chunk.word_count,
                semantic_keywords=chunk.semantic_keywords,
                chunk_type=chunk.chunk_type,
                language='en',
                processing_metadata=chunk.processing_metadata,
                sentence_count=chunk.sentence_count,
                dialogue_ratio=chunk.dialogue_ratio
            )
            unified_chunks.append(unified_chunk)
        
        return UnifiedProcessingResult(
            success=result.success,
            chunks=unified_chunks,
            processing_time_ms=result.processing_time_ms,
            language='en',
            error_message=result.error_message,
            metadata=result.metadata
        )
    
    def get_processing_stats(self) -> Dict:
        return self.processor.get_processing_stats()
    
    async def cleanup(self):
        await self.processor.cleanup()


class LanguageProcessorFactory:
    """
    Factory for creating language-specific processors
    Supports automatic language detection and processor selection
    """
    
    _processors = {
        'zh': ChineseProcessorAdapter,
        'en': EnglishProcessorAdapter,
    }
    
    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Detect language of text using multiple methods
        Returns: 'zh', 'en', or 'unknown'
        """
        if not text or len(text.strip()) < 10:
            return 'unknown'
        
        # Method 1: Character-based detection (most reliable for Chinese)
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = len(text.replace(' ', '').replace('\n', ''))
        
        if total_chars == 0:
            return 'unknown'
        
        chinese_ratio = chinese_chars / total_chars
        english_ratio = english_chars / total_chars
        
        # Strong indicators
        if chinese_ratio > 0.3:  # At least 30% Chinese characters
            return 'zh'
        elif english_ratio > 0.5:  # At least 50% English characters
            return 'en'
        
        # Method 2: Language detection library (if available)
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text[:1000])  # Sample first 1000 chars for performance
                if detected in ['zh', 'zh-cn', 'zh-tw']:
                    return 'zh'
                elif detected == 'en':
                    return 'en'
            except LangDetectError:
                pass
        
        # Method 3: Keyword-based detection
        chinese_keywords = ['的', '是', '在', '了', '有', '和', '我', '你', '他', '她']
        english_keywords = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with']
        
        text_lower = text.lower()
        chinese_count = sum(1 for keyword in chinese_keywords if keyword in text)
        english_count = sum(1 for keyword in english_keywords if keyword in text_lower)
        
        if chinese_count > english_count and chinese_count > 2:
            return 'zh'
        elif english_count > chinese_count and english_count > 2:
            return 'en'
        
        # Default fallback based on character ratios
        if chinese_ratio > english_ratio:
            return 'zh'
        elif english_ratio > 0.2:  # Lower threshold for mixed content
            return 'en'
        
        return 'unknown'
    
    @classmethod
    def create_processor(cls, language: str) -> BaseLanguageProcessor:
        """
        Create a processor for the specified language
        
        Args:
            language: Language code ('zh', 'en', or 'auto' for detection)
            
        Returns:
            Language processor instance
            
        Raises:
            ValueError: If language is not supported
        """
        if language not in cls._processors:
            supported = ', '.join(cls._processors.keys())
            raise ValueError(f"Unsupported language: {language}. Supported: {supported}")
        
        processor_class = cls._processors[language]
        return processor_class()
    
    @classmethod
    async def create_and_initialize_processor(cls, language: str) -> BaseLanguageProcessor:
        """
        Create and initialize a processor for the specified language
        
        Args:
            language: Language code ('zh' or 'en')
            
        Returns:
            Initialized processor instance
            
        Raises:
            ValueError: If language is not supported
            RuntimeError: If processor initialization fails
        """
        processor = cls.create_processor(language)
        
        if not await processor.initialize():
            raise RuntimeError(f"Failed to initialize {language} processor")
        
        return processor
    
    @classmethod
    async def process_with_auto_detection(cls, text: str, title: str = "", metadata: Dict = None) -> UnifiedProcessingResult:
        """
        Automatically detect language and process text
        
        Args:
            text: Text to process
            title: Optional title
            metadata: Optional metadata
            
        Returns:
            Processing result with unified format
        """
        # Detect language
        detected_language = cls.detect_language(text)
        
        if detected_language == 'unknown':
            return UnifiedProcessingResult(
                success=False,
                chunks=[],
                processing_time_ms=0,
                language='unknown',
                error_message="Unable to detect language or unsupported language"
            )
        
        # Process with detected language
        try:
            processor = await cls.create_and_initialize_processor(detected_language)
            result = await processor.process_story(text, title, metadata)
            await processor.cleanup()
            return result
        except Exception as e:
            return UnifiedProcessingResult(
                success=False,
                chunks=[],
                processing_time_ms=0,
                language=detected_language,
                error_message=f"Processing failed: {str(e)}"
            )
    
    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Get list of supported language codes"""
        return list(cls._processors.keys())
    
    @classmethod
    def register_processor(cls, language: str, processor_class: type):
        """
        Register a new language processor
        
        Args:
            language: Language code
            processor_class: Processor class that implements BaseLanguageProcessor
        """
        if not issubclass(processor_class, BaseLanguageProcessor):
            raise ValueError("Processor class must inherit from BaseLanguageProcessor")
        
        cls._processors[language] = processor_class
        print(f"✅ Registered processor for language: {language}")


# Convenience functions
async def process_text(text: str, language: str = None, title: str = "", metadata: Dict = None) -> UnifiedProcessingResult:
    """
    Convenience function to process text with optional language detection
    
    Args:
        text: Text to process
        language: Language code ('zh', 'en') or None for auto-detection
        title: Optional title
        metadata: Optional metadata
        
    Returns:
        Processing result
    """
    if language is None:
        return await LanguageProcessorFactory.process_with_auto_detection(text, title, metadata)
    else:
        processor = await LanguageProcessorFactory.create_and_initialize_processor(language)
        result = await processor.process_story(text, title, metadata)
        await processor.cleanup()
        return result


# Export main classes
__all__ = [
    'LanguageProcessorFactory',
    'BaseLanguageProcessor',
    'UnifiedChunk',
    'UnifiedProcessingResult',
    'ChineseProcessorAdapter',
    'EnglishProcessorAdapter',
    'process_text'
]
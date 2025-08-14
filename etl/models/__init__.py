"""
Multi-language Model Integration Package
Factory pattern for language-specific processors
"""

from .chinese_processor import ChineseProcessor
from .english_processor import EnglishProcessor
from .embedding_manager import EmbeddingManager
from .processor_factory import (
    LanguageProcessorFactory,
    BaseLanguageProcessor,
    UnifiedChunk,
    UnifiedProcessingResult,
    process_text
)

__all__ = [
    "ChineseProcessor", 
    "EnglishProcessor", 
    "EmbeddingManager",
    "LanguageProcessorFactory",
    "BaseLanguageProcessor",
    "UnifiedChunk",
    "UnifiedProcessingResult",
    "process_text"
]
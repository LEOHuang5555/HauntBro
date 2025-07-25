"""
Multi-language Model Integration Package
DeepSeek for Chinese content, LLaMA for English content
"""

from .chinese_processor import ChineseProcessor
from .english_processor import EnglishProcessor
from .embedding_manager import EmbeddingManager

__all__ = ["ChineseProcessor", "EnglishProcessor", "EmbeddingManager"]
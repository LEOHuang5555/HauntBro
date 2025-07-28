import os
from dataclasses import dataclass
from typing import Dict, Any
from dotenv import load_dotenv
load_dotenv()
@dataclass
class ModelConfig:
    """Configuration for local models"""
    ollama_base_url: str = "http://localhost:11434"
    english_model: str = "llama3.2"  # Updated to llama3.2
    chinese_model: str = "deepseek-coder"  # Updated model name
    use_gpu: bool = True
    max_context_length: int = 4096
    temperature: float = 0.3
    top_p: float = 0.9

@dataclass
class ChunkingConfig:
    """Enhanced chunking configuration"""
    target_chunk_size: int = 512
    max_chunk_size: int = 768
    min_chunk_size: int = 100
    overlap_size: int = 64
    context_window: int = 128
    
    # Quality thresholds
    min_quality_score: float = 0.5
    max_chunks_per_story: int = 50
    
    # Embedding settingsㄏ
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    
    # Language-specific settings
    chinese_char_per_token: float = 1.5
    english_words_per_token: float = 0.75

@dataclass
class DatabaseConfig:
    """Database connection settings"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "hauntbro")
    username: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")
    
    # Connection pool settings
    min_connections: int = 5
    max_connections: int = 20

@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    chunking_model: str = "gpt-4o-mini"  # Model for text chunking and processing
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 100
    max_retries: int = 3
    timeout: int = 30

@dataclass
class EmbeddingConfig:
    """Embedding generation configuration"""
    # Default strategy settings
    default_strategy: str = "cost_optimized"  # cost_optimized, quality_optimized, speed_optimized
    default_language: str = "auto"  # auto, zh, en
    
    # Model configurations with costs and capabilities
    openai_small: Dict[str, Any] = None
    openai_large: Dict[str, Any] = None
    sentence_transformer_multilingual: Dict[str, Any] = None
    sentence_transformer_english: Dict[str, Any] = None
    
    # Performance settings
    max_concurrent_requests: int = 3
    batch_size_openai: int = 10
    batch_size_sentence_transformer: int = 32
    
    # Cost thresholds for recommendations
    cost_warning_threshold: float = 10.0  # Warn if costs exceed $10
    processing_time_threshold: int = 2000  # Warn if avg time > 2000ms
    
    def __post_init__(self):
        """Initialize model configurations if not provided"""
        if self.openai_small is None:
            self.openai_small = {
                'model': 'text-embedding-3-small',
                'dimensions': 1536,
                'cost_per_1k_tokens': 0.00002,
                'max_batch_size': 100,
                'context_length': 8192
            }
        
        if self.openai_large is None:
            self.openai_large = {
                'model': 'text-embedding-3-large',
                'dimensions': 3072,
                'cost_per_1k_tokens': 0.00013,
                'max_batch_size': 100,
                'context_length': 8192
            }
        
        if self.sentence_transformer_multilingual is None:
            self.sentence_transformer_multilingual = {
                'model': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'dimensions': 384,
                'cost_per_1k_tokens': 0.0,
                'max_batch_size': 32,
                'context_length': 512
            }
        
        if self.sentence_transformer_english is None:
            self.sentence_transformer_english = {
                'model': 'sentence-transformers/all-MiniLM-L6-v2',
                'dimensions': 384,
                'cost_per_1k_tokens': 0.0,
                'max_batch_size': 32,
                'context_length': 512
            }

# Global configuration
CONFIG = {
    "model": ModelConfig(),
    "chunking": ChunkingConfig(), 
    "database": DatabaseConfig(),
    "openai": OpenAIConfig(),
    "embedding": EmbeddingConfig()
}
import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ModelConfig:
    """Configuration for local models"""
    ollama_base_url: str = "http://localhost:11434"
    english_model: str = "llama3:8b"  # Updated to llama3
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
    
    # Embedding settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
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
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 100
    max_retries: int = 3
    timeout: int = 30

# Global configuration
CONFIG = {
    "model": ModelConfig(),
    "chunking": ChunkingConfig(), 
    "database": DatabaseConfig(),
    "openai": OpenAIConfig()
}
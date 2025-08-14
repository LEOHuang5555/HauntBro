"""
Configuration settings for FastAPI backend
"""

import os
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class APIConfig:
    """API configuration settings"""
    title: str = "Ghost Story Search Engine API"
    description: str = "Production API with authentication and analytics"
    version: str = "1.0.0"
    docs_url: str = "/api/docs"
    redoc_url: str = "/api/redoc"
    openapi_url: str = "/api/openapi.json"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS settings
    allowed_origins: List[str] = None
    allow_credentials: bool = True
    
    def __post_init__(self):
        if self.allowed_origins is None:
            origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
            self.allowed_origins = [origin.strip() for origin in origins.split(",")]


@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    password_hash_rounds: int = 12




@dataclass
class RedisConfig:
    """Redis configuration for caching and WebSocket messaging"""
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    decode_responses: bool = True
    
    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    storage_uri: str = None
    default_limit: str = "100/hour"
    premium_limit: str = "1000/hour"
    admin_limit: str = "10000/hour"
    
    def __post_init__(self):
        if self.storage_uri is None:
            redis_config = RedisConfig()
            self.storage_uri = redis_config.url


@dataclass 
class BackendConfig:
    """Main backend configuration"""
    api: APIConfig = None
    security: SecurityConfig = None
    redis: RedisConfig = None
    rate_limit: RateLimitConfig = None
    
    def __post_init__(self):
        if self.api is None:
            self.api = APIConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.redis is None:
            self.redis = RedisConfig()
        if self.rate_limit is None:
            self.rate_limit = RateLimitConfig()


# Global backend configuration
backend_config = BackendConfig()
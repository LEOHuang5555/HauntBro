"""
Rate limiting middleware using SlowAPI with Redis backend
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.app.core.config import backend_config

# Try to import SlowAPI, fallback to basic implementation if not available
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    Limiter = None
    SlowAPIMiddleware = None
    RateLimitExceeded = Exception

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RateLimitService:
    """
    Rate limiting service with Redis backend and user-tier support
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.limiter: Optional[Limiter] = None
        self.enabled = SLOWAPI_AVAILABLE
        
        if self.enabled:
            # Initialize limiter with Redis if available, otherwise use memory
            storage_uri = backend_config.rate_limit.storage_uri if REDIS_AVAILABLE else None
            
            self.limiter = Limiter(
                key_func=get_remote_address,
                storage_uri=storage_uri,
                default_limits=[]  # We'll set limits per endpoint
            )
            
            logger.info(f"✅ Rate limiter initialized (Redis: {REDIS_AVAILABLE})")
        else:
            logger.warning("⚠️ SlowAPI not available - rate limiting disabled")
    
    async def initialize_redis(self):
        """Initialize Redis connection for advanced rate limiting"""
        if not REDIS_AVAILABLE:
            return False
        
        try:
            self.redis_client = redis.Redis.from_url(
                backend_config.redis.url,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ Redis connection for rate limiting established")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis for rate limiting: {e}")
            return False
    
    def get_user_rate_limit(self, user_tier: str = "free") -> str:
        """
        Get rate limit based on user tier
        
        Args:
            user_tier: User tier (free, premium, admin)
        
        Returns:
            Rate limit string (e.g., "100/hour")
        """
        limits = {
            "free": backend_config.rate_limit.default_limit,
            "premium": backend_config.rate_limit.premium_limit,
            "admin": backend_config.rate_limit.admin_limit
        }
        
        return limits.get(user_tier, limits["free"])
    
    async def check_custom_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> Dict[str, Any]:
        """
        Check custom rate limit using Redis
        
        Args:
            key: Rate limit key (e.g., user_id, IP)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            Rate limit status information
        """
        if not self.redis_client:
            # Fallback - always allow if Redis not available
            return {
                "allowed": True,
                "remaining": limit,
                "reset_time": None,
                "total": limit
            }
        
        try:
            current_time = datetime.now(timezone.utc)
            window_start = int(current_time.timestamp()) // window_seconds * window_seconds
            
            redis_key = f"rate_limit:{key}:{window_start}"
            
            # Get current count
            current_count = await self.redis_client.get(redis_key)
            current_count = int(current_count) if current_count else 0
            
            if current_count >= limit:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": window_start + window_seconds,
                    "total": limit,
                    "current": current_count
                }
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds)
            await pipe.execute()
            
            return {
                "allowed": True,
                "remaining": limit - (current_count + 1),
                "reset_time": window_start + window_seconds,
                "total": limit,
                "current": current_count + 1
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fallback - allow request if check fails
            return {
                "allowed": True,
                "remaining": limit,
                "reset_time": None,
                "total": limit,
                "error": str(e)
            }
    
    async def record_request(
        self, 
        endpoint: str, 
        user_id: Optional[str] = None, 
        ip_address: Optional[str] = None
    ):
        """Record API request for monitoring and analytics"""
        try:
            if not self.redis_client:
                return
            
            timestamp = datetime.now(timezone.utc)
            day_key = timestamp.strftime("%Y-%m-%d")
            hour_key = timestamp.strftime("%Y-%m-%d:%H")
            
            # Record daily and hourly request counts
            pipe = self.redis_client.pipeline()
            
            # Global counters
            pipe.incr(f"requests:global:day:{day_key}")
            pipe.incr(f"requests:global:hour:{hour_key}")
            
            # Endpoint counters
            pipe.incr(f"requests:endpoint:{endpoint}:day:{day_key}")
            pipe.incr(f"requests:endpoint:{endpoint}:hour:{hour_key}")
            
            # User counters
            if user_id:
                pipe.incr(f"requests:user:{user_id}:day:{day_key}")
                pipe.incr(f"requests:user:{user_id}:hour:{hour_key}")
            
            # IP counters
            if ip_address:
                pipe.incr(f"requests:ip:{ip_address}:day:{day_key}")
                pipe.incr(f"requests:ip:{ip_address}:hour:{hour_key}")
            
            # Set expiration (7 days for daily, 24 hours for hourly)
            for key in [f"requests:global:day:{day_key}", f"requests:endpoint:{endpoint}:day:{day_key}"]:
                pipe.expire(key, 7 * 24 * 3600)
            
            for key in [f"requests:global:hour:{hour_key}", f"requests:endpoint:{endpoint}:hour:{hour_key}"]:
                pipe.expire(key, 24 * 3600)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Request recording error: {e}")
    
    async def get_rate_limit_stats(self, timeframe: str = "hour") -> Dict[str, Any]:
        """Get rate limiting statistics"""
        if not self.redis_client:
            return {"error": "Redis not available"}
        
        try:
            current_time = datetime.now(timezone.utc)
            
            if timeframe == "hour":
                key_suffix = current_time.strftime("%Y-%m-%d:%H")
            else:  # day
                key_suffix = current_time.strftime("%Y-%m-%d")
            
            # Get global request count
            global_requests = await self.redis_client.get(f"requests:global:{timeframe}:{key_suffix}")
            global_requests = int(global_requests) if global_requests else 0
            
            # Get top endpoints
            endpoint_pattern = f"requests:endpoint:*:{timeframe}:{key_suffix}"
            endpoint_keys = await self.redis_client.keys(endpoint_pattern)
            
            top_endpoints = []
            for key in endpoint_keys[:10]:  # Top 10 endpoints
                count = await self.redis_client.get(key)
                endpoint = key.split(':')[2]  # Extract endpoint name
                top_endpoints.append({
                    "endpoint": endpoint,
                    "requests": int(count) if count else 0
                })
            
            top_endpoints.sort(key=lambda x: x["requests"], reverse=True)
            
            return {
                "timeframe": timeframe,
                "global_requests": global_requests,
                "top_endpoints": top_endpoints[:5],
                "timestamp": current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Rate limit stats error: {e}")
            return {"error": str(e)}


# Global rate limit service instance
rate_limit_service = RateLimitService()


def get_rate_limiter():
    """Get the rate limiter instance"""
    return rate_limit_service.limiter


def get_rate_limit_service():
    """Get the rate limit service instance"""
    return rate_limit_service
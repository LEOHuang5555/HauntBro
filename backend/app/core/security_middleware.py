"""
Enhanced security middleware for production deployment
"""

import sys
from pathlib import Path
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import ipaddress

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.app.core.rate_limiter import rate_limit_service

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration for middleware"""
    
    # Blocked IP ranges (example - configure for production)
    BLOCKED_IP_RANGES = [
        # "192.168.1.0/24",  # Example private range
    ]
    
    # Blocked user agents
    BLOCKED_USER_AGENTS = [
        r".*bot.*",
        r".*crawler.*", 
        r".*spider.*",
        r".*scraper.*"
    ]
    
    # Suspicious patterns in requests
    SUSPICIOUS_PATTERNS = [
        r"<script.*?>",  # XSS attempts
        r"javascript:",
        r"union.*select",  # SQL injection
        r"drop.*table",
        r"\.\.\/",  # Directory traversal
        r"etc\/passwd",
        r"cmd\.exe",
        r"\/bin\/",
    ]
    
    # Maximum request sizes (bytes)
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_JSON_SIZE = 1 * 1024 * 1024      # 1MB for JSON
    
    # Rate limiting thresholds
    RATE_LIMIT_THRESHOLD = 1000  # requests per hour per IP
    BURST_THRESHOLD = 100        # requests per minute per IP


class EnhancedSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced security middleware for production security
    """
    
    def __init__(self, app, config: SecurityConfig = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.blocked_ips: set = set()
        self.suspicious_requests: Dict[str, int] = {}
        
    async def dispatch(self, request: Request, call_next):
        """Main security middleware dispatch"""
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Security checks
        security_result = await self._perform_security_checks(request, client_ip)
        if security_result:
            return security_result
        
        # Record request for monitoring
        await self._record_request(request, client_ip)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Add security headers to response
            self._add_security_headers(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Request processing error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error"}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address with proxy support"""
        # Check for forwarded headers (reverse proxy setup)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _perform_security_checks(
        self, 
        request: Request, 
        client_ip: str
    ) -> Optional[Response]:
        """Perform comprehensive security checks"""
        
        # 1. IP-based blocking
        if await self._check_blocked_ip(client_ip):
            logger.warning(f"Blocked IP attempt: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Access denied"}
            )
        
        # 2. User agent checking
        if await self._check_user_agent(request):
            logger.warning(f"Blocked user agent from {client_ip}: {request.headers.get('user-agent', 'unknown')}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Access denied"}
            )
        
        # 3. Request size validation
        if await self._check_request_size(request):
            logger.warning(f"Request too large from {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": "Request too large"}
            )
        
        # 4. Content pattern analysis
        if await self._check_suspicious_patterns(request, client_ip):
            logger.warning(f"Suspicious patterns detected from {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid request"}
            )
        
        # 5. Rate limiting (additional check beyond SlowAPI)
        if await self._check_rate_limits(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded"}
            )
        
        return None
    
    async def _check_blocked_ip(self, client_ip: str) -> bool:
        """Check if IP is in blocked ranges"""
        if client_ip == "unknown":
            return False
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            for blocked_range in self.config.BLOCKED_IP_RANGES:
                if client_addr in ipaddress.ip_network(blocked_range):
                    return True
            
            # Check dynamically blocked IPs
            return client_ip in self.blocked_ips
            
        except ValueError:
            # Invalid IP format
            return True
    
    async def _check_user_agent(self, request: Request) -> bool:
        """Check for blocked user agents"""
        user_agent = request.headers.get("user-agent", "").lower()
        
        if not user_agent:
            # Block requests without user agent
            return True
        
        for pattern in self.config.BLOCKED_USER_AGENTS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True
        
        return False
    
    async def _check_request_size(self, request: Request) -> bool:
        """Check request size limits"""
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                
                # Check overall size
                if size > self.config.MAX_REQUEST_SIZE:
                    return True
                
                # Check JSON size for JSON requests
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type and size > self.config.MAX_JSON_SIZE:
                    return True
                
            except ValueError:
                # Invalid content-length header
                return True
        
        return False
    
    async def _check_suspicious_patterns(self, request: Request, client_ip: str) -> bool:
        """Check for suspicious patterns in request"""
        # Check URL path
        path = str(request.url.path)
        query = str(request.url.query) if request.url.query else ""
        
        # Combine path and query for pattern matching
        request_content = f"{path} {query}".lower()
        
        for pattern in self.config.SUSPICIOUS_PATTERNS:
            if re.search(pattern, request_content, re.IGNORECASE):
                # Track suspicious activity
                self.suspicious_requests[client_ip] = self.suspicious_requests.get(client_ip, 0) + 1
                
                # Auto-block after multiple suspicious requests
                if self.suspicious_requests[client_ip] >= 5:
                    self.blocked_ips.add(client_ip)
                    logger.warning(f"Auto-blocked IP for suspicious activity: {client_ip}")
                
                return True
        
        return False
    
    async def _check_rate_limits(self, client_ip: str) -> bool:
        """Additional rate limiting check"""
        if not rate_limit_service.redis_client:
            return False
        
        try:
            # Check hourly rate limit
            hourly_check = await rate_limit_service.check_custom_rate_limit(
                key=f"ip:{client_ip}",
                limit=self.config.RATE_LIMIT_THRESHOLD,
                window_seconds=3600  # 1 hour
            )
            
            if not hourly_check["allowed"]:
                return True
            
            # Check burst rate limit
            burst_check = await rate_limit_service.check_custom_rate_limit(
                key=f"ip:{client_ip}:burst",
                limit=self.config.BURST_THRESHOLD,
                window_seconds=60  # 1 minute
            )
            
            if not burst_check["allowed"]:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False
    
    async def _record_request(self, request: Request, client_ip: str):
        """Record request for monitoring"""
        try:
            await rate_limit_service.record_request(
                endpoint=request.url.path,
                ip_address=client_ip
            )
        except Exception as e:
            logger.error(f"Request recording error: {e}")
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        # These headers are already added in main.py SecurityHeadersMiddleware
        # This is a backup/enhancement location
        
        # Additional security headers
        response.headers["X-Request-ID"] = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        response.headers["X-Rate-Limit-Policy"] = "1000/hour"
        
        # Remove server information
        response.headers.pop("server", None)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Input validation and sanitization middleware
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.max_json_depth = 10
        self.max_array_length = 1000
        self.max_string_length = 10000
    
    async def dispatch(self, request: Request, call_next):
        """Validate and sanitize input"""
        
        # Only validate JSON requests
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            validation_result = await self._validate_json_request(request)
            if validation_result:
                return validation_result
        
        return await call_next(request)
    
    async def _validate_json_request(self, request: Request) -> Optional[Response]:
        """Validate JSON request structure"""
        try:
            # This is a placeholder for JSON validation
            # In production, you might want to:
            # 1. Parse JSON and check structure
            # 2. Validate against schemas
            # 3. Sanitize string inputs
            # 4. Check for malicious payloads
            
            # For now, just check content length
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 1024 * 1024:  # 1MB
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"error": "JSON payload too large"}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"JSON validation error: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid JSON format"}
            )
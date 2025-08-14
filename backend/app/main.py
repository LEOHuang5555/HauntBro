"""
Ghost Story Search Engine API
Production-ready FastAPI application with authentication, search, and analytics
"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.app.core.config import backend_config
from backend.app.core.rate_limiter import rate_limit_service, get_rate_limiter
from backend.app.core.security_middleware import EnhancedSecurityMiddleware, InputValidationMiddleware
from infrastructure.database.connection import db_manager, init_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Ghost Story Search Engine API...")
    
    try:
        # Test database connection
        logger.info("📊 Testing database connection...")
        if not db_manager.test_connection():
            raise RuntimeError("Failed to connect to database")
        logger.info("✅ Database connection successful")
        
        # Initialize database if needed
        logger.info("🔧 Initializing database...")
        init_database()
        logger.info("✅ Database initialized")
        
        # Initialize rate limiting service
        logger.info("🔧 Initializing rate limiting...")
        await rate_limit_service.initialize_redis()
        logger.info("✅ Rate limiting initialized")
        
        logger.info("🎉 API startup complete!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Ghost Story Search Engine API...")
    logger.info("👋 Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=backend_config.api.title,
    description=backend_config.api.description,
    version=backend_config.api.version,
    docs_url=backend_config.api.docs_url,
    redoc_url=backend_config.api.redoc_url,
    openapi_url=backend_config.api.openapi_url,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health check and system status endpoints"
        },
        {
            "name": "Authentication", 
            "description": "User authentication and JWT management"
        },
        {
            "name": "Search",
            "description": "RAG-powered contextual search endpoints"
        },
        {
            "name": "Analytics",
            "description": "User behavior tracking and insights"
        },
        {
            "name": "Content",
            "description": "Story management and user preferences"
        },
        {
            "name": "WebSocket",
            "description": "Real-time features and notifications"
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints and system management"
        }
    ]
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Configure properly for production
)

# Add enhanced security middleware (before other middleware)
app.add_middleware(EnhancedSecurityMiddleware)

# Add input validation middleware
app.add_middleware(InputValidationMiddleware)


# Add SlowAPI rate limiting middleware if available
limiter = get_rate_limiter()
if limiter:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    logger.info("✅ SlowAPI rate limiting enabled")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=backend_config.api.allowed_origins,
    allow_credentials=backend_config.api.allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db_healthy = db_manager.test_connection()
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": backend_config.api.version,
            "components": {
                "database": "healthy" if db_healthy else "unhealthy",
                "api": "healthy"
            }
        }
        
        if not db_healthy:
            return JSONResponse(
                status_code=503,
                content=health_status
            )
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


# Detailed health check endpoint
@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with component status"""
    try:
        components = {}
        
        # Test database
        try:
            db_healthy = db_manager.test_connection()
            components["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "details": "Connection successful" if db_healthy else "Connection failed"
            }
        except Exception as e:
            components["database"] = {
                "status": "unhealthy",
                "details": str(e)
            }
        
        # Overall status
        all_healthy = all(
            comp["status"] == "healthy" 
            for comp in components.values()
        )
        
        health_status = {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "version": backend_config.api.version,
            "components": components
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


# Include API routers
from backend.app.api.v1 import auth, search, analytics, websockets, content, admin

# Register all API routes with /api/v1 prefix
for router_module in [auth, search, analytics, websockets, content, admin]:
    app.include_router(router_module.router, prefix="/api/v1")

# WebSocket endpoints
from backend.app.websocket.endpoints import websocket_endpoint, websocket_test_endpoint

@app.websocket("/ws/{user_id}")
async def websocket_user_endpoint(websocket: WebSocket, user_id: str, token: str = Query(None)):
    """WebSocket endpoint for authenticated users"""
    await websocket_endpoint(websocket, token)

@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """Test WebSocket endpoint without authentication"""
    await websocket_test_endpoint(websocket)

# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": backend_config.api.title,
        "version": backend_config.api.version,
        "description": backend_config.api.description,
        "docs_url": backend_config.api.docs_url,
        "health_check": "/health",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=backend_config.api.debug,
        log_level="info"
    )
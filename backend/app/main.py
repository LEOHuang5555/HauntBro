"""
Main FastAPI application for HauntBro ghost story search engine.
"""

import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app.database.connection import init_database
from app.auth.routes import router as auth_router

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting HauntBro application...")
    try:
        init_database()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    print("📴 Shutting down HauntBro application...")


app = FastAPI(
    title="HauntBro API",
    description="Ghost story search engine API with web scraping and RAG capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to HauntBro - Ghost Story Search Engine",
        "version": "1.0.0",
        "status": "active"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("API_DEBUG", "true").lower() == "true"
    uvicorn.run(app, host=host, port=port, reload=debug)
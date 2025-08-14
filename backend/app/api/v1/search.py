"""
Search API endpoints integrating with EmbeddingManager and similarity search
"""

import sys
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from backend.app.core.auth import get_current_user_optional, get_current_user
from backend.app.core.search import SearchService, get_search_service
from backend.app.core.schemas import SearchRequest, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "/",
    summary="Search stories",
    description="Search ghost stories using hybrid keyword and semantic search"
)
async def search_stories(
    search_request: SearchRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    search_service: SearchService = Depends(get_search_service)
) -> Any:
    """
    Search ghost stories using hybrid approach (keyword + semantic search)
    
    - **query**: Search query text
    - **language**: Language hint (zh, en, auto) - auto-detected if not specified
    - **page**: Page number (default: 1)
    - **per_page**: Results per page (default: 10, max: 100)
    """
    try:
        results = await search_service.search_stories(
            query=search_request.query,
            user=current_user,
            language=search_request.language or "auto",
            page=search_request.page,
            per_page=search_request.per_page,
            search_type="hybrid"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Search endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get(
    "/",
    summary="Search stories (GET)",
    description="Search ghost stories using query parameters"
)
async def search_stories_get(
    query: str = Query(..., description="Search query"),
    language: Optional[str] = Query("auto", description="Language hint (zh, en, auto)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Results per page"),
    search_type: str = Query("hybrid", description="Search type (keyword, semantic, hybrid)"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    search_service: SearchService = Depends(get_search_service)
) -> Any:
    """
    Search ghost stories using GET request with query parameters
    """
    try:
        results = await search_service.search_stories(
            query=query,
            user=current_user,
            language=language,
            page=page,
            per_page=per_page,
            search_type=search_type
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Search GET endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.post(
    "/keyword",
    summary="Keyword search",
    description="Search stories using keyword-only search"
)
async def keyword_search(
    search_request: SearchRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    search_service: SearchService = Depends(get_search_service)
) -> Any:
    """
    Search stories using keyword-only search
    """
    try:
        results = await search_service.search_stories(
            query=search_request.query,
            user=current_user,
            language=search_request.language or "auto",
            page=search_request.page,
            per_page=search_request.per_page,
            search_type="keyword"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Keyword search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keyword search failed"
        )


@router.post(
    "/semantic",
    summary="Semantic search",
    description="Search stories using semantic similarity (embeddings)"
)
async def semantic_search(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user),  # Require auth for semantic search
    search_service: SearchService = Depends(get_search_service)
) -> Any:
    """
    Search stories using semantic similarity (requires authentication)
    
    This endpoint uses AI embeddings to find semantically similar content,
    which is more resource-intensive and requires user authentication.
    """
    try:
        results = await search_service.search_stories(
            query=search_request.query,
            user=current_user,
            language=search_request.language or "auto",
            page=search_request.page,
            per_page=search_request.per_page,
            search_type="semantic"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Semantic search failed"
        )


@router.get(
    "/suggestions",
    summary="Search suggestions",
    description="Get search query suggestions based on popular searches"
)
async def get_search_suggestions(
    query: Optional[str] = Query(None, description="Partial query for suggestions"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get search query suggestions based on popular searches
    """
    try:
        # Simple implementation - can be enhanced with more sophisticated logic
        from sqlalchemy import select, func
        from infrastructure.database.models import SearchInteraction
        
        # Get popular search queries
        stmt = (
            select(
                SearchInteraction.query,
                func.count(SearchInteraction.id).label('count')
            )
            .group_by(SearchInteraction.query)
            .order_by(func.count(SearchInteraction.id).desc())
            .limit(limit)
        )
        
        if query:
            stmt = stmt.where(SearchInteraction.query.ilike(f"%{query}%"))
        
        results = db.execute(stmt).all()
        
        suggestions = [
            {
                "query": result.query,
                "count": result.count
            }
            for result in results
        ]
        
        return {
            "suggestions": suggestions,
            "query": query,
            "count": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Search suggestions error: {e}")
        return {
            "suggestions": [],
            "query": query,
            "count": 0
        }


@router.get(
    "/trending",
    summary="Trending searches",
    description="Get trending search queries"
)
async def get_trending_searches(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of trending queries"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get trending search queries from the specified time window
    """
    try:
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import select, func
        from infrastructure.database.models import SearchInteraction
        
        # Calculate time window
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Get trending queries
        stmt = (
            select(
                SearchInteraction.query,
                func.count(SearchInteraction.id).label('search_count'),
                func.max(SearchInteraction.search_timestamp).label('latest_search')
            )
            .where(SearchInteraction.search_timestamp >= since)
            .group_by(SearchInteraction.query)
            .order_by(func.count(SearchInteraction.id).desc())
            .limit(limit)
        )
        
        results = db.execute(stmt).all()
        
        trending = [
            {
                "query": result.query,
                "search_count": result.search_count,
                "latest_search": result.latest_search.isoformat() if result.latest_search else None
            }
            for result in results
        ]
        
        return {
            "trending": trending,
            "time_window_hours": hours,
            "count": len(trending)
        }
        
    except Exception as e:
        logger.error(f"Trending searches error: {e}")
        return {
            "trending": [],
            "time_window_hours": hours,
            "count": 0
        }


@router.get(
    "/health",
    summary="Search service health",
    description="Check search service health and capabilities"
)
async def search_health(
    search_service: SearchService = Depends(get_search_service)
) -> Any:
    """
    Check search service health and capabilities
    """
    try:
        await search_service.initialize()
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "keyword_search": True,
                "semantic_search": search_service.embedding_manager is not None,
                "hybrid_search": True,
                "search_analytics": True
            },
            "embedding_manager": {
                "available": search_service.embedding_manager is not None,
                "initialized": search_service.embedding_manager is not None
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Search health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
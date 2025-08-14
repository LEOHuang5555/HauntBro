"""
Content management API endpoints for stories, bookmarks, and user preferences
"""

import sys
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path as PathParam
from sqlalchemy.orm import Session
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from backend.app.core.auth import get_current_user, get_current_user_optional
from backend.app.core.content import ContentService, get_content_service
from backend.app.core.schemas import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content"])


@router.get(
    "/stories/{story_id}",
    summary="Get story details",
    description="Get detailed information about a specific story"
)
async def get_story_details(
    story_id: str = PathParam(..., description="Story ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    content_service: ContentService = Depends(get_content_service)
) -> Any:
    """
    Get detailed story information
    
    - **story_id**: Unique story identifier
    
    Returns comprehensive story details including:
    - Basic story information (title, author, content)
    - Processed metadata (word count, reading time, tags)
    - User-specific data (favorites, ratings, reading history) if authenticated
    - Content preview (first few chunks)
    """
    try:
        story_detail = await content_service.get_story_detail(
            story_id=story_id,
            user=current_user
        )
        
        return story_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get story details error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get story details"
        )


@router.get(
    "/favorites",
    summary="Get user favorites",
    description="Get current user's favorite stories with pagination"
)
async def get_user_favorites(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
) -> Any:
    """
    Get current user's favorite stories
    
    - **page**: Page number (default: 1)
    - **per_page**: Results per page (default: 20, max: 100)
    
    Returns paginated list of favorite stories with:
    - Story basic information
    - Favorited timestamp
    - Story metadata (word count, reading time, tags)
    """
    try:
        favorites = await content_service.get_user_favorites(
            user_id=str(current_user.id),
            page=page,
            per_page=per_page
        )
        
        return favorites
        
    except Exception as e:
        logger.error(f"Get user favorites error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user favorites"
        )


@router.post(
    "/stories/{story_id}/favorite",
    response_model=MessageResponse,
    summary="Add story to favorites",
    description="Add a story to current user's favorites"
)
async def add_to_favorites(
    story_id: str = PathParam(..., description="Story ID"),
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
) -> Any:
    """
    Add story to current user's favorites
    
    - **story_id**: ID of the story to favorite
    """
    try:
        result = await content_service.toggle_favorite(
            story_id=story_id,
            user_id=str(current_user.id),
            is_favorite=True
        )
        
        if result["action"] == "added":
            message = "Story added to favorites"
        elif result["action"] == "no_change":
            message = "Story is already in favorites"
        else:
            message = "Favorite status updated"
        
        return MessageResponse(message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add to favorites error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add story to favorites"
        )


@router.delete(
    "/stories/{story_id}/favorite",
    response_model=MessageResponse,
    summary="Remove story from favorites",
    description="Remove a story from current user's favorites"
)
async def remove_from_favorites(
    story_id: str = PathParam(..., description="Story ID"),
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
) -> Any:
    """
    Remove story from current user's favorites
    
    - **story_id**: ID of the story to unfavorite
    """
    try:
        result = await content_service.toggle_favorite(
            story_id=story_id,
            user_id=str(current_user.id),
            is_favorite=False
        )
        
        if result["action"] == "removed":
            message = "Story removed from favorites"
        elif result["action"] == "no_change":
            message = "Story was not in favorites"
        else:
            message = "Favorite status updated"
        
        return MessageResponse(message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remove from favorites error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove story from favorites"
        )


@router.post(
    "/stories/{story_id}/rating",
    summary="Rate a story",
    description="Rate a story from 1 to 5 stars"
)
async def rate_story(
    story_id: str = PathParam(..., description="Story ID"),
    rating: int = Query(..., ge=1, le=5, description="Rating (1-5 stars)"),
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
) -> Any:
    """
    Rate a story from 1 to 5 stars
    
    - **story_id**: ID of the story to rate
    - **rating**: Rating value (1-5 stars)
    """
    try:
        result = await content_service.rate_story(
            story_id=story_id,
            user_id=str(current_user.id),
            rating=rating
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate story error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rate story"
        )


@router.get(
    "/ratings",
    summary="Get user ratings",
    description="Get current user's story ratings with pagination"
)
async def get_user_ratings(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
) -> Any:
    """
    Get current user's story ratings
    
    - **page**: Page number (default: 1)
    - **per_page**: Results per page (default: 20, max: 100)
    
    Returns paginated list of user ratings with:
    - Rating value and timestamps
    - Story basic information
    - Story metadata
    """
    try:
        ratings = await content_service.get_user_ratings(
            user_id=str(current_user.id),
            page=page,
            per_page=per_page
        )
        
        return ratings
        
    except Exception as e:
        logger.error(f"Get user ratings error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user ratings"
        )


@router.get(
    "/reading-history",
    summary="Get reading history",
    description="Get current user's reading history with pagination"
)
async def get_reading_history(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
) -> Any:
    """
    Get current user's reading history
    
    - **page**: Page number (default: 1)
    - **per_page**: Results per page (default: 20, max: 100)
    
    Returns paginated reading history with:
    - Reading session details (start time, duration, completion)
    - Story information
    - Reading progress
    """
    try:
        history = await content_service.get_reading_history(
            user_id=str(current_user.id),
            page=page,
            per_page=per_page
        )
        
        return history
        
    except Exception as e:
        logger.error(f"Get reading history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get reading history"
        )


@router.get(
    "/dashboard",
    summary="Get user content dashboard",
    description="Get user's content dashboard with statistics and recent activity"
)
async def get_content_dashboard(
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
) -> Any:
    """
    Get user's content dashboard with key statistics
    
    Returns:
    - Favorite stories count and recent favorites
    - Rating statistics and recent ratings
    - Reading history summary
    - Content recommendations (placeholder)
    """
    try:
        # Get recent favorites (last 5)
        recent_favorites = await content_service.get_user_favorites(
            user_id=str(current_user.id),
            page=1,
            per_page=5
        )
        
        # Get recent ratings (last 5)
        recent_ratings = await content_service.get_user_ratings(
            user_id=str(current_user.id),
            page=1,
            per_page=5
        )
        
        # Get recent reading history (last 5)
        recent_history = await content_service.get_reading_history(
            user_id=str(current_user.id),
            page=1,
            per_page=5
        )
        
        dashboard = {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "summary": {
                "total_favorites": recent_favorites["pagination"]["total_count"],
                "total_ratings": recent_ratings["pagination"]["total_count"],
                "total_reading_sessions": recent_history["pagination"]["total_count"]
            },
            "recent_activity": {
                "favorites": recent_favorites["favorites"],
                "ratings": recent_ratings["ratings"],
                "reading_history": recent_history["reading_history"]
            },
            "preferences": {
                "favorite_genres": [],  # Placeholder for genre analysis
                "average_rating": 0.0,  # Placeholder for rating analysis
                "reading_patterns": {}  # Placeholder for reading pattern analysis
            },
            "generated_at": datetime.now().isoformat()
        }
        
        # Calculate average rating if ratings exist
        if recent_ratings["ratings"]:
            total_rating = sum(r["rating"] for r in recent_ratings["ratings"])
            dashboard["preferences"]["average_rating"] = round(
                total_rating / len(recent_ratings["ratings"]), 1
            )
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Get content dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get content dashboard"
        )


@router.get(
    "/health",
    summary="Content service health",
    description="Check content service health and capabilities"
)
async def content_health() -> Any:
    """
    Check content service health and capabilities
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "story_details": True,
                "user_favorites": True,
                "story_ratings": True,
                "reading_history": True,
                "content_dashboard": True
            },
            "features": {
                "bookmark_management": True,
                "rating_system": True,
                "reading_tracking": True,
                "user_preferences": True,
                "content_analytics": True
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Content health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
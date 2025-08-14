"""
Analytics API endpoints for user behavior tracking and insights
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
from backend.app.core.auth import get_current_user, get_current_user_optional
from backend.app.core.analytics import AnalyticsService, get_analytics_service
from backend.app.core.schemas import EventTrackingRequest, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post(
    "/events",
    response_model=MessageResponse,
    summary="Track user event",
    description="Track user behavior event for analytics"
)
async def track_event(
    event_request: EventTrackingRequest,
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Track a user behavior event
    
    - **event_type**: Type of event (story_viewed, search_performed, story_rated, story_favorited)
    - **event_data**: Event-specific data (story_id, rating, etc.)
    - **timestamp**: Optional event timestamp (defaults to current time)
    """
    try:
        success = await analytics_service.track_user_event(
            user_id=str(current_user.id),
            event_type=event_request.event_type,
            event_data=event_request.event_data,
            timestamp=event_request.timestamp
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to track event"
            )
        
        return MessageResponse(
            message=f"Event '{event_request.event_type}' tracked successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Event tracking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event tracking failed"
        )


@router.get(
    "/user",
    summary="Get user analytics",
    description="Get comprehensive analytics for the current user"
)
async def get_user_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Get comprehensive analytics for the current authenticated user
    
    - **days**: Number of days to analyze (default: 30, max: 365)
    
    Returns analytics including:
    - Search behavior and patterns
    - Reading behavior and completion rates
    - Rating patterns and preferences
    - Favorite stories and trends
    """
    try:
        analytics = await analytics_service.get_user_analytics(
            user_id=str(current_user.id),
            days=days
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"User analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user analytics"
        )


@router.get(
    "/user/{user_id}",
    summary="Get user analytics by ID",
    description="Get analytics for a specific user (admin only placeholder)"
)
async def get_user_analytics_by_id(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Get analytics for a specific user (placeholder for admin functionality)
    
    Note: In a production system, this would require admin privileges
    """
    try:
        # For now, users can only view their own analytics
        if str(current_user.id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view your own analytics"
            )
        
        analytics = await analytics_service.get_user_analytics(
            user_id=user_id,
            days=days
        )
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User analytics by ID error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user analytics"
        )


@router.get(
    "/system",
    summary="Get system analytics",
    description="Get system-wide analytics and metrics"
)
async def get_system_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Get system-wide analytics and metrics
    
    - **days**: Number of days to analyze (default: 7, max: 90)
    
    Returns system analytics including:
    - Total and active user counts
    - Content statistics (stories, searches)
    - System performance metrics
    - Usage trends
    """
    try:
        analytics = await analytics_service.get_system_analytics(days=days)
        
        # Remove sensitive metrics for non-authenticated users
        if not current_user:
            analytics.pop("system_metrics", None)
        
        return analytics
        
    except Exception as e:
        logger.error(f"System analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system analytics"
        )


@router.post(
    "/events/story-view",
    response_model=MessageResponse,
    summary="Track story view",
    description="Track when a user views a story"
)
async def track_story_view(
    story_id: str,
    reading_duration: int = Query(0, ge=0, description="Reading duration in seconds"),
    completed_reading: bool = Query(False, description="Whether user completed reading"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Track story view event with reading behavior
    
    - **story_id**: ID of the story being viewed
    - **reading_duration**: Time spent reading in seconds
    - **completed_reading**: Whether the user finished reading the story
    """
    try:
        success = await analytics_service.track_user_event(
            user_id=str(current_user.id),
            event_type="story_viewed",
            event_data={
                "story_id": story_id,
                "reading_duration": reading_duration,
                "completed_reading": completed_reading
            }
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to track story view"
            )
        
        return MessageResponse(
            message="Story view tracked successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Story view tracking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Story view tracking failed"
        )


@router.post(
    "/events/story-rating",
    response_model=MessageResponse,
    summary="Track story rating",
    description="Track when a user rates a story"
)
async def track_story_rating(
    story_id: str,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1 to 5"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Track story rating event
    
    - **story_id**: ID of the story being rated
    - **rating**: Rating value (1-5 stars)
    """
    try:
        success = await analytics_service.track_user_event(
            user_id=str(current_user.id),
            event_type="story_rated",
            event_data={
                "story_id": story_id,
                "rating": rating
            }
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to track story rating"
            )
        
        return MessageResponse(
            message="Story rating tracked successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Story rating tracking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Story rating tracking failed"
        )


@router.post(
    "/events/story-favorite",
    response_model=MessageResponse,
    summary="Track story favorite",
    description="Track when a user favorites/unfavorites a story"
)
async def track_story_favorite(
    story_id: str,
    is_favorite: bool = Query(True, description="Whether story is being favorited or unfavorited"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Track story favorite/unfavorite event
    
    - **story_id**: ID of the story being favorited
    - **is_favorite**: True for favorite, False for unfavorite
    """
    try:
        success = await analytics_service.track_user_event(
            user_id=str(current_user.id),
            event_type="story_favorited",
            event_data={
                "story_id": story_id,
                "is_favorite": is_favorite
            }
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to track story favorite"
            )
        
        action = "favorited" if is_favorite else "unfavorited"
        return MessageResponse(
            message=f"Story {action} successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Story favorite tracking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Story favorite tracking failed"
        )


@router.get(
    "/dashboard",
    summary="Get analytics dashboard",
    description="Get user analytics dashboard with key metrics"
)
async def get_analytics_dashboard(
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Get analytics dashboard with key user metrics
    
    Returns a simplified dashboard view with:
    - Recent activity summary
    - Key performance indicators
    - Trending insights
    """
    try:
        # Get analytics for different time periods
        analytics_7d = await analytics_service.get_user_analytics(
            user_id=str(current_user.id),
            days=7
        )
        analytics_30d = await analytics_service.get_user_analytics(
            user_id=str(current_user.id),
            days=30
        )
        
        # Extract key metrics for dashboard
        dashboard = {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "recent_activity": {
                "last_7_days": {
                    "searches": analytics_7d.get("search_analytics", {}).get("total_searches", 0),
                    "stories_viewed": analytics_7d.get("reading_analytics", {}).get("total_stories_viewed", 0),
                    "reading_time_minutes": round(
                        analytics_7d.get("reading_analytics", {}).get("total_reading_time_seconds", 0) / 60, 1
                    )
                },
                "last_30_days": {
                    "searches": analytics_30d.get("search_analytics", {}).get("total_searches", 0),
                    "stories_viewed": analytics_30d.get("reading_analytics", {}).get("total_stories_viewed", 0),
                    "reading_time_minutes": round(
                        analytics_30d.get("reading_analytics", {}).get("total_reading_time_seconds", 0) / 60, 1
                    )
                }
            },
            "preferences": {
                "completion_rate": analytics_30d.get("reading_analytics", {}).get("completion_rate_percentage", 0),
                "average_rating": analytics_30d.get("rating_analytics", {}).get("average_rating", 0),
                "total_favorites": analytics_30d.get("favorite_analytics", {}).get("total_favorites", 0)
            },
            "generated_at": datetime.now().isoformat()
        }
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Analytics dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics dashboard"
        )


@router.get(
    "/health",
    summary="Analytics service health",
    description="Check analytics service health and capabilities"
)
async def analytics_health(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Any:
    """
    Check analytics service health and capabilities
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "event_tracking": True,
                "user_analytics": True,
                "system_analytics": True,
                "dashboard_generation": True
            },
            "metrics_collector": {
                "available": analytics_service.metrics_collector is not None
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Analytics health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
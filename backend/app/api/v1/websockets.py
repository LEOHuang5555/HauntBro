"""
WebSocket API endpoints and management
"""

import sys
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from backend.app.core.auth import get_current_user
from backend.app.websocket.manager import websocket_manager
from backend.app.websocket.endpoints import (
    send_user_notification, 
    broadcast_system_message,
    notify_story_recommendation,
    notify_search_result_update
)
from backend.app.core.schemas import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/websocket", tags=["WebSocket"])


@router.get(
    "/status",
    summary="WebSocket service status",
    description="Get WebSocket service status and connection statistics"
)
async def websocket_status() -> Any:
    """
    Get WebSocket service status and statistics
    """
    try:
        stats = websocket_manager.get_connection_stats()
        connected_users = websocket_manager.get_connected_users()
        
        return {
            "status": "active" if websocket_manager.redis_client else "inactive",
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "connected_users_sample": connected_users[:5],  # Show first 5 users
            "redis_available": websocket_manager.redis_client is not None
        }
        
    except Exception as e:
        logger.error(f"WebSocket status error: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get(
    "/connections",
    summary="Get active connections",
    description="Get list of active WebSocket connections (admin only placeholder)"
)
async def get_active_connections(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get list of active WebSocket connections
    
    Note: In production, this would require admin privileges
    """
    try:
        # For now, users can only see their own connections
        user_connections = websocket_manager.connections.get(str(current_user.id), {})
        
        connections = [
            {
                "connection_id": conn_id,
                "connected_at": conn.connected_at.isoformat(),
                "last_heartbeat": conn.last_heartbeat.isoformat(),
                "is_alive": conn.is_alive
            }
            for conn_id, conn in user_connections.items()
        ]
        
        return {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "connections": connections,
            "connection_count": len(connections)
        }
        
    except Exception as e:
        logger.error(f"Get connections error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get connections"
        )


@router.post(
    "/notify/user/{user_id}",
    response_model=MessageResponse,
    summary="Send notification to user",
    description="Send notification to a specific user via WebSocket"
)
async def send_notification_to_user(
    user_id: str,
    notification_type: str = Query(..., description="Notification type (info, warning, success, error)"),
    title: str = Query(..., description="Notification title"),
    content: str = Query(..., description="Notification content"),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Send notification to a specific user
    
    Note: In production, this would require appropriate permissions
    """
    try:
        # For now, users can only send notifications to themselves
        if str(current_user.id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only send notifications to yourself"
            )
        
        await send_user_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            content=content
        )
        
        return MessageResponse(
            message=f"Notification sent to user {user_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send notification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )


@router.post(
    "/notify/story-recommendation",
    response_model=MessageResponse,
    summary="Send story recommendation",
    description="Send story recommendation notification to user"
)
async def send_story_recommendation(
    story_id: str = Query(..., description="Story ID to recommend"),
    story_title: str = Query(..., description="Story title"),
    story_author: str = Query(None, description="Story author"),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Send story recommendation notification to current user
    """
    try:
        story_data = {
            "id": story_id,
            "title": story_title,
            "author": story_author,
            "recommended_at": datetime.now().isoformat()
        }
        
        await notify_story_recommendation(
            user_id=str(current_user.id),
            story_data=story_data
        )
        
        return MessageResponse(
            message="Story recommendation sent"
        )
        
    except Exception as e:
        logger.error(f"Story recommendation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send story recommendation"
        )


@router.post(
    "/notify/search-update",
    response_model=MessageResponse,
    summary="Send search update notification",
    description="Notify user about new search results"
)
async def send_search_update_notification(
    query: str = Query(..., description="Search query"),
    new_results_count: int = Query(..., ge=0, description="Number of new results"),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Send search result update notification to current user
    """
    try:
        await notify_search_result_update(
            user_id=str(current_user.id),
            query=query,
            new_results_count=new_results_count
        )
        
        return MessageResponse(
            message="Search update notification sent"
        )
        
    except Exception as e:
        logger.error(f"Search update notification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send search update notification"
        )


@router.post(
    "/broadcast",
    response_model=MessageResponse,
    summary="Broadcast system message",
    description="Broadcast system message to all connected users (admin only placeholder)"
)
async def broadcast_message(
    message_type: str = Query(..., description="Message type"),
    title: str = Query(..., description="Message title"),
    content: str = Query(..., description="Message content"),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Broadcast system message to all connected users
    
    Note: In production, this would require admin privileges
    """
    try:
        # Placeholder for admin check
        # In production: if not current_user.is_admin: raise HTTPException(403)
        
        await broadcast_system_message(
            message_type=message_type,
            title=title,
            content=content
        )
        
        return MessageResponse(
            message="System message broadcasted"
        )
        
    except Exception as e:
        logger.error(f"Broadcast message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast message"
        )


@router.get(
    "/health",
    summary="WebSocket health check",
    description="Check WebSocket service health and capabilities"
)
async def websocket_health() -> Any:
    """
    Check WebSocket service health and capabilities
    """
    try:
        # Check Redis connection
        redis_healthy = websocket_manager.redis_client is not None
        if redis_healthy and websocket_manager.redis_client:
            try:
                await websocket_manager.redis_client.ping()
            except:
                redis_healthy = False
        
        stats = websocket_manager.get_connection_stats()
        
        health_status = {
            "status": "healthy" if redis_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "redis": "healthy" if redis_healthy else "unhealthy",
                "websocket_manager": "healthy",
                "message_delivery": "healthy" if redis_healthy else "degraded"
            },
            "statistics": stats,
            "capabilities": {
                "real_time_messaging": True,
                "persistent_messaging": redis_healthy,
                "user_notifications": True,
                "system_broadcasts": True,
                "connection_management": True
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"WebSocket health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
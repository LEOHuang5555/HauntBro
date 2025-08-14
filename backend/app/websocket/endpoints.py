"""
WebSocket endpoints with JWT authentication
"""

import sys
from pathlib import Path
import uuid
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status, Query, Depends
from sqlalchemy.orm import Session

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.app.websocket.manager import websocket_manager
from backend.app.core.security import security_service
from backend.app.core.auth import AuthService
from infrastructure.database.connection import get_db
from infrastructure.database.models import User

logger = logging.getLogger(__name__)


async def authenticate_websocket(
    token: str,
    db: Session
) -> Optional[User]:
    """
    Authenticate WebSocket connection using JWT token
    
    Args:
        token: JWT token
        db: Database session
    
    Returns:
        Authenticated user or None
    """
    try:
        # Verify JWT token
        payload = security_service.verify_token(token, expected_type="access_token")
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        # Get user from database
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        
        if not user or not user.is_active:
            return None
        
        return user
        
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        return None


async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token"),
    db: Session = Depends(get_db)
):
    """
    Main WebSocket endpoint with JWT authentication
    
    Args:
        websocket: WebSocket connection
        token: JWT access token for authentication
    """
    connection_id = str(uuid.uuid4())
    user = None
    
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
            return
        
        user = await authenticate_websocket(token, db)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
        
        # Initialize WebSocket manager if needed
        if not websocket_manager.redis_client:
            initialized = await websocket_manager.initialize()
            if not initialized:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Service unavailable")
                return
        
        # Connect user
        success = await websocket_manager.connect(
            websocket=websocket,
            user_id=str(user.id),
            connection_id=connection_id
        )
        
        if not success:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Connection failed")
            return
        
        logger.info(f"WebSocket authenticated: user {user.username} ({connection_id})")
        
        # Keep connection alive (handled by manager)
        while True:
            try:
                # The connection lifecycle is handled by WebSocketManager
                # This loop just keeps the endpoint alive
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal error")
        except:
            pass
    finally:
        # Clean up connection
        if user:
            await websocket_manager.disconnect(str(user.id), connection_id)


async def websocket_test_endpoint(websocket: WebSocket):
    """
    Test WebSocket endpoint without authentication (for development/testing)
    """
    connection_id = str(uuid.uuid4())
    
    try:
        await websocket.accept()
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "message": "Test WebSocket connection established",
            "connection_id": connection_id
        })
        
        # Echo messages back
        while True:
            try:
                data = await websocket.receive_text()
                await websocket.send_json({
                    "type": "echo",
                    "message": f"Echo: {data}",
                    "connection_id": connection_id
                })
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logger.info(f"Test WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Test WebSocket error: {e}")


# Notification helper functions
async def send_user_notification(
    user_id: str,
    notification_type: str,
    title: str,
    content: str,
    data: Optional[dict] = None
):
    """
    Send notification to a specific user
    
    Args:
        user_id: Target user ID
        notification_type: Type of notification (info, warning, success, error)
        title: Notification title
        content: Notification content
        data: Additional data
    """
    try:
        await websocket_manager.send_system_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            content=content,
            data=data
        )
        logger.info(f"Notification sent to user {user_id}: {title}")
        
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {e}")


async def broadcast_system_message(
    message_type: str,
    title: str,
    content: str,
    user_ids: Optional[list] = None
):
    """
    Broadcast system message to users
    
    Args:
        message_type: Type of message
        title: Message title
        content: Message content
        user_ids: List of user IDs (None for all connected users)
    """
    try:
        message = {
            "type": "system_message",
            "message_type": message_type,
            "title": title,
            "content": content
        }
        
        await websocket_manager.broadcast(message, user_ids)
        logger.info(f"System message broadcasted: {title}")
        
    except Exception as e:
        logger.error(f"Failed to broadcast system message: {e}")


async def notify_story_recommendation(user_id: str, story_data: dict):
    """Send story recommendation notification"""
    await send_user_notification(
        user_id=user_id,
        notification_type="recommendation",
        title="New Story Recommendation",
        content=f"We found a story you might like: {story_data.get('title', 'Untitled')}",
        data=story_data
    )


async def notify_search_result_update(user_id: str, query: str, new_results_count: int):
    """Send search result update notification"""
    await send_user_notification(
        user_id=user_id,
        notification_type="search_update",
        title="Search Results Updated",
        content=f"Found {new_results_count} new results for '{query}'",
        data={"query": query, "new_results_count": new_results_count}
    )
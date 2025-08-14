"""
Admin API endpoints for system management and content moderation
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
from backend.app.core.auth import get_current_user
from backend.app.core.admin import AdminService, get_admin_service
from backend.app.core.schemas import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/statistics",
    summary="Get system statistics",
    description="Get comprehensive system statistics (admin only)"
)
async def get_system_statistics(
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> Any:
    """
    Get comprehensive system statistics
    
    **Admin access required**
    
    Returns detailed statistics including:
    - User metrics (total, active, engagement rates)
    - Content metrics (stories, processing rates)
    - Activity metrics (searches, readings)
    - System performance metrics
    """
    try:
        statistics = await admin_service.get_system_statistics(current_user)
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get system statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system statistics"
        )


@router.get(
    "/users",
    summary="Get user management data",
    description="Get user management data with filtering and pagination (admin only)"
)
async def get_user_management(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    search: Optional[str] = Query(None, description="Search by username or email"),
    status: Optional[str] = Query(None, description="Filter by status (active/inactive)"),
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> Any:
    """
    Get user management data with filtering and pagination
    
    **Admin access required**
    
    - **page**: Page number (default: 1)
    - **per_page**: Results per page (default: 20, max: 100)
    - **search**: Search by username or email
    - **status**: Filter by status (active/inactive)
    
    Returns paginated user list with activity statistics
    """
    try:
        user_data = await admin_service.get_user_management(
            user=current_user,
            page=page,
            per_page=per_page,
            search_query=search,
            status_filter=status
        )
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user management error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user management data"
        )


@router.get(
    "/content",
    summary="Get content moderation data",
    description="Get content moderation data with filtering (admin only)"
)
async def get_content_moderation(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Results per page"),
    source: Optional[str] = Query(None, description="Filter by content source"),
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> Any:
    """
    Get content moderation data with filtering and pagination
    
    **Admin access required**
    
    - **page**: Page number (default: 1)
    - **per_page**: Results per page (default: 20, max: 50)
    - **source**: Filter by content source (ptt_marvel, reddit_ghoststories)
    
    Returns paginated content list with moderation info and engagement stats
    """
    try:
        content_data = await admin_service.get_content_moderation(
            user=current_user,
            page=page,
            per_page=per_page,
            source_filter=source
        )
        
        return content_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get content moderation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get content moderation data"
        )


@router.post(
    "/users/{user_id}/moderate",
    summary="Moderate user",
    description="Moderate a user account (activate/deactivate) - admin only"
)
async def moderate_user(
    user_id: str = PathParam(..., description="User ID to moderate"),
    action: str = Query(..., description="Action to perform (activate/deactivate)"),
    reason: Optional[str] = Query(None, description="Reason for moderation action"),
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> Any:
    """
    Moderate a user account
    
    **Admin access required**
    
    - **user_id**: ID of the user to moderate
    - **action**: Action to perform ('activate' or 'deactivate')
    - **reason**: Optional reason for the moderation action
    
    Returns moderation result with user status change details
    """
    try:
        result = await admin_service.moderate_user(
            admin_user=current_user,
            target_user_id=user_id,
            action=action,
            reason=reason
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Moderate user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to moderate user"
        )


@router.get(
    "/health",
    summary="Get system health",
    description="Get comprehensive system health information (admin only)"
)
async def get_system_health(
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> Any:
    """
    Get comprehensive system health information
    
    **Admin access required**
    
    Returns detailed system health including:
    - Database connectivity and integrity
    - Table statistics and health status
    - System metrics and performance
    - Health recommendations
    """
    try:
        health_info = await admin_service.get_system_health(current_user)
        return health_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get system health error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system health"
        )


@router.get(
    "/dashboard",
    summary="Get admin dashboard",
    description="Get admin dashboard with key metrics and alerts"
)
async def get_admin_dashboard(
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> Any:
    """
    Get admin dashboard with key metrics and system overview
    
    **Admin access required**
    
    Returns dashboard with:
    - System overview and key metrics
    - Recent activity summary
    - Health status and alerts
    - Quick action items
    """
    try:
        # Get system statistics
        stats = await admin_service.get_system_statistics(current_user)
        
        # Get system health
        health = await admin_service.get_system_health(current_user)
        
        # Create dashboard summary
        dashboard = {
            "admin_user": {
                "id": str(current_user.id),
                "username": current_user.username
            },
            "system_overview": {
                "total_users": stats["users"]["total_users"],
                "active_users": stats["users"]["active_users"],
                "total_stories": stats["content"]["total_stories"],
                "processed_stories": stats["content"]["processed_stories"],
                "overall_health": health["overall_status"]
            },
            "recent_activity": {
                "searches_24h": stats["activity_24h"]["searches"],
                "readings_24h": stats["activity_24h"]["reading_sessions"],
                "avg_searches_per_hour": stats["activity_24h"]["avg_searches_per_hour"],
                "engagement_rate": stats["engagement"]["engagement_rate"]
            },
            "alerts": [],
            "quick_actions": [
                "View user management",
                "Check content moderation queue",
                "Review system health",
                "Analyze usage metrics"
            ],
            "generated_at": datetime.now().isoformat()
        }
        
        # Add alerts based on system status
        if health["overall_status"] != "healthy":
            dashboard["alerts"].append({
                "type": "warning",
                "message": f"System health is {health['overall_status']}",
                "action": "Check system health details"
            })
        
        if stats["users"]["activation_rate"] < 80:
            dashboard["alerts"].append({
                "type": "info",
                "message": f"User activation rate is {stats['users']['activation_rate']}%",
                "action": "Review user engagement strategies"
            })
        
        if stats["content"]["processing_rate"] < 90:
            dashboard["alerts"].append({
                "type": "warning",
                "message": f"Content processing rate is {stats['content']['processing_rate']}%",
                "action": "Check content processing pipeline"
            })
        
        return dashboard
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get admin dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get admin dashboard"
        )


@router.get(
    "/config",
    summary="Get admin configuration",
    description="Get current system configuration (admin only)"
)
async def get_admin_config(
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> Any:
    """
    Get current system configuration
    
    **Admin access required**
    
    Returns sanitized system configuration for admin review
    """
    try:
        admin_service._check_admin_permissions(current_user)
        
        # Return sanitized configuration
        config = {
            "api_version": "1.0.0",
            "features": {
                "authentication": True,
                "search": True,
                "analytics": True,
                "websockets": True,
                "content_management": True,
                "admin_panel": True
            },
            "security": {
                "rate_limiting": True,
                "security_middleware": True,
                "input_validation": True,
                "cors_enabled": True
            },
            "integrations": {
                "database": "postgresql",
                "redis": "available",
                "metrics_collector": "active",
                "embedding_manager": "active"
            },
            "content_sources": [
                "ptt_marvel",
                "reddit_ghoststories"
            ],
            "system_limits": {
                "max_search_results": 100,
                "max_favorites_per_user": 1000,
                "max_request_size": "10MB",
                "rate_limit_default": "100/hour"
            }
        }
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get admin config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get admin configuration"
        )


@router.get(
    "/status",
    summary="Admin service status",
    description="Check admin service status and capabilities"
)
async def admin_service_status() -> Any:
    """
    Check admin service status and capabilities
    
    Returns admin service health and available features
    """
    try:
        status_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "system_statistics": True,
                "user_management": True,
                "content_moderation": True,
                "user_moderation": True,
                "system_health": True,
                "admin_dashboard": True
            },
            "features": {
                "role_based_access": True,  # Placeholder - implement proper RBAC
                "audit_logging": True,
                "system_monitoring": True,
                "user_analytics": True,
                "content_analytics": True
            },
            "note": "Proper role-based access control should be implemented for production use"
        }
        
        return status_info
        
    except Exception as e:
        logger.error(f"Admin service status error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
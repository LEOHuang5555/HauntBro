"""
Admin service for system management and content moderation
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc, text
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.models import (
    User, BronzeStory, SilverStory, SearchInteraction, UserReadingBehavior,
    UserFavorite, StoryRating, SilverStoryChunks, GoldLayerMetrics
)
from monitoring.metrics_dashboard import MetricsCollector
from fastapi import Depends, HTTPException, status
from infrastructure.database.connection import get_db

logger = logging.getLogger(__name__)


class AdminService:
    """
    Admin service for system management and content moderation
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.metrics_collector = MetricsCollector()
    
    def _check_admin_permissions(self, user: User):
        """Check if user has admin permissions (placeholder)"""
        # In production, you would check user.role or user.is_admin
        # For now, we'll allow all authenticated users for demo purposes
        # This should be replaced with proper role-based access control
        
        # Placeholder admin check - in production, implement proper RBAC
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account not active"
            )
        
        # TODO: Implement proper admin role checking
        # if not user.is_admin:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admin privileges required"
        #     )
    
    async def get_system_statistics(self, user: User) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        try:
            self._check_admin_permissions(user)
            
            # User statistics
            total_users = self.db.execute(select(func.count(User.id))).scalar() or 0
            active_users = self.db.execute(
                select(func.count(User.id)).where(User.is_active == True)
            ).scalar() or 0
            
            # Content statistics
            total_stories = self.db.execute(select(func.count(BronzeStory.id))).scalar() or 0
            processed_stories = self.db.execute(select(func.count(SilverStory.id))).scalar() or 0
            total_chunks = self.db.execute(select(func.count(SilverStoryChunks.id))).scalar() or 0
            
            # Activity statistics (last 24 hours)
            since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            
            recent_searches = self.db.execute(
                select(func.count(SearchInteraction.id))
                .where(SearchInteraction.search_timestamp >= since_24h)
            ).scalar() or 0
            
            recent_readings = self.db.execute(
                select(func.count(UserReadingBehavior.id))
                .where(UserReadingBehavior.reading_start_time >= since_24h)
            ).scalar() or 0
            
            # Content engagement
            total_favorites = self.db.execute(select(func.count(UserFavorite.id))).scalar() or 0
            total_ratings = self.db.execute(select(func.count(StoryRating.id))).scalar() or 0
            avg_rating = self.db.execute(select(func.avg(StoryRating.rating))).scalar() or 0
            
            # Get current metrics from collector
            current_metrics = self.metrics_collector.get_all_current_metrics()
            
            statistics = {
                "users": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "inactive_users": total_users - active_users,
                    "activation_rate": round((active_users / total_users * 100) if total_users > 0 else 0, 2)
                },
                "content": {
                    "total_stories": total_stories,
                    "processed_stories": processed_stories,
                    "processing_rate": round((processed_stories / total_stories * 100) if total_stories > 0 else 0, 2),
                    "total_chunks": total_chunks,
                    "avg_chunks_per_story": round((total_chunks / processed_stories) if processed_stories > 0 else 0, 2)
                },
                "activity_24h": {
                    "searches": recent_searches,
                    "reading_sessions": recent_readings,
                    "avg_searches_per_hour": round(recent_searches / 24, 2),
                    "avg_readings_per_hour": round(recent_readings / 24, 2)
                },
                "engagement": {
                    "total_favorites": total_favorites,
                    "total_ratings": total_ratings,
                    "average_rating": round(float(avg_rating), 2) if avg_rating else 0,
                    "engagement_rate": round((total_favorites / total_users * 100) if total_users > 0 else 0, 2)
                },
                "system_metrics": current_metrics,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return statistics
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get system statistics"
            )
    
    async def get_user_management(
        self, 
        user: User, 
        page: int = 1, 
        per_page: int = 20,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user management data with filtering and pagination"""
        try:
            self._check_admin_permissions(user)
            
            offset = (page - 1) * per_page
            
            # Build query
            query = select(User)
            
            # Apply filters
            if search_query:
                query = query.where(
                    or_(
                        User.username.ilike(f"%{search_query}%"),
                        User.email.ilike(f"%{search_query}%")
                    )
                )
            
            if status_filter == "active":
                query = query.where(User.is_active == True)
            elif status_filter == "inactive":
                query = query.where(User.is_active == False)
            
            # Get users with pagination
            users_query = query.order_by(desc(User.created_at)).offset(offset).limit(per_page)
            users = self.db.execute(users_query).scalars().all()
            
            # Get total count
            count_query = select(func.count(User.id))
            if search_query:
                count_query = count_query.where(
                    or_(
                        User.username.ilike(f"%{search_query}%"),
                        User.email.ilike(f"%{search_query}%")
                    )
                )
            if status_filter == "active":
                count_query = count_query.where(User.is_active == True)
            elif status_filter == "inactive":
                count_query = count_query.where(User.is_active == False)
            
            total_count = self.db.execute(count_query).scalar() or 0
            
            # Format user data
            user_list = []
            for u in users:
                # Get user activity stats
                searches_count = self.db.execute(
                    select(func.count(SearchInteraction.id))
                    .where(SearchInteraction.user_id == u.id)
                ).scalar() or 0
                
                favorites_count = self.db.execute(
                    select(func.count(UserFavorite.id))
                    .where(UserFavorite.user_id == u.id)
                ).scalar() or 0
                
                user_list.append({
                    "id": str(u.id),
                    "username": u.username,
                    "email": u.email,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat(),
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "activity_stats": {
                        "total_searches": searches_count,
                        "total_favorites": favorites_count
                    }
                })
            
            return {
                "users": user_list,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": (total_count + per_page - 1) // per_page
                },
                "filters": {
                    "search_query": search_query,
                    "status_filter": status_filter
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user management data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user management data"
            )
    
    async def get_content_moderation(
        self, 
        user: User, 
        page: int = 1, 
        per_page: int = 20,
        source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get content moderation data"""
        try:
            self._check_admin_permissions(user)
            
            offset = (page - 1) * per_page
            
            # Build query for stories
            query = select(BronzeStory, SilverStory).join(
                SilverStory, BronzeStory.id == SilverStory.bronze_story_id, isouter=True
            )
            
            # Apply source filter
            if source_filter:
                query = query.where(BronzeStory.source == source_filter)
            
            # Get stories with pagination
            stories_query = query.order_by(desc(BronzeStory.scraped_at)).offset(offset).limit(per_page)
            results = self.db.execute(stories_query).all()
            
            # Get total count
            count_query = select(func.count(BronzeStory.id))
            if source_filter:
                count_query = count_query.where(BronzeStory.source == source_filter)
            
            total_count = self.db.execute(count_query).scalar() or 0
            
            # Format story data
            stories = []
            for bronze_story, silver_story in results:
                # Get engagement stats
                favorites_count = self.db.execute(
                    select(func.count(UserFavorite.id))
                    .where(UserFavorite.story_id == bronze_story.id)
                ).scalar() or 0
                
                ratings_count = self.db.execute(
                    select(func.count(StoryRating.id))
                    .where(StoryRating.story_id == bronze_story.id)
                ).scalar() or 0
                
                avg_rating = self.db.execute(
                    select(func.avg(StoryRating.rating))
                    .where(StoryRating.story_id == bronze_story.id)
                ).scalar() or 0
                
                stories.append({
                    "id": str(bronze_story.id),
                    "title": bronze_story.title,
                    "author": bronze_story.author,
                    "source": bronze_story.source,
                    "source_url": bronze_story.source_url,
                    "post_date": bronze_story.post_date.isoformat() if bronze_story.post_date else None,
                    "scraped_at": bronze_story.scraped_at.isoformat() if bronze_story.scraped_at else None,
                    "content_length": len(bronze_story.content) if bronze_story.content else 0,
                    "processed": silver_story is not None,
                    "processing_info": {
                        "word_count": silver_story.word_count if silver_story else None,
                        "language_detected": silver_story.language_detected if silver_story else None,
                        "tags": silver_story.tags if silver_story else []
                    } if silver_story else None,
                    "engagement_stats": {
                        "favorites_count": favorites_count,
                        "ratings_count": ratings_count,
                        "average_rating": round(float(avg_rating), 2) if avg_rating else 0
                    }
                })
            
            return {
                "stories": stories,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": (total_count + per_page - 1) // per_page
                },
                "filters": {
                    "source_filter": source_filter
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting content moderation data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get content moderation data"
            )
    
    async def moderate_user(
        self, 
        admin_user: User, 
        target_user_id: str, 
        action: str, 
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Moderate a user (activate/deactivate)"""
        try:
            self._check_admin_permissions(admin_user)
            
            # Get target user
            target_user = self.db.execute(
                select(User).where(User.id == target_user_id)
            ).scalar_one_or_none()
            
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Prevent self-moderation
            if str(target_user.id) == str(admin_user.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot moderate yourself"
                )
            
            old_status = target_user.is_active
            
            if action == "activate":
                target_user.is_active = True
                action_performed = "activated"
            elif action == "deactivate":
                target_user.is_active = False
                action_performed = "deactivated"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid action. Use 'activate' or 'deactivate'"
                )
            
            target_user.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(
                f"User {target_user.username} {action_performed} by admin {admin_user.username}. "
                f"Reason: {reason or 'No reason provided'}"
            )
            
            return {
                "action": action_performed,
                "target_user": {
                    "id": str(target_user.id),
                    "username": target_user.username,
                    "email": target_user.email,
                    "previous_status": old_status,
                    "current_status": target_user.is_active
                },
                "admin_user": {
                    "id": str(admin_user.id),
                    "username": admin_user.username
                },
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error moderating user: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to moderate user"
            )
    
    async def get_system_health(self, user: User) -> Dict[str, Any]:
        """Get comprehensive system health information"""
        try:
            self._check_admin_permissions(user)
            
            # Database health
            db_healthy = True
            try:
                self.db.execute(text("SELECT 1"))
            except Exception:
                db_healthy = False
            
            # Check table counts and basic integrity
            table_stats = {}
            tables = [
                ("users", User),
                ("bronze_stories", BronzeStory),
                ("silver_stories", SilverStory),
                ("search_interactions", SearchInteraction),
                ("user_favorites", UserFavorite),
                ("story_ratings", StoryRating)
            ]
            
            for table_name, model in tables:
                try:
                    count = self.db.execute(select(func.count(model.id))).scalar() or 0
                    table_stats[table_name] = {
                        "count": count,
                        "status": "healthy"
                    }
                except Exception as e:
                    table_stats[table_name] = {
                        "count": 0,
                        "status": "error",
                        "error": str(e)
                    }
            
            # System metrics
            current_metrics = self.metrics_collector.get_all_current_metrics()
            
            # Determine overall health
            unhealthy_tables = sum(1 for stats in table_stats.values() if stats["status"] != "healthy")
            overall_status = "healthy" if db_healthy and unhealthy_tables == 0 else "degraded" if unhealthy_tables < 3 else "critical"
            
            health_info = {
                "overall_status": overall_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "database": "healthy" if db_healthy else "unhealthy",
                    "tables": table_stats,
                    "metrics_collector": "healthy" if current_metrics else "unhealthy"
                },
                "system_metrics": current_metrics,
                "recommendations": []
            }
            
            # Add recommendations based on health status
            if not db_healthy:
                health_info["recommendations"].append("Database connection issues detected - check connectivity")
            
            if unhealthy_tables > 0:
                health_info["recommendations"].append(f"{unhealthy_tables} tables showing issues - investigate data integrity")
            
            if not current_metrics:
                health_info["recommendations"].append("Metrics collection not working - check monitoring setup")
            
            return health_info
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get system health"
            )


# Dependency to get admin service
def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    """Get admin service instance"""
    return AdminService(db)
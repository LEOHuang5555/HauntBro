"""
Analytics service for user behavior tracking and insights
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.models import (
    User, SearchInteraction, UserReadingBehavior, UserFavorite, 
    StoryRating, BronzeStory, SilverStory
)
from monitoring.metrics_dashboard import MetricsCollector
from fastapi import Depends
from infrastructure.database.connection import get_db

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Analytics service for user behavior tracking and insights
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.metrics_collector = MetricsCollector()
    
    async def track_user_event(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Track user event for analytics
        
        Args:
            user_id: User ID
            event_type: Type of event (search_performed, story_viewed, etc.)
            event_data: Event-specific data
            timestamp: Event timestamp (defaults to now)
        
        Returns:
            Success status
        """
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Record metric in metrics collector
            await self.metrics_collector._record_metric(
                f"user_event_{event_type}", 1.0, timestamp
            )
            
            # Handle specific event types
            if event_type == "story_viewed":
                await self._track_story_view(user_id, event_data, timestamp)
            elif event_type == "search_performed":
                await self._track_search_event(user_id, event_data, timestamp)
            elif event_type == "story_rated":
                await self._track_story_rating(user_id, event_data, timestamp)
            elif event_type == "story_favorited":
                await self._track_story_favorite(user_id, event_data, timestamp)
            
            logger.info(f"Tracked event '{event_type}' for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking user event: {e}")
            return False
    
    async def _track_story_view(
        self, 
        user_id: str, 
        event_data: Dict[str, Any], 
        timestamp: datetime
    ):
        """Track story view event"""
        try:
            story_id = event_data.get("story_id")
            reading_duration = event_data.get("reading_duration", 0)
            completed_reading = event_data.get("completed_reading", False)
            
            if not story_id:
                return
            
            # Create or update reading behavior record
            existing_behavior = self.db.execute(
                select(UserReadingBehavior).where(
                    and_(
                        UserReadingBehavior.user_id == user_id,
                        UserReadingBehavior.story_id == story_id
                    )
                )
            ).scalar_one_or_none()
            
            if existing_behavior:
                # Update existing record
                existing_behavior.reading_duration = reading_duration
                existing_behavior.completed_reading = completed_reading
            else:
                # Create new record
                behavior = UserReadingBehavior(
                    user_id=user_id,
                    story_id=story_id,
                    reading_start_time=timestamp,
                    reading_duration=reading_duration,
                    completed_reading=completed_reading
                )
                self.db.add(behavior)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error tracking story view: {e}")
            self.db.rollback()
    
    async def _track_search_event(
        self, 
        user_id: str, 
        event_data: Dict[str, Any], 
        timestamp: datetime
    ):
        """Track search event"""
        # Search tracking is already handled in the search service
        # This is a placeholder for additional search analytics
        pass
    
    async def _track_story_rating(
        self, 
        user_id: str, 
        event_data: Dict[str, Any], 
        timestamp: datetime
    ):
        """Track story rating event"""
        try:
            story_id = event_data.get("story_id")
            rating = event_data.get("rating")
            
            if not story_id or not rating:
                return
            
            # Check if rating already exists
            existing_rating = self.db.execute(
                select(StoryRating).where(
                    and_(
                        StoryRating.user_id == user_id,
                        StoryRating.story_id == story_id
                    )
                )
            ).scalar_one_or_none()
            
            if existing_rating:
                existing_rating.rating = rating
                existing_rating.updated_at = timestamp
            else:
                rating_record = StoryRating(
                    user_id=user_id,
                    story_id=story_id,
                    rating=rating
                )
                self.db.add(rating_record)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error tracking story rating: {e}")
            self.db.rollback()
    
    async def _track_story_favorite(
        self, 
        user_id: str, 
        event_data: Dict[str, Any], 
        timestamp: datetime
    ):
        """Track story favorite event"""
        try:
            story_id = event_data.get("story_id")
            is_favorite = event_data.get("is_favorite", True)
            
            if not story_id:
                return
            
            existing_favorite = self.db.execute(
                select(UserFavorite).where(
                    and_(
                        UserFavorite.user_id == user_id,
                        UserFavorite.story_id == story_id
                    )
                )
            ).scalar_one_or_none()
            
            if is_favorite and not existing_favorite:
                favorite = UserFavorite(
                    user_id=user_id,
                    story_id=story_id
                )
                self.db.add(favorite)
                self.db.commit()
            elif not is_favorite and existing_favorite:
                self.db.delete(existing_favorite)
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error tracking story favorite: {e}")
            self.db.rollback()
    
    async def get_user_analytics(
        self, 
        user_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a user
        
        Args:
            user_id: User ID
            days: Number of days to analyze
        
        Returns:
            User analytics data
        """
        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Search analytics
            search_stats = await self._get_user_search_stats(user_id, since)
            
            # Reading behavior analytics
            reading_stats = await self._get_user_reading_stats(user_id, since)
            
            # Rating and favorite analytics
            rating_stats = await self._get_user_rating_stats(user_id, since)
            favorite_stats = await self._get_user_favorite_stats(user_id, since)
            
            return {
                "user_id": user_id,
                "period_days": days,
                "search_analytics": search_stats,
                "reading_analytics": reading_stats,
                "rating_analytics": rating_stats,
                "favorite_analytics": favorite_stats,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {
                "user_id": user_id,
                "period_days": days,
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def _get_user_search_stats(
        self, 
        user_id: str, 
        since: datetime
    ) -> Dict[str, Any]:
        """Get user search statistics"""
        try:
            # Total searches
            total_searches = self.db.execute(
                select(func.count(SearchInteraction.id))
                .where(
                    and_(
                        SearchInteraction.user_id == user_id,
                        SearchInteraction.search_timestamp >= since
                    )
                )
            ).scalar() or 0
            
            # Average execution time
            avg_execution_time = self.db.execute(
                select(func.avg(SearchInteraction.execution_time_ms))
                .where(
                    and_(
                        SearchInteraction.user_id == user_id,
                        SearchInteraction.search_timestamp >= since
                    )
                )
            ).scalar() or 0
            
            # Most common search types
            search_type_stats = self.db.execute(
                select(
                    SearchInteraction.search_type,
                    func.count(SearchInteraction.id).label('count')
                )
                .where(
                    and_(
                        SearchInteraction.user_id == user_id,
                        SearchInteraction.search_timestamp >= since
                    )
                )
                .group_by(SearchInteraction.search_type)
                .order_by(desc('count'))
            ).all()
            
            # Top search queries
            top_queries = self.db.execute(
                select(
                    SearchInteraction.query,
                    func.count(SearchInteraction.id).label('count')
                )
                .where(
                    and_(
                        SearchInteraction.user_id == user_id,
                        SearchInteraction.search_timestamp >= since
                    )
                )
                .group_by(SearchInteraction.query)
                .order_by(desc('count'))
                .limit(10)
            ).all()
            
            return {
                "total_searches": total_searches,
                "average_execution_time_ms": float(avg_execution_time) if avg_execution_time else 0,
                "search_types": [
                    {"type": st.search_type, "count": st.count} 
                    for st in search_type_stats
                ],
                "top_queries": [
                    {"query": q.query, "count": q.count} 
                    for q in top_queries
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {"error": str(e)}
    
    async def _get_user_reading_stats(
        self, 
        user_id: str, 
        since: datetime
    ) -> Dict[str, Any]:
        """Get user reading behavior statistics"""
        try:
            # Total stories viewed
            total_stories_viewed = self.db.execute(
                select(func.count(UserReadingBehavior.id))
                .where(
                    and_(
                        UserReadingBehavior.user_id == user_id,
                        UserReadingBehavior.reading_start_time >= since
                    )
                )
            ).scalar() or 0
            
            # Total reading time
            total_reading_time = self.db.execute(
                select(func.sum(UserReadingBehavior.reading_duration))
                .where(
                    and_(
                        UserReadingBehavior.user_id == user_id,
                        UserReadingBehavior.reading_start_time >= since
                    )
                )
            ).scalar() or 0
            
            # Completion rate
            completed_stories = self.db.execute(
                select(func.count(UserReadingBehavior.id))
                .where(
                    and_(
                        UserReadingBehavior.user_id == user_id,
                        UserReadingBehavior.reading_start_time >= since,
                        UserReadingBehavior.completed_reading == True
                    )
                )
            ).scalar() or 0
            
            completion_rate = (
                (completed_stories / total_stories_viewed * 100) 
                if total_stories_viewed > 0 else 0
            )
            
            # Average reading session duration
            avg_session_duration = (
                total_reading_time / total_stories_viewed 
                if total_stories_viewed > 0 else 0
            )
            
            return {
                "total_stories_viewed": total_stories_viewed,
                "total_reading_time_seconds": total_reading_time,
                "completed_stories": completed_stories,
                "completion_rate_percentage": round(completion_rate, 2),
                "average_session_duration_seconds": round(avg_session_duration, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting reading stats: {e}")
            return {"error": str(e)}
    
    async def _get_user_rating_stats(
        self, 
        user_id: str, 
        since: datetime
    ) -> Dict[str, Any]:
        """Get user rating statistics"""
        try:
            # Total ratings given
            total_ratings = self.db.execute(
                select(func.count(StoryRating.id))
                .where(
                    and_(
                        StoryRating.user_id == user_id,
                        StoryRating.created_at >= since
                    )
                )
            ).scalar() or 0
            
            # Average rating given
            avg_rating = self.db.execute(
                select(func.avg(StoryRating.rating))
                .where(
                    and_(
                        StoryRating.user_id == user_id,
                        StoryRating.created_at >= since
                    )
                )
            ).scalar() or 0
            
            # Rating distribution
            rating_distribution = self.db.execute(
                select(
                    StoryRating.rating,
                    func.count(StoryRating.id).label('count')
                )
                .where(
                    and_(
                        StoryRating.user_id == user_id,
                        StoryRating.created_at >= since
                    )
                )
                .group_by(StoryRating.rating)
                .order_by(StoryRating.rating)
            ).all()
            
            return {
                "total_ratings": total_ratings,
                "average_rating": round(float(avg_rating), 2) if avg_rating else 0,
                "rating_distribution": [
                    {"rating": rd.rating, "count": rd.count} 
                    for rd in rating_distribution
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting rating stats: {e}")
            return {"error": str(e)}
    
    async def _get_user_favorite_stats(
        self, 
        user_id: str, 
        since: datetime
    ) -> Dict[str, Any]:
        """Get user favorite statistics"""
        try:
            # Total favorites
            total_favorites = self.db.execute(
                select(func.count(UserFavorite.id))
                .where(
                    and_(
                        UserFavorite.user_id == user_id,
                        UserFavorite.created_at >= since
                    )
                )
            ).scalar() or 0
            
            # Recent favorites with story details
            recent_favorites = self.db.execute(
                select(
                    BronzeStory.title,
                    BronzeStory.author,
                    UserFavorite.created_at
                )
                .join(BronzeStory, UserFavorite.story_id == BronzeStory.id)
                .where(
                    and_(
                        UserFavorite.user_id == user_id,
                        UserFavorite.created_at >= since
                    )
                )
                .order_by(desc(UserFavorite.created_at))
                .limit(10)
            ).all()
            
            return {
                "total_favorites": total_favorites,
                "recent_favorites": [
                    {
                        "title": rf.title,
                        "author": rf.author,
                        "favorited_at": rf.created_at.isoformat() if rf.created_at else None
                    }
                    for rf in recent_favorites
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting favorite stats: {e}")
            return {"error": str(e)}
    
    async def get_system_analytics(
        self, 
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get system-wide analytics
        
        Args:
            days: Number of days to analyze
        
        Returns:
            System analytics data
        """
        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Total users
            total_users = self.db.execute(
                select(func.count(User.id))
            ).scalar() or 0
            
            # Active users (users who performed any action in the period)
            active_users = self.db.execute(
                select(func.count(func.distinct(SearchInteraction.user_id)))
                .where(SearchInteraction.search_timestamp >= since)
            ).scalar() or 0
            
            # Total searches
            total_searches = self.db.execute(
                select(func.count(SearchInteraction.id))
                .where(SearchInteraction.search_timestamp >= since)
            ).scalar() or 0
            
            # Total stories
            total_stories = self.db.execute(
                select(func.count(BronzeStory.id))
            ).scalar() or 0
            
            # Get current metrics from metrics collector
            current_metrics = self.metrics_collector.get_all_current_metrics()
            
            return {
                "period_days": days,
                "users": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "activity_rate_percentage": round(
                        (active_users / total_users * 100) if total_users > 0 else 0, 2
                    )
                },
                "content": {
                    "total_stories": total_stories,
                    "total_searches": total_searches,
                    "searches_per_day": round(total_searches / days, 2) if days > 0 else 0
                },
                "system_metrics": current_metrics,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system analytics: {e}")
            return {
                "period_days": days,
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }


# Dependency to get analytics service
def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    """Get analytics service instance"""
    return AnalyticsService(db)
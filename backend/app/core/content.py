"""
Content management service for stories, bookmarks, and user preferences
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.models import (
    BronzeStory, SilverStory, User, UserFavorite, StoryRating,
    UserReadingBehavior, SilverStoryChunks
)
from fastapi import Depends, HTTPException, status
from infrastructure.database.connection import get_db
from .base import BaseService, PaginatedResponse, TimestampMixin

logger = logging.getLogger(__name__)


class ContentService(BaseService, TimestampMixin):
    """Content management service for stories, bookmarks, and user preferences"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session)
    
    async def get_story_detail(
        self, 
        story_id: str, 
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Get detailed story information with user-specific data
        
        Args:
            story_id: Story ID
            user: Optional authenticated user
        
        Returns:
            Detailed story information
        """
        try:
            # Get bronze story
            bronze_stmt = select(BronzeStory).where(BronzeStory.id == story_id)
            bronze_story = self.db.execute(bronze_stmt).scalar_one_or_none()
            
            if not bronze_story:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Story not found"
                )
            
            # Get silver story for processed metadata
            silver_stmt = select(SilverStory).where(
                SilverStory.bronze_story_id == story_id
            )
            silver_story = self.db.execute(silver_stmt).scalar_one_or_none()
            
            # Get user-specific data if authenticated
            user_data = {}
            if user:
                user_data = await self._get_user_story_data(story_id, user.id)
            
            # Get story chunks for content preview
            chunks_stmt = (
                select(SilverStoryChunks)
                .where(SilverStoryChunks.story_id == story_id)
                .order_by(SilverStoryChunks.chunk_order)
                .limit(3)  # First 3 chunks for preview
            )
            chunks = self.db.execute(chunks_stmt).scalars().all()
            
            story_detail = {
                "id": str(bronze_story.id),
                "title": bronze_story.title,
                "content": bronze_story.content,
                "author": bronze_story.author,
                "source": bronze_story.source,
                "source_url": bronze_story.source_url,
                "post_date": bronze_story.post_date.isoformat() if bronze_story.post_date else None,
                "scraped_at": bronze_story.scraped_at.isoformat() if bronze_story.scraped_at else None,
                "raw_metadata": bronze_story.raw_metadata,
                "processed_metadata": {
                    "word_count": silver_story.word_count if silver_story else None,
                    "reading_time_minutes": silver_story.reading_time_minutes if silver_story else None,
                    "language_detected": silver_story.language_detected if silver_story else None,
                    "tags": silver_story.tags if silver_story else [],
                    "cleaned_content": silver_story.cleaned_content if silver_story else None
                },
                "user_data": user_data,
                "content_preview": [
                    {
                        "chunk_order": chunk.chunk_order,
                        "chunk_text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                        "chunk_type": chunk.chunk_type
                    }
                    for chunk in chunks
                ]
            }
            
            return story_detail
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting story detail: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get story detail"
            )
    
    async def _get_user_story_data(self, story_id: str, user_id: str) -> Dict[str, Any]:
        """Get user-specific data for a story"""
        try:
            # Check if story is favorited
            favorite_stmt = select(UserFavorite).where(
                and_(
                    UserFavorite.user_id == user_id,
                    UserFavorite.story_id == story_id
                )
            )
            favorite = self.db.execute(favorite_stmt).scalar_one_or_none()
            
            # Get user rating
            rating_stmt = select(StoryRating).where(
                and_(
                    StoryRating.user_id == user_id,
                    StoryRating.story_id == story_id
                )
            )
            rating = self.db.execute(rating_stmt).scalar_one_or_none()
            
            # Get reading behavior
            behavior_stmt = select(UserReadingBehavior).where(
                and_(
                    UserReadingBehavior.user_id == user_id,
                    UserReadingBehavior.story_id == story_id
                )
            ).order_by(desc(UserReadingBehavior.reading_start_time))
            
            behavior = self.db.execute(behavior_stmt).scalar_one_or_none()
            
            return {
                "is_favorited": favorite is not None,
                "favorited_at": favorite.created_at.isoformat() if favorite else None,
                "user_rating": rating.rating if rating else None,
                "rated_at": rating.created_at.isoformat() if rating else None,
                "reading_history": {
                    "last_read": behavior.reading_start_time.isoformat() if behavior else None,
                    "reading_duration": behavior.reading_duration if behavior else None,
                    "completed_reading": behavior.completed_reading if behavior else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user story data: {e}")
            return {}
    
    async def get_user_favorites(
        self, 
        user_id: str, 
        page: int = 1, 
        per_page: int = 20
    ) -> Dict[str, Any]:
        """Get user's favorite stories with pagination"""
        try:
            offset, per_page = self._validate_pagination(page, per_page, 100)
            
            # Get favorites with story details
            favorites_stmt = (
                select(UserFavorite, BronzeStory, SilverStory)
                .join(BronzeStory, UserFavorite.story_id == BronzeStory.id)
                .join(SilverStory, BronzeStory.id == SilverStory.bronze_story_id, isouter=True)
                .where(UserFavorite.user_id == user_id)
                .order_by(desc(UserFavorite.created_at))
                .offset(offset)
                .limit(per_page)
            )
            
            results = self.db.execute(favorites_stmt).all()
            
            # Get total count
            count_stmt = select(func.count(UserFavorite.id)).where(
                UserFavorite.user_id == user_id
            )
            total_count = self.db.execute(count_stmt).scalar() or 0
            
            favorites = []
            for favorite, bronze_story, silver_story in results:
                favorites.append({
                    "favorite_id": str(favorite.id),
                    "favorited_at": favorite.created_at.isoformat(),
                    "story": {
                        "id": str(bronze_story.id),
                        "title": bronze_story.title,
                        "author": bronze_story.author,
                        "source": bronze_story.source,
                        "post_date": bronze_story.post_date.isoformat() if bronze_story.post_date else None,
                        "word_count": silver_story.word_count if silver_story else None,
                        "reading_time_minutes": silver_story.reading_time_minutes if silver_story else None,
                        "tags": silver_story.tags if silver_story else []
                    }
                })
            
            return PaginatedResponse.create(
                favorites, page, per_page, total_count, "favorites"
            )
            
        except Exception as e:
            logger.error(f"Error getting user favorites: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user favorites"
            )
    
    async def toggle_favorite(
        self, 
        story_id: str, 
        user_id: str, 
        is_favorite: bool = True
    ) -> Dict[str, Any]:
        """Add or remove story from user favorites"""
        try:
            # Check if story exists
            story_stmt = select(BronzeStory).where(BronzeStory.id == story_id)
            story = self.db.execute(story_stmt).scalar_one_or_none()
            
            if not story:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Story not found"
                )
            
            # Check existing favorite
            favorite_stmt = select(UserFavorite).where(
                and_(
                    UserFavorite.user_id == user_id,
                    UserFavorite.story_id == story_id
                )
            )
            existing_favorite = self.db.execute(favorite_stmt).scalar_one_or_none()
            
            if is_favorite and not existing_favorite:
                # Add to favorites
                favorite = UserFavorite(
                    user_id=user_id,
                    story_id=story_id
                )
                self.db.add(favorite)
                self.db.commit()
                
                return {
                    "action": "added",
                    "is_favorited": True,
                    "story_id": story_id,
                    "favorited_at": favorite.created_at.isoformat()
                }
                
            elif not is_favorite and existing_favorite:
                # Remove from favorites
                self.db.delete(existing_favorite)
                self.db.commit()
                
                return {
                    "action": "removed",
                    "is_favorited": False,
                    "story_id": story_id
                }
            
            else:
                # No change needed
                return {
                    "action": "no_change",
                    "is_favorited": existing_favorite is not None,
                    "story_id": story_id
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error toggling favorite: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update favorite status"
            )
    
    async def rate_story(
        self, 
        story_id: str, 
        user_id: str, 
        rating: int
    ) -> Dict[str, Any]:
        """Rate a story (1-5 stars)"""
        try:
            if not 1 <= rating <= 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rating must be between 1 and 5"
                )
            
            # Check if story exists
            story_stmt = select(BronzeStory).where(BronzeStory.id == story_id)
            story = self.db.execute(story_stmt).scalar_one_or_none()
            
            if not story:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Story not found"
                )
            
            # Check existing rating
            rating_stmt = select(StoryRating).where(
                and_(
                    StoryRating.user_id == user_id,
                    StoryRating.story_id == story_id
                )
            )
            existing_rating = self.db.execute(rating_stmt).scalar_one_or_none()
            
            if existing_rating:
                # Update existing rating
                old_rating = existing_rating.rating
                existing_rating.rating = rating
                existing_rating.updated_at = datetime.now(timezone.utc)
                action = "updated"
            else:
                # Create new rating
                story_rating = StoryRating(
                    user_id=user_id,
                    story_id=story_id,
                    rating=rating
                )
                self.db.add(story_rating)
                old_rating = None
                action = "created"
            
            self.db.commit()
            
            return {
                "action": action,
                "story_id": story_id,
                "rating": rating,
                "previous_rating": old_rating,
                "rated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error rating story: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to rate story"
            )
    
    async def get_user_ratings(
        self, 
        user_id: str, 
        page: int = 1, 
        per_page: int = 20
    ) -> Dict[str, Any]:
        """Get user's story ratings with pagination"""
        try:
            offset, per_page = self._validate_pagination(page, per_page, 100)
            
            # Get ratings with story details
            ratings_stmt = (
                select(StoryRating, BronzeStory, SilverStory)
                .join(BronzeStory, StoryRating.story_id == BronzeStory.id)
                .join(SilverStory, BronzeStory.id == SilverStory.bronze_story_id, isouter=True)
                .where(StoryRating.user_id == user_id)
                .order_by(desc(StoryRating.updated_at))
                .offset(offset)
                .limit(per_page)
            )
            
            results = self.db.execute(ratings_stmt).all()
            
            # Get total count
            count_stmt = select(func.count(StoryRating.id)).where(
                StoryRating.user_id == user_id
            )
            total_count = self.db.execute(count_stmt).scalar() or 0
            
            ratings = []
            for rating, bronze_story, silver_story in results:
                ratings.append({
                    "rating_id": str(rating.id),
                    "rating": rating.rating,
                    "created_at": rating.created_at.isoformat(),
                    "updated_at": rating.updated_at.isoformat(),
                    "story": {
                        "id": str(bronze_story.id),
                        "title": bronze_story.title,
                        "author": bronze_story.author,
                        "source": bronze_story.source,
                        "post_date": bronze_story.post_date.isoformat() if bronze_story.post_date else None,
                        "word_count": silver_story.word_count if silver_story else None,
                        "tags": silver_story.tags if silver_story else []
                    }
                })
            
            return PaginatedResponse.create(
                ratings, page, per_page, total_count, "ratings"
            )
            
        except Exception as e:
            logger.error(f"Error getting user ratings: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user ratings"
            )
    
    async def get_reading_history(
        self, 
        user_id: str, 
        page: int = 1, 
        per_page: int = 20
    ) -> Dict[str, Any]:
        """Get user's reading history"""
        try:
            offset, per_page = self._validate_pagination(page, per_page, 100)
            
            # Get reading history with story details
            history_stmt = (
                select(UserReadingBehavior, BronzeStory, SilverStory)
                .join(BronzeStory, UserReadingBehavior.story_id == BronzeStory.id)
                .join(SilverStory, BronzeStory.id == SilverStory.bronze_story_id, isouter=True)
                .where(UserReadingBehavior.user_id == user_id)
                .order_by(desc(UserReadingBehavior.reading_start_time))
                .offset(offset)
                .limit(per_page)
            )
            
            results = self.db.execute(history_stmt).all()
            
            # Get total count
            count_stmt = select(func.count(UserReadingBehavior.id)).where(
                UserReadingBehavior.user_id == user_id
            )
            total_count = self.db.execute(count_stmt).scalar() or 0
            
            history = []
            for behavior, bronze_story, silver_story in results:
                history.append({
                    "reading_id": str(behavior.id),
                    "reading_start_time": behavior.reading_start_time.isoformat(),
                    "reading_duration": behavior.reading_duration,
                    "completed_reading": behavior.completed_reading,
                    "story": {
                        "id": str(bronze_story.id),
                        "title": bronze_story.title,
                        "author": bronze_story.author,
                        "source": bronze_story.source,
                        "word_count": silver_story.word_count if silver_story else None,
                        "reading_time_minutes": silver_story.reading_time_minutes if silver_story else None
                    }
                })
            
            return PaginatedResponse.create(
                history, page, per_page, total_count, "reading_history"
            )
            
        except Exception as e:
            logger.error(f"Error getting reading history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get reading history"
            )


# Dependency to get content service
def get_content_service(db: Session = Depends(get_db)) -> ContentService:
    """Get content service instance"""
    return ContentService(db)
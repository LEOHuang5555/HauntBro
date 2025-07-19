"""
Database models for HauntBro ghost story search engine.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, 
    ARRAY, CheckConstraint, func, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, TSVECTOR
from sqlalchemy.sql import expression

Base = declarative_base()


class User(Base):
    """User model for authentication and user management."""
    
    __tablename__ = 'users'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    search_logs = relationship("SearchLog", back_populates="user")
    favorites = relationship("UserFavorite", back_populates="user")
    ratings = relationship("StoryRating", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Story(Base):
    """Story model for storing scraped ghost stories."""
    
    __tablename__ = 'stories'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    source_url = Column(String(1000))
    author = Column(String(100))
    post_date = Column(DateTime(timezone=True))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Search optimization fields
    search_vector = Column(TSVECTOR)
    
    # Metadata
    word_count = Column(Integer)
    reading_time_minutes = Column(Integer)
    tags = Column(ARRAY(String))
    
    # Quality indicators
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    
    # Content classification
    is_nsfw = Column(Boolean, default=False)
    content_warning = Column(Text)
    
    # Relationships
    favorites = relationship("UserFavorite", back_populates="story")
    ratings = relationship("StoryRating", back_populates="story")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("source IN ('ptt_marvel', 'reddit_ghoststories')", name='valid_source'),
        Index('idx_stories_source', 'source'),
        Index('idx_stories_post_date', 'post_date'),
        Index('idx_stories_scraped_at', 'scraped_at'),
        Index('idx_stories_search_vector', 'search_vector', postgresql_using='gin'),
        Index('idx_stories_tags', 'tags', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<Story(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"


class SearchLog(Base):
    """Search log model for analytics and improving search results."""
    
    __tablename__ = 'search_logs'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    query = Column(Text, nullable=False)
    results_count = Column(Integer, nullable=False)
    search_type = Column(String(50), nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Search performance metrics
    execution_time_ms = Column(Integer)
    
    # User interaction data
    clicked_results = Column(ARRAY(PostgresUUID))
    session_id = Column(PostgresUUID(as_uuid=True))
    
    # Search filters used
    source_filter = Column(String(100))
    date_range_start = Column(DateTime(timezone=True))
    date_range_end = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="search_logs")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("search_type IN ('keyword', 'semantic', 'hybrid')", name='valid_search_type'),
        Index('idx_search_logs_user_id', 'user_id'),
        Index('idx_search_logs_executed_at', 'executed_at'),
        Index('idx_search_logs_query', 'query'),
    )
    
    def __repr__(self):
        return f"<SearchLog(id={self.id}, query='{self.query[:30]}...', results_count={self.results_count})>"


class UserFavorite(Base):
    """User favorites/bookmarks model."""
    
    __tablename__ = 'user_favorites'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    story_id = Column(PostgresUUID(as_uuid=True), ForeignKey('stories.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="favorites")
    story = relationship("Story", back_populates="favorites")
    
    # Constraints
    __table_args__ = (
        Index('idx_user_favorites_user_id', 'user_id'),
        Index('idx_user_favorites_story_id', 'story_id'),
    )
    
    def __repr__(self):
        return f"<UserFavorite(id={self.id}, user_id={self.user_id}, story_id={self.story_id})>"


class StoryRating(Base):
    """Story ratings model."""
    
    __tablename__ = 'story_ratings'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    story_id = Column(PostgresUUID(as_uuid=True), ForeignKey('stories.id', ondelete='CASCADE'), nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="ratings")
    story = relationship("Story", back_populates="ratings")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name='valid_rating'),
        Index('idx_story_ratings_story_id', 'story_id'),
        Index('idx_story_ratings_rating', 'rating'),
    )
    
    def __repr__(self):
        return f"<StoryRating(id={self.id}, user_id={self.user_id}, story_id={self.story_id}, rating={self.rating})>"


class ScrapingJob(Base):
    """Scraping jobs tracking model."""
    
    __tablename__ = 'scraping_jobs'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    source = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default='pending')
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    stories_scraped = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_log = Column(Text)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name='valid_status'),
    )
    
    def __repr__(self):
        return f"<ScrapingJob(id={self.id}, source='{self.source}', status='{self.status}')>"
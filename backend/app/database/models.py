"""
Database models for HauntBro - Medallion Architecture
Bronze-Silver-Gold data pipeline with user-facing features.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Float,
    ARRAY, CheckConstraint, func, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, TSVECTOR, JSONB

Base = declarative_base()


# =============================================================================
# BRONZE LAYER - Raw Data (Immutable)
# =============================================================================

class BronzeStory(Base):
    """Raw scraped stories - immutable source of truth."""
    
    __tablename__ = 'bronze_stories'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(Text)
    content = Column(Text)
    source = Column(String(100))
    source_url = Column(String(1000))
    author = Column(String(100))
    post_date = Column(DateTime(timezone=True))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_metadata = Column(JSONB)
    
    # Relationships
    silver_story = relationship("SilverStory", back_populates="bronze_story", uselist=False)
    chunks = relationship("SilverStoryChunk", back_populates="bronze_story")
    performance = relationship("GoldStoryPerformance", back_populates="story", uselist=False)
    favorites = relationship("UserFavorite", back_populates="story")
    ratings = relationship("StoryRating", back_populates="story")
    reading_behaviors = relationship("UserReadingBehavior", back_populates="story")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("source IN ('ptt_marvel', 'reddit_ghoststories')", name='valid_source'),
        Index('idx_bronze_stories_source', 'source'),
        Index('idx_bronze_stories_scraped_at', 'scraped_at'),
        Index('idx_bronze_stories_post_date', 'post_date'),
        Index('idx_bronze_stories_raw_metadata', 'raw_metadata', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<BronzeStory(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"


# =============================================================================
# SILVER LAYER - Processed Data
# =============================================================================

class SilverStoryChunk(Base):
    """Chunked stories for RAG retrieval."""
    
    __tablename__ = 'silver_story_chunks'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    bronze_story_id = Column(PostgresUUID(as_uuid=True), ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False)
    
    # Chunking data
    chunk_text = Column(Text, nullable=False)
    chunk_context = Column(Text)
    chunk_order = Column(Integer, nullable=False)
    
    # Search vectors
    # Note: VECTOR type requires pgvector extension
    # For now, we'll store as Text and cast when needed
    embedding = Column(Text)  # Will be VECTOR(1536) when pgvector is available
    search_vector = Column(TSVECTOR)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bronze_story = relationship("BronzeStory", back_populates="chunks")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('bronze_story_id', 'chunk_order', name='unique_chunk_order'),
        Index('idx_silver_story_chunks_bronze_id', 'bronze_story_id'),
        Index('idx_silver_story_chunks_search_vector', 'search_vector', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<SilverStoryChunk(id={self.id}, story_id={self.bronze_story_id}, order={self.chunk_order})>"


class SilverStory(Base):
    """Cleaned story metadata."""
    
    __tablename__ = 'silver_stories'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    bronze_story_id = Column(PostgresUUID(as_uuid=True), ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(500))
    cleaned_content = Column(Text)
    author = Column(String(100))
    post_date = Column(DateTime(timezone=True))
    tags = Column(ARRAY(String))
    reading_time_minutes = Column(Integer)
    word_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bronze_story = relationship("BronzeStory", back_populates="silver_story")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('bronze_story_id', name='unique_bronze_story'),
        Index('idx_silver_stories_bronze_id', 'bronze_story_id'),
        Index('idx_silver_stories_tags', 'tags', postgresql_using='gin'),
        Index('idx_silver_stories_post_date', 'post_date'),
    )
    
    def __repr__(self):
        return f"<SilverStory(id={self.id}, bronze_id={self.bronze_story_id}, title='{self.title[:50]}...')>"


# =============================================================================
# GOLD LAYER - Business Metrics
# =============================================================================

class GoldStoryPerformance(Base):
    """Business performance metrics."""
    
    __tablename__ = 'gold_story_performance'
    
    story_id = Column(PostgresUUID(as_uuid=True), ForeignKey('bronze_stories.id', ondelete='CASCADE'), primary_key=True)
    total_reads = Column(Integer, default=0)
    unique_readers = Column(Integer, default=0)
    avg_user_rating = Column(Float)
    favorites_count = Column(Integer, default=0)
    search_impressions = Column(Integer, default=0)
    search_clicks = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    story = relationship("BronzeStory", back_populates="performance")
    
    # Constraints
    __table_args__ = (
        Index('idx_gold_performance_total_reads', 'total_reads'),
        Index('idx_gold_performance_avg_rating', 'avg_user_rating'),
        Index('idx_gold_performance_last_updated', 'last_updated'),
    )
    
    def __repr__(self):
        return f"<GoldStoryPerformance(story_id={self.story_id}, reads={self.total_reads}, rating={self.avg_user_rating})>"


# =============================================================================
# USER LAYER - Application Features
# =============================================================================

class User(Base):
    """User authentication and profile."""
    
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
    favorites = relationship("UserFavorite", back_populates="user")
    ratings = relationship("StoryRating", back_populates="user")
    search_interactions = relationship("SearchInteraction", back_populates="user")
    reading_behaviors = relationship("UserReadingBehavior", back_populates="user")
    
    # Constraints
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class UserFavorite(Base):
    """User bookmarks."""
    
    __tablename__ = 'user_favorites'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    story_id = Column(PostgresUUID(as_uuid=True), ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="favorites")
    story = relationship("BronzeStory", back_populates="favorites")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'story_id', name='unique_user_story_favorite'),
        Index('idx_user_favorites_user_id', 'user_id'),
        Index('idx_user_favorites_story_id', 'story_id'),
        Index('idx_user_favorites_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<UserFavorite(id={self.id}, user_id={self.user_id}, story_id={self.story_id})>"


class StoryRating(Base):
    """User ratings for stories."""
    
    __tablename__ = 'story_ratings'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    story_id = Column(PostgresUUID(as_uuid=True), ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="ratings")
    story = relationship("BronzeStory", back_populates="ratings")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name='valid_rating'),
        UniqueConstraint('user_id', 'story_id', name='unique_user_story_rating'),
        Index('idx_story_ratings_user_id', 'user_id'),
        Index('idx_story_ratings_story_id', 'story_id'),
        Index('idx_story_ratings_rating', 'rating'),
    )
    
    def __repr__(self):
        return f"<StoryRating(id={self.id}, user_id={self.user_id}, story_id={self.story_id}, rating={self.rating})>"


# =============================================================================
# ANALYTICS LAYER - User Behavior & Search
# =============================================================================

class SearchInteraction(Base):
    """Search analytics and user interactions."""
    
    __tablename__ = 'search_interactions'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    session_id = Column(PostgresUUID(as_uuid=True))
    query = Column(Text, nullable=False)
    search_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Interaction data
    results_shown = Column(ARRAY(PostgresUUID))
    results_clicked = Column(ARRAY(PostgresUUID))
    click_positions = Column(ARRAY(Integer))
    time_to_first_click = Column(Integer)
    
    # Search performance
    search_type = Column(String(50), default='hybrid')
    execution_time_ms = Column(Integer)
    
    # Relationships
    user = relationship("User", back_populates="search_interactions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("search_type IN ('keyword', 'semantic', 'hybrid')", name='valid_search_type'),
        Index('idx_search_interactions_user_id', 'user_id'),
        Index('idx_search_interactions_session_id', 'session_id'),
        Index('idx_search_interactions_timestamp', 'search_timestamp'),
        Index('idx_search_interactions_query', 'query'),
    )
    
    def __repr__(self):
        return f"<SearchInteraction(id={self.id}, query='{self.query[:30]}...', type='{self.search_type}')>"


class UserReadingBehavior(Base):
    """Reading behavior analytics."""
    
    __tablename__ = 'user_reading_behavior'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    story_id = Column(PostgresUUID(as_uuid=True), ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False)
    
    reading_start_time = Column(DateTime(timezone=True), server_default=func.now())
    reading_duration = Column(Integer)  # Seconds
    return_visits = Column(Integer, default=1)
    favorited = Column(Boolean, default=False)
    shared = Column(Boolean, default=False)
    
    # Engagement metrics
    scroll_depth = Column(Float)  # Percentage of content viewed
    bounce_rate = Column(Boolean, default=False)  # Left immediately
    
    # Relationships
    user = relationship("User", back_populates="reading_behaviors")
    story = relationship("BronzeStory", back_populates="reading_behaviors")
    
    # Constraints
    __table_args__ = (
        Index('idx_user_reading_behavior_user_id', 'user_id'),
        Index('idx_user_reading_behavior_story_id', 'story_id'),
        Index('idx_user_reading_behavior_start_time', 'reading_start_time'),
    )
    
    def __repr__(self):
        return f"<UserReadingBehavior(id={self.id}, user_id={self.user_id}, story_id={self.story_id})>"


# =============================================================================
# PIPELINE LAYER - Data Engineering Metrics
# =============================================================================

class ScrapingPipelineMetrics(Base):
    """Business-specific pipeline metrics."""
    
    __tablename__ = 'scraping_pipeline_metrics'
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    airflow_dag_run_id = Column(String(250))
    source_name = Column(String(100), nullable=False)
    stories_discovered = Column(Integer, default=0)
    stories_new = Column(Integer, default=0)
    stories_updated = Column(Integer, default=0)
    duplicate_rate = Column(Float, default=0.0)
    processing_time_seconds = Column(Integer)
    errors_count = Column(Integer, default=0)
    error_log = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("source_name IN ('ptt_marvel', 'reddit_ghoststories')", name='valid_source_name'),
        Index('idx_scraping_pipeline_metrics_dag_run_id', 'airflow_dag_run_id'),
        Index('idx_scraping_pipeline_metrics_source', 'source_name'),
        Index('idx_scraping_pipeline_metrics_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScrapingPipelineMetrics(id={self.id}, source='{self.source_name}', new_stories={self.stories_new})>"
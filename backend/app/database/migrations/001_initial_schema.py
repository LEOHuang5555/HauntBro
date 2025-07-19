"""
Initial database schema migration.
Creates all the core tables for HauntBro ghost story search engine.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TSVECTOR


def upgrade():
    """Create initial database schema."""
    
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_login', sa.DateTime(timezone=True)),
    )
    
    # Create stories table
    op.create_table(
        'stories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('source_url', sa.String(1000)),
        sa.Column('author', sa.String(100)),
        sa.Column('post_date', sa.DateTime(timezone=True)),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('search_vector', TSVECTOR),
        sa.Column('word_count', sa.Integer),
        sa.Column('reading_time_minutes', sa.Integer),
        sa.Column('tags', ARRAY(sa.String)),
        sa.Column('upvotes', sa.Integer, default=0),
        sa.Column('downvotes', sa.Integer, default=0),
        sa.Column('comments_count', sa.Integer, default=0),
        sa.Column('is_nsfw', sa.Boolean, default=False),
        sa.Column('content_warning', sa.Text),
        sa.CheckConstraint("source IN ('ptt_marvel', 'reddit_ghoststories')", name='valid_source'),
    )
    
    # Create search_logs table
    op.create_table(
        'search_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('query', sa.Text, nullable=False),
        sa.Column('results_count', sa.Integer, nullable=False),
        sa.Column('search_type', sa.String(50), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('execution_time_ms', sa.Integer),
        sa.Column('clicked_results', ARRAY(UUID)),
        sa.Column('session_id', UUID(as_uuid=True)),
        sa.Column('source_filter', sa.String(100)),
        sa.Column('date_range_start', sa.DateTime(timezone=True)),
        sa.Column('date_range_end', sa.DateTime(timezone=True)),
        sa.CheckConstraint("search_type IN ('keyword', 'semantic', 'hybrid')", name='valid_search_type'),
    )
    
    # Create user_favorites table
    op.create_table(
        'user_favorites',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('story_id', UUID(as_uuid=True), sa.ForeignKey('stories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('notes', sa.Text),
        sa.UniqueConstraint('user_id', 'story_id'),
    )
    
    # Create story_ratings table
    op.create_table(
        'story_ratings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('story_id', UUID(as_uuid=True), sa.ForeignKey('stories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name='valid_rating'),
        sa.UniqueConstraint('user_id', 'story_id'),
    )
    
    # Create scraping_jobs table
    op.create_table(
        'scraping_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('stories_scraped', sa.Integer, default=0),
        sa.Column('errors_count', sa.Integer, default=0),
        sa.Column('error_log', sa.Text),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name='valid_status'),
    )
    
    # Create indexes for performance
    op.create_index('idx_stories_source', 'stories', ['source'])
    op.create_index('idx_stories_post_date', 'stories', ['post_date'])
    op.create_index('idx_stories_scraped_at', 'stories', ['scraped_at'])
    op.create_index('idx_stories_search_vector', 'stories', ['search_vector'], postgresql_using='gin')
    op.create_index('idx_stories_tags', 'stories', ['tags'], postgresql_using='gin')
    
    op.create_index('idx_search_logs_user_id', 'search_logs', ['user_id'])
    op.create_index('idx_search_logs_executed_at', 'search_logs', ['executed_at'])
    op.create_index('idx_search_logs_query', 'search_logs', ['query'])
    
    op.create_index('idx_user_favorites_user_id', 'user_favorites', ['user_id'])
    op.create_index('idx_user_favorites_story_id', 'user_favorites', ['story_id'])
    
    op.create_index('idx_story_ratings_story_id', 'story_ratings', ['story_id'])
    op.create_index('idx_story_ratings_rating', 'story_ratings', ['rating'])
    
    # Create trigger function for updating timestamps
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create triggers for updating timestamps
    op.execute("""
        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_stories_updated_at BEFORE UPDATE ON stories
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_story_ratings_updated_at BEFORE UPDATE ON story_ratings
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Create function to update search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION update_story_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', 
                COALESCE(NEW.title, '') || ' ' || 
                COALESCE(NEW.content, '') || ' ' || 
                COALESCE(NEW.author, '') || ' ' || 
                COALESCE(array_to_string(NEW.tags, ' '), '')
            );
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create trigger for updating search vector
    op.execute("""
        CREATE TRIGGER update_story_search_vector_trigger
            BEFORE INSERT OR UPDATE ON stories
            FOR EACH ROW EXECUTE FUNCTION update_story_search_vector();
    """)


def downgrade():
    """Drop all tables and functions."""
    
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_story_search_vector_trigger ON stories')
    op.execute('DROP TRIGGER IF EXISTS update_story_ratings_updated_at ON story_ratings')
    op.execute('DROP TRIGGER IF EXISTS update_stories_updated_at ON stories')
    op.execute('DROP TRIGGER IF EXISTS update_users_updated_at ON users')
    
    # Drop functions
    op.execute('DROP FUNCTION IF EXISTS update_story_search_vector()')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    
    # Drop tables
    op.drop_table('scraping_jobs')
    op.drop_table('story_ratings')
    op.drop_table('user_favorites')
    op.drop_table('search_logs')
    op.drop_table('stories')
    op.drop_table('users')
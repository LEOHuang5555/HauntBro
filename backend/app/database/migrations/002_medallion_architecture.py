"""
Migration to Medallion Architecture.
Restructures database from simple schema to Bronze-Silver-Gold layers.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TSVECTOR, JSONB


def upgrade():
    """Migrate to medallion architecture."""
    
    # =========================================================================
    # STEP 1: Create new medallion tables
    # =========================================================================
    
    # Bronze Layer - Raw Data
    op.create_table(
        'bronze_stories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('title', sa.Text),
        sa.Column('content', sa.Text),
        sa.Column('source', sa.String(100)),
        sa.Column('source_url', sa.String(1000)),
        sa.Column('author', sa.String(100)),
        sa.Column('post_date', sa.DateTime(timezone=True)),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('raw_metadata', JSONB),
        sa.CheckConstraint("source IN ('ptt_marvel', 'reddit_ghoststories')", name='valid_source'),
    )
    
    # Silver Layer - Processed Data
    op.create_table(
        'silver_story_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('bronze_story_id', UUID(as_uuid=True), sa.ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_text', sa.Text, nullable=False),
        sa.Column('chunk_context', sa.Text),
        sa.Column('chunk_order', sa.Integer, nullable=False),
        sa.Column('embedding', sa.Text),  # Will be VECTOR(1536) when pgvector is available
        sa.Column('search_vector', TSVECTOR),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('bronze_story_id', 'chunk_order', name='unique_chunk_order'),
    )
    
    op.create_table(
        'silver_stories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('bronze_story_id', UUID(as_uuid=True), sa.ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(500)),
        sa.Column('cleaned_content', sa.Text),
        sa.Column('author', sa.String(100)),
        sa.Column('post_date', sa.DateTime(timezone=True)),
        sa.Column('tags', ARRAY(sa.String)),
        sa.Column('reading_time_minutes', sa.Integer),
        sa.Column('word_count', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('bronze_story_id', name='unique_bronze_story'),
    )
    
    # Gold Layer - Business Metrics
    op.create_table(
        'gold_story_performance',
        sa.Column('story_id', UUID(as_uuid=True), sa.ForeignKey('bronze_stories.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('total_reads', sa.Integer, default=0),
        sa.Column('unique_readers', sa.Integer, default=0),
        sa.Column('avg_user_rating', sa.Float),
        sa.Column('favorites_count', sa.Integer, default=0),
        sa.Column('search_impressions', sa.Integer, default=0),
        sa.Column('search_clicks', sa.Integer, default=0),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Analytics Layer - Enhanced search and behavior
    op.create_table(
        'search_interactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('session_id', UUID(as_uuid=True)),
        sa.Column('query', sa.Text, nullable=False),
        sa.Column('search_timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('results_shown', ARRAY(UUID)),
        sa.Column('results_clicked', ARRAY(UUID)),
        sa.Column('click_positions', ARRAY(sa.Integer)),
        sa.Column('time_to_first_click', sa.Integer),
        sa.Column('search_type', sa.String(50), default='hybrid'),
        sa.Column('execution_time_ms', sa.Integer),
        sa.CheckConstraint("search_type IN ('keyword', 'semantic', 'hybrid')", name='valid_search_type'),
    )
    
    op.create_table(
        'user_reading_behavior',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('story_id', UUID(as_uuid=True), sa.ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reading_start_time', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('reading_duration', sa.Integer),
        sa.Column('return_visits', sa.Integer, default=1),
        sa.Column('favorited', sa.Boolean, default=False),
        sa.Column('shared', sa.Boolean, default=False),
        sa.Column('scroll_depth', sa.Float),
        sa.Column('bounce_rate', sa.Boolean, default=False),
    )
    
    # Pipeline Layer - Data Engineering Metrics
    op.create_table(
        'scraping_pipeline_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('airflow_dag_run_id', sa.String(250)),
        sa.Column('source_name', sa.String(100), nullable=False),
        sa.Column('stories_discovered', sa.Integer, default=0),
        sa.Column('stories_new', sa.Integer, default=0),
        sa.Column('stories_updated', sa.Integer, default=0),
        sa.Column('duplicate_rate', sa.Float, default=0.0),
        sa.Column('processing_time_seconds', sa.Integer),
        sa.Column('errors_count', sa.Integer, default=0),
        sa.Column('error_log', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("source_name IN ('ptt_marvel', 'reddit_ghoststories')", name='valid_source_name'),
    )
    
    # =========================================================================
    # STEP 2: Migrate data from old schema to new schema
    # =========================================================================
    
    # Migrate stories to bronze_stories
    op.execute("""
        INSERT INTO bronze_stories (id, title, content, source, source_url, author, post_date, scraped_at, raw_metadata)
        SELECT 
            id, 
            title, 
            content, 
            source, 
            source_url, 
            author, 
            post_date, 
            scraped_at,
            jsonb_build_object(
                'upvotes', upvotes,
                'downvotes', downvotes,
                'comments_count', comments_count,
                'is_nsfw', is_nsfw,
                'content_warning', content_warning,
                'tags', tags
            ) as raw_metadata
        FROM stories
    """)
    
    # Create silver_stories from bronze_stories
    op.execute("""
        INSERT INTO silver_stories (bronze_story_id, title, cleaned_content, author, post_date, tags, reading_time_minutes, word_count)
        SELECT 
            id as bronze_story_id,
            title,
            content as cleaned_content,
            author,
            post_date,
            (raw_metadata->>'tags')::text[] as tags,
            (raw_metadata->>'reading_time_minutes')::integer as reading_time_minutes,
            (raw_metadata->>'word_count')::integer as word_count
        FROM bronze_stories
    """)
    
    # Initialize gold_story_performance
    op.execute("""
        INSERT INTO gold_story_performance (story_id, total_reads, unique_readers, avg_user_rating, favorites_count)
        SELECT 
            bs.id as story_id,
            0 as total_reads,
            0 as unique_readers,
            (SELECT AVG(rating)::FLOAT FROM story_ratings WHERE story_id = bs.id) as avg_user_rating,
            (SELECT COUNT(*) FROM user_favorites WHERE story_id = bs.id) as favorites_count
        FROM bronze_stories bs
    """)
    
    # Migrate search_logs to search_interactions
    op.execute("""
        INSERT INTO search_interactions (user_id, query, search_timestamp, search_type, execution_time_ms, results_shown, results_clicked)
        SELECT 
            user_id,
            query,
            executed_at as search_timestamp,
            search_type,
            execution_time_ms,
            ARRAY[]::uuid[] as results_shown,  -- Initialize empty, will be populated later
            clicked_results as results_clicked
        FROM search_logs
    """)
    
    # =========================================================================
    # STEP 3: Update foreign keys in user tables
    # =========================================================================
    
    # Update user_favorites to reference bronze_stories
    op.execute("ALTER TABLE user_favorites DROP CONSTRAINT IF EXISTS user_favorites_story_id_fkey")
    op.execute("ALTER TABLE user_favorites ADD CONSTRAINT user_favorites_story_id_fkey FOREIGN KEY (story_id) REFERENCES bronze_stories(id) ON DELETE CASCADE")
    
    # Update story_ratings to reference bronze_stories
    op.execute("ALTER TABLE story_ratings DROP CONSTRAINT IF EXISTS story_ratings_story_id_fkey")
    op.execute("ALTER TABLE story_ratings ADD CONSTRAINT story_ratings_story_id_fkey FOREIGN KEY (story_id) REFERENCES bronze_stories(id) ON DELETE CASCADE")
    
    # =========================================================================
    # STEP 4: Create indexes for performance
    # =========================================================================
    
    # Bronze layer indexes
    op.create_index('idx_bronze_stories_source', 'bronze_stories', ['source'])
    op.create_index('idx_bronze_stories_scraped_at', 'bronze_stories', ['scraped_at'])
    op.create_index('idx_bronze_stories_post_date', 'bronze_stories', ['post_date'])
    op.create_index('idx_bronze_stories_raw_metadata', 'bronze_stories', ['raw_metadata'], postgresql_using='gin')
    
    # Silver layer indexes
    op.create_index('idx_silver_story_chunks_bronze_id', 'silver_story_chunks', ['bronze_story_id'])
    op.create_index('idx_silver_story_chunks_search_vector', 'silver_story_chunks', ['search_vector'], postgresql_using='gin')
    
    op.create_index('idx_silver_stories_bronze_id', 'silver_stories', ['bronze_story_id'])
    op.create_index('idx_silver_stories_tags', 'silver_stories', ['tags'], postgresql_using='gin')
    op.create_index('idx_silver_stories_post_date', 'silver_stories', ['post_date'])
    
    # Gold layer indexes
    op.create_index('idx_gold_performance_total_reads', 'gold_story_performance', ['total_reads'])
    op.create_index('idx_gold_performance_avg_rating', 'gold_story_performance', ['avg_user_rating'])
    op.create_index('idx_gold_performance_last_updated', 'gold_story_performance', ['last_updated'])
    
    # Analytics layer indexes
    op.create_index('idx_search_interactions_user_id', 'search_interactions', ['user_id'])
    op.create_index('idx_search_interactions_session_id', 'search_interactions', ['session_id'])
    op.create_index('idx_search_interactions_timestamp', 'search_interactions', ['search_timestamp'])
    op.create_index('idx_search_interactions_query', 'search_interactions', ['query'])
    
    op.create_index('idx_user_reading_behavior_user_id', 'user_reading_behavior', ['user_id'])
    op.create_index('idx_user_reading_behavior_story_id', 'user_reading_behavior', ['story_id'])
    op.create_index('idx_user_reading_behavior_start_time', 'user_reading_behavior', ['reading_start_time'])
    
    # Pipeline layer indexes
    op.create_index('idx_scraping_pipeline_metrics_dag_run_id', 'scraping_pipeline_metrics', ['airflow_dag_run_id'])
    op.create_index('idx_scraping_pipeline_metrics_source', 'scraping_pipeline_metrics', ['source_name'])
    op.create_index('idx_scraping_pipeline_metrics_created_at', 'scraping_pipeline_metrics', ['created_at'])
    
    # =========================================================================
    # STEP 5: Create new triggers and functions
    # =========================================================================
    
    # Function to update search vector for chunks
    op.execute("""
        CREATE OR REPLACE FUNCTION update_chunk_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', 
                COALESCE(NEW.chunk_text, '') || ' ' || 
                COALESCE(NEW.chunk_context, '')
            );
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Trigger for updating search vector
    op.execute("""
        CREATE TRIGGER update_chunk_search_vector_trigger
            BEFORE INSERT OR UPDATE ON silver_story_chunks
            FOR EACH ROW EXECUTE FUNCTION update_chunk_search_vector();
    """)
    
    # Function to update story performance metrics
    op.execute("""
        CREATE OR REPLACE FUNCTION update_story_performance()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Update favorites count
            IF TG_TABLE_NAME = 'user_favorites' THEN
                INSERT INTO gold_story_performance (story_id, favorites_count, last_updated)
                VALUES (NEW.story_id, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (story_id) 
                DO UPDATE SET 
                    favorites_count = gold_story_performance.favorites_count + 1,
                    last_updated = CURRENT_TIMESTAMP;
            END IF;
            
            -- Update average rating
            IF TG_TABLE_NAME = 'story_ratings' THEN
                INSERT INTO gold_story_performance (story_id, avg_user_rating, last_updated)
                VALUES (NEW.story_id, NEW.rating, CURRENT_TIMESTAMP)
                ON CONFLICT (story_id) 
                DO UPDATE SET 
                    avg_user_rating = (
                        SELECT AVG(rating)::FLOAT 
                        FROM story_ratings 
                        WHERE story_id = NEW.story_id
                    ),
                    last_updated = CURRENT_TIMESTAMP;
            END IF;
            
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Triggers for updating performance metrics
    op.execute("""
        CREATE TRIGGER update_favorites_performance_trigger
            AFTER INSERT ON user_favorites
            FOR EACH ROW EXECUTE FUNCTION update_story_performance();
    """)
    
    op.execute("""
        CREATE TRIGGER update_ratings_performance_trigger
            AFTER INSERT OR UPDATE ON story_ratings
            FOR EACH ROW EXECUTE FUNCTION update_story_performance();
    """)
    
    # =========================================================================
    # STEP 6: Drop old tables
    # =========================================================================
    
    # Drop old tables (keep scraping_jobs for now as it's different from pipeline metrics)
    op.drop_table('search_logs')
    op.drop_table('stories')


def downgrade():
    """Rollback medallion architecture."""
    
    # This is a complex migration - for safety, we'll preserve the old backup tables
    # and recreate the original structure
    
    # Drop new triggers
    op.execute('DROP TRIGGER IF EXISTS update_chunk_search_vector_trigger ON silver_story_chunks')
    op.execute('DROP TRIGGER IF EXISTS update_favorites_performance_trigger ON user_favorites')
    op.execute('DROP TRIGGER IF EXISTS update_ratings_performance_trigger ON story_ratings')
    
    # Drop new functions
    op.execute('DROP FUNCTION IF EXISTS update_chunk_search_vector()')
    op.execute('DROP FUNCTION IF EXISTS update_story_performance()')
    
    # Drop new tables
    op.drop_table('scraping_pipeline_metrics')
    op.drop_table('user_reading_behavior')
    op.drop_table('search_interactions')
    op.drop_table('gold_story_performance')
    op.drop_table('silver_stories')
    op.drop_table('silver_story_chunks')
    op.drop_table('bronze_stories')
    
    # Recreate original stories table structure
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
    
    # Recreate search_logs table
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
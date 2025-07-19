"""
Manual migration to medallion architecture with proper data migration.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TSVECTOR, JSONB


def upgrade():
    """Migrate to medallion architecture with data preservation."""
    
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # =========================================================================
    # STEP 1: Create all new medallion tables
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
        sa.CheckConstraint("source IN ('ptt_marvel', 'reddit_ghoststories')", name='bronze_valid_source'),
    )
    
    # Silver Layer - Processed Data
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
        sa.UniqueConstraint('bronze_story_id', name='unique_bronze_story_ref'),
    )
    
    op.create_table(
        'silver_story_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('bronze_story_id', UUID(as_uuid=True), sa.ForeignKey('bronze_stories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_text', sa.Text, nullable=False),
        sa.Column('chunk_context', sa.Text),
        sa.Column('chunk_order', sa.Integer, nullable=False),
        sa.Column('embedding', sa.Text),
        sa.Column('search_vector', TSVECTOR),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('bronze_story_id', 'chunk_order', name='unique_chunk_order_ref'),
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
    
    # Analytics Layer
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
        sa.CheckConstraint("search_type IN ('keyword', 'semantic', 'hybrid')", name='search_valid_type'),
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
    
    # Pipeline Layer
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
        sa.CheckConstraint("source_name IN ('ptt_marvel', 'reddit_ghoststories')", name='pipeline_valid_source'),
    )
    
    # =========================================================================
    # STEP 2: Migrate data if old tables exist
    # =========================================================================
    
    # Check if old tables exist and migrate data
    connection = op.get_bind()
    
    # Check if stories table exists
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'stories'
        );
    """))
    
    if result.scalar():
        print("Migrating data from old schema to medallion architecture...")
        
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
                    'upvotes', COALESCE(upvotes, 0),
                    'downvotes', COALESCE(downvotes, 0),
                    'comments_count', COALESCE(comments_count, 0),
                    'is_nsfw', COALESCE(is_nsfw, false),
                    'content_warning', content_warning,
                    'tags', tags,
                    'word_count', word_count,
                    'reading_time_minutes', reading_time_minutes
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
        
        # Check if search_logs table exists and migrate
        result = connection.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'search_logs'
            );
        """))
        
        if result.scalar():
            # Migrate search_logs to search_interactions
            op.execute("""
                INSERT INTO search_interactions (user_id, query, search_timestamp, search_type, execution_time_ms, results_shown, results_clicked)
                SELECT 
                    user_id,
                    query,
                    executed_at as search_timestamp,
                    search_type,
                    execution_time_ms,
                    ARRAY[]::uuid[] as results_shown,
                    COALESCE(clicked_results, ARRAY[]::uuid[]) as results_clicked
                FROM search_logs
            """)
        
        # =========================================================================
        # STEP 3: Update foreign key constraints
        # =========================================================================
        
        # Drop old foreign key constraints
        op.drop_constraint('user_favorites_story_id_fkey', 'user_favorites', type_='foreignkey')
        op.drop_constraint('story_ratings_story_id_fkey', 'story_ratings', type_='foreignkey')
        
        # Add new foreign key constraints pointing to bronze_stories
        op.create_foreign_key('user_favorites_story_id_fkey', 'user_favorites', 'bronze_stories', ['story_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('story_ratings_story_id_fkey', 'story_ratings', 'bronze_stories', ['story_id'], ['id'], ondelete='CASCADE')
        
        # =========================================================================
        # STEP 4: Drop old tables
        # =========================================================================
        
        # Drop old tables
        op.drop_table('search_logs')
        op.drop_table('scraping_jobs')
        op.drop_table('stories')
        
        print("Data migration completed successfully!")
    
    # =========================================================================
    # STEP 5: Create indexes
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
    
    # Enhanced user table indexes
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    
    # Enhanced user interaction indexes
    op.create_index('idx_user_favorites_created_at', 'user_favorites', ['created_at'])
    op.create_index('idx_story_ratings_user_id', 'story_ratings', ['user_id'])
    
    # Add unique constraints
    op.create_unique_constraint('unique_user_story_favorite', 'user_favorites', ['user_id', 'story_id'])
    op.create_unique_constraint('unique_user_story_rating', 'story_ratings', ['user_id', 'story_id'])
    
    # =========================================================================
    # STEP 6: Create triggers and functions
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


def downgrade():
    """Rollback medallion architecture (not recommended for production)."""
    
    print("Rolling back medallion architecture...")
    
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_chunk_search_vector_trigger ON silver_story_chunks')
    op.execute('DROP TRIGGER IF EXISTS update_favorites_performance_trigger ON user_favorites')
    op.execute('DROP TRIGGER IF EXISTS update_ratings_performance_trigger ON story_ratings')
    
    # Drop functions
    op.execute('DROP FUNCTION IF EXISTS update_chunk_search_vector()')
    op.execute('DROP FUNCTION IF EXISTS update_story_performance()')
    
    # Drop medallion tables
    op.drop_table('scraping_pipeline_metrics')
    op.drop_table('user_reading_behavior')
    op.drop_table('search_interactions')
    op.drop_table('gold_story_performance')
    op.drop_table('silver_story_chunks')
    op.drop_table('silver_stories')
    op.drop_table('bronze_stories')
    
    print("Medallion architecture rollback completed!")
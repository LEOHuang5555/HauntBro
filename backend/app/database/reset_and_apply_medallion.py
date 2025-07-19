"""
Reset database and apply medallion architecture cleanly.
This is a development-friendly approach that drops all tables and recreates them.
"""

from sqlalchemy import text
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_manager, init_database


def reset_and_apply_medallion():
    """Drop all tables and apply medallion architecture."""
    
    print("🗑️  Resetting database and applying medallion architecture...")
    
    with db_manager.get_session() as db:
        # Drop all tables in the correct order (reverse dependency order)
        print("Dropping existing tables...")
        
        drop_tables = [
            'user_reading_behavior',
            'search_interactions', 
            'scraping_pipeline_metrics',
            'gold_story_performance',
            'silver_story_chunks',
            'silver_stories',
            'story_ratings',
            'user_favorites',
            'bronze_stories',
            'search_logs',
            'scraping_jobs',
            'stories',
            'users',
            'alembic_version'  # Reset migration tracking
        ]
        
        for table in drop_tables:
            try:
                db.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))
                print(f"✓ Dropped {table}")
            except Exception as e:
                print(f"⚠️  Could not drop {table}: {e}")
        
        # Drop any remaining functions and triggers
        print("Dropping functions and triggers...")
        db.execute(text('DROP FUNCTION IF EXISTS update_chunk_search_vector() CASCADE'))
        db.execute(text('DROP FUNCTION IF EXISTS update_story_performance() CASCADE'))
        db.execute(text('DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE'))
        
        db.commit()
        print("✓ Database reset completed")
        
        # Enable required extensions
        print("Enabling required extensions...")
        db.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        # Note: Vector extension is optional and not available in this setup
        db.commit()
        
        # Create all medallion tables
        print("Creating medallion architecture tables...")
        
        # =====================================================================
        # BRONZE LAYER - Raw Data
        # =====================================================================
        
        db.execute(text('''
            CREATE TABLE bronze_stories (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                title TEXT,
                content TEXT,
                source VARCHAR(100),
                source_url VARCHAR(1000),
                author VARCHAR(100),
                post_date TIMESTAMP WITH TIME ZONE,
                scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                raw_metadata JSONB,
                CONSTRAINT valid_source CHECK (source IN ('ptt_marvel', 'reddit_ghoststories'))
            )
        '''))
        print("✓ Created bronze_stories")
        
        # =====================================================================
        # SILVER LAYER - Processed Data
        # =====================================================================
        
        db.execute(text('''
            CREATE TABLE silver_stories (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                bronze_story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
                title VARCHAR(500),
                cleaned_content TEXT,
                author VARCHAR(100),
                post_date TIMESTAMP WITH TIME ZONE,
                tags TEXT[],
                reading_time_minutes INTEGER,
                word_count INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(bronze_story_id)
            )
        '''))
        print("✓ Created silver_stories")
        
        db.execute(text('''
            CREATE TABLE silver_story_chunks (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                bronze_story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
                chunk_text TEXT NOT NULL,
                chunk_context TEXT,
                chunk_order INTEGER NOT NULL,
                embedding TEXT,
                search_vector TSVECTOR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(bronze_story_id, chunk_order)
            )
        '''))
        print("✓ Created silver_story_chunks")
        
        # =====================================================================
        # GOLD LAYER - Business Metrics
        # =====================================================================
        
        db.execute(text('''
            CREATE TABLE gold_story_performance (
                story_id UUID PRIMARY KEY REFERENCES bronze_stories(id) ON DELETE CASCADE,
                total_reads INTEGER DEFAULT 0,
                unique_readers INTEGER DEFAULT 0,
                avg_user_rating FLOAT,
                favorites_count INTEGER DEFAULT 0,
                search_impressions INTEGER DEFAULT 0,
                search_clicks INTEGER DEFAULT 0,
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        print("✓ Created gold_story_performance")
        
        # =====================================================================
        # USER LAYER - Application Features
        # =====================================================================
        
        db.execute(text('''
            CREATE TABLE users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP WITH TIME ZONE
            )
        '''))
        print("✓ Created users")
        
        db.execute(text('''
            CREATE TABLE user_favorites (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                UNIQUE(user_id, story_id)
            )
        '''))
        print("✓ Created user_favorites")
        
        db.execute(text('''
            CREATE TABLE story_ratings (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, story_id)
            )
        '''))
        print("✓ Created story_ratings")
        
        # =====================================================================
        # ANALYTICS LAYER - User Behavior & Search
        # =====================================================================
        
        db.execute(text('''
            CREATE TABLE search_interactions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                session_id UUID,
                query TEXT NOT NULL,
                search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                results_shown UUID[],
                results_clicked UUID[],
                click_positions INTEGER[],
                time_to_first_click INTEGER,
                search_type VARCHAR(50) DEFAULT 'hybrid',
                execution_time_ms INTEGER,
                CONSTRAINT valid_search_type CHECK (search_type IN ('keyword', 'semantic', 'hybrid'))
            )
        '''))
        print("✓ Created search_interactions")
        
        db.execute(text('''
            CREATE TABLE user_reading_behavior (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
                reading_start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                reading_duration INTEGER,
                return_visits INTEGER DEFAULT 1,
                favorited BOOLEAN DEFAULT FALSE,
                shared BOOLEAN DEFAULT FALSE,
                scroll_depth FLOAT,
                bounce_rate BOOLEAN DEFAULT FALSE
            )
        '''))
        print("✓ Created user_reading_behavior")
        
        # =====================================================================
        # PIPELINE LAYER - Data Engineering Metrics
        # =====================================================================
        
        db.execute(text('''
            CREATE TABLE scraping_pipeline_metrics (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                airflow_dag_run_id VARCHAR(250),
                source_name VARCHAR(100) NOT NULL,
                stories_discovered INTEGER DEFAULT 0,
                stories_new INTEGER DEFAULT 0,
                stories_updated INTEGER DEFAULT 0,
                duplicate_rate FLOAT DEFAULT 0.0,
                processing_time_seconds INTEGER,
                errors_count INTEGER DEFAULT 0,
                error_log TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_source_name CHECK (source_name IN ('ptt_marvel', 'reddit_ghoststories'))
            )
        '''))
        print("✓ Created scraping_pipeline_metrics")
        
        # =====================================================================
        # CREATE INDEXES
        # =====================================================================
        
        print("Creating indexes...")
        
        # Bronze layer indexes
        db.execute(text('CREATE INDEX idx_bronze_stories_source ON bronze_stories(source)'))
        db.execute(text('CREATE INDEX idx_bronze_stories_scraped_at ON bronze_stories(scraped_at)'))
        db.execute(text('CREATE INDEX idx_bronze_stories_post_date ON bronze_stories(post_date)'))
        db.execute(text('CREATE INDEX idx_bronze_stories_raw_metadata ON bronze_stories USING gin(raw_metadata)'))
        
        # Silver layer indexes
        db.execute(text('CREATE INDEX idx_silver_story_chunks_bronze_id ON silver_story_chunks(bronze_story_id)'))
        db.execute(text('CREATE INDEX idx_silver_story_chunks_search_vector ON silver_story_chunks USING gin(search_vector)'))
        db.execute(text('CREATE INDEX idx_silver_stories_bronze_id ON silver_stories(bronze_story_id)'))
        db.execute(text('CREATE INDEX idx_silver_stories_tags ON silver_stories USING gin(tags)'))
        db.execute(text('CREATE INDEX idx_silver_stories_post_date ON silver_stories(post_date)'))
        
        # Gold layer indexes
        db.execute(text('CREATE INDEX idx_gold_performance_total_reads ON gold_story_performance(total_reads)'))
        db.execute(text('CREATE INDEX idx_gold_performance_avg_rating ON gold_story_performance(avg_user_rating)'))
        db.execute(text('CREATE INDEX idx_gold_performance_last_updated ON gold_story_performance(last_updated)'))
        
        # User layer indexes
        db.execute(text('CREATE INDEX idx_users_username ON users(username)'))
        db.execute(text('CREATE INDEX idx_users_email ON users(email)'))
        db.execute(text('CREATE INDEX idx_users_created_at ON users(created_at)'))
        db.execute(text('CREATE INDEX idx_user_favorites_user_id ON user_favorites(user_id)'))
        db.execute(text('CREATE INDEX idx_user_favorites_story_id ON user_favorites(story_id)'))
        db.execute(text('CREATE INDEX idx_user_favorites_created_at ON user_favorites(created_at)'))
        db.execute(text('CREATE INDEX idx_story_ratings_user_id ON story_ratings(user_id)'))
        db.execute(text('CREATE INDEX idx_story_ratings_story_id ON story_ratings(story_id)'))
        db.execute(text('CREATE INDEX idx_story_ratings_rating ON story_ratings(rating)'))
        
        # Analytics layer indexes
        db.execute(text('CREATE INDEX idx_search_interactions_user_id ON search_interactions(user_id)'))
        db.execute(text('CREATE INDEX idx_search_interactions_session_id ON search_interactions(session_id)'))
        db.execute(text('CREATE INDEX idx_search_interactions_timestamp ON search_interactions(search_timestamp)'))
        db.execute(text('CREATE INDEX idx_search_interactions_query ON search_interactions(query)'))
        db.execute(text('CREATE INDEX idx_user_reading_behavior_user_id ON user_reading_behavior(user_id)'))
        db.execute(text('CREATE INDEX idx_user_reading_behavior_story_id ON user_reading_behavior(story_id)'))
        db.execute(text('CREATE INDEX idx_user_reading_behavior_start_time ON user_reading_behavior(reading_start_time)'))
        
        # Pipeline layer indexes
        db.execute(text('CREATE INDEX idx_scraping_pipeline_metrics_dag_run_id ON scraping_pipeline_metrics(airflow_dag_run_id)'))
        db.execute(text('CREATE INDEX idx_scraping_pipeline_metrics_source ON scraping_pipeline_metrics(source_name)'))
        db.execute(text('CREATE INDEX idx_scraping_pipeline_metrics_created_at ON scraping_pipeline_metrics(created_at)'))
        
        print("✓ Created all indexes")
        
        # =====================================================================
        # CREATE TRIGGERS AND FUNCTIONS
        # =====================================================================
        
        print("Creating functions and triggers...")
        
        # Function to update updated_at timestamp
        db.execute(text('''
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        '''))
        
        # Function to update search vector for chunks
        db.execute(text('''
            CREATE OR REPLACE FUNCTION update_chunk_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english', 
                    COALESCE(NEW.chunk_text, '') || ' ' || 
                    COALESCE(NEW.chunk_context, '')
                );
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        '''))
        
        # Function to update story performance metrics
        db.execute(text('''
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
            $$ language 'plpgsql'
        '''))
        
        # Create triggers
        db.execute(text('''
            CREATE TRIGGER update_users_updated_at 
                BEFORE UPDATE ON users
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        '''))
        
        db.execute(text('''
            CREATE TRIGGER update_story_ratings_updated_at 
                BEFORE UPDATE ON story_ratings
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        '''))
        
        db.execute(text('''
            CREATE TRIGGER update_chunk_search_vector_trigger
                BEFORE INSERT OR UPDATE ON silver_story_chunks
                FOR EACH ROW EXECUTE FUNCTION update_chunk_search_vector()
        '''))
        
        db.execute(text('''
            CREATE TRIGGER update_favorites_performance_trigger
                AFTER INSERT ON user_favorites
                FOR EACH ROW EXECUTE FUNCTION update_story_performance()
        '''))
        
        db.execute(text('''
            CREATE TRIGGER update_ratings_performance_trigger
                AFTER INSERT OR UPDATE ON story_ratings
                FOR EACH ROW EXECUTE FUNCTION update_story_performance()
        '''))
        
        print("✓ Created all triggers and functions")
        
        # Commit all changes
        db.commit()
        
        print("\n🎉 Medallion architecture applied successfully!")
        print("\nDatabase structure:")
        print("📊 Bronze Layer: bronze_stories")
        print("🔧 Silver Layer: silver_stories, silver_story_chunks") 
        print("📈 Gold Layer: gold_story_performance")
        print("👥 User Layer: users, user_favorites, story_ratings")
        print("📋 Analytics Layer: search_interactions, user_reading_behavior")
        print("🔧 Pipeline Layer: scraping_pipeline_metrics")
        print("\n✅ Ready for seeding with medallion architecture data!")


if __name__ == "__main__":
    reset_and_apply_medallion()
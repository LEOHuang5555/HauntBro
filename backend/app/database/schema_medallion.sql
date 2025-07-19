-- HauntBro Database Schema - Medallion Architecture
-- Ghost Story Search Engine with Bronze-Silver-Gold Data Pipeline

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector"; -- For embeddings (optional)

-- =============================================================================
-- BRONZE LAYER - Raw Data (Immutable)
-- =============================================================================

-- Raw scraped stories - immutable source of truth
CREATE TABLE bronze_stories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT,
    content TEXT,
    source VARCHAR(100), -- 'ptt_marvel', 'reddit_ghoststories'
    source_url VARCHAR(1000),
    author VARCHAR(100),
    post_date TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    raw_metadata JSONB, -- All original metadata
    
    -- Constraint for valid sources
    CONSTRAINT valid_source CHECK (source IN ('ptt_marvel', 'reddit_ghoststories'))
);

-- =============================================================================
-- SILVER LAYER - Processed Data
-- =============================================================================

-- Chunked stories for RAG retrieval
CREATE TABLE silver_story_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bronze_story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
    
    -- Chunking data
    chunk_text TEXT NOT NULL,           -- Actual chunk (512 tokens)
    chunk_context TEXT,                 -- Chunk + surrounding sentences for context
    chunk_order INTEGER NOT NULL,      -- Position in original story
    
    -- Search vectors
    embedding VECTOR(1536),             -- Semantic embedding for similarity search
    search_vector TSVECTOR,             -- Full-text search tokens
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique ordering per story
    UNIQUE(bronze_story_id, chunk_order)
);

-- Cleaned story metadata
CREATE TABLE silver_stories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bronze_story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
    title VARCHAR(500),
    cleaned_content TEXT,               -- Cleaned content (no emojis, excessive caps, etc.)
    author VARCHAR(100),
    post_date TIMESTAMP WITH TIME ZONE,
    tags TEXT[],
    reading_time_minutes INTEGER,
    word_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one-to-one relationship with bronze
    UNIQUE(bronze_story_id)
);

-- =============================================================================
-- GOLD LAYER - Business Metrics
-- =============================================================================

-- Business performance metrics
CREATE TABLE gold_story_performance (
    story_id UUID PRIMARY KEY REFERENCES bronze_stories(id) ON DELETE CASCADE,
    total_reads INTEGER DEFAULT 0,
    unique_readers INTEGER DEFAULT 0,
    avg_user_rating FLOAT,
    favorites_count INTEGER DEFAULT 0,
    search_impressions INTEGER DEFAULT 0,
    search_clicks INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- USER LAYER - Application Features
-- =============================================================================

-- User authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE
);

-- User bookmarks
CREATE TABLE user_favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    UNIQUE(user_id, story_id)
);

-- User ratings
CREATE TABLE story_ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, story_id)
);

-- =============================================================================
-- ANALYTICS LAYER - User Behavior & Search
-- =============================================================================

-- Search analytics (feasible to collect)
CREATE TABLE search_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID,
    query TEXT NOT NULL,
    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Interaction data
    results_shown UUID[],               -- Story IDs returned
    results_clicked UUID[],             -- Story IDs clicked
    click_positions INTEGER[],          -- Position of clicks in results
    time_to_first_click INTEGER,        -- Milliseconds
    
    -- Search performance
    search_type VARCHAR(50) DEFAULT 'hybrid', -- 'keyword', 'semantic', 'hybrid'
    execution_time_ms INTEGER,
    
    CONSTRAINT valid_search_type CHECK (search_type IN ('keyword', 'semantic', 'hybrid'))
);

-- Reading behavior (simplified, feasible)
CREATE TABLE user_reading_behavior (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    story_id UUID REFERENCES bronze_stories(id) ON DELETE CASCADE,
    
    reading_start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reading_duration INTEGER,           -- Seconds
    return_visits INTEGER DEFAULT 1,
    favorited BOOLEAN DEFAULT FALSE,
    shared BOOLEAN DEFAULT FALSE,
    
    -- Engagement metrics
    scroll_depth FLOAT,                 -- Percentage of content viewed
    bounce_rate BOOLEAN DEFAULT FALSE   -- Left immediately
);

-- =============================================================================
-- PIPELINE LAYER - Data Engineering Metrics
-- =============================================================================

-- Business-specific pipeline metrics (complements Airflow's built-in tables)
CREATE TABLE scraping_pipeline_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    airflow_dag_run_id VARCHAR(250),    -- Links to Airflow
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
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Bronze layer indexes
CREATE INDEX idx_bronze_stories_source ON bronze_stories(source);
CREATE INDEX idx_bronze_stories_scraped_at ON bronze_stories(scraped_at DESC);
CREATE INDEX idx_bronze_stories_post_date ON bronze_stories(post_date DESC);
CREATE INDEX idx_bronze_stories_raw_metadata ON bronze_stories USING gin(raw_metadata);

-- Silver layer indexes
CREATE INDEX idx_silver_story_chunks_bronze_id ON silver_story_chunks(bronze_story_id);
CREATE INDEX idx_silver_story_chunks_search_vector ON silver_story_chunks USING gin(search_vector);
CREATE INDEX idx_silver_story_chunks_embedding ON silver_story_chunks USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_silver_stories_bronze_id ON silver_stories(bronze_story_id);
CREATE INDEX idx_silver_stories_tags ON silver_stories USING gin(tags);
CREATE INDEX idx_silver_stories_post_date ON silver_stories(post_date DESC);

-- Gold layer indexes
CREATE INDEX idx_gold_performance_total_reads ON gold_story_performance(total_reads DESC);
CREATE INDEX idx_gold_performance_avg_rating ON gold_story_performance(avg_user_rating DESC);
CREATE INDEX idx_gold_performance_last_updated ON gold_story_performance(last_updated DESC);

-- User layer indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

CREATE INDEX idx_user_favorites_user_id ON user_favorites(user_id);
CREATE INDEX idx_user_favorites_story_id ON user_favorites(story_id);
CREATE INDEX idx_user_favorites_created_at ON user_favorites(created_at DESC);

CREATE INDEX idx_story_ratings_user_id ON story_ratings(user_id);
CREATE INDEX idx_story_ratings_story_id ON story_ratings(story_id);
CREATE INDEX idx_story_ratings_rating ON story_ratings(rating DESC);

-- Analytics layer indexes
CREATE INDEX idx_search_interactions_user_id ON search_interactions(user_id);
CREATE INDEX idx_search_interactions_session_id ON search_interactions(session_id);
CREATE INDEX idx_search_interactions_timestamp ON search_interactions(search_timestamp DESC);
CREATE INDEX idx_search_interactions_query ON search_interactions(query);

CREATE INDEX idx_user_reading_behavior_user_id ON user_reading_behavior(user_id);
CREATE INDEX idx_user_reading_behavior_story_id ON user_reading_behavior(story_id);
CREATE INDEX idx_user_reading_behavior_start_time ON user_reading_behavior(reading_start_time DESC);

-- Pipeline layer indexes
CREATE INDEX idx_scraping_pipeline_metrics_dag_run_id ON scraping_pipeline_metrics(airflow_dag_run_id);
CREATE INDEX idx_scraping_pipeline_metrics_source ON scraping_pipeline_metrics(source_name);
CREATE INDEX idx_scraping_pipeline_metrics_created_at ON scraping_pipeline_metrics(created_at DESC);

-- =============================================================================
-- TRIGGERS AND FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updating timestamps
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_story_ratings_updated_at 
    BEFORE UPDATE ON story_ratings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update search vector for chunks
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

-- Trigger for updating search vector
CREATE TRIGGER update_chunk_search_vector_trigger
    BEFORE INSERT OR UPDATE ON silver_story_chunks
    FOR EACH ROW EXECUTE FUNCTION update_chunk_search_vector();

-- Function to update story performance metrics
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

-- Triggers for updating performance metrics
CREATE TRIGGER update_favorites_performance_trigger
    AFTER INSERT ON user_favorites
    FOR EACH ROW EXECUTE FUNCTION update_story_performance();

CREATE TRIGGER update_ratings_performance_trigger
    AFTER INSERT OR UPDATE ON story_ratings
    FOR EACH ROW EXECUTE FUNCTION update_story_performance();
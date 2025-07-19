-- HauntBro Database Schema
-- Ghost Story Search Engine Database Design

-- Enable UUID extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table for authentication and user management
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

-- Stories table for storing scraped ghost stories
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(100) NOT NULL, -- 'ptt_marvel', 'reddit_ghoststories'
    source_url VARCHAR(1000),
    author VARCHAR(100),
    post_date TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Search optimization fields
    embedding VECTOR(1536), -- For storing embeddings (assuming OpenAI embeddings)
    search_vector TSVECTOR, -- For full-text search
    
    -- Metadata
    word_count INTEGER,
    reading_time_minutes INTEGER,
    tags TEXT[], -- Array of tags
    
    -- Quality indicators
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    
    -- Content classification
    is_nsfw BOOLEAN DEFAULT FALSE,
    content_warning TEXT,
    
    CONSTRAINT valid_source CHECK (source IN ('ptt_marvel', 'reddit_ghoststories'))
);

-- Search logs for analytics and improving search results
CREATE TABLE search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    results_count INTEGER NOT NULL,
    search_type VARCHAR(50) NOT NULL, -- 'keyword', 'semantic', 'hybrid'
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Search performance metrics
    execution_time_ms INTEGER,
    
    -- User interaction data
    clicked_results UUID[], -- Array of story IDs that were clicked
    session_id UUID,
    
    -- Search filters used
    source_filter VARCHAR(100),
    date_range_start TIMESTAMP WITH TIME ZONE,
    date_range_end TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_search_type CHECK (search_type IN ('keyword', 'semantic', 'hybrid'))
);

-- User favorites/bookmarks
CREATE TABLE user_favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    UNIQUE(user_id, story_id)
);

-- User ratings for stories
CREATE TABLE story_ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, story_id)
);

-- Scraping jobs tracking
CREATE TABLE scraping_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    stories_scraped INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_log TEXT,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

-- Indexes for performance optimization
CREATE INDEX idx_stories_source ON stories(source);
CREATE INDEX idx_stories_post_date ON stories(post_date DESC);
CREATE INDEX idx_stories_scraped_at ON stories(scraped_at DESC);
CREATE INDEX idx_stories_search_vector ON stories USING gin(search_vector);
CREATE INDEX idx_stories_tags ON stories USING gin(tags);

CREATE INDEX idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX idx_search_logs_executed_at ON search_logs(executed_at DESC);
CREATE INDEX idx_search_logs_query ON search_logs(query);

CREATE INDEX idx_user_favorites_user_id ON user_favorites(user_id);
CREATE INDEX idx_user_favorites_story_id ON user_favorites(story_id);

CREATE INDEX idx_story_ratings_story_id ON story_ratings(story_id);
CREATE INDEX idx_story_ratings_rating ON story_ratings(rating);

-- Triggers for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stories_updated_at BEFORE UPDATE ON stories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_story_ratings_updated_at BEFORE UPDATE ON story_ratings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update search vector when story content changes
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

CREATE TRIGGER update_story_search_vector_trigger
    BEFORE INSERT OR UPDATE ON stories
    FOR EACH ROW EXECUTE FUNCTION update_story_search_vector();
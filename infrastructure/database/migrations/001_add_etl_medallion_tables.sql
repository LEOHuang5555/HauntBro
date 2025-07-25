-- Migration: Add ETL Medallion Architecture Tables
-- Description: Creates tables for Bronze processing metadata, Silver chunks, and Gold metrics
-- Date: 2025-07-24
-- Author: ETL Medallion Architecture Implementation

-- Enable pgvector extension for embeddings (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Bronze Story Processing Table
CREATE TABLE IF NOT EXISTS bronze_story_processing (
    story_id UUID PRIMARY KEY REFERENCES bronze_stories(id) ON DELETE CASCADE,
    processing_status VARCHAR(20) DEFAULT 'pending' 
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'skipped')),
    etl_run_id VARCHAR(100),
    quality_checks JSONB,
    processing_metadata JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for Bronze Story Processing
CREATE INDEX IF NOT EXISTS idx_bronze_processing_status ON bronze_story_processing(processing_status);
CREATE INDEX IF NOT EXISTS idx_bronze_processing_etl_run_id ON bronze_story_processing(etl_run_id);
CREATE INDEX IF NOT EXISTS idx_bronze_processing_created_at ON bronze_story_processing(created_at);
CREATE INDEX IF NOT EXISTS idx_bronze_processing_updated_at ON bronze_story_processing(updated_at);

-- Silver Story Chunks Table
CREATE TABLE IF NOT EXISTS silver_story_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES bronze_stories(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_context TEXT NOT NULL,
    chunk_order INTEGER NOT NULL CHECK (chunk_order > 0),
    chunk_type VARCHAR(20),
    overlap_start INTEGER DEFAULT 0,
    overlap_end INTEGER DEFAULT 0,
    -- Embeddings stored as TEXT for now (will migrate to VECTOR type when pgvector is fully configured)
    content_embedding TEXT,
    search_embedding TEXT,
    chunk_length INTEGER NOT NULL CHECK (chunk_length > 0),
    chunk_word_count INTEGER DEFAULT 0 CHECK (chunk_word_count >= 0),
    semantic_keywords TEXT[],
    embedding_model VARCHAR(100) NOT NULL,
    embedding_version VARCHAR(20) NOT NULL,
    embedding_model_version VARCHAR(50),
    processing_language VARCHAR(10) CHECK (processing_language IN ('zh', 'en', 'mixed', 'unknown')),
    chunk_quality_score FLOAT CHECK (chunk_quality_score >= 0.0 AND chunk_quality_score <= 1.0),
    embedding_cost FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for Silver Story Chunks
CREATE INDEX IF NOT EXISTS idx_silver_chunks_story_id ON silver_story_chunks(story_id);
CREATE INDEX IF NOT EXISTS idx_silver_chunks_order ON silver_story_chunks(story_id, chunk_order);
CREATE INDEX IF NOT EXISTS idx_silver_chunks_language ON silver_story_chunks(processing_language);
CREATE INDEX IF NOT EXISTS idx_silver_chunks_quality ON silver_story_chunks(chunk_quality_score);
CREATE INDEX IF NOT EXISTS idx_silver_chunks_embedding_model ON silver_story_chunks(embedding_model_version);
CREATE INDEX IF NOT EXISTS idx_silver_chunks_created_at ON silver_story_chunks(created_at);

-- Gold Layer Metrics Table  
CREATE TABLE IF NOT EXISTS gold_layer_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type VARCHAR(50) NOT NULL 
        CHECK (metric_type IN ('daily_summary', 'user_behavior', 'content_performance', 'business_kpis')),
    metric_date TIMESTAMP WITH TIME ZONE NOT NULL,
    source_platform VARCHAR(20) CHECK (source_platform IN ('ptt', 'reddit', 'combined')),
    -- Aggregated metrics
    total_stories_processed INTEGER DEFAULT 0 CHECK (total_stories_processed >= 0),
    total_chunks_generated INTEGER DEFAULT 0 CHECK (total_chunks_generated >= 0),
    avg_quality_score FLOAT CHECK (avg_quality_score >= 0.0 AND avg_quality_score <= 1.0),
    total_embeddings_cost FLOAT,
    processing_time_minutes INTEGER,
    -- User engagement metrics
    total_searches INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    avg_session_duration FLOAT,
    bounce_rate FLOAT,
    -- Content performance metrics  
    top_performing_stories UUID[],
    trending_keywords TEXT[],
    language_distribution JSONB,
    -- Business metrics
    conversion_rate FLOAT,
    revenue_attribution FLOAT,
    user_lifetime_value FLOAT,
    -- ETL metadata
    etl_run_id VARCHAR(100),
    data_freshness_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Unique constraint to prevent duplicate metrics
    UNIQUE(metric_type, metric_date, source_platform)
);

-- Indexes for Gold Layer Metrics
CREATE INDEX IF NOT EXISTS idx_gold_metrics_type ON gold_layer_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_gold_metrics_date ON gold_layer_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_gold_metrics_platform ON gold_layer_metrics(source_platform);
CREATE INDEX IF NOT EXISTS idx_gold_metrics_etl_run ON gold_layer_metrics(etl_run_id);
CREATE INDEX IF NOT EXISTS idx_gold_metrics_created_at ON gold_layer_metrics(created_at);

-- Add update trigger for bronze_story_processing
CREATE OR REPLACE FUNCTION update_bronze_processing_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bronze_processing_updated_at_trigger
    BEFORE UPDATE ON bronze_story_processing
    FOR EACH ROW
    EXECUTE FUNCTION update_bronze_processing_updated_at();

-- Create views for common ETL queries
CREATE OR REPLACE VIEW etl_processing_summary AS
SELECT 
    bsp.processing_status,
    COUNT(*) as story_count,
    AVG(EXTRACT(EPOCH FROM (bsp.updated_at - bsp.created_at))/60) as avg_processing_time_minutes,
    AVG(ssc_stats.chunk_count) as avg_chunks_per_story,
    AVG(ssc_stats.avg_quality_score) as avg_quality_score
FROM bronze_story_processing bsp
LEFT JOIN LATERAL (
    SELECT 
        COUNT(*) as chunk_count,
        AVG(chunk_quality_score) as avg_quality_score
    FROM silver_story_chunks ssc 
    WHERE ssc.story_id = bsp.story_id
) ssc_stats ON true
GROUP BY bsp.processing_status;

-- Create view for daily processing metrics
CREATE OR REPLACE VIEW daily_etl_metrics AS
SELECT 
    DATE(bsp.created_at) as processing_date,
    COUNT(*) as total_stories,
    COUNT(CASE WHEN bsp.processing_status = 'completed' THEN 1 END) as completed_stories,
    COUNT(CASE WHEN bsp.processing_status = 'failed' THEN 1 END) as failed_stories,
    AVG(CASE WHEN bsp.processing_status = 'completed' 
        THEN EXTRACT(EPOCH FROM (bsp.updated_at - bsp.created_at))
        END)/60 as avg_processing_time_minutes,
    SUM(ssc_stats.chunk_count) as total_chunks_generated,
    AVG(ssc_stats.avg_quality_score) as overall_quality_score
FROM bronze_story_processing bsp
LEFT JOIN LATERAL (
    SELECT 
        COUNT(*) as chunk_count,
        AVG(chunk_quality_score) as avg_quality_score
    FROM silver_story_chunks ssc 
    WHERE ssc.story_id = bsp.story_id
) ssc_stats ON true
GROUP BY DATE(bsp.created_at)
ORDER BY processing_date DESC;

-- Grant permissions (adjust as needed based on your user setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON bronze_story_processing TO etl_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON silver_story_chunks TO etl_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON gold_layer_metrics TO etl_user;
-- GRANT SELECT ON etl_processing_summary TO etl_user;
-- GRANT SELECT ON daily_etl_metrics TO etl_user;

-- Insert initial data for testing (optional)
-- This will be handled by the actual ETL pipeline

COMMENT ON TABLE bronze_story_processing IS 'Tracks ETL processing status and metadata for each bronze story';
COMMENT ON TABLE silver_story_chunks IS 'Processed and chunked stories with embeddings for semantic search';  
COMMENT ON TABLE gold_layer_metrics IS 'Business intelligence metrics aggregated from silver layer data';
COMMENT ON VIEW etl_processing_summary IS 'Summary view of ETL processing status and performance metrics';
COMMENT ON VIEW daily_etl_metrics IS 'Daily aggregated ETL processing metrics for monitoring';
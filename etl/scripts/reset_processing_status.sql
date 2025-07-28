-- Reset Bronze to Silver ETL Pipeline
-- This script resets processing status and clears silver layer data

-- 1. Reset all bronze_story_processing status to 'pending'
UPDATE bronze_story_processing 
SET processing_status = 'pending',
    processing_metadata = jsonb_build_object(
        'reset_at', now()::text,
        'reset_reason', 'pipeline_optimization'
    ),
    error_message = NULL,
    quality_checks = NULL,
    updated_at = now()
WHERE processing_status != 'pending';

-- 2. Clear silver layer data to start fresh
DELETE FROM silver_story_chunks;
DELETE FROM silver_stories;

-- 3. Show reset summary
SELECT 
    'Bronze Processing Status Reset' as action,
    COUNT(*) as affected_records
FROM bronze_story_processing 
WHERE processing_status = 'pending'

UNION ALL

SELECT 
    'Silver Stories Cleared' as action,
    0 as affected_records

UNION ALL

SELECT 
    'Silver Chunks Cleared' as action,
    0 as affected_records;

-- 4. Show current status distribution
SELECT 
    processing_status,
    COUNT(*) as count
FROM bronze_story_processing 
GROUP BY processing_status
ORDER BY count DESC;
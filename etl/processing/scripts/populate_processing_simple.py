#!/usr/bin/env python3
"""
Simple script to populate bronze_story_processing table for existing bronze_stories
Uses direct SQL to avoid ORM complexity
"""

import sys
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    try:
        # Try to load from .env file
        env_file = Path(__file__).resolve().parents[3] / '.env'
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value.strip('"\'')
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def populate_processing_table():
    """Populate bronze_story_processing table with existing stories"""
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check current state
            cur.execute("SELECT COUNT(*) as count FROM bronze_stories")
            total_stories = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM bronze_story_processing")
            existing_processing = cur.fetchone()['count']
            
            logger.info(f"Total bronze stories: {total_stories}")
            logger.info(f"Existing processing records: {existing_processing}")
            
            if total_stories == 0:
                logger.warning("No bronze stories found!")
                return
            
            # Find stories without processing records that have valid content
            cur.execute("""
                SELECT bs.id, bs.title, bs.content, bs.source, bs.scraped_at
                FROM bronze_stories bs
                LEFT JOIN bronze_story_processing bsp ON bs.id = bsp.story_id
                WHERE bsp.story_id IS NULL
                AND bs.content IS NOT NULL
                AND LENGTH(bs.content) >= 50
                ORDER BY bs.scraped_at DESC
            """)
            
            untracked_stories = cur.fetchall()
            logger.info(f"Stories without processing records: {len(untracked_stories)}")
            
            if len(untracked_stories) == 0:
                logger.info("All valid stories already have processing records!")
                return
            
            # Insert processing records
            insert_query = """
                INSERT INTO bronze_story_processing 
                (story_id, processing_status, processing_metadata, error_message, retry_count, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            processing_records = []
            current_time = datetime.utcnow()
            
            for story in untracked_stories:
                metadata = {
                    'created_by': 'populate_processing_simple_script',
                    'story_length': len(story['content']),
                    'story_source': story['source'],
                    'story_title': story['title']
                }
                
                record = (
                    story['id'],           # story_id
                    'pending',             # processing_status
                    json.dumps(metadata),  # processing_metadata
                    None,                  # error_message
                    0,                     # retry_count
                    current_time,          # created_at
                    current_time           # updated_at
                )
                processing_records.append(record)
            
            # Bulk insert
            cur.executemany(insert_query, processing_records)
            conn.commit()
            
            logger.info(f"✅ Created {len(processing_records)} processing records")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error populating processing table: {e}")
        raise
    finally:
        conn.close()

def check_processing_status():
    """Check current processing status"""
    conn = get_db_connection()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Status breakdown
            cur.execute("""
                SELECT processing_status, COUNT(*) as count
                FROM bronze_story_processing 
                GROUP BY processing_status
                ORDER BY processing_status
            """)
            
            logger.info("Processing Status Breakdown:")
            for row in cur.fetchall():
                logger.info(f"  {row['processing_status']}: {row['count']}")
            
            # Stories ready for processing
            cur.execute("""
                SELECT COUNT(*) as ready_count
                FROM bronze_stories bs
                LEFT JOIN bronze_story_processing bsp ON bs.id = bsp.story_id
                LEFT JOIN silver_story_chunks ssc ON bs.id = ssc.story_id
                WHERE bs.content IS NOT NULL 
                AND LENGTH(bs.content) >= 50
                AND (
                    bsp.processing_status IS NULL 
                    OR bsp.processing_status IN ('pending', 'failed')
                )
                AND ssc.story_id IS NULL
            """)
            
            result = cur.fetchone()
            logger.info(f"Stories ready for silver processing: {result['ready_count']}")
            
    except Exception as e:
        logger.error(f"❌ Error checking status: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate bronze_story_processing table")
    parser.add_argument('--check-only', action='store_true', 
                       help='Only check status, do not populate')
    
    args = parser.parse_args()
    
    try:
        if args.check_only:
            logger.info("🔍 Checking processing status...")
            check_processing_status()
        else:
            logger.info("🚀 Populating bronze_story_processing table...")
            populate_processing_table()
            
            logger.info("🔍 Checking final status...")
            check_processing_status()
            
        logger.info("✅ Script completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)
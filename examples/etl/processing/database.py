import asyncio
import asyncpg
import json
from typing import List, Dict, Optional
from datetime import datetime
from config import CONFIG

class DatabaseManager:
    """Database operations for the chunking pipeline"""
    
    def __init__(self):
        self.pool = None
        self.db_config = CONFIG["database"]
    
    async def connect(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.database,
                user=self.db_config.username,
                password=self.db_config.password,
                min_size=self.db_config.min_connections,
                max_size=self.db_config.max_connections,
                command_timeout=60
            )
            print("✅ Database connection pool created")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            print("Database connections closed")
    
    async def get_unprocessed_stories(self, limit: int = 50) -> List[Dict]:
        """Get stories from bronze layer that need chunking"""
        query = """
        SELECT bs.id, bs.title, bs.content, bs.source, bs.post_date
        FROM bronze_stories bs
        LEFT JOIN silver_story_chunks ssc ON bs.id = ssc.story_id
        WHERE ssc.story_id IS NULL  -- Not yet processed into chunks
        AND LENGTH(bs.content) >= $1  -- Minimum content length
        AND bs.content IS NOT NULL
        ORDER BY bs.scraped_at DESC
        LIMIT $2
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, CONFIG["chunking"].min_chunk_size, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error fetching unprocessed stories: {e}")
            return []
    
    async def save_chunks_to_silver(self, chunks: List[Dict]) -> bool:
        """Save processed chunks to silver_story_chunks table"""
        if not chunks:
            return True
        
        insert_query = """
        INSERT INTO silver_story_chunks (
            id, story_id, chunk_text, chunk_context, chunk_order, chunk_type,
            overlap_start, overlap_end, content_embedding, search_embedding,
            chunk_length, chunk_word_count, semantic_keywords,
            embedding_model, embedding_version, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        ON CONFLICT (id) DO NOTHING  -- Avoid duplicates
        """
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for chunk in chunks:
                        await conn.execute(
                            insert_query,
                            chunk['id'],
                            chunk['story_id'],
                            chunk['chunk_text'],
                            chunk['chunk_context'],
                            chunk['chunk_order'],
                            chunk['chunk_type'],
                            chunk['overlap_start'],
                            chunk['overlap_end'],
                            chunk.get('content_embedding'),
                            chunk.get('search_embedding'),
                            chunk['chunk_length'],
                            chunk['chunk_word_count'],
                            chunk.get('semantic_keywords', []),
                            chunk.get('embedding_model', 'text-embedding-3-small'),
                            chunk.get('embedding_version', '2024-01'),
                            chunk.get('created_at', datetime.utcnow())
                        )
            
            print(f"✅ Saved {len(chunks)} chunks to database")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save chunks: {e}")
            return False
    
    async def update_story_processing_status(self, story_id: str, status: str, metadata: Dict = None) -> bool:
        """Update processing status in bronze_stories"""
        query = """
        UPDATE bronze_stories 
        SET raw_metadata = COALESCE(raw_metadata, '{}'::jsonb) || jsonb_build_object(
            'processing_status', $2,
            'last_processed', $3,
            'processing_metadata', $4
        )
        WHERE id = $1
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query, 
                    story_id, 
                    status, 
                    datetime.utcnow().isoformat(),
                    json.dumps(metadata or {})
                )
            return True
        except Exception as e:
            print(f"Failed to update processing status: {e}")
            return False
    
    async def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        queries = {
            'total_stories': "SELECT COUNT(*) FROM bronze_stories",
            'processed_stories': """
                SELECT COUNT(DISTINCT story_id) 
                FROM silver_story_chunks
            """,
            'total_chunks': "SELECT COUNT(*) FROM silver_story_chunks",
            'avg_chunks_per_story': """
                SELECT AVG(chunk_count) 
                FROM (
                    SELECT story_id, COUNT(*) as chunk_count 
                    FROM silver_story_chunks 
                    GROUP BY story_id
                ) subq
            """
        }
        
        stats = {}
        try:
            async with self.pool.acquire() as conn:
                for key, query in queries.items():
                    result = await conn.fetchval(query)
                    stats[key] = result
            
            # Calculate pending stories
            stats['pending_stories'] = stats['total_stories'] - stats['processed_stories']
            
            return stats
            
        except Exception as e:
            print(f"Error getting processing stats: {e}")
            return {}
    
    async def cleanup_failed_chunks(self, story_id: str) -> bool:
        """Remove failed/incomplete chunks for a story"""
        query = "DELETE FROM silver_story_chunks WHERE story_id = $1"
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, story_id)
                print(f"Cleaned up chunks for story {story_id}")
                return True
        except Exception as e:
            print(f"Failed to cleanup chunks: {e}")
            return False
    
    async def get_story_chunks(self, story_id: str) -> List[Dict]:
        """Get all chunks for a specific story"""
        query = """
        SELECT * FROM silver_story_chunks 
        WHERE story_id = $1 
        ORDER BY chunk_order ASC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, story_id)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error fetching story chunks: {e}")
            return []
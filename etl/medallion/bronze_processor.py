"""
Bronze Layer Processor - Immutable Data Ingestion
Implements medallion architecture bronze layer with audit trails, Kafka integration, and duplicate detection.
"""

import asyncio
import asyncpg
import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.config.config import CONFIG
from infrastructure.database.models import BronzeStory, BronzeStoryProcessing

# Kafka imports for real-time ingestion
try:
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False


@dataclass
class BronzeIngestionResult:
    """Result of bronze layer ingestion operation"""
    story_id: str
    status: str  # 'inserted', 'duplicate', 'failed'
    is_duplicate: bool
    processing_time_ms: int
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class BronzeProcessor:
    """
    Bronze Layer Processor for immutable data ingestion
    Handles raw data preservation with audit trails and real-time streaming
    """
    
    def __init__(self, kafka_config: Optional[Dict] = None):
        """Initialize Bronze Processor with database and Kafka connections"""
        self.pool = None
        self.db_config = CONFIG["database"]
        self.kafka_config = kafka_config or self._get_default_kafka_config()
        self.kafka_producer = None
        self.stats = {
            'total_processed': 0,
            'inserted': 0,
            'duplicates': 0,
            'failed': 0,
            'processing_time': 0.0
        }
        
    def _get_default_kafka_config(self) -> Dict:
        """Get default Kafka configuration"""
        return {
            'bootstrap_servers': ['localhost:9092'],
            'topics': {
                'bronze_stories': 'bronze_stories',
                'processing_events': 'bronze_processing_events'
            },
            'producer_config': {
                'enable_idempotence': True,  # Exactly-once semantics
                'acks': 'all',
                'retries': 3,
                'key_serializer': lambda x: x.encode('utf-8') if x else None,
                'value_serializer': lambda x: json.dumps(x).encode('utf-8')
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize database connection pool and Kafka producer"""
        try:
            # Initialize database connection pool
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
            print("✅ Bronze processor database connection pool created")
            
            # Initialize Kafka producer if available
            if KAFKA_AVAILABLE:
                self.kafka_producer = KafkaProducer(**self.kafka_config['producer_config'])
                print("✅ Kafka producer initialized for real-time ingestion")
            else:
                print("⚠️  Kafka not available - running without real-time streaming")
                
            return True
            
        except Exception as e:
            print(f"❌ Bronze processor initialization failed: {e}")
            return False
    
    async def disconnect(self):
        """Close database connections and Kafka producer"""
        if self.pool:
            await self.pool.close()
            print("Database connections closed")
            
        if self.kafka_producer:
            self.kafka_producer.close()
            print("Kafka producer closed")
    
    def _generate_content_hash(self, content: str, source_url: str) -> str:
        """Generate SHA-256 hash for duplicate detection"""
        # Combine content and source URL for unique identification
        combined = f"{content.strip()}{source_url}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def _create_audit_metadata(self, etl_run_id: str, source_info: Dict) -> Dict:
        """Create comprehensive audit metadata"""
        return {
            'ingestion_timestamp': datetime.now(timezone.utc).isoformat(),
            'etl_run_id': etl_run_id,
            'source_info': source_info,
            'processor_version': '1.0.0',
            'validation_rules_applied': ['duplicate_check', 'content_length_check'],
            'data_lineage': {
                'source_system': source_info.get('source', 'unknown'),
                'extraction_method': source_info.get('extraction_method', 'scraper'),
                'transformation_applied': 'none'  # Bronze layer = no transformation
            }
        }
    
    async def _check_duplicate_by_hash(self, content_hash: str) -> Optional[str]:
        """Check if content already exists using hash-based deduplication"""
        query = """
        SELECT id FROM bronze_stories 
        WHERE raw_metadata->>'content_hash' = $1
        LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(query, content_hash)
                return str(result['id']) if result else None
        except Exception as e:
            print(f"Error checking duplicate: {e}")
            return None
    
    async def _check_duplicate_by_url(self, source_url: str) -> Optional[str]:
        """Check if story already exists by source URL"""
        query = """
        SELECT id FROM bronze_stories 
        WHERE source_url = $1
        LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(query, source_url)
                return str(result['id']) if result else None
        except Exception as e:
            print(f"Error checking URL duplicate: {e}")
            return None
    
    async def ingest_story(self, story_data: Dict, etl_run_id: str) -> BronzeIngestionResult:
        """
        Ingest a single story into the bronze layer with immutable storage
        
        Args:
            story_data: Raw story data from scraper
            etl_run_id: Airflow DAG run ID for lineage tracking
            
        Returns:
            BronzeIngestionResult with processing details
        """
        start_time = datetime.now()
        story_id = str(uuid.uuid4())
        
        try:
            # Extract required fields
            title = story_data.get('title', '')
            content = story_data.get('content', '')
            source = story_data.get('source', '')
            source_url = story_data.get('source_url', '')
            author = story_data.get('author', '')
            post_date = story_data.get('post_date')
            
            # Validate minimum required data
            if not content or not source_url:
                return BronzeIngestionResult(
                    story_id=story_id,
                    status='failed',
                    is_duplicate=False,
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    error_message="Missing required fields: content or source_url"
                )
            
            # Generate content hash for duplicate detection
            content_hash = self._generate_content_hash(content, source_url)
            
            # Check for duplicates using both hash and URL
            duplicate_by_hash = await self._check_duplicate_by_hash(content_hash)
            duplicate_by_url = await self._check_duplicate_by_url(source_url)
            
            if duplicate_by_hash or duplicate_by_url:
                existing_id = duplicate_by_hash or duplicate_by_url
                print(f"📭 Duplicate story detected: {existing_id}")
                
                # Update processing metadata for duplicate
                await self._update_processing_status(
                    existing_id, 'skipped', etl_run_id, 
                    {'reason': 'duplicate', 'duplicate_detection_method': 'hash_and_url'}
                )
                
                return BronzeIngestionResult(
                    story_id=existing_id,
                    status='duplicate',
                    is_duplicate=True,
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                )
            
            # Create audit metadata
            audit_metadata = self._create_audit_metadata(etl_run_id, {
                'source': source,
                'extraction_method': 'scraper',
                'original_data_keys': list(story_data.keys())
            })
            
            # Add content hash to metadata
            raw_metadata = story_data.copy()
            raw_metadata.update({
                'content_hash': content_hash,
                'audit_trail': audit_metadata,
                'ingestion_metadata': {
                    'content_length': len(content),
                    'title_length': len(title),
                    'estimated_language': self._detect_language_simple(content)
                }
            })
            
            # Insert into bronze_stories table (immutable)
            insert_query = """
            INSERT INTO bronze_stories (
                id, title, content, source, source_url, author, post_date, 
                scraped_at, raw_metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8)
            """
            
            # Insert processing metadata
            processing_query = """
            INSERT INTO bronze_story_processing (
                story_id, processing_status, etl_run_id, processing_metadata, created_at
            ) VALUES ($1, $2, $3, $4, NOW())
            """
            
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Insert bronze story
                    await conn.execute(
                        insert_query,
                        story_id, title, content, source, source_url, author,
                        post_date, json.dumps(raw_metadata)
                    )
                    
                    # Insert processing metadata
                    processing_metadata = {
                        'processing_start_time': start_time.isoformat(),
                        'content_hash': content_hash,
                        'validation_passed': True
                    }
                    
                    await conn.execute(
                        processing_query,
                        story_id, 'pending', etl_run_id, json.dumps(processing_metadata)
                    )
            
            # Send to Kafka for real-time processing (if available)
            await self._send_to_kafka('bronze_stories', {
                'story_id': story_id,
                'source': source,
                'etl_run_id': etl_run_id,
                'event_type': 'story_ingested',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            print(f"✅ Story ingested: {story_id} ({processing_time_ms}ms)")
            
            return BronzeIngestionResult(
                story_id=story_id,
                status='inserted',
                is_duplicate=False,
                processing_time_ms=processing_time_ms,
                metadata={'content_hash': content_hash}
            )
            
        except Exception as e:
            error_msg = f"Error ingesting story: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Record failed processing
            try:
                await self._update_processing_status(
                    story_id, 'failed', etl_run_id, 
                    {'error_message': error_msg, 'error_type': type(e).__name__}
                )
            except:
                pass  # Don't fail completely if we can't update status
            
            return BronzeIngestionResult(
                story_id=story_id,
                status='failed',
                is_duplicate=False,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error_message=error_msg
            )
    
    async def ingest_batch(self, stories: List[Dict], etl_run_id: str) -> List[BronzeIngestionResult]:
        """
        Ingest multiple stories in batch with controlled concurrency
        
        Args:
            stories: List of raw story data from scrapers
            etl_run_id: Airflow DAG run ID for lineage tracking
            
        Returns:
            List of BronzeIngestionResult for each story
        """
        batch_start_time = datetime.now()
        
        print(f"📚 Processing batch of {len(stories)} stories...")
        
        # Process stories with controlled concurrency (max 5 concurrent)
        semaphore = asyncio.Semaphore(5)
        
        async def process_with_semaphore(story_data):
            async with semaphore:
                return await self.ingest_story(story_data, etl_run_id)
        
        # Process all stories concurrently
        tasks = [process_with_semaphore(story) for story in stories]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Story {i} failed with exception: {result}")
                processed_results.append(BronzeIngestionResult(
                    story_id=str(uuid.uuid4()),
                    status='failed',
                    is_duplicate=False,
                    processing_time_ms=0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        # Update statistics
        self._update_batch_stats(processed_results, batch_start_time)
        
        # Send batch completion event to Kafka
        await self._send_to_kafka('processing_events', {
            'event_type': 'batch_completed',
            'etl_run_id': etl_run_id,
            'batch_size': len(stories),
            'results_summary': self._summarize_results(processed_results),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        return processed_results
    
    def _detect_language_simple(self, content: str) -> str:
        """Simple language detection based on character composition"""
        if not content:
            return 'unknown'
            
        # Count Chinese characters
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        total_chars = len(content.replace(' ', ''))
        
        if total_chars == 0:
            return 'unknown'
            
        chinese_ratio = chinese_chars / total_chars
        
        if chinese_ratio > 0.3:
            return 'zh'  # Chinese dominant
        elif chinese_ratio < 0.1:
            return 'en'  # Likely English
        else:
            return 'mixed'  # Mixed language
    
    async def _update_processing_status(self, story_id: str, status: str, etl_run_id: str, metadata: Dict):
        """Update processing status for a story"""
        query = """
        UPDATE bronze_story_processing 
        SET processing_status = $2, 
            processing_metadata = processing_metadata || $3,
            error_message = $4,
            updated_at = NOW()
        WHERE story_id = $1
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query, 
                    story_id, 
                    status, 
                    json.dumps(metadata),
                    metadata.get('error_message')
                )
        except Exception as e:
            print(f"Error updating processing status: {e}")
    
    async def _send_to_kafka(self, topic_key: str, message: Dict):
        """Send message to Kafka topic for real-time processing"""
        if not self.kafka_producer:
            return
            
        try:
            topic = self.kafka_config['topics'].get(topic_key)
            if topic:
                future = self.kafka_producer.send(
                    topic, 
                    key=message.get('story_id', ''),
                    value=message
                )
                # Don't wait for completion to avoid blocking
                print(f"📨 Sent to Kafka topic '{topic}': {message.get('event_type', 'message')}")
        except Exception as e:
            print(f"⚠️  Kafka send failed: {e}")
    
    def _update_batch_stats(self, results: List[BronzeIngestionResult], start_time: datetime):
        """Update processing statistics"""
        self.stats['total_processed'] += len(results)
        
        for result in results:
            if result.status == 'inserted':
                self.stats['inserted'] += 1
            elif result.status == 'duplicate':
                self.stats['duplicates'] += 1
            elif result.status == 'failed':
                self.stats['failed'] += 1
        
        batch_time = (datetime.now() - start_time).total_seconds()
        self.stats['processing_time'] += batch_time
    
    def _summarize_results(self, results: List[BronzeIngestionResult]) -> Dict:
        """Create summary of batch processing results"""
        summary = {
            'total': len(results),
            'inserted': len([r for r in results if r.status == 'inserted']),
            'duplicates': len([r for r in results if r.status == 'duplicate']),
            'failed': len([r for r in results if r.status == 'failed']),
            'avg_processing_time_ms': sum(r.processing_time_ms for r in results) / len(results) if results else 0
        }
        return summary
    
    async def get_processing_stats(self) -> Dict:
        """Get comprehensive processing statistics"""
        stats_query = """
        SELECT 
            processing_status,
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_processing_time_seconds
        FROM bronze_story_processing 
        GROUP BY processing_status
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(stats_query)
                
            db_stats = {}
            for row in rows:
                db_stats[row['processing_status']] = {
                    'count': row['count'],
                    'avg_processing_time_seconds': float(row['avg_processing_time_seconds'] or 0)
                }
            
            # Combine with in-memory stats
            combined_stats = {
                'session_stats': self.stats,
                'database_stats': db_stats,
                'duplicate_rate': self.stats['duplicates'] / max(self.stats['total_processed'], 1),
                'success_rate': self.stats['inserted'] / max(self.stats['total_processed'], 1),
                'avg_processing_time_seconds': self.stats['processing_time'] / max(self.stats['total_processed'], 1)
            }
            
            return combined_stats
            
        except Exception as e:
            print(f"Error getting processing stats: {e}")
            return {'error': str(e), 'session_stats': self.stats}
    
    async def cleanup_failed_processing(self, max_age_hours: int = 24) -> int:
        """Clean up old failed processing records"""
        cleanup_query = """
        DELETE FROM bronze_story_processing 
        WHERE processing_status = 'failed' 
        AND created_at < NOW() - INTERVAL '%s hours'
        """
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(cleanup_query % max_age_hours)
                cleaned_count = int(result.split()[-1])  # Extract count from "DELETE n"
                print(f"🧹 Cleaned up {cleaned_count} old failed processing records")
                return cleaned_count
        except Exception as e:
            print(f"Error during cleanup: {e}")
            return 0


# CLI interface for testing
async def main():
    """Main CLI interface for testing bronze processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bronze Layer Processor")
    parser.add_argument('--test-data', type=str, help='Path to test data JSON file')
    parser.add_argument('--etl-run-id', type=str, default='test-run', help='ETL run ID')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    
    args = parser.parse_args()
    
    processor = BronzeProcessor()
    
    try:
        await processor.initialize()
        
        if args.stats:
            stats = await processor.get_processing_stats()
            print(f"📊 Processing Statistics: {json.dumps(stats, indent=2)}")
        
        if args.test_data:
            with open(args.test_data, 'r') as f:
                test_stories = json.load(f)
            
            results = await processor.ingest_batch(test_stories, args.etl_run_id)
            
            print(f"\n📋 Batch Results:")
            for result in results:
                print(f"  {result.story_id}: {result.status} ({result.processing_time_ms}ms)")
                
        print("\n📊 Final Statistics:")
        final_stats = await processor.get_processing_stats()
        print(json.dumps(final_stats, indent=2))
        
    finally:
        await processor.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
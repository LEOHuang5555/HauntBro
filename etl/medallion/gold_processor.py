"""
Gold Layer Processor - Business Intelligence
Aggregates silver layer data into business metrics and user analytics
"""

import asyncio
import asyncpg
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import sys
import statistics
from collections import Counter, defaultdict

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.processing.config import CONFIG
from infrastructure.database.models import GoldLayerMetrics


@dataclass
class BusinessMetrics:
    """Business intelligence metrics for a time period"""
    metric_date: datetime
    source_platform: str  # 'ptt', 'reddit', 'combined'
    total_stories_processed: int
    total_chunks_generated: int
    avg_quality_score: float
    total_embeddings_cost: float
    processing_time_minutes: int
    
    # User engagement metrics
    total_searches: int
    unique_users: int
    avg_session_duration: float
    bounce_rate: float
    
    # Content performance metrics
    top_performing_stories: List[str]
    trending_keywords: List[str]
    language_distribution: Dict[str, int]
    
    # Business KPIs
    conversion_rate: float
    revenue_attribution: float
    user_lifetime_value: float


@dataclass
class GoldProcessingResult:
    """Result of gold layer processing"""
    success: bool
    metrics_generated: int
    processing_time_ms: int
    date_range: Tuple[datetime, datetime]
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class GoldProcessor:
    """
    Gold Layer Processor for business intelligence aggregations
    Transforms Silver layer data into actionable business metrics
    """
    
    def __init__(self):
        """Initialize gold processor"""
        self.pool = None
        self.db_config = CONFIG["database"]
        
        # Processing statistics
        self.stats = {
            'total_metrics_generated': 0,
            'daily_summaries': 0,
            'user_behavior_metrics': 0,
            'content_performance_metrics': 0,
            'business_kpis': 0,
            'processing_errors': 0,
            'avg_processing_time': 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize database connections"""
        try:
            print("🚀 Initializing Gold Layer Processor...")
            
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
            print("✅ Gold processor database connection pool created")
            return True
            
        except Exception as e:
            print(f"❌ Gold processor initialization failed: {e}")
            return False
    
    async def disconnect(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            print("Gold processor database connections closed")
    
    async def calculate_daily_summary_metrics(self, target_date: datetime, source_platform: str = 'combined') -> BusinessMetrics:
        """
        Calculate daily summary metrics for a specific date and platform
        
        Args:
            target_date: Date to calculate metrics for
            source_platform: 'ptt', 'reddit', or 'combined'
            
        Returns:
            BusinessMetrics object with aggregated data
        """
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        try:
            async with self.pool.acquire() as conn:
                # Story processing metrics
                story_metrics = await self._get_story_processing_metrics(conn, start_date, end_date, source_platform)
                
                # Chunk generation metrics
                chunk_metrics = await self._get_chunk_metrics(conn, start_date, end_date, source_platform)
                
                # Quality and cost metrics
                quality_metrics = await self._get_quality_metrics(conn, start_date, end_date, source_platform)
                
                # User engagement metrics (if available)
                user_metrics = await self._get_user_engagement_metrics(conn, start_date, end_date)
                
                # Content performance metrics
                content_metrics = await self._get_content_performance_metrics(conn, start_date, end_date, source_platform)
                
                # Language distribution
                language_dist = await self._get_language_distribution(conn, start_date, end_date, source_platform)
                
                # Business KPIs (mock data for now - would integrate with real business systems)
                business_kpis = await self._calculate_business_kpis(conn, start_date, end_date)
                
                return BusinessMetrics(
                    metric_date=target_date,
                    source_platform=source_platform,
                    total_stories_processed=story_metrics.get('total_stories', 0),
                    total_chunks_generated=chunk_metrics.get('total_chunks', 0),
                    avg_quality_score=quality_metrics.get('avg_quality_score', 0.0),
                    total_embeddings_cost=quality_metrics.get('total_cost', 0.0),
                    processing_time_minutes=story_metrics.get('total_processing_time_minutes', 0),
                    total_searches=user_metrics.get('total_searches', 0),
                    unique_users=user_metrics.get('unique_users', 0),
                    avg_session_duration=user_metrics.get('avg_session_duration', 0.0),
                    bounce_rate=user_metrics.get('bounce_rate', 0.0),
                    top_performing_stories=content_metrics.get('top_stories', []),
                    trending_keywords=content_metrics.get('trending_keywords', []),
                    language_distribution=language_dist,
                    conversion_rate=business_kpis.get('conversion_rate', 0.0),
                    revenue_attribution=business_kpis.get('revenue_attribution', 0.0),
                    user_lifetime_value=business_kpis.get('user_lifetime_value', 0.0)
                )
                
        except Exception as e:
            print(f"❌ Error calculating daily summary metrics: {e}")
            raise e
    
    async def _get_story_processing_metrics(self, conn, start_date: datetime, end_date: datetime, source_platform: str) -> Dict:
        """Get story processing metrics for date range"""
        platform_filter = ""
        if source_platform != 'combined':
            platform_filter = f"AND bs.source = '{source_platform}_ghoststories'"
        
        query = f"""
        SELECT 
            COUNT(*) as total_stories,
            COUNT(CASE WHEN bsp.processing_status = 'completed' THEN 1 END) as completed_stories,
            COUNT(CASE WHEN bsp.processing_status = 'failed' THEN 1 END) as failed_stories,
            AVG(EXTRACT(EPOCH FROM (bsp.updated_at - bsp.created_at))/60) as avg_processing_time_minutes,
            SUM(EXTRACT(EPOCH FROM (bsp.updated_at - bsp.created_at))/60) as total_processing_time_minutes
        FROM bronze_stories bs
        JOIN bronze_story_processing bsp ON bs.id = bsp.story_id
        WHERE bsp.created_at >= $1 AND bsp.created_at < $2
        {platform_filter}
        """
        
        result = await conn.fetchrow(query, start_date, end_date)
        return dict(result) if result else {}
    
    async def _get_chunk_metrics(self, conn, start_date: datetime, end_date: datetime, source_platform: str) -> Dict:
        """Get chunk generation metrics"""
        platform_filter = ""
        if source_platform != 'combined':
            platform_filter = f"AND ssc.processing_language = '{source_platform[:2]}'"
        
        query = f"""
        SELECT 
            COUNT(*) as total_chunks,
            AVG(chunk_length) as avg_chunk_length,
            AVG(chunk_word_count) as avg_word_count,
            COUNT(DISTINCT story_id) as stories_with_chunks
        FROM silver_story_chunks ssc
        WHERE ssc.created_at >= $1 AND ssc.created_at < $2
        {platform_filter}
        """
        
        result = await conn.fetchrow(query, start_date, end_date)
        return dict(result) if result else {}
    
    async def _get_quality_metrics(self, conn, start_date: datetime, end_date: datetime, source_platform: str) -> Dict:
        """Get quality and cost metrics"""
        platform_filter = ""
        if source_platform != 'combined':
            platform_filter = f"AND ssc.processing_language = '{source_platform[:2]}'"
        
        query = f"""
        SELECT 
            AVG(chunk_quality_score) as avg_quality_score,
            SUM(embedding_cost) as total_cost,
            COUNT(CASE WHEN chunk_quality_score >= 0.8 THEN 1 END) as high_quality_chunks,
            COUNT(CASE WHEN chunk_quality_score < 0.5 THEN 1 END) as low_quality_chunks
        FROM silver_story_chunks ssc
        WHERE ssc.created_at >= $1 AND ssc.created_at < $2
        {platform_filter}
        """
        
        result = await conn.fetchrow(query, start_date, end_date)
        return dict(result) if result else {}
    
    async def _get_user_engagement_metrics(self, conn, start_date: datetime, end_date: datetime) -> Dict:
        """Get user engagement metrics (if search interaction data exists)"""
        try:
            # Check if search_interactions table exists
            check_query = """
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'search_interactions'
            """
            table_exists = await conn.fetchval(check_query)
            
            if not table_exists:
                return {
                    'total_searches': 0,
                    'unique_users': 0,
                    'avg_session_duration': 0.0,
                    'bounce_rate': 0.0
                }
            
            query = """
            SELECT 
                COUNT(*) as total_searches,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(EXTRACT(EPOCH FROM search_timestamp)) as avg_session_duration,
                COUNT(CASE WHEN time_to_first_click IS NULL THEN 1 END)::float / COUNT(*) as bounce_rate
            FROM search_interactions
            WHERE search_timestamp >= $1 AND search_timestamp < $2
            """
            
            result = await conn.fetchrow(query, start_date, end_date)
            return dict(result) if result else {}
            
        except Exception as e:
            print(f"⚠️  User engagement metrics unavailable: {e}")
            return {
                'total_searches': 0,
                'unique_users': 0,
                'avg_session_duration': 0.0,
                'bounce_rate': 0.0
            }
    
    async def _get_content_performance_metrics(self, conn, start_date: datetime, end_date: datetime, source_platform: str) -> Dict:
        """Get content performance metrics"""
        platform_filter = ""
        if source_platform != 'combined':
            platform_filter = f"AND bs.source LIKE '{source_platform}%'"
        
        try:
            # Top performing stories (by chunk count as proxy for engagement)
            top_stories_query = f"""
            SELECT bs.id
            FROM bronze_stories bs
            JOIN silver_story_chunks ssc ON bs.id = ssc.story_id
            WHERE ssc.created_at >= $1 AND ssc.created_at < $2
            {platform_filter}
            GROUP BY bs.id
            ORDER BY COUNT(ssc.id) DESC, AVG(ssc.chunk_quality_score) DESC
            LIMIT 10
            """
            
            top_stories = await conn.fetch(top_stories_query, start_date, end_date)
            top_story_ids = [str(row['id']) for row in top_stories]
            
            # Trending keywords
            keywords_query = f"""
            SELECT unnest(semantic_keywords) as keyword, COUNT(*) as frequency
            FROM silver_story_chunks ssc
            JOIN bronze_stories bs ON ssc.story_id = bs.id
            WHERE ssc.created_at >= $1 AND ssc.created_at < $2
            {platform_filter}
            AND semantic_keywords IS NOT NULL
            GROUP BY keyword
            HAVING COUNT(*) > 1
            ORDER BY frequency DESC
            LIMIT 20
            """
            
            keywords = await conn.fetch(keywords_query, start_date, end_date)
            trending_keywords = [row['keyword'] for row in keywords if row['keyword']]
            
            return {
                'top_stories': top_story_ids,
                'trending_keywords': trending_keywords
            }
            
        except Exception as e:
            print(f"⚠️  Content performance metrics error: {e}")
            return {'top_stories': [], 'trending_keywords': []}
    
    async def _get_language_distribution(self, conn, start_date: datetime, end_date: datetime, source_platform: str) -> Dict:
        """Get language distribution metrics"""
        platform_filter = ""
        if source_platform != 'combined':
            platform_filter = f"AND processing_language = '{source_platform[:2]}'"
        
        query = f"""
        SELECT 
            processing_language,
            COUNT(*) as chunk_count
        FROM silver_story_chunks
        WHERE created_at >= $1 AND created_at < $2
        {platform_filter}
        GROUP BY processing_language
        """
        
        try:
            results = await conn.fetch(query, start_date, end_date)
            return {row['processing_language']: row['chunk_count'] for row in results}
        except Exception as e:
            print(f"⚠️  Language distribution error: {e}")
            return {}
    
    async def _calculate_business_kpis(self, conn, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate business KPIs (mock implementation)"""
        try:
            # In a real system, this would integrate with business systems
            # For now, return mock data based on processing volume
            
            story_count_query = """
            SELECT COUNT(*) FROM bronze_stories
            WHERE scraped_at >= $1 AND scraped_at < $2
            """
            
            story_count = await conn.fetchval(story_count_query, start_date, end_date)
            
            # Mock business metrics based on content volume
            base_conversion_rate = 0.05  # 5% base conversion rate
            conversion_rate = min(0.15, base_conversion_rate + (story_count / 10000) * 0.02)
            
            revenue_per_conversion = 9.99  # Average subscription price
            revenue_attribution = story_count * conversion_rate * revenue_per_conversion
            
            user_lifetime_value = revenue_per_conversion * 12  # Assume 12 month retention
            
            return {
                'conversion_rate': round(conversion_rate, 4),
                'revenue_attribution': round(revenue_attribution, 2),
                'user_lifetime_value': round(user_lifetime_value, 2)
            }
            
        except Exception as e:
            print(f"⚠️  Business KPIs calculation error: {e}")
            return {
                'conversion_rate': 0.0,
                'revenue_attribution': 0.0,
                'user_lifetime_value': 0.0
            }
    
    async def save_metrics_to_gold(self, metrics: BusinessMetrics, etl_run_id: str) -> bool:
        """Save business metrics to gold layer"""
        try:
            insert_query = """
            INSERT INTO gold_layer_metrics (
                id, metric_type, metric_date, source_platform,
                total_stories_processed, total_chunks_generated, avg_quality_score,
                total_embeddings_cost, processing_time_minutes,
                total_searches, unique_users, avg_session_duration, bounce_rate,
                top_performing_stories, trending_keywords, language_distribution,
                conversion_rate, revenue_attribution, user_lifetime_value,
                etl_run_id, data_freshness_minutes, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, NOW()
            )
            ON CONFLICT (metric_type, metric_date, source_platform) DO UPDATE SET
                total_stories_processed = $5,
                total_chunks_generated = $6,
                avg_quality_score = $7,
                total_embeddings_cost = $8,
                processing_time_minutes = $9,
                total_searches = $10,
                unique_users = $11,
                avg_session_duration = $12,
                bounce_rate = $13,
                top_performing_stories = $14,
                trending_keywords = $15,
                language_distribution = $16,
                conversion_rate = $17,
                revenue_attribution = $18,
                user_lifetime_value = $19,
                etl_run_id = $20,
                data_freshness_minutes = $21,
                created_at = NOW()
            """
            
            # Calculate data freshness (time since latest silver data)
            data_freshness_minutes = 15  # Default assumption
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    insert_query,
                    str(uuid.uuid4()),  # id
                    'daily_summary',  # metric_type
                    metrics.metric_date,  # metric_date
                    metrics.source_platform,  # source_platform
                    metrics.total_stories_processed,
                    metrics.total_chunks_generated,
                    metrics.avg_quality_score,
                    metrics.total_embeddings_cost,
                    metrics.processing_time_minutes,
                    metrics.total_searches,
                    metrics.unique_users,
                    metrics.avg_session_duration,
                    metrics.bounce_rate,
                    metrics.top_performing_stories,  # Array of UUIDs
                    metrics.trending_keywords,  # Array of strings
                    json.dumps(metrics.language_distribution),  # JSONB
                    metrics.conversion_rate,
                    metrics.revenue_attribution,
                    metrics.user_lifetime_value,
                    etl_run_id,
                    data_freshness_minutes
                )
            
            print(f"✅ Saved gold metrics for {metrics.metric_date.date()} ({metrics.source_platform})")
            return True
            
        except Exception as e:
            print(f"❌ Error saving gold metrics: {e}")
            return False
    
    async def generate_cross_platform_insights(self, target_date: datetime, etl_run_id: str) -> Dict:
        """Generate insights comparing PTT and Reddit platforms"""
        try:
            # Get metrics for both platforms
            ptt_metrics = await self.calculate_daily_summary_metrics(target_date, 'ptt')
            reddit_metrics = await self.calculate_daily_summary_metrics(target_date, 'reddit')
            
            # Calculate comparative insights
            insights = {
                'date': target_date.date().isoformat(),
                'platform_comparison': {
                    'ptt': {
                        'stories_processed': ptt_metrics.total_stories_processed,
                        'avg_quality_score': ptt_metrics.avg_quality_score,
                        'processing_cost': ptt_metrics.total_embeddings_cost,
                        'language': 'zh'
                    },
                    'reddit': {
                        'stories_processed': reddit_metrics.total_stories_processed,
                        'avg_quality_score': reddit_metrics.avg_quality_score,
                        'processing_cost': reddit_metrics.total_embeddings_cost,
                        'language': 'en'
                    }
                },
                'insights': []
            }
            
            # Generate actionable insights
            if ptt_metrics.avg_quality_score > reddit_metrics.avg_quality_score:
                insights['insights'].append(
                    f"PTT content shows {((ptt_metrics.avg_quality_score / reddit_metrics.avg_quality_score - 1) * 100):.1f}% higher quality scores"
                )
            
            total_cost = ptt_metrics.total_embeddings_cost + reddit_metrics.total_embeddings_cost
            if total_cost > 0:
                cost_per_story = total_cost / max(ptt_metrics.total_stories_processed + reddit_metrics.total_stories_processed, 1)
                insights['insights'].append(f"Average processing cost per story: ${cost_per_story:.4f}")
            
            # Language-specific insights
            ptt_keywords = set(ptt_metrics.trending_keywords)
            reddit_keywords = set(reddit_metrics.trending_keywords)
            common_themes = ptt_keywords.intersection(reddit_keywords)
            
            if common_themes:
                insights['insights'].append(f"Cross-cultural themes detected: {', '.join(list(common_themes)[:5])}")
            
            return insights
            
        except Exception as e:
            print(f"❌ Error generating cross-platform insights: {e}")
            return {'error': str(e)}
    
    async def process_daily_metrics(self, target_date: datetime, etl_run_id: str) -> GoldProcessingResult:
        """
        Process daily metrics for all platforms
        
        Args:
            target_date: Date to process metrics for
            etl_run_id: ETL run identifier
            
        Returns:
            GoldProcessingResult with processing details
        """
        start_time = datetime.now()
        metrics_generated = 0
        
        try:
            print(f"📊 Processing gold layer metrics for {target_date.date()}")
            
            # Process metrics for each platform
            platforms = ['ptt', 'reddit', 'combined']
            
            for platform in platforms:
                try:
                    print(f"📈 Calculating {platform} metrics...")
                    metrics = await self.calculate_daily_summary_metrics(target_date, platform)
                    
                    success = await self.save_metrics_to_gold(metrics, etl_run_id)
                    if success:
                        metrics_generated += 1
                        self.stats[f'daily_summaries'] += 1
                    
                except Exception as e:
                    print(f"❌ Error processing {platform} metrics: {e}")
                    self.stats['processing_errors'] += 1
            
            # Generate cross-platform insights
            try:
                insights = await self.generate_cross_platform_insights(target_date, etl_run_id)
                print(f"🔍 Cross-platform insights: {len(insights.get('insights', []))} insights generated")
            except Exception as e:
                print(f"⚠️  Cross-platform insights failed: {e}")
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Update statistics
            self.stats['total_metrics_generated'] += metrics_generated
            self._update_avg_processing_time(processing_time_ms)
            
            end_date = target_date + timedelta(days=1)
            
            return GoldProcessingResult(
                success=metrics_generated > 0,
                metrics_generated=metrics_generated,
                processing_time_ms=processing_time_ms,
                date_range=(target_date, end_date),
                metadata={
                    'platforms_processed': platforms,
                    'insights_generated': True,
                    'etl_run_id': etl_run_id
                }
            )
            
        except Exception as e:
            error_msg = f"Gold layer processing failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            return GoldProcessingResult(
                success=False,
                metrics_generated=metrics_generated,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                date_range=(target_date, target_date + timedelta(days=1)),
                error_message=error_msg
            )
    
    async def process_date_range(self, start_date: datetime, end_date: datetime, etl_run_id: str) -> List[GoldProcessingResult]:
        """Process metrics for multiple dates"""
        results = []
        current_date = start_date
        
        while current_date < end_date:
            result = await self.process_daily_metrics(current_date, etl_run_id)
            results.append(result)
            current_date += timedelta(days=1)
            
            # Small delay to avoid overwhelming the database
            await asyncio.sleep(1)
        
        return results
    
    def _update_avg_processing_time(self, processing_time_ms: int):
        """Update average processing time statistics"""
        total_metrics = self.stats['total_metrics_generated']
        if total_metrics > 1:
            self.stats['avg_processing_time'] = (
                (self.stats['avg_processing_time'] * (total_metrics - 1) + processing_time_ms) / total_metrics
            )
        else:
            self.stats['avg_processing_time'] = processing_time_ms
    
    def get_processing_stats(self) -> Dict:
        """Get comprehensive processing statistics"""
        return {
            'processor_type': 'gold_layer',
            'metrics_generated': self.stats['total_metrics_generated'],
            'breakdown': {
                'daily_summaries': self.stats['daily_summaries'],
                'user_behavior_metrics': self.stats['user_behavior_metrics'],
                'content_performance_metrics': self.stats['content_performance_metrics'],
                'business_kpis': self.stats['business_kpis']
            },
            'performance': {
                'avg_processing_time_ms': self.stats['avg_processing_time'],
                'processing_errors': self.stats['processing_errors'],
                'success_rate': (self.stats['total_metrics_generated'] / 
                               max(self.stats['total_metrics_generated'] + self.stats['processing_errors'], 1))
            }
        }


# CLI interface for testing
async def main():
    """Main CLI interface for testing gold processor"""
    import argparse
    from datetime import date
    
    parser = argparse.ArgumentParser(description="Gold Layer Processor")
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD)', 
                       default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--start-date', type=str, help='Start date for range processing (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date for range processing (YYYY-MM-DD)')
    parser.add_argument('--etl-run-id', type=str, help='ETL run ID for tracking')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    
    args = parser.parse_args()
    
    processor = GoldProcessor()
    
    try:
        await processor.initialize()
        
        if args.stats:
            stats = processor.get_processing_stats()
            print(f"📊 Processing Statistics: {json.dumps(stats, indent=2)}")
        
        etl_run_id = args.etl_run_id or f"gold_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if args.start_date and args.end_date:
            # Process date range
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
            
            results = await processor.process_date_range(start_date, end_date, etl_run_id)
            
            print(f"\n📋 Range Processing Results:")
            successful = sum(1 for r in results if r.success)
            print(f"   Dates processed: {len(results)}")
            print(f"   Successful: {successful}")
            print(f"   Failed: {len(results) - successful}")
            print(f"   Total metrics: {sum(r.metrics_generated for r in results)}")
        else:
            # Process single date
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
            result = await processor.process_daily_metrics(target_date, etl_run_id)
            
            print(f"\n📋 Processing Result:")
            print(f"   Success: {result.success}")
            print(f"   Metrics generated: {result.metrics_generated}")
            print(f"   Processing time: {result.processing_time_ms}ms")
            
            if result.error_message:
                print(f"   Error: {result.error_message}")
        
        # Final statistics
        print(f"\n📊 Final Statistics:")
        final_stats = processor.get_processing_stats()
        print(json.dumps(final_stats, indent=2))
        
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    except Exception as e:
        print(f"❌ Gold processor error: {e}")
    finally:
        await processor.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
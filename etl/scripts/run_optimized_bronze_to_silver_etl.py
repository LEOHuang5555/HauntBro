#!/usr/bin/env python3
"""
Ultra-Fast Bronze to Silver ETL Pipeline
Optimized for 100+ stories/minute processing
"""
import asyncio
import os
import sys
import argparse
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from etl.medallion.silver_processor import SilverProcessor
    from etl.config.config import CONFIG
except ImportError as e:
    print(f"Import error: {e}")
    print("Please run from project root or check module paths")
    sys.exit(1)


class OptimizedBronzeToSilverETL:
    """
    Ultra-optimized Bronze to Silver ETL Pipeline
    Target: 100+ stories/minute
    """
    
    def __init__(self, test_mode: bool = False, target_rate: int = 100):
        """Initialize optimized ETL pipeline"""
        self.test_mode = test_mode
        self.target_rate = target_rate  # stories per minute
        self.target_batch_time = 60 / target_rate  # seconds per story
        
        # Aggressive optimization settings
        self.max_concurrent_stories = 20  # Increased from 3
        self.batch_size = 50  # Larger batches
        self.max_batches_concurrent = 3  # Process multiple batches
        
        # Initialize processor
        self.silver_processor = SilverProcessor()
        
        # ETL run metadata
        import uuid
        self.etl_run_id = uuid.uuid4()
        
        # Performance tracking
        self.stats = {
            'start_time': None,
            'end_time': None,
            'stories_processed': 0,
            'stories_failed': 0,
            'stories_skipped': 0,
            'total_chunks_generated': 0,
            'avg_processing_time_per_story': 0,
            'stories_per_minute': 0,
            'bottlenecks': [],
            'optimization_metrics': {}
        }
    
    async def initialize(self) -> bool:
        """Initialize processor with optimizations"""
        print(f"🚀 Initializing OPTIMIZED Bronze to Silver ETL Pipeline")
        print(f"   Target Rate: {self.target_rate} stories/minute")
        print(f"   Max Concurrent: {self.max_concurrent_stories} stories")
        print(f"   Batch Size: {self.batch_size} stories")
        
        try:
            # Initialize silver processor
            if not await self.silver_processor.initialize():
                print("❌ Silver processor initialization failed")
                return False
            
            # Apply performance optimizations
            await self._apply_performance_optimizations()
            
            print("✅ Optimized ETL pipeline initialized")
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    async def _apply_performance_optimizations(self):
        """Apply aggressive performance optimizations"""
        print("⚡ Applying performance optimizations...")
        
        # 1. Reduce embedding generation overhead
        if hasattr(self.silver_processor.embedding_manager, 'performance_stats'):
            # Optimize embedding batch sizes
            self.silver_processor.embedding_manager.embedding_config.batch_size_openai = 10
            self.silver_processor.embedding_manager.embedding_config.max_concurrent_requests = 15
        
        # 2. Optimize chunking settings for speed
        original_chunk_size = self.silver_processor.chunking_config.target_chunk_size
        self.silver_processor.chunking_config.target_chunk_size = min(800, original_chunk_size)  # Smaller chunks = faster processing
        
        # 3. Reduce quality assessment complexity
        self.silver_processor.min_quality_score = 0.3  # Lower threshold for speed
        
        # 4. Optimize processor settings
        if hasattr(self.silver_processor.chinese_processor, 'min_call_interval'):
            self.silver_processor.chinese_processor.min_call_interval = 1  # Reduce API delays
        
        print("✅ Performance optimizations applied")
    
    async def get_stories_batch(self) -> List[Dict]:
        """Get a batch of stories optimized for high throughput"""
        try:
            stories = await self.silver_processor.get_unprocessed_stories(
                limit=self.batch_size
            )
            
            if self.test_mode and stories:
                # In test mode, limit to smaller subset
                stories = stories[:min(10, len(stories))]
            
            return stories
            
        except Exception as e:
            print(f"❌ Error fetching stories batch: {e}")
            return []
    
    async def process_story_optimized(self, story_data: Dict) -> Dict:
        """Process single story with optimization tracking"""
        start_time = time.time()
        story_id = str(story_data['id'])
        
        try:
            # Process through silver layer
            result = await self.silver_processor.process_story(story_data, str(self.etl_run_id))
            
            processing_time = time.time() - start_time
            
            if result.success:
                self.stats['stories_processed'] += 1
                self.stats['total_chunks_generated'] += result.chunks_generated
                
                return {
                    'status': 'success',
                    'story_id': story_id,
                    'processing_time': processing_time,
                    'chunks': result.chunks_generated,
                    'language': result.language_detected
                }
            else:
                if "Quality score" in (result.error_message or ""):
                    self.stats['stories_skipped'] += 1
                    return {
                        'status': 'skipped',
                        'story_id': story_id,
                        'processing_time': processing_time,
                        'reason': 'low_quality'
                    }
                else:
                    self.stats['stories_failed'] += 1
                    return {
                        'status': 'failed',
                        'story_id': story_id,
                        'processing_time': processing_time,
                        'error': result.error_message
                    }
                    
        except Exception as e:
            processing_time = time.time() - start_time
            self.stats['stories_failed'] += 1
            return {
                'status': 'failed',
                'story_id': story_id,
                'processing_time': processing_time,
                'error': str(e)
            }
    
    async def process_batch_concurrent(self, stories: List[Dict]) -> List[Dict]:
        """Process batch with high concurrency"""
        if not stories:
            return []
        
        print(f"🔥 Processing {len(stories)} stories with {self.max_concurrent_stories} concurrent workers...")
        
        # Create semaphore for controlled concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_stories)
        
        async def process_with_semaphore(story):
            async with semaphore:
                return await self.process_story_optimized(story)
        
        # Process all stories concurrently
        batch_start = time.time()
        tasks = [process_with_semaphore(story) for story in stories]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        batch_time = time.time() - batch_start
        
        # Calculate batch performance
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        skipped = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'skipped')
        failed = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'failed' or isinstance(r, Exception))
        
        stories_per_minute = (len(stories) / batch_time) * 60
        
        print(f"📊 Batch complete: {successful} success, {skipped} skipped, {failed} failed")
        print(f"⚡ Performance: {stories_per_minute:.1f} stories/minute ({batch_time:.1f}s)")
        
        return [r for r in results if isinstance(r, dict)]
    
    async def run_optimized_pipeline(self) -> bool:
        """Execute the optimized pipeline"""
        self.stats['start_time'] = time.time()
        
        try:
            print(f"\n{'='*80}")
            print(f"🚀 STARTING OPTIMIZED BRONZE TO SILVER ETL PIPELINE")
            print(f"{'='*80}")
            
            total_processed = 0
            batch_number = 0
            
            while True:
                batch_number += 1
                
                # Get batch of stories
                stories = await self.get_stories_batch()
                
                if not stories:
                    print("📭 No more stories to process")
                    break
                
                print(f"\n🔥 Batch #{batch_number}: {len(stories)} stories")
                
                # Process batch with high concurrency
                batch_results = await self.process_batch_concurrent(stories)
                total_processed += len(stories)
                
                # Calculate real-time performance
                elapsed_time = time.time() - self.stats['start_time']
                current_rate = (total_processed / elapsed_time) * 60
                
                print(f"📈 Current rate: {current_rate:.1f} stories/minute")
                print(f"📊 Total processed: {total_processed}")
                
                # Check if we're meeting target rate
                if current_rate < self.target_rate * 0.8:  # 80% of target
                    print(f"⚠️  Performance below target ({self.target_rate}/min)")
                    # Could implement dynamic optimization here
                
                # Short delay between batches to avoid overwhelming
                await asyncio.sleep(0.5)
                
                # In test mode, limit total processing
                if self.test_mode and total_processed >= 50:
                    print("🧪 Test mode: stopping after 50 stories")
                    break
            
            self.stats['end_time'] = time.time()
            return True
            
        except Exception as e:
            print(f"❌ Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        print("\n🧹 Cleaning up optimized pipeline...")
        await self.silver_processor.disconnect()
        print("✅ Cleanup completed")
    
    def calculate_final_metrics(self):
        """Calculate comprehensive performance metrics"""
        if not self.stats['start_time'] or not self.stats['end_time']:
            return {}
        
        total_time = self.stats['end_time'] - self.stats['start_time']
        total_stories = self.stats['stories_processed'] + self.stats['stories_failed'] + self.stats['stories_skipped']
        
        metrics = {
            'total_processing_time_seconds': total_time,
            'total_stories_attempted': total_stories,
            'stories_processed': self.stats['stories_processed'],
            'stories_failed': self.stats['stories_failed'],
            'stories_skipped': self.stats['stories_skipped'],
            'success_rate': (self.stats['stories_processed'] / max(total_stories, 1)) * 100,
            'stories_per_minute': (total_stories / total_time) * 60 if total_time > 0 else 0,
            'chunks_per_story': self.stats['total_chunks_generated'] / max(self.stats['stories_processed'], 1),
            'target_rate_achievement': (((total_stories / total_time) * 60) / self.target_rate) * 100 if total_time > 0 else 0
        }
        
        return metrics
    
    def print_performance_report(self):
        """Print comprehensive performance report"""
        metrics = self.calculate_final_metrics()
        
        if not metrics:
            print("❌ No performance data available")
            return
        
        print(f"\n{'='*80}")
        print(f"⚡ OPTIMIZED ETL PIPELINE PERFORMANCE REPORT")
        print(f"{'='*80}")
        
        print(f"\n🎯 PERFORMANCE TARGETS:")
        print(f"   Target Rate: {self.target_rate} stories/minute")
        print(f"   Achieved Rate: {metrics['stories_per_minute']:.1f} stories/minute")
        print(f"   Target Achievement: {metrics['target_rate_achievement']:.1f}%")
        
        print(f"\n📊 PROCESSING STATISTICS:")
        print(f"   Total Stories: {metrics['total_stories_attempted']}")
        print(f"   Successful: {metrics['stories_processed']}")
        print(f"   Failed: {metrics['stories_failed']}")
        print(f"   Skipped: {metrics['stories_skipped']}")
        print(f"   Success Rate: {metrics['success_rate']:.1f}%")
        
        print(f"\n⏱️  TIMING METRICS:")
        print(f"   Total Time: {metrics['total_processing_time_seconds']:.1f} seconds")
        print(f"   Avg per Story: {(metrics['total_processing_time_seconds'] / max(metrics['total_stories_attempted'], 1)):.2f} seconds")
        
        print(f"\n🧩 CHUNKING PERFORMANCE:")
        print(f"   Total Chunks: {self.stats['total_chunks_generated']}")
        print(f"   Avg Chunks/Story: {metrics['chunks_per_story']:.1f}")
        
        # Performance assessment
        if metrics['stories_per_minute'] >= self.target_rate:
            print(f"\n🎉 TARGET ACHIEVED! Processing at {metrics['stories_per_minute']:.1f}/min")
        elif metrics['stories_per_minute'] >= self.target_rate * 0.8:
            print(f"\n⚡ GOOD PERFORMANCE: {metrics['stories_per_minute']:.1f}/min (80%+ of target)")
        else:
            print(f"\n⚠️  NEEDS OPTIMIZATION: {metrics['stories_per_minute']:.1f}/min (below 80% of target)")
            print("   Consider increasing concurrency or reducing processing complexity")


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Optimized Bronze to Silver ETL Pipeline")
    parser.add_argument('--test-mode', action='store_true', 
                       help='Run in test mode with limited data')
    parser.add_argument('--target-rate', type=int, default=100,
                       help='Target processing rate (stories per minute)')
    
    args = parser.parse_args()
    
    # Initialize and run optimized pipeline
    etl = OptimizedBronzeToSilverETL(
        test_mode=args.test_mode, 
        target_rate=args.target_rate
    )
    
    try:
        # Initialize
        if not await etl.initialize():
            print("❌ ETL initialization failed")
            return
        
        # Run pipeline
        success = await etl.run_optimized_pipeline()
        
        # Print performance report
        etl.print_performance_report()
        
        if success:
            print("\n🎉 Optimized ETL pipeline completed!")
        else:
            print("\n❌ Optimized ETL pipeline completed with errors")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await etl.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
ULTRA-FAST Bronze to Silver ETL Pipeline
Target: 100+ stories/minute
All non-essential processing removed for maximum speed
"""
import asyncio
import time
import sys
import uuid
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from etl.medallion.silver_processor import SilverProcessor
from etl.config.config import CONFIG

class UltraFastETL:
    """Ultra-optimized ETL for maximum throughput"""
    
    def __init__(self):
        self.processor = SilverProcessor()
        
        # Ultra-aggressive settings
        self.max_concurrent = 50  # Maximum concurrency
        self.batch_size = 100     # Large batches
        self.target_rate = 100    # stories/minute
        
        # ETL run metadata
        self.etl_run_id = str(uuid.uuid4())
        
        # Performance tracking
        self.stats = {
            'start_time': None,
            'stories_processed': 0,
            'stories_failed': 0,
            'total_chunks': 0,
            'processing_times': []
        }
        
        # Apply ultra-fast optimizations
        self._apply_ultra_optimizations()
    
    def _apply_ultra_optimizations(self):
        """Apply ultra-aggressive optimizations"""
        print("🚀 Applying ULTRA-FAST optimizations...")
        
        # 1. SKIP NON-ESSENTIAL PROCESSING
        print("   ⚡ Skipping non-essential processing...")
        
        # Minimal quality assessment
        self.processor.min_quality_score = 0.1  # Very low threshold
        
        # Minimal chunking
        CONFIG["chunking"].target_chunk_size = 1000  # Larger chunks
        CONFIG["chunking"].max_chunks_per_story = 10  # Fewer chunks
        CONFIG["chunking"].min_chunk_size = 200      # Larger minimum
        
        # Fast embedding settings - use sentence transformers only
        CONFIG["embedding"].max_concurrent_requests = 30
        CONFIG["embedding"].batch_size_sentence_transformer = 50
        CONFIG["embedding"].default_strategy = "speed_optimized"
        
        # Minimal API timeouts
        CONFIG["openai"].timeout = 10
        CONFIG["openai"].max_retries = 1
        
        # 2. INCREASE CONCURRENCY
        print("   🔥 Maximizing concurrency...")
        
        # Database connection pool optimization
        CONFIG["database"].max_connections = 50
        CONFIG["database"].min_connections = 20
        
        # 3. SIMPLIFY PROCESSING
        print("   ⚡ Simplifying processing pipeline...")
        
        # Disable complex features
        self._disable_complex_features()
        
        print("✅ Ultra-fast optimizations applied!")
    
    def _disable_complex_features(self):
        """Disable complex features for speed"""
        # Monkey patch methods to skip heavy processing
        
        # Simplified language detection
        original_detect = self.processor.detect_language
        def fast_detect_language(text: str) -> str:
            # Super fast Chinese detection
            chinese_chars = sum(1 for c in text[:200] if '\u4e00' <= c <= '\u9fff')
            return 'zh' if chinese_chars > 20 else 'en'
        self.processor.detect_language = fast_detect_language
        
        # Simplified quality assessment
        original_quality = self.processor.assess_content_quality
        def fast_quality_assessment(content: str, title: str = "", source: str = "") -> float:
            # Very basic quality check
            return 0.8 if len(content.strip()) > 100 else 0.1
        self.processor.assess_content_quality = fast_quality_assessment
        
        # Skip tag generation for speed
        original_tags = self.processor._generate_story_tags
        async def fast_tag_generation(content: str, title: str, language: str) -> List[str]:
            # Extract simple keywords from title only
            if title:
                words = [w.strip() for w in title.replace('[', '').replace(']', '').split() if len(w.strip()) > 1]
                return words[:3]  # Max 3 simple tags
            return []
        self.processor._generate_story_tags = fast_tag_generation
    
    async def initialize(self) -> bool:
        """Initialize with ultra-fast settings"""
        print("🚀 Initializing ULTRA-FAST ETL Pipeline")
        print(f"   Target: {self.target_rate} stories/minute")
        print(f"   Max Concurrent: {self.max_concurrent}")
        print(f"   Batch Size: {self.batch_size}")
        
        try:
            if not await self.processor.initialize():
                print("❌ Initialization failed")
                return False
            
            print("✅ Ultra-fast ETL initialized")
            return True
            
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return False
    
    async def get_stories_ultra_batch(self) -> List[Dict]:
        """Get large batch of stories"""
        try:
            stories = await self.processor.get_unprocessed_stories(
                limit=self.batch_size
            )
            return stories
        except Exception as e:
            print(f"❌ Error fetching stories: {e}")
            return []
    
    async def process_story_minimal(self, story_data: Dict) -> Dict:
        """Process story with minimal overhead"""
        start_time = time.time()
        story_id = str(story_data['id'])
        
        try:
            # Skip status updates for speed - only process core functionality
            result = await self.processor.process_story(story_data, self.etl_run_id)
            
            processing_time = time.time() - start_time
            self.stats['processing_times'].append(processing_time)
            
            if result.success:
                self.stats['stories_processed'] += 1
                self.stats['total_chunks'] += result.chunks_generated
                return {'status': 'success', 'time': processing_time, 'chunks': result.chunks_generated}
            else:
                self.stats['stories_failed'] += 1
                return {'status': 'failed', 'time': processing_time, 'error': str(result.error_message)[:50]}
                
        except Exception as e:
            processing_time = time.time() - start_time
            self.stats['stories_failed'] += 1
            return {'status': 'error', 'time': processing_time, 'error': str(e)[:50]}
    
    async def process_ultra_batch(self, stories: List[Dict]) -> List[Dict]:
        """Process batch with maximum concurrency"""
        if not stories:
            return []
        
        print(f"🔥 Processing {len(stories)} stories with {self.max_concurrent} workers...")
        
        # Maximum concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(story):
            async with semaphore:
                return await self.process_story_minimal(story)
        
        # Process all stories
        batch_start = time.time()
        tasks = [process_with_semaphore(story) for story in stories]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        batch_time = time.time() - batch_start
        
        # Calculate performance
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        failed = len(stories) - successful
        rate = (len(stories) / batch_time) * 60
        
        print(f"📊 Batch: {successful} success, {failed} failed in {batch_time:.1f}s")
        print(f"⚡ Rate: {rate:.1f} stories/minute")
        
        return [r for r in results if isinstance(r, dict)]
    
    async def run_ultra_fast_pipeline(self, target_stories: int = 200) -> Dict:
        """Run ultra-fast pipeline"""
        self.stats['start_time'] = time.time()
        
        try:
            print(f"\n{'='*80}")
            print(f"🚀 ULTRA-FAST ETL PIPELINE - TARGET: {target_stories} STORIES")
            print(f"{'='*80}")
            
            total_processed = 0
            
            while total_processed < target_stories:
                # Get stories
                stories = await self.get_stories_ultra_batch()
                
                if not stories:
                    print("📭 No more stories available")
                    break
                
                # Limit to remaining target
                remaining = target_stories - total_processed
                if len(stories) > remaining:
                    stories = stories[:remaining]
                
                # Process batch
                batch_results = await self.process_ultra_batch(stories)
                total_processed += len(stories)
                
                # Real-time performance
                elapsed = time.time() - self.stats['start_time']
                current_rate = (total_processed / elapsed) * 60
                
                print(f"📈 Total processed: {total_processed}/{target_stories}")
                print(f"🎯 Current rate: {current_rate:.1f} stories/minute")
                
                # Check if we're meeting target
                if current_rate >= self.target_rate:
                    print(f"🎉 TARGET ACHIEVED: {current_rate:.1f}/min!")
                
                print("-" * 60)
            
            return self._calculate_final_performance()
            
        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _calculate_final_performance(self) -> Dict:
        """Calculate final performance metrics"""
        end_time = time.time()
        total_time = end_time - self.stats['start_time']
        total_stories = self.stats['stories_processed'] + self.stats['stories_failed']
        
        final_rate = (total_stories / total_time) * 60 if total_time > 0 else 0
        avg_time_per_story = sum(self.stats['processing_times']) / len(self.stats['processing_times']) if self.stats['processing_times'] else 0
        
        metrics = {
            'total_time_seconds': total_time,
            'total_stories': total_stories,
            'stories_processed': self.stats['stories_processed'],
            'stories_failed': self.stats['stories_failed'],
            'success_rate': (self.stats['stories_processed'] / max(total_stories, 1)) * 100,
            'final_rate_per_minute': final_rate,
            'avg_time_per_story': avg_time_per_story,
            'total_chunks': self.stats['total_chunks'],
            'avg_chunks_per_story': self.stats['total_chunks'] / max(self.stats['stories_processed'], 1),
            'target_achievement': (final_rate / self.target_rate) * 100 if self.target_rate > 0 else 0
        }
        
        return metrics
    
    def print_ultra_performance_report(self, metrics: Dict):
        """Print ultra performance report"""
        print(f"\n{'='*80}")
        print(f"⚡ ULTRA-FAST ETL PERFORMANCE REPORT")
        print(f"{'='*80}")
        
        print(f"\n🎯 PERFORMANCE RESULTS:")
        print(f"   Target Rate: {self.target_rate} stories/minute")
        print(f"   Achieved Rate: {metrics['final_rate_per_minute']:.1f} stories/minute")
        print(f"   Target Achievement: {metrics['target_achievement']:.1f}%")
        
        print(f"\n📊 PROCESSING STATS:")
        print(f"   Total Stories: {metrics['total_stories']}")
        print(f"   Successful: {metrics['stories_processed']}")
        print(f"   Failed: {metrics['stories_failed']}")
        print(f"   Success Rate: {metrics['success_rate']:.1f}%")
        
        print(f"\n⏱️  TIMING:")
        print(f"   Total Time: {metrics['total_time_seconds']:.1f} seconds")
        print(f"   Avg per Story: {metrics['avg_time_per_story']:.2f} seconds")
        
        print(f"\n🧩 CHUNKING:")
        print(f"   Total Chunks: {metrics['total_chunks']}")
        print(f"   Avg per Story: {metrics['avg_chunks_per_story']:.1f}")
        
        # Performance assessment
        if metrics['final_rate_per_minute'] >= self.target_rate:
            print(f"\n🏆 SUCCESS! Achieved {metrics['final_rate_per_minute']:.1f}/min (target: {self.target_rate}/min)")
        else:
            improvement_needed = self.target_rate / metrics['final_rate_per_minute']
            print(f"\n📈 Need {improvement_needed:.1f}x more improvement for target")
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.processor.disconnect()
        print("✅ Ultra-fast ETL cleanup completed")

async def main():
    """Run ultra-fast ETL"""
    etl = UltraFastETL()
    
    try:
        # Initialize
        if not await etl.initialize():
            return
        
        # Run pipeline with 100 stories for testing
        metrics = await etl.run_ultra_fast_pipeline(target_stories=100)
        
        # Print results
        if metrics:
            etl.print_ultra_performance_report(metrics)
        
    except KeyboardInterrupt:
        print("\n🛑 Pipeline interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await etl.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
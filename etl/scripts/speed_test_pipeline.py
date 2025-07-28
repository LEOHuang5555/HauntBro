#!/usr/bin/env python3
"""
Speed Test Pipeline for Performance Optimization
Target: 100 stories/minute (from current 4.5/minute)
"""
import asyncio
import time
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from etl.medallion.silver_processor import SilverProcessor
from etl.config.config import CONFIG

class SpeedTestETL:
    def __init__(self):
        self.processor = SilverProcessor()
        
        # Apply aggressive optimizations
        self._apply_speed_optimizations()
    
    def _apply_speed_optimizations(self):
        """Apply aggressive speed optimizations"""
        print("⚡ Applying AGGRESSIVE speed optimizations...")
        
        # 1. Reduce quality thresholds
        self.processor.min_quality_score = 0.2
        
        # 2. Smaller chunks for faster processing
        CONFIG["chunking"].target_chunk_size = 300
        CONFIG["chunking"].max_chunks_per_story = 20
        
        # 3. Faster embedding settings
        CONFIG["embedding"].max_concurrent_requests = 20
        CONFIG["embedding"].batch_size_openai = 25
        
        # 4. Reduce API timeouts
        CONFIG["openai"].timeout = 15
        CONFIG["openai"].max_retries = 1
        
        # 5. Optimize Chinese processor
        if hasattr(self.processor.chinese_processor, 'min_call_interval'):
            self.processor.chinese_processor.min_call_interval = 0.1
        
        print("✅ Speed optimizations applied")
    
    async def run_speed_test(self, target_stories: int = 60):
        """Run speed test with specific number of stories"""
        print(f"\n🚀 SPEED TEST: Processing {target_stories} stories")
        print("="*60)
        
        start_time = time.time()
        
        try:
            # Initialize
            if not await self.processor.initialize():
                print("❌ Initialization failed")
                return
            
            processed_count = 0
            batch_size = 20  # Large batches
            
            while processed_count < target_stories:
                # Get stories
                stories = await self.processor.get_unprocessed_stories(
                    limit=min(batch_size, target_stories - processed_count)
                )
                
                if not stories:
                    print("📭 No more stories available")
                    break
                
                batch_start = time.time()
                
                # Process with maximum concurrency
                semaphore = asyncio.Semaphore(25)  # Very high concurrency
                
                async def process_with_semaphore(story):
                    async with semaphore:
                        return await self.processor.process_story(story, "speed_test")
                
                # Process batch
                tasks = [process_with_semaphore(story) for story in stories]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Calculate batch performance
                successful = sum(1 for r in results if hasattr(r, 'success') and r.success)
                batch_time = time.time() - batch_start
                batch_rate = (len(stories) / batch_time) * 60
                
                processed_count += len(stories)
                
                print(f"📦 Batch: {len(stories)} stories, {successful} successful")
                print(f"⚡ Rate: {batch_rate:.1f} stories/minute")
                print(f"📊 Total processed: {processed_count}/{target_stories}")
                
                # Show real-time performance
                elapsed = time.time() - start_time
                current_rate = (processed_count / elapsed) * 60
                print(f"🎯 Current overall rate: {current_rate:.1f}/min")
                print("-" * 40)
            
            # Final results
            total_time = time.time() - start_time
            final_rate = (processed_count / total_time) * 60
            
            print(f"\n🏁 SPEED TEST RESULTS:")
            print(f"   Stories Processed: {processed_count}")
            print(f"   Total Time: {total_time:.1f} seconds")
            print(f"   Final Rate: {final_rate:.1f} stories/minute")
            
            # Performance assessment
            target_rate = 100
            if final_rate >= target_rate:
                print(f"🎉 TARGET ACHIEVED! {final_rate:.1f}/min >= {target_rate}/min")
            else:
                improvement_needed = target_rate / final_rate
                print(f"📈 Need {improvement_needed:.1f}x improvement to reach {target_rate}/min")
            
        except Exception as e:
            print(f"❌ Speed test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.processor.disconnect()

async def main():
    """Run speed test"""
    speed_test = SpeedTestETL()
    await speed_test.run_speed_test(target_stories=30)  # Test with 30 stories

if __name__ == "__main__":
    asyncio.run(main())
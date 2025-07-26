#!/usr/bin/env python3
"""
Enhanced Bronze to Silver ETL Pipeline
Integrates with medallion architecture components for intelligent processing
"""
import asyncio
import os
import sys
import argparse
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

try:
    from etl.medallion.bronze_processor import BronzeProcessor
    from etl.medallion.silver_processor import SilverProcessor
    from etl.config.config import CONFIG
except ImportError as e:
    print(f"Import error: {e}")
    print("Please run from project root or check module paths")
    sys.exit(1)


class BronzeToSilverETL:
    """
    Enhanced Bronze to Silver ETL Pipeline
    Orchestrates the complete transformation process with monitoring
    """
    
    def __init__(self, test_mode: bool = False, limit: Optional[int] = None):
        """Initialize ETL pipeline"""
        self.test_mode = test_mode
        self.limit = limit if limit else (10 if test_mode else None)
        
        # Initialize processors
        self.bronze_processor = BronzeProcessor()
        self.silver_processor = SilverProcessor()
        
        # ETL run metadata
        self.etl_run_id = f"b2s_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Processing statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'stories_fetched': 0,
            'stories_processed': 0,
            'stories_skipped': 0,
            'stories_failed': 0,
            'total_chunks_generated': 0,
            'total_processing_cost': 0.0,
            'language_distribution': {},
            'quality_score_distribution': {},
            'processing_errors': [],
            'performance_metrics': {}
        }
        
    async def initialize(self) -> bool:
        """Initialize all processors and connections"""
        print(f"🚀 Initializing Bronze to Silver ETL Pipeline")
        print(f"   ETL Run ID: {self.etl_run_id}")
        print(f"   Test Mode: {'ON' if self.test_mode else 'OFF'}")
        print(f"   Processing Limit: {self.limit or 'None'}")
        
        try:
            # Check environment configuration
            if not self._validate_environment():
                return False
            
            # Initialize processors
            print("\n📋 Initializing processors...")
            
            # Bronze processor (for status updates)
            bronze_init = await self.bronze_processor.initialize()
            if not bronze_init:
                print("❌ Bronze processor initialization failed")
                return False
            
            # Silver processor (main processing)
            silver_init = await self.silver_processor.initialize()
            if not silver_init:
                print("❌ Silver processor initialization failed")
                return False
            
            print("✅ All processors initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def _validate_environment(self) -> bool:
        """Validate environment configuration"""
        print("🔍 Validating environment configuration...")
        
        required_env_vars = [
            'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            print("   Please check your .env file")
            return False
        
        # Check Ollama configuration
        ollama_url = CONFIG["model"].ollama_base_url
        print(f"   Ollama URL: {ollama_url}")
        print(f"   Chinese Model: {CONFIG['model'].chinese_model}")
        print(f"   English Model: {CONFIG['model'].english_model}")
        
        # Check OpenAI configuration (optional)
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            print("   OpenAI API: Available")
        else:
            print("   OpenAI API: Not configured (using free models)")
        
        print("✅ Environment validation passed")
        return True
    
    async def get_unprocessed_stories(self) -> List[Dict]:
        """Get bronze stories that need silver processing"""
        print(f"\n📚 Fetching unprocessed bronze stories...")
        
        try:
            stories = await self.silver_processor.get_unprocessed_stories(
                limit=self.limit or 1000
            )
            
            self.stats['stories_fetched'] = len(stories)
            print(f"   Found {len(stories)} stories to process")
            
            if self.test_mode and stories:
                print(f"   Test mode: Processing first {min(len(stories), 10)} stories")
                stories = stories[:10]
            
            return stories
            
        except Exception as e:
            print(f"❌ Error fetching stories: {e}")
            return []
    
    async def process_single_story(self, story_data: Dict) -> Dict:
        """Process a single story through the silver pipeline"""
        story_id = str(story_data['id'])
        title = story_data.get('title', 'Untitled')[:50]
        
        try:
            print(f"\n📖 Processing: {title}...")
            print(f"   Story ID: {story_id}")
            print(f"   Content Length: {len(story_data.get('content', ''))} chars")
            
            # Process through silver layer
            result = await self.silver_processor.process_story(story_data, self.etl_run_id)
            
            # Update statistics
            if result.success:
                self.stats['stories_processed'] += 1
                self.stats['total_chunks_generated'] += result.chunks_generated
                self.stats['total_processing_cost'] += result.model_cost
                
                # Language distribution
                lang = result.language_detected
                self.stats['language_distribution'][lang] = \
                    self.stats['language_distribution'].get(lang, 0) + 1
                
                # Quality score distribution
                quality_bucket = f"{int(result.quality_score * 10) / 10:.1f}"
                self.stats['quality_score_distribution'][quality_bucket] = \
                    self.stats['quality_score_distribution'].get(quality_bucket, 0) + 1
                
                print(f"   ✅ Success: {result.chunks_generated} chunks, "
                      f"${result.model_cost:.4f} cost, "
                      f"{result.processing_time_ms}ms")
                
                return {
                    'status': 'success',
                    'story_id': story_id,
                    'chunks': result.chunks_generated,
                    'cost': result.model_cost,
                    'language': result.language_detected,
                    'quality_score': result.quality_score
                }
            else:
                # Handle different failure types
                if "Quality score" in (result.error_message or ""):
                    self.stats['stories_skipped'] += 1
                    print(f"   ⚠️  Skipped: {result.error_message}")
                    return {
                        'status': 'skipped',
                        'story_id': story_id,
                        'reason': 'low_quality',
                        'quality_score': result.quality_score
                    }
                else:
                    self.stats['stories_failed'] += 1
                    print(f"   ❌ Failed: {result.error_message}")
                    self.stats['processing_errors'].append({
                        'story_id': story_id,
                        'title': title,
                        'error': result.error_message
                    })
                    return {
                        'status': 'failed',
                        'story_id': story_id,
                        'error': result.error_message
                    }
                    
        except Exception as e:
            error_msg = f"Unexpected error processing story {story_id}: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            self.stats['stories_failed'] += 1
            self.stats['processing_errors'].append({
                'story_id': story_id,
                'title': title,
                'error': error_msg
            })
            
            return {
                'status': 'failed',
                'story_id': story_id,
                'error': error_msg
            }
    
    async def run_pipeline(self) -> bool:
        """Execute the complete Bronze to Silver pipeline"""
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        try:
            print(f"\n{'='*80}")
            print(f"🚀 STARTING BRONZE TO SILVER ETL PIPELINE")
            print(f"{'='*80}")
            
            # Get unprocessed stories
            stories = await self.get_unprocessed_stories()
            
            if not stories:
                print("📭 No stories to process")
                return True
            
            # Process stories with controlled concurrency
            print(f"\n⚙️  Processing {len(stories)} stories...")
            batch_size = 5 if not self.test_mode else 2  # Smaller batches for testing
            
            for i in range(0, len(stories), batch_size):
                batch = stories[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(stories) + batch_size - 1) // batch_size
                
                print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} stories)")
                
                # Process batch concurrently
                tasks = [self.process_single_story(story) for story in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Print batch summary
                successful = sum(1 for r in batch_results 
                               if isinstance(r, dict) and r.get('status') == 'success')
                skipped = sum(1 for r in batch_results 
                            if isinstance(r, dict) and r.get('status') == 'skipped')
                failed = sum(1 for r in batch_results 
                           if isinstance(r, dict) and r.get('status') == 'failed' or isinstance(r, Exception))
                
                print(f"   📊 Batch results: {successful} success, {skipped} skipped, {failed} failed")
                
                # Small delay between batches to avoid overwhelming the system
                if i + batch_size < len(stories):
                    await asyncio.sleep(2)
            
            # Calculate final statistics
            self.stats['end_time'] = datetime.now(timezone.utc)
            
            return True
            
        except Exception as e:
            print(f"❌ Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        print("\n🧹 Cleaning up resources...")
        
        try:
            await self.silver_processor.disconnect()
            await self.bronze_processor.disconnect()
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    def print_final_report(self):
        """Print comprehensive pipeline execution report"""
        if not self.stats['start_time'] or not self.stats['end_time']:
            print("❌ Pipeline did not complete - no report available")
            return
        
        total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"📊 BRONZE TO SILVER ETL PIPELINE REPORT")
        print(f"{'='*80}")
        
        # ETL Metadata
        print(f"\n🏷️  ETL METADATA:")
        print(f"   ETL Run ID: {self.etl_run_id}")
        print(f"   Start Time: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   End Time: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Total Duration: {total_time:.2f} seconds")
        print(f"   Test Mode: {'ON' if self.test_mode else 'OFF'}")
        
        # Processing Statistics
        print(f"\n📈 PROCESSING STATISTICS:")
        print(f"   Stories Fetched: {self.stats['stories_fetched']}")
        print(f"   Stories Processed: {self.stats['stories_processed']}")
        print(f"   Stories Skipped: {self.stats['stories_skipped']}")
        print(f"   Stories Failed: {self.stats['stories_failed']}")
        print(f"   Total Chunks Generated: {self.stats['total_chunks_generated']}")
        
        # Performance Metrics
        if self.stats['stories_processed'] > 0:
            avg_chunks = self.stats['total_chunks_generated'] / self.stats['stories_processed']
            stories_per_min = (self.stats['stories_processed'] / total_time) * 60
            print(f"   Average Chunks per Story: {avg_chunks:.1f}")
            print(f"   Processing Rate: {stories_per_min:.1f} stories/minute")
        
        # Success Rates
        total_attempted = (self.stats['stories_processed'] + 
                          self.stats['stories_skipped'] + 
                          self.stats['stories_failed'])
        if total_attempted > 0:
            success_rate = (self.stats['stories_processed'] / total_attempted) * 100
            print(f"   Success Rate: {success_rate:.1f}%")
        
        # Cost Analysis
        print(f"\n💰 COST ANALYSIS:")
        print(f"   Total Processing Cost: ${self.stats['total_processing_cost']:.4f}")
        if self.stats['stories_processed'] > 0:
            cost_per_story = self.stats['total_processing_cost'] / self.stats['stories_processed']
            cost_per_chunk = self.stats['total_processing_cost'] / max(self.stats['total_chunks_generated'], 1)
            print(f"   Average Cost per Story: ${cost_per_story:.4f}")
            print(f"   Average Cost per Chunk: ${cost_per_chunk:.6f}")
        
        # Language Distribution
        if self.stats['language_distribution']:
            print(f"\n🌐 LANGUAGE DISTRIBUTION:")
            for lang, count in self.stats['language_distribution'].items():
                percentage = (count / max(self.stats['stories_processed'], 1)) * 100
                print(f"   {lang.upper()}: {count} stories ({percentage:.1f}%)")
        
        # Quality Score Distribution
        if self.stats['quality_score_distribution']:
            print(f"\n⭐ QUALITY SCORE DISTRIBUTION:")
            for score, count in sorted(self.stats['quality_score_distribution'].items()):
                percentage = (count / max(self.stats['stories_processed'], 1)) * 100
                print(f"   {score}: {count} stories ({percentage:.1f}%)")
        
        # Error Summary
        if self.stats['processing_errors']:
            print(f"\n❌ ERROR SUMMARY:")
            print(f"   Total Errors: {len(self.stats['processing_errors'])}")
            
            # Group errors by type
            error_types = {}
            for error in self.stats['processing_errors']:
                error_msg = error['error']
                # Extract error type
                if "failed:" in error_msg:
                    error_type = error_msg.split("failed:")[1].strip().split()[0]
                else:
                    error_type = "unknown"
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"   {error_type}: {count} errors")
            
            # Show recent errors
            print(f"\n   Recent Errors:")
            for error in self.stats['processing_errors'][-3:]:  # Last 3 errors
                print(f"   • {error['title']}: {error['error'][:100]}...")
        
        print(f"\n{'='*80}")
        
        # Performance recommendations
        if self.stats['stories_processed'] > 0:
            print(f"\n💡 PERFORMANCE INSIGHTS:")
            if self.stats['total_processing_cost'] > 1.0:
                print("   • Consider using more free models to reduce costs")
            if total_time > 300:  # More than 5 minutes
                print("   • Consider increasing batch size or concurrency for faster processing")
            if self.stats['stories_skipped'] > self.stats['stories_processed']:
                print("   • High skip rate - consider adjusting quality thresholds")


async def main():
    """Main execution function with command line interface"""
    parser = argparse.ArgumentParser(description="Bronze to Silver ETL Pipeline")
    parser.add_argument('--test-mode', action='store_true', 
                       help='Run in test mode with limited data')
    parser.add_argument('--limit', type=int, 
                       help='Limit number of stories to process')
    parser.add_argument('--stats-only', action='store_true',
                       help='Show only statistics from previous runs')
    
    args = parser.parse_args()
    
    if args.stats_only:
        # TODO: Implement stats-only mode to show recent ETL run statistics
        print("📊 Stats-only mode not yet implemented")
        return
    
    # Initialize and run pipeline
    etl = BronzeToSilverETL(test_mode=args.test_mode, limit=args.limit)
    
    try:
        # Initialize processors
        if not await etl.initialize():
            print("❌ ETL initialization failed")
            return
        
        # Run the pipeline
        success = await etl.run_pipeline()
        
        # Print final report
        etl.print_final_report()
        
        if success:
            print("\n🎉 Bronze to Silver ETL pipeline completed successfully!")
        else:
            print("\n❌ Bronze to Silver ETL pipeline completed with errors")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await etl.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
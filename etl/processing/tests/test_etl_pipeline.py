#!/usr/bin/env python3
"""
ETL Pipeline Test and Validation Script
Tests Bronze->Silver->Gold pipeline with sample data
"""
import asyncio
import os
import sys
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path
import argparse

# Add etl modules to path
sys.path.append(str(Path(__file__).parent / "etl"))

from etl.medallion.bronze_processor import BronzeProcessor
from etl.medallion.silver_processor import SilverProcessor
from etl.medallion.gold_processor import GoldProcessor


class ETLPipelineTestSuite:
    """
    Comprehensive test suite for ETL pipeline validation
    """
    
    def __init__(self, use_test_data: bool = True):
        """Initialize test suite"""
        self.use_test_data = use_test_data
        self.test_run_id = f"test_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Processors
        self.bronze_processor = None
        self.silver_processor = None
        self.gold_processor = None
        
        # Test results
        self.test_results = {
            'start_time': None,
            'end_time': None,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'test_details': [],
            'sample_story_ids': [],
            'performance_metrics': {}
        }
        
        # Sample test data
        self.sample_stories = [
            {
                'title': 'The Haunted Library',
                'content': '''
                It was a dark and stormy night when I first encountered the ghost in our university library. 
                I was studying late for my final exams, alone on the fourth floor of the old building. 
                The fluorescent lights flickered occasionally, but I thought nothing of it. 
                
                Around midnight, I heard footsteps in the corridor outside. Slow, deliberate steps that seemed 
                to echo through the empty halls. When I looked up from my books, I saw a translucent figure 
                of an elderly man in Victorian clothing walking past the windows. 
                
                He stopped and looked directly at me through the glass. His eyes were completely black, 
                and his mouth moved as if he was trying to speak, but no sound came out. 
                I was frozen with fear, unable to move or even breathe properly. 
                
                The ghost raised his hand and pointed at a specific section of books. When I finally worked up 
                the courage to investigate, I found an old journal hidden behind the books. The journal belonged 
                to the library's first librarian, who had died in 1892 under mysterious circumstances.
                ''',
                'source': 'reddit_ghoststories',
                'source_url': 'https://reddit.com/r/ghoststories/test1',
                'author': 'TestUser1',
                'post_date': datetime.now()
            },
            {
                'title': '深夜的腳步聲',
                'content': '''
                那是一個月黑風高的夜晚，我獨自一人在宿舍裡念書。突然間，我聽到走廊上傳來奇怪的腳步聲。
                
                起初我以為是其他同學回來了，但是腳步聲很不尋常 - 非常緩慢，而且似乎是拖著腳在走路。
                我悄悄地打開房門往外看，走廊上空無一人，但是腳步聲還在繼續。
                
                我跟著聲音走到樓梯間，看到一個穿著白衣的女子正在往樓上走。她的頭髮很長，遮住了整張臉。
                當她轉過身來看我的時候，我發現她沒有眼睛，只有兩個黑洞。
                
                我嚇得立刻跑回房間，把門鎖好。從那以後，每天晚上都會聽到那個腳步聲，
                但是我再也不敢出去看了。後來聽管理員說，這棟宿舍之前有個女學生跳樓自殺了。
                ''',
                'source': 'ptt_marvel',
                'source_url': 'https://ptt.cc/marvel/test2',
                'author': 'TestUser2',
                'post_date': datetime.now()
            },
            {
                'title': 'The Mirror in the Basement',
                'content': '''
                When we moved into our new house, I discovered an old mirror in the basement. 
                It was covered with dust and had an ornate silver frame that looked antique. 
                My wife wanted to throw it away, but I thought it would look nice in our bedroom.
                
                That was my first mistake. As soon as we hung it up, strange things started happening. 
                I would catch glimpses of movement in the mirror from the corner of my eye, but when I looked directly, 
                nothing was there. My wife complained about having nightmares every night.
                
                One evening, I was getting ready for bed when I saw someone else's reflection in the mirror. 
                It was a woman with long black hair, wearing a white dress that looked like it was from the 1800s. 
                She was standing right behind me, but when I turned around, nobody was there.
                
                The woman in the mirror started appearing more frequently. She would mouth words I couldn't understand 
                and gesture frantically, as if she was trying to warn me about something. 
                Finally, I couldn't take it anymore and smashed the mirror with a hammer. 
                
                As the glass shattered, I heard a woman's voice whisper "Thank you" and felt a cold breeze 
                sweep through the room. We never had any paranormal experiences after that.
                ''',
                'source': 'reddit_ghoststories',
                'source_url': 'https://reddit.com/r/ghoststories/test3',
                'author': 'TestUser3',
                'post_date': datetime.now()
            }
        ]
    
    async def initialize_processors(self) -> bool:
        """Initialize all ETL processors"""
        print("🚀 Initializing ETL processors for testing...")
        
        try:
            # Initialize Bronze processor
            self.bronze_processor = BronzeProcessor()
            if not await self.bronze_processor.initialize():
                print("❌ Bronze processor initialization failed")
                return False
            
            # Initialize Silver processor
            self.silver_processor = SilverProcessor()
            if not await self.silver_processor.initialize():
                print("❌ Silver processor initialization failed")
                return False
            
            # Initialize Gold processor
            self.gold_processor = GoldProcessor()
            if not await self.gold_processor.initialize():
                print("❌ Gold processor initialization failed")
                return False
            
            print("✅ All processors initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Processor initialization failed: {e}")
            return False
    
    async def cleanup_processors(self):
        """Cleanup all processors"""
        print("🧹 Cleaning up processors...")
        
        try:
            if self.bronze_processor:
                await self.bronze_processor.disconnect()
            if self.silver_processor:
                await self.silver_processor.disconnect()
            if self.gold_processor:
                await self.gold_processor.disconnect()
            print("✅ Processor cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    def log_test_result(self, test_name: str, passed: bool, details: str = "", duration_ms: int = 0):
        """Log a test result"""
        self.test_results['tests_run'] += 1
        if passed:
            self.test_results['tests_passed'] += 1
            status = "✅ PASS"
        else:
            self.test_results['tests_failed'] += 1
            status = "❌ FAIL"
        
        result = {
            'test_name': test_name,
            'status': status,
            'passed': passed,
            'details': details,
            'duration_ms': duration_ms,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results['test_details'].append(result)
        print(f"   {status} {test_name} ({duration_ms}ms)")
        if details:
            print(f"      {details}")
    
    async def test_environment_setup(self) -> bool:
        """Test environment configuration and dependencies"""
        print("\n🔧 Testing Environment Setup...")
        
        start_time = datetime.now()
        
        # Test 1: Environment variables
        try:
            required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                self.log_test_result(
                    "Environment Variables",
                    False,
                    f"Missing variables: {', '.join(missing_vars)}",
                    int((datetime.now() - start_time).total_seconds() * 1000)
                )
                return False
            else:
                self.log_test_result(
                    "Environment Variables",
                    True,
                    "All required variables present",
                    int((datetime.now() - start_time).total_seconds() * 1000)
                )
        except Exception as e:
            self.log_test_result("Environment Variables", False, str(e))
            return False
        
        # Test 2: Processor initialization
        try:
            init_start = datetime.now()
            success = await self.initialize_processors()
            init_time = int((datetime.now() - init_start).total_seconds() * 1000)
            
            self.log_test_result(
                "Processor Initialization",
                success,
                "All processors ready" if success else "Processor initialization failed",
                init_time
            )
            
            if not success:
                return False
        except Exception as e:
            self.log_test_result("Processor Initialization", False, str(e))
            return False
        
        return True
    
    async def test_bronze_layer_ingestion(self) -> bool:
        """Test bronze layer data ingestion"""
        print("\n🥉 Testing Bronze Layer Ingestion...")
        
        success_count = 0
        
        for i, story in enumerate(self.sample_stories):
            start_time = datetime.now()
            
            try:
                # Generate unique story ID
                story_id = str(uuid.uuid4())
                story_data = story.copy()
                story_data['id'] = story_id
                
                # Ingest story
                result = await self.bronze_processor.ingest_story(story_data, self.test_run_id)
                
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if result.success and not result.is_duplicate:
                    success_count += 1
                    self.test_results['sample_story_ids'].append(story_id)
                    self.log_test_result(
                        f"Bronze Ingestion {i+1}",
                        True,
                        f"Story ingested: {story['title'][:30]}...",
                        duration_ms
                    )
                else:
                    self.log_test_result(
                        f"Bronze Ingestion {i+1}",
                        False,
                        result.error_message or "Duplicate or failed",
                        duration_ms
                    )
                    
            except Exception as e:
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self.log_test_result(f"Bronze Ingestion {i+1}", False, str(e), duration_ms)
        
        # Summary test
        expected_stories = len(self.sample_stories)
        self.log_test_result(
            "Bronze Layer Summary",
            success_count >= expected_stories // 2,  # At least half should succeed
            f"Ingested {success_count}/{expected_stories} stories",
            0
        )
        
        return success_count > 0
    
    async def test_silver_layer_processing(self) -> bool:
        """Test silver layer processing"""
        print("\n🥈 Testing Silver Layer Processing...")
        
        if not self.test_results['sample_story_ids']:
            self.log_test_result("Silver Layer Processing", False, "No bronze stories to process", 0)
            return False
        
        success_count = 0
        total_chunks = 0
        
        # Get a few stories to process
        for i, story_id in enumerate(self.test_results['sample_story_ids'][:2]):  # Test first 2 stories
            start_time = datetime.now()
            
            try:
                # Get unprocessed stories
                stories = await self.silver_processor.get_unprocessed_stories(limit=1)
                
                if not stories:
                    self.log_test_result(
                        f"Silver Processing {i+1}",
                        False,
                        "No unprocessed stories found",
                        0
                    )
                    continue
                
                # Process the story
                story_data = stories[0]
                result = await self.silver_processor.process_story(story_data, self.test_run_id)
                
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if result.success:
                    success_count += 1
                    total_chunks += result.chunks_generated
                    self.log_test_result(
                        f"Silver Processing {i+1}",
                        True,
                        f"Generated {result.chunks_generated} chunks, lang: {result.language_detected}",
                        duration_ms
                    )
                else:
                    self.log_test_result(
                        f"Silver Processing {i+1}",
                        False,
                        result.error_message or "Processing failed",
                        duration_ms
                    )
                    
            except Exception as e:
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self.log_test_result(f"Silver Processing {i+1}", False, str(e), duration_ms)
        
        # Summary test
        self.log_test_result(
            "Silver Layer Summary",
            success_count > 0,
            f"Processed {success_count} stories, generated {total_chunks} chunks",
            0
        )
        
        return success_count > 0
    
    async def test_gold_layer_aggregation(self) -> bool:
        """Test gold layer metric aggregation"""
        print("\n🥇 Testing Gold Layer Aggregation...")
        
        start_time = datetime.now()
        
        try:
            # Test processing metrics for yesterday
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            result = await self.gold_processor.process_daily_metrics(target_date, self.test_run_id)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if result.success:
                self.log_test_result(
                    "Gold Layer Processing",
                    True,
                    f"Generated {result.metrics_generated} metrics",
                    duration_ms
                )
                
                # Test cross-platform insights
                insight_start = datetime.now()
                insights = await self.gold_processor.generate_cross_platform_insights(
                    target_date, self.test_run_id
                )
                insight_duration = int((datetime.now() - insight_start).total_seconds() * 1000)
                
                self.log_test_result(
                    "Cross-Platform Insights",
                    'error' not in insights,
                    f"Generated insights: {len(insights.get('insights', []))} items",
                    insight_duration
                )
                
                return True
            else:
                self.log_test_result(
                    "Gold Layer Processing",
                    False,
                    result.error_message or "Processing failed",
                    duration_ms
                )
                return False
                
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_test_result("Gold Layer Processing", False, str(e), duration_ms)
            return False
    
    async def test_end_to_end_pipeline(self) -> bool:
        """Test complete end-to-end pipeline"""
        print("\n🔄 Testing End-to-End Pipeline...")
        
        start_time = datetime.now()
        
        try:
            # Create a new test story
            test_story = {
                'title': 'End-to-End Test Story',
                'content': 'This is a test story for validating the complete ETL pipeline. It contains enough content to be processed through all layers and should generate meaningful chunks and metrics.',
                'source': 'test_source',
                'source_url': 'https://test.com/e2e',
                'author': 'TestAutomation',
                'post_date': datetime.now()
            }
            
            story_id = str(uuid.uuid4())
            test_story['id'] = story_id
            
            # Step 1: Bronze ingestion
            bronze_result = await self.bronze_processor.ingest_story(test_story, self.test_run_id)
            
            if not bronze_result.success:
                self.log_test_result(
                    "E2E Pipeline",
                    False,
                    f"Bronze ingestion failed: {bronze_result.error_message}",
                    0
                )
                return False
            
            # Step 2: Silver processing
            silver_result = await self.silver_processor.process_story(test_story, self.test_run_id)
            
            if not silver_result.success:
                self.log_test_result(
                    "E2E Pipeline",
                    False,
                    f"Silver processing failed: {silver_result.error_message}",
                    0
                )
                return False
            
            # Step 3: Gold aggregation (using current date)
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            gold_result = await self.gold_processor.process_daily_metrics(target_date, self.test_run_id)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self.log_test_result(
                "E2E Pipeline",
                gold_result.success,
                f"Bronze→Silver→Gold: {bronze_result.success}→{silver_result.success}→{gold_result.success}",
                duration_ms
            )
            
            return gold_result.success
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.log_test_result("E2E Pipeline", False, str(e), duration_ms)
            return False
    
    async def run_performance_tests(self) -> Dict:
        """Run performance and load tests"""
        print("\n⚡ Running Performance Tests...")
        
        performance_results = {
            'bronze_ingestion_rate': 0,
            'silver_processing_rate': 0,
            'gold_aggregation_time': 0,
            'memory_usage': 'N/A',
            'concurrent_processing': False
        }
        
        try:
            # Test concurrent processing
            start_time = datetime.now()
            
            # Create multiple test stories
            test_stories = []
            for i in range(5):
                story = {
                    'id': str(uuid.uuid4()),
                    'title': f'Performance Test Story {i+1}',
                    'content': f'This is performance test story number {i+1}. ' * 20,  # Make it longer
                    'source': 'performance_test',
                    'source_url': f'https://test.com/perf{i+1}',
                    'author': f'PerfTest{i+1}',
                    'post_date': datetime.now()
                }
                test_stories.append(story)
            
            # Test bronze ingestion rate
            bronze_start = datetime.now()
            bronze_tasks = [
                self.bronze_processor.ingest_story(story, self.test_run_id)
                for story in test_stories
            ]
            bronze_results = await asyncio.gather(*bronze_tasks, return_exceptions=True)
            bronze_time = (datetime.now() - bronze_start).total_seconds()
            
            successful_bronze = sum(1 for r in bronze_results if hasattr(r, 'success') and r.success)
            performance_results['bronze_ingestion_rate'] = successful_bronze / bronze_time if bronze_time > 0 else 0
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            self.log_test_result(
                "Performance Test",
                successful_bronze >= 3,  # At least 3 should succeed
                f"Processed {successful_bronze}/5 stories in {total_time:.2f}s",
                int(total_time * 1000)
            )
            
            performance_results['concurrent_processing'] = successful_bronze >= 3
            
        except Exception as e:
            self.log_test_result("Performance Test", False, str(e), 0)
        
        return performance_results
    
    async def run_all_tests(self) -> bool:
        """Run the complete test suite"""
        print(f"\n{'='*80}")
        print(f"🧪 HAUNTBRO ETL PIPELINE TEST SUITE")
        print(f"{'='*80}")
        print(f"Test Run ID: {self.test_run_id}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.test_results['start_time'] = datetime.now()
        
        try:
            # Run all test phases
            env_success = await self.test_environment_setup()
            if not env_success:
                print("\n❌ Environment setup failed - aborting tests")
                return False
            
            bronze_success = await self.test_bronze_layer_ingestion()
            silver_success = await self.test_silver_layer_processing()
            gold_success = await self.test_gold_layer_aggregation()
            e2e_success = await self.test_end_to_end_pipeline()
            
            # Performance tests (optional)
            self.test_results['performance_metrics'] = await self.run_performance_tests()
            
            self.test_results['end_time'] = datetime.now()
            
            # Overall success
            overall_success = bronze_success and silver_success and gold_success and e2e_success
            
            return overall_success
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.cleanup_processors()
    
    def print_test_report(self):
        """Print comprehensive test report"""
        if not self.test_results['start_time'] or not self.test_results['end_time']:
            print("❌ Test suite did not complete - no report available")
            return
        
        total_time = (self.test_results['end_time'] - self.test_results['start_time']).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"📊 ETL PIPELINE TEST REPORT")
        print(f"{'='*80}")
        
        # Test Summary
        print(f"\n📋 TEST SUMMARY:")
        print(f"   Test Run ID: {self.test_run_id}")
        print(f"   Total Duration: {total_time:.2f} seconds")
        print(f"   Tests Run: {self.test_results['tests_run']}")
        print(f"   Tests Passed: {self.test_results['tests_passed']}")
        print(f"   Tests Failed: {self.test_results['tests_failed']}")
        
        # Success Rate
        if self.test_results['tests_run'] > 0:
            success_rate = (self.test_results['tests_passed'] / self.test_results['tests_run']) * 100
            print(f"   Success Rate: {success_rate:.1f}%")
        
        # Test Details
        print(f"\n📝 TEST DETAILS:")
        for test in self.test_results['test_details']:
            print(f"   {test['status']} {test['test_name']} ({test['duration_ms']}ms)")
            if test['details']:
                print(f"      📄 {test['details']}")
        
        # Performance Metrics
        if self.test_results['performance_metrics']:
            perf = self.test_results['performance_metrics']
            print(f"\n⚡ PERFORMANCE METRICS:")
            print(f"   Bronze Ingestion Rate: {perf['bronze_ingestion_rate']:.2f} stories/second")
            print(f"   Concurrent Processing: {'✅ Supported' if perf['concurrent_processing'] else '❌ Issues detected'}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if self.test_results['tests_failed'] == 0:
            print("   ✅ All tests passed - pipeline is ready for production")
        else:
            print("   ⚠️  Some tests failed - review errors before production deployment")
        
        if total_time > 60:
            print("   ⏱️  Consider optimizing for faster test execution")
        
        if self.test_results['tests_passed'] >= 10:
            print("   🎯 Comprehensive test coverage achieved")
        
        print(f"\n{'='*80}")


async def main():
    """Main test execution function"""
    parser = argparse.ArgumentParser(description="ETL Pipeline Test Suite")
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick tests only (skip performance tests)')
    parser.add_argument('--environment-only', action='store_true',
                       help='Test only environment setup')
    parser.add_argument('--bronze-only', action='store_true',
                       help='Test only bronze layer')
    parser.add_argument('--silver-only', action='store_true',
                       help='Test only silver layer')
    parser.add_argument('--gold-only', action='store_true',
                       help='Test only gold layer')
    
    args = parser.parse_args()
    
    # Initialize test suite
    test_suite = ETLPipelineTestSuite()
    
    try:
        if args.environment_only:
            success = await test_suite.test_environment_setup()
        elif args.bronze_only:
            await test_suite.test_environment_setup()
            success = await test_suite.test_bronze_layer_ingestion()
        elif args.silver_only:
            await test_suite.test_environment_setup()
            await test_suite.test_bronze_layer_ingestion()
            success = await test_suite.test_silver_layer_processing()
        elif args.gold_only:
            await test_suite.test_environment_setup()
            success = await test_suite.test_gold_layer_aggregation()
        else:
            # Run full test suite
            success = await test_suite.run_all_tests()
        
        # Print comprehensive report
        test_suite.print_test_report()
        
        if success:
            print("\n🎉 All tests completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
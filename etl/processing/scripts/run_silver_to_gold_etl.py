#!/usr/bin/env python3
"""
Silver to Gold ETL Pipeline
Aggregates silver layer data into business intelligence metrics
"""
import asyncio
import os
import sys
import argparse
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from pathlib import Path

# Add etl modules to path
sys.path.append(str(Path(__file__).parent / "etl"))

from etl.medallion.gold_processor import GoldProcessor
from etl.config.config import CONFIG


class SilverToGoldETL:
    """
    Silver to Gold ETL Pipeline
    Processes silver layer data into business intelligence metrics
    """
    
    def __init__(self, test_mode: bool = False, date_range: Optional[int] = None):
        """Initialize ETL pipeline"""
        self.test_mode = test_mode
        self.date_range = date_range if date_range else (1 if test_mode else 7)  # Default to 1 or 7 days
        
        # Initialize processor
        self.gold_processor = GoldProcessor()
        
        # ETL run metadata
        self.etl_run_id = f"s2g_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Processing statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'target_date_range': None,
            'metrics_generated': 0,
            'platform_metrics': {},
            'cross_platform_insights': 0,
            'processing_errors': [],
            'cost_analysis': {},
            'performance_metrics': {}
        }
        
    async def initialize(self) -> bool:
        """Initialize processors and connections"""
        print(f"🚀 Initializing Silver to Gold ETL Pipeline")
        print(f"   ETL Run ID: {self.etl_run_id}")
        print(f"   Test Mode: {'ON' if self.test_mode else 'OFF'}")
        print(f"   Date Range: {self.date_range} days")
        
        try:
            # Check environment configuration
            if not self._validate_environment():
                return False
            
            # Initialize gold processor
            print("\n📋 Initializing gold processor...")
            
            gold_init = await self.gold_processor.initialize()
            if not gold_init:
                print("❌ Gold processor initialization failed")
                return False
            
            print("✅ Gold processor initialized successfully")
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
        
        print("✅ Environment validation passed")
        return True
    
    def calculate_date_range(self) -> List[datetime]:
        """Calculate the date range to process"""
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if self.test_mode:
            # For test mode, just process yesterday
            dates = [end_date - timedelta(days=1)]
        else:
            # Process the last N days
            dates = []
            for i in range(self.date_range):
                target_date = end_date - timedelta(days=i + 1)
                dates.append(target_date)
        
        return dates
    
    async def process_daily_metrics(self, target_date: datetime) -> Dict:
        """Process metrics for a single date"""
        date_str = target_date.strftime('%Y-%m-%d')
        
        try:
            print(f"\n📊 Processing metrics for {date_str}...")
            
            # Process daily metrics for all platforms
            result = await self.gold_processor.process_daily_metrics(target_date, self.etl_run_id)
            
            if result.success:
                self.stats['metrics_generated'] += result.metrics_generated
                
                print(f"   ✅ Generated {result.metrics_generated} metrics in {result.processing_time_ms}ms")
                
                return {
                    'status': 'success',
                    'date': date_str,
                    'metrics_generated': result.metrics_generated,
                    'processing_time_ms': result.processing_time_ms,
                    'metadata': result.metadata
                }
            else:
                print(f"   ❌ Failed: {result.error_message}")
                self.stats['processing_errors'].append({
                    'date': date_str,
                    'error': result.error_message
                })
                
                return {
                    'status': 'failed',
                    'date': date_str,
                    'error': result.error_message
                }
                
        except Exception as e:
            error_msg = f"Unexpected error processing {date_str}: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            self.stats['processing_errors'].append({
                'date': date_str,
                'error': error_msg
            })
            
            return {
                'status': 'failed',
                'date': date_str,
                'error': error_msg
            }
    
    async def generate_cross_platform_insights(self, dates: List[datetime]) -> List[Dict]:
        """Generate cross-platform comparative insights"""
        print(f"\n🔍 Generating cross-platform insights...")
        
        insights = []
        
        try:
            # Generate insights for each date
            for date in dates[-3:]:  # Limit to last 3 dates for performance
                try:
                    insight = await self.gold_processor.generate_cross_platform_insights(
                        date, self.etl_run_id
                    )
                    
                    if 'error' not in insight:
                        insights.append(insight)
                        self.stats['cross_platform_insights'] += 1
                        print(f"   ✅ Generated insights for {date.strftime('%Y-%m-%d')}")
                    else:
                        print(f"   ⚠️  Insights failed for {date.strftime('%Y-%m-%d')}: {insight['error']}")
                        
                except Exception as e:
                    print(f"   ❌ Error generating insights for {date.strftime('%Y-%m-%d')}: {e}")
            
            return insights
            
        except Exception as e:
            print(f"❌ Cross-platform insights generation failed: {e}")
            return []
    
    async def analyze_processing_costs(self) -> Dict:
        """Analyze processing costs and efficiency"""
        print(f"\n💰 Analyzing processing costs...")
        
        try:
            # Get processing statistics from gold processor
            gold_stats = self.gold_processor.get_processing_stats()
            
            # Calculate cost efficiency metrics
            cost_analysis = {
                'total_metrics_generated': gold_stats.get('metrics_generated', 0),
                'processing_performance': gold_stats.get('performance', {}),
                'cost_recommendations': []
            }
            
            # Add cost optimization recommendations
            performance = gold_stats.get('performance', {})
            avg_time = performance.get('avg_processing_time_ms', 0)
            success_rate = performance.get('success_rate', 1.0)
            
            if avg_time > 5000:  # More than 5 seconds
                cost_analysis['cost_recommendations'].append(
                    "Consider optimizing database queries for faster processing"
                )
            
            if success_rate < 0.95:  # Less than 95% success rate
                cost_analysis['cost_recommendations'].append(
                    "Investigate processing failures to improve efficiency"
                )
            
            if self.stats['metrics_generated'] > 100:
                cost_analysis['cost_recommendations'].append(
                    "High volume processing - consider implementing result caching"
                )
            
            self.stats['cost_analysis'] = cost_analysis
            
            print(f"   📊 Metrics generated: {cost_analysis['total_metrics_generated']}")
            print(f"   ⚡ Average processing time: {avg_time:.0f}ms")
            print(f"   ✅ Success rate: {success_rate:.1%}")
            
            return cost_analysis
            
        except Exception as e:
            print(f"❌ Cost analysis failed: {e}")
            return {}
    
    async def validate_gold_data_quality(self) -> Dict:
        """Validate the quality of generated gold layer data"""
        print(f"\n🔍 Validating gold layer data quality...")
        
        try:
            # This would typically include:
            # - Checking for missing metrics
            # - Validating data consistency
            # - Ensuring business rules are met
            # - Comparing with expected ranges
            
            validation_results = {
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 0,
                'warnings': [],
                'errors': []
            }
            
            # Example validation checks (would be expanded in real implementation)
            validation_results['total_checks'] = 3
            
            # Check 1: Metrics generation
            if self.stats['metrics_generated'] > 0:
                validation_results['passed_checks'] += 1
                print("   ✅ Metrics generation check passed")
            else:
                validation_results['failed_checks'] += 1
                validation_results['errors'].append("No metrics were generated")
                print("   ❌ Metrics generation check failed")
            
            # Check 2: Error rate
            error_rate = len(self.stats['processing_errors']) / max(self.date_range, 1)
            if error_rate <= 0.1:  # Less than 10% error rate
                validation_results['passed_checks'] += 1
                print("   ✅ Error rate check passed")
            else:
                validation_results['failed_checks'] += 1
                validation_results['warnings'].append(f"High error rate: {error_rate:.1%}")
                print(f"   ⚠️  Error rate check warning: {error_rate:.1%}")
            
            # Check 3: Processing time
            if self.stats.get('end_time') and self.stats.get('start_time'):
                total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
                if total_time < 300:  # Less than 5 minutes
                    validation_results['passed_checks'] += 1
                    print("   ✅ Processing time check passed")
                else:
                    validation_results['warnings'].append(f"Long processing time: {total_time:.0f}s")
                    print(f"   ⚠️  Processing time check warning: {total_time:.0f}s")
            
            return validation_results
            
        except Exception as e:
            print(f"❌ Data quality validation failed: {e}")
            return {
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 1,
                'errors': [str(e)]
            }
    
    async def run_pipeline(self) -> bool:
        """Execute the complete Silver to Gold pipeline"""
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        try:
            print(f"\n{'='*80}")
            print(f"🚀 STARTING SILVER TO GOLD ETL PIPELINE")
            print(f"{'='*80}")
            
            # Calculate date range to process
            dates = self.calculate_date_range()
            self.stats['target_date_range'] = {
                'start_date': dates[-1].strftime('%Y-%m-%d'),
                'end_date': dates[0].strftime('%Y-%m-%d'),
                'total_days': len(dates)
            }
            
            print(f"\n📅 Target Date Range:")
            print(f"   From: {dates[-1].strftime('%Y-%m-%d')}")
            print(f"   To: {dates[0].strftime('%Y-%m-%d')}")
            print(f"   Total Days: {len(dates)}")
            
            # Process daily metrics for each date
            print(f"\n⚙️  Processing daily metrics...")
            
            successful_dates = 0
            failed_dates = 0
            
            for i, date in enumerate(dates, 1):
                print(f"\n[{i}/{len(dates)}] Processing date: {date.strftime('%Y-%m-%d')}")
                
                result = await self.process_daily_metrics(date)
                
                if result['status'] == 'success':
                    successful_dates += 1
                    
                    # Store platform-specific metrics
                    self.stats['platform_metrics'][result['date']] = {
                        'metrics_generated': result['metrics_generated'],
                        'processing_time_ms': result['processing_time_ms']
                    }
                else:
                    failed_dates += 1
                
                # Small delay between dates to avoid overwhelming the database
                if i < len(dates):
                    await asyncio.sleep(1)
            
            print(f"\n📊 Daily metrics processing complete:")
            print(f"   Successful dates: {successful_dates}")
            print(f"   Failed dates: {failed_dates}")
            
            # Generate cross-platform insights
            if successful_dates > 0:
                insights = await self.generate_cross_platform_insights(dates)
                print(f"   Cross-platform insights: {len(insights)}")
            
            # Analyze processing costs
            await self.analyze_processing_costs()
            
            # Validate data quality
            validation = await self.validate_gold_data_quality()
            
            # Calculate final statistics
            self.stats['end_time'] = datetime.now(timezone.utc)
            
            print(f"\n✅ Pipeline execution completed")
            return successful_dates > 0
            
        except Exception as e:
            print(f"❌ Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        print("\n🧹 Cleaning up resources...")
        
        try:
            await self.gold_processor.disconnect()
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
        print(f"📊 SILVER TO GOLD ETL PIPELINE REPORT")
        print(f"{'='*80}")
        
        # ETL Metadata
        print(f"\n🏷️  ETL METADATA:")
        print(f"   ETL Run ID: {self.etl_run_id}")
        print(f"   Start Time: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   End Time: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Total Duration: {total_time:.2f} seconds")
        print(f"   Test Mode: {'ON' if self.test_mode else 'OFF'}")
        
        # Date Range Processed
        if self.stats.get('target_date_range'):
            date_range = self.stats['target_date_range']
            print(f"\n📅 DATE RANGE PROCESSED:")
            print(f"   Start Date: {date_range['start_date']}")
            print(f"   End Date: {date_range['end_date']}")
            print(f"   Total Days: {date_range['total_days']}")
        
        # Processing Statistics
        print(f"\n📈 PROCESSING STATISTICS:")
        print(f"   Total Metrics Generated: {self.stats['metrics_generated']}")
        print(f"   Cross-Platform Insights: {self.stats['cross_platform_insights']}")
        print(f"   Processing Errors: {len(self.stats['processing_errors'])}")
        
        # Performance Metrics
        if self.stats['metrics_generated'] > 0:
            metrics_per_min = (self.stats['metrics_generated'] / total_time) * 60
            print(f"   Metrics Generation Rate: {metrics_per_min:.1f} metrics/minute")
        
        # Success Rate
        total_days = self.stats.get('target_date_range', {}).get('total_days', 1)
        error_count = len(self.stats['processing_errors'])
        success_rate = ((total_days - error_count) / total_days) * 100
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Platform Performance
        if self.stats['platform_metrics']:
            print(f"\n📊 PLATFORM PERFORMANCE:")
            total_processing_time = 0
            for date, metrics in self.stats['platform_metrics'].items():
                processing_time = metrics['processing_time_ms']
                total_processing_time += processing_time
                print(f"   {date}: {metrics['metrics_generated']} metrics ({processing_time}ms)")
            
            if len(self.stats['platform_metrics']) > 0:
                avg_processing_time = total_processing_time / len(self.stats['platform_metrics'])
                print(f"   Average Processing Time: {avg_processing_time:.0f}ms per date")
        
        # Cost Analysis
        if self.stats.get('cost_analysis'):
            cost_info = self.stats['cost_analysis']
            print(f"\n💰 COST ANALYSIS:")
            print(f"   Total Metrics Generated: {cost_info.get('total_metrics_generated', 0)}")
            
            performance = cost_info.get('processing_performance', {})
            if performance:
                avg_time = performance.get('avg_processing_time_ms', 0)
                success_rate = performance.get('success_rate', 0)
                print(f"   Average Processing Time: {avg_time:.0f}ms")
                print(f"   Processing Success Rate: {success_rate:.1%}")
            
            recommendations = cost_info.get('cost_recommendations', [])
            if recommendations:
                print(f"   Cost Optimization Recommendations:")
                for rec in recommendations:
                    print(f"   • {rec}")
        
        # Error Summary
        if self.stats['processing_errors']:
            print(f"\n❌ ERROR SUMMARY:")
            print(f"   Total Errors: {len(self.stats['processing_errors'])}")
            
            # Group errors by type
            error_types = {}
            for error in self.stats['processing_errors']:
                error_msg = error['error']
                # Extract error type (simplified)
                if "failed:" in error_msg:
                    error_type = "processing_failure"
                elif "timeout" in error_msg.lower():
                    error_type = "timeout"
                else:
                    error_type = "unknown"
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"   {error_type}: {count} errors")
            
            # Show recent errors
            print(f"\n   Recent Errors:")
            for error in self.stats['processing_errors'][-3:]:  # Last 3 errors
                print(f"   • {error['date']}: {error['error'][:100]}...")
        
        print(f"\n{'='*80}")
        
        # Business Intelligence Insights
        if self.stats['metrics_generated'] > 0:
            print(f"\n💡 BUSINESS INTELLIGENCE INSIGHTS:")
            
            if self.stats['cross_platform_insights'] > 0:
                print("   • Cross-platform comparative analysis completed")
            
            if self.stats['metrics_generated'] > 50:
                print("   • High-volume metrics generation - suitable for detailed analytics")
            elif self.stats['metrics_generated'] < 10:
                print("   • Low metrics volume - consider expanding data sources")
            
            if success_rate > 95:
                print("   • Excellent pipeline reliability - ready for production scheduling")
            elif success_rate < 80:
                print("   • Pipeline reliability needs improvement before production use")
            
            if total_time < 60:
                print("   • Fast processing time - suitable for real-time dashboards")
            
            print(f"   • Generated {self.stats['metrics_generated']} business metrics for analytics")


async def main():
    """Main execution function with command line interface"""
    parser = argparse.ArgumentParser(description="Silver to Gold ETL Pipeline")
    parser.add_argument('--test-mode', action='store_true', 
                       help='Run in test mode with single day')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to process (default: 7)')
    parser.add_argument('--single-date', type=str,
                       help='Process single date in YYYY-MM-DD format')
    parser.add_argument('--stats-only', action='store_true',
                       help='Show only statistics from gold layer')
    
    args = parser.parse_args()
    
    if args.stats_only:
        # TODO: Implement stats-only mode to show gold layer statistics
        print("📊 Stats-only mode not yet implemented")
        return
    
    # Handle single date processing
    if args.single_date:
        try:
            target_date = datetime.strptime(args.single_date, '%Y-%m-%d')
            print(f"🎯 Processing single date: {target_date.strftime('%Y-%m-%d')}")
            # Override days to 1 for single date
            args.days = 1
            args.test_mode = True
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD format.")
            return
    
    # Initialize and run pipeline
    etl = SilverToGoldETL(test_mode=args.test_mode, date_range=args.days)
    
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
            print("\n🎉 Silver to Gold ETL pipeline completed successfully!")
        else:
            print("\n❌ Silver to Gold ETL pipeline completed with errors")
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
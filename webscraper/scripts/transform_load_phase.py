"""
Phase 2: Transform & Load Script - Pure ETL Only
Processes raw data from Bronze layer to Silver layer.
NO scraping - just pure ETL processing.
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add backend to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'backend'))
sys.path.append(str(project_root / 'data-pipeline'))

from app.database.connection import db_manager
from app.database.models import BronzeStory, SilverStory
from sqlalchemy import func, and_

from etl.ptt_etl_pure import PTTPureETLProcessor
from etl.reddit_etl_pure import RedditPureETLProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ETLOrchestrator:
    """Orchestrates pure ETL processing for multiple sources."""
    
    def __init__(self):
        """Initialize ETL orchestrator."""
        self.ptt_etl = PTTPureETLProcessor()
        self.reddit_etl = RedditPureETLProcessor()
        logger.info("ETL Orchestrator initialized")
    
    def get_processing_status(self) -> Dict[str, Dict]:
        """Get current processing status for all sources."""
        with db_manager.get_session() as session:
            # PTT status
            ptt_bronze = session.query(func.count(BronzeStory.id)).filter(BronzeStory.source == 'ptt_marvel').scalar()
            ptt_silver = session.query(func.count(SilverStory.id)).join(BronzeStory).filter(BronzeStory.source == 'ptt_marvel').scalar()
            ptt_unprocessed = session.query(func.count(BronzeStory.id)).filter(
                and_(
                    BronzeStory.source == 'ptt_marvel',
                    ~BronzeStory.silver_story.has()
                )
            ).scalar()
            
            # Reddit status
            reddit_bronze = session.query(func.count(BronzeStory.id)).filter(BronzeStory.source == 'reddit_nosleep').scalar()
            reddit_silver = session.query(func.count(SilverStory.id)).join(BronzeStory).filter(BronzeStory.source == 'reddit_nosleep').scalar()
            reddit_unprocessed = session.query(func.count(BronzeStory.id)).filter(
                and_(
                    BronzeStory.source == 'reddit_nosleep',
                    ~BronzeStory.silver_story.has()
                )
            ).scalar()
            
            return {
                'ptt': {
                    'bronze_total': ptt_bronze,
                    'silver_total': ptt_silver,
                    'unprocessed': ptt_unprocessed
                },
                'reddit': {
                    'bronze_total': reddit_bronze,
                    'silver_total': reddit_silver,
                    'unprocessed': reddit_unprocessed
                }
            }
    
    def process_ptt_data(self, batch_size: int = 50, continuous: bool = False) -> Dict[str, int]:
        """Process raw PTT data from Bronze to Silver."""
        logger.info(f"Starting PTT ETL processing (batch_size: {batch_size}, continuous: {continuous})")
        
        try:
            total_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'failed': 0}
            
            if continuous:
                # Process until no more data
                batch_count = 0
                while True:
                    stats = self.ptt_etl.process_batch(batch_size=batch_size)
                    
                    if stats['total'] == 0:
                        break
                    
                    batch_count += 1
                    for key in total_stats:
                        total_stats[key] += stats[key]
                    
                    logger.info(f"PTT batch {batch_count} completed: {stats}")
            else:
                # Single batch
                total_stats = self.ptt_etl.process_batch(batch_size=batch_size)
            
            logger.info(f"PTT ETL processing completed: {total_stats}")
            return total_stats
        
        except Exception as e:
            logger.error(f"PTT ETL processing failed: {e}")
            return {'total': 0, 'processed': 0, 'skipped': 0, 'failed': 1}
    
    def process_reddit_data(self, batch_size: int = 50, continuous: bool = False) -> Dict[str, int]:
        """Process raw Reddit data from Bronze to Silver."""
        logger.info(f"Starting Reddit ETL processing (batch_size: {batch_size}, continuous: {continuous})")
        
        try:
            total_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'failed': 0}
            
            if continuous:
                # Process until no more data
                batch_count = 0
                while True:
                    stats = self.reddit_etl.process_batch(batch_size=batch_size)
                    
                    if stats['total'] == 0:
                        break
                    
                    batch_count += 1
                    for key in total_stats:
                        total_stats[key] += stats[key]
                    
                    logger.info(f"Reddit batch {batch_count} completed: {stats}")
            else:
                # Single batch
                total_stats = self.reddit_etl.process_batch(batch_size=batch_size)
            
            logger.info(f"Reddit ETL processing completed: {total_stats}")
            return total_stats
        
        except Exception as e:
            logger.error(f"Reddit ETL processing failed: {e}")
            return {'total': 0, 'processed': 0, 'skipped': 0, 'failed': 1}
    
    def run_etl_batch(self, 
                      sources: List[str] = ['ptt', 'reddit'],
                      batch_size: int = 50,
                      continuous: bool = False) -> Dict[str, Dict]:
        """Run ETL batch for specified sources."""
        logger.info(f"Starting ETL batch for sources: {sources}")
        
        results = {}
        
        # PTT ETL
        if 'ptt' in sources:
            results['ptt'] = self.process_ptt_data(batch_size=batch_size, continuous=continuous)
        
        # Reddit ETL
        if 'reddit' in sources:
            results['reddit'] = self.process_reddit_data(batch_size=batch_size, continuous=continuous)
        
        logger.info(f"ETL batch completed: {results}")
        return results


def main():
    """Main function for Phase 2: Transform & Load."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 2: Transform & Load - Pure ETL Only')
    parser.add_argument(
        '--sources',
        nargs='+',
        choices=['ptt', 'reddit'],
        default=['ptt', 'reddit'],
        help='Sources to process (default: ptt reddit)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of stories to process per batch (default: 50)'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously until no raw data to process'
    )
    parser.add_argument(
        '--status-only',
        action='store_true',
        help='Show processing status and exit'
    )
    
    args = parser.parse_args()
    
    print("⚙️  Phase 2: Transform & Load - Pure ETL Only")
    print("=" * 50)
    print(f"Sources: {', '.join(args.sources)}")
    print(f"Batch size: {args.batch_size}")
    print(f"Mode: {'continuous' if args.continuous else 'single batch'}")
    print(f"Source: Bronze layer (raw data)")
    print(f"Target: Silver layer (processed data)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize ETL orchestrator
        orchestrator = ETLOrchestrator()
        
        # Show current status
        print(f"\\n📊 Current Processing Status:")
        print("-" * 30)
        status = orchestrator.get_processing_status()
        
        for source, stats in status.items():
            if source in args.sources:
                print(f"{source.upper()}:")
                print(f"  Bronze (raw): {stats['bronze_total']}")
                print(f"  Silver (processed): {stats['silver_total']}")
                print(f"  Unprocessed: {stats['unprocessed']}")
        
        # If status-only, exit here
        if args.status_only:
            return 0
        
        # Run ETL processing
        print(f"\\n🔄 Starting ETL Processing...")
        results = orchestrator.run_etl_batch(
            sources=args.sources,
            batch_size=args.batch_size,
            continuous=args.continuous
        )
        
        # Print results
        print(f"\\n📊 Phase 2 (ETL) Results:")
        print("-" * 30)
        
        total_processed = 0
        total_raw = 0
        total_skipped = 0
        total_failed = 0
        
        for source, stats in results.items():
            print(f"{source.upper()}:")
            print(f"  Raw stories processed: {stats['total']}")
            print(f"  Successfully transformed: {stats['processed']}")
            print(f"  Skipped (invalid/duplicate): {stats['skipped']}")
            print(f"  Failed: {stats['failed']}")
            
            if stats['total'] > 0:
                success_rate = (stats['processed'] / stats['total'] * 100)
                print(f"  Success rate: {success_rate:.1f}%")
            
            total_processed += stats['processed']
            total_raw += stats['total']
            total_skipped += stats['skipped']
            total_failed += stats['failed']
        
        print(f"\\nTOTAL SUMMARY:")
        print(f"  Raw stories processed: {total_raw}")
        print(f"  Successfully transformed: {total_processed}")
        print(f"  Skipped: {total_skipped}")
        print(f"  Failed: {total_failed}")
        
        if total_raw > 0:
            overall_success = (total_processed / total_raw * 100)
            print(f"  Overall success rate: {overall_success:.1f}%")
        
        if total_processed > 0:
            print(f"\\n✅ Phase 2 Complete: {total_processed} stories transformed to Silver layer!")
        else:
            print(f"\\n⚠️  No new stories transformed.")
        
        return 0
    
    except Exception as e:
        print(f"\\n❌ Phase 2 failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
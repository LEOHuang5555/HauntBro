"""
Phase 1: Extract Script - Pure Scraping Only
Orchestrates scraping from multiple sources and stores raw data in Bronze layer.
NO ETL processing - just pure extraction.
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

from scrapers.ptt_scraper_pure import PTTPureScrapingManager
from scrapers.reddit_scraper_pure import RedditPureScrapingManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExtractionOrchestrator:
    """Orchestrates pure extraction from multiple sources."""
    
    def __init__(self):
        """Initialize extraction orchestrator."""
        self.ptt_scraper = PTTPureScrapingManager()
        self.reddit_scraper = RedditPureScrapingManager()
        logger.info("Extraction Orchestrator initialized")
    
    def extract_ptt_data(self, max_pages: int = 3, max_articles: int = 20) -> Dict[str, int]:
        """Extract raw data from PTT Marvel board."""
        logger.info(f"Starting PTT extraction (max {max_pages} pages, {max_articles} articles)")
        
        try:
            stats = self.ptt_scraper.scrape_and_store_raw(
                max_pages=max_pages,
                max_articles=max_articles
            )
            logger.info(f"PTT extraction completed: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"PTT extraction failed: {e}")
            return {'discovered': 0, 'stored': 0, 'duplicates': 0, 'errors': 1}
    
    def extract_reddit_data(self, target_count: int = 30, time_filters: List[str] = None) -> Dict[str, int]:
        """Extract raw data from Reddit r/nosleep."""
        logger.info(f"Starting Reddit extraction (target: {target_count} stories)")
        
        try:
            if time_filters is None:
                time_filters = ['hot', 'new']
            
            stats = self.reddit_scraper.scrape_and_store_raw(
                target_count=target_count,
                time_filters=time_filters
            )
            logger.info(f"Reddit extraction completed: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"Reddit extraction failed: {e}")
            return {'discovered': 0, 'stored': 0, 'duplicates': 0, 'errors': 1}
    
    def run_extraction_batch(self, 
                           sources: List[str] = ['ptt', 'reddit'],
                           ptt_params: Dict = None,
                           reddit_params: Dict = None) -> Dict[str, Dict]:
        """Run extraction batch for specified sources."""
        logger.info(f"Starting extraction batch for sources: {sources}")
        
        results = {}
        
        # PTT extraction
        if 'ptt' in sources:
            ptt_params = ptt_params or {'max_pages': 3, 'max_articles': 20}
            results['ptt'] = self.extract_ptt_data(**ptt_params)
        
        # Reddit extraction
        if 'reddit' in sources:
            reddit_params = reddit_params or {'target_count': 30, 'time_filters': ['hot', 'new']}
            results['reddit'] = self.extract_reddit_data(**reddit_params)
        
        logger.info(f"Extraction batch completed: {results}")
        return results


def main():
    """Main function for Phase 1: Extract."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 1: Extract - Pure Scraping Only')
    parser.add_argument(
        '--sources',
        nargs='+',
        choices=['ptt', 'reddit'],
        default=['ptt', 'reddit'],
        help='Sources to extract from (default: ptt reddit)'
    )
    parser.add_argument(
        '--ptt-pages',
        type=int,
        default=3,
        help='PTT: Maximum pages to scrape (default: 3)'
    )
    parser.add_argument(
        '--ptt-articles',
        type=int,
        default=20,
        help='PTT: Maximum articles to collect (default: 20)'
    )
    parser.add_argument(
        '--reddit-count',
        type=int,
        default=30,
        help='Reddit: Target story count (default: 30)'
    )
    parser.add_argument(
        '--reddit-filters',
        nargs='+',
        choices=['hot', 'new', 'week', 'month', 'year', 'all'],
        default=['hot', 'new'],
        help='Reddit: Time filters to use (default: hot new)'
    )
    
    args = parser.parse_args()
    
    print("📥 Phase 1: Extract - Pure Scraping Only")
    print("=" * 50)
    print(f"Sources: {', '.join(args.sources)}")
    print(f"PTT: {args.ptt_pages} pages, {args.ptt_articles} articles max")
    print(f"Reddit: {args.reddit_count} stories, filters: {', '.join(args.reddit_filters)}")
    print(f"Target: Bronze layer (raw storage)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize extraction orchestrator
        orchestrator = ExtractionOrchestrator()
        
        # Prepare parameters
        ptt_params = {
            'max_pages': args.ptt_pages,
            'max_articles': args.ptt_articles
        }
        
        reddit_params = {
            'target_count': args.reddit_count,
            'time_filters': args.reddit_filters
        }
        
        # Run extraction
        results = orchestrator.run_extraction_batch(
            sources=args.sources,
            ptt_params=ptt_params,
            reddit_params=reddit_params
        )
        
        # Print results
        print(f"\\n📊 Phase 1 (Extract) Results:")
        print("-" * 30)
        
        total_stored = 0
        total_discovered = 0
        total_duplicates = 0
        total_errors = 0
        
        for source, stats in results.items():
            print(f"{source.upper()}:")
            print(f"  Stories discovered: {stats['discovered']}")
            print(f"  Raw stories stored: {stats['stored']}")
            print(f"  Duplicates skipped: {stats['duplicates']}")
            print(f"  Errors: {stats['errors']}")
            
            total_stored += stats['stored']
            total_discovered += stats['discovered']
            total_duplicates += stats['duplicates']
            total_errors += stats['errors']
        
        print(f"\\nTOTAL SUMMARY:")
        print(f"  Stories discovered: {total_discovered}")
        print(f"  Raw stories stored: {total_stored}")
        print(f"  Duplicates skipped: {total_duplicates}")
        print(f"  Errors: {total_errors}")
        
        if total_stored > 0:
            print(f"\\n✅ Phase 1 Complete: {total_stored} raw stories stored in Bronze layer!")
            print(f"🔄 Next: Run 'transform_load_phase.py' to process Bronze → Silver")
        else:
            print(f"\\n⚠️  No new stories stored.")
        
        return 0
    
    except Exception as e:
        print(f"\\n❌ Phase 1 failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
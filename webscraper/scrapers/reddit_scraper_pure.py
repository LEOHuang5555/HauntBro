"""
Pure Reddit Scraper - Phase 1: Extract Only
Scrapes Reddit r/ghoststories and stores raw data in Bronze layer.
NO ETL processing - just pure extraction.
"""

import sys
import os
import logging
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database models and Reddit scraper
from app.database.models import BronzeStory
from app.database.connection import get_db_url
from scrapers.reddit_scraper import RedditScraper

# Configure logging with file support
def setup_logging(log_to_file: bool = True):
    """Setup logging with optional file output."""
    handlers = [logging.StreamHandler()]
    
    if log_to_file:
        # Create logs directory
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f'reddit_pure_scraper_{timestamp}.log'
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()


class RedditPureScrapingManager:
    """Pure Reddit scraper that only extracts and stores raw data."""
    
    def __init__(self, database_url: str = None, log_to_file: bool = True):
        """Initialize Reddit pure scraping manager."""
        # Setup logging if requested
        if log_to_file:
            global logger
            logger = setup_logging(log_to_file)
        
        # Initialize failed jobs tracking
        self.failed_jobs = []
        if log_to_file:
            log_dir = Path(__file__).parent.parent / 'logs'
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.failed_jobs_file = log_dir / f'reddit_pure_failed_jobs_{timestamp}.json'
        else:
            self.failed_jobs_file = None
        
        self.database_url = database_url or get_db_url()
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.scraper = RedditScraper(log_to_file=log_to_file)
        
        logger.info("Reddit Pure Scraping Manager initialized")
    
    def store_raw_story_to_bronze(self, story: Dict) -> bool:
        """Store raw Reddit story directly to Bronze layer without processing."""
        db_session = self.SessionLocal()
        
        try:
            # Create Bronze story with minimal processing (just raw storage)
            bronze_story = BronzeStory(
                title=story.get('title', 'Untitled'),
                content=story.get('content', ''),
                source='reddit_ghoststories',
                source_url=story.get('source_url', ''),
                author=story.get('author', 'unknown'),
                post_date=story.get('post_date'),
                raw_metadata={
                    'reddit_id': story.get('raw_metadata', {}).get('reddit_id'),
                    'score': story.get('raw_metadata', {}).get('score'),
                    'upvote_ratio': story.get('raw_metadata', {}).get('upvote_ratio'),
                    'num_comments': story.get('raw_metadata', {}).get('num_comments'),
                    'flair': story.get('raw_metadata', {}).get('flair'),
                    'created_utc': story.get('raw_metadata', {}).get('created_utc'),
                    'scraping_phase': 'raw_extraction',
                    'scraped_at': datetime.now(timezone.utc).isoformat(),
                    'processing_status': 'raw'  # Mark as needing ETL processing
                }
            )
            
            db_session.add(bronze_story)
            db_session.commit()
            
            logger.debug(f"Stored raw Reddit story: {story.get('title', '')[:50]}...")
            return True
            
        except IntegrityError as e:
            if 'unique_source_url' in str(e):
                logger.debug(f"Duplicate story skipped: {story.get('source_url', '')}")
                db_session.rollback()
                return False  # Duplicate, not an error
            else:
                logger.error(f"Database integrity error: {e}")
                db_session.rollback()
                raise
        except Exception as e:
            error_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': 'story_storage_error',
                'error_message': str(e),
                'story_title': story.get('title', 'Unknown')[:100],
                'source_url': story.get('source_url', 'Unknown')
            }
            self.failed_jobs.append(error_info)
            logger.error(f"Error storing raw story: {e}")
            db_session.rollback()
            raise
        finally:
            db_session.close()
    
    def _save_failed_jobs(self) -> None:
        """Save failed jobs to JSON file."""
        if self.failed_jobs_file and self.failed_jobs:
            try:
                with open(self.failed_jobs_file, 'w') as f:
                    json.dump({
                        'scraper_type': 'reddit_pure_scraper',
                        'total_failed_jobs': len(self.failed_jobs),
                        'generated_at': datetime.now(timezone.utc).isoformat(),
                        'failed_jobs': self.failed_jobs
                    }, f, indent=2)
                logger.info(f"Saved {len(self.failed_jobs)} failed jobs to {self.failed_jobs_file}")
            except Exception as e:
                logger.error(f"Failed to save failed jobs: {e}")
    
    def get_failed_jobs_summary(self) -> Dict:
        """Get summary of failed jobs."""
        if not self.failed_jobs:
            return {'total_failed': 0, 'error_types': {}}
        
        error_types = {}
        for job in self.failed_jobs:
            error_type = job.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_failed': len(self.failed_jobs),
            'error_types': error_types,
            'failed_jobs_file': str(self.failed_jobs_file) if self.failed_jobs_file else None
        }
    
    def scrape_and_store_raw(self, 
                            target_count: int = 50,
                            time_filters: List[str] = None) -> Dict[str, int]:
        """
        Scrape Reddit stories and store raw data in Bronze layer.
        
        Args:
            target_count: Number of stories to scrape
            time_filters: List of time filters to use
        
        Returns:
            Dictionary with scraping statistics
        """
        logger.info(f"Starting Reddit raw scraping (target: {target_count} stories)")
        
        stats = {
            'discovered': 0,
            'stored': 0,
            'duplicates': 0,
            'errors': 0
        }
        
        try:
            # Default time filters if none provided
            if time_filters is None:
                time_filters = ['hot', 'new', 'week']
            
            all_stories = []
            seen_urls = set()
            
            # Scrape using different strategies
            for time_filter in time_filters:
                try:
                    batch_size = min(target_count // len(time_filters), 100)
                    logger.info(f"Scraping {batch_size} stories with filter: {time_filter}")
                    
                    stories = self.scraper.get_ghoststories_stories(
                        limit=batch_size,
                        time_filter=time_filter
                    )
                    
                    # Deduplicate by URL
                    for story in stories:
                        story_url = story.get('source_url', '')
                        if story_url and story_url not in seen_urls:
                            seen_urls.add(story_url)
                            all_stories.append(story)
                    
                    logger.info(f"Collected {len(stories)} stories from {time_filter} filter")
                    
                except Exception as e:
                    logger.error(f"Error scraping with filter {time_filter}: {e}")
                    continue
            
            stats['discovered'] = len(all_stories)
            logger.info(f"Total unique stories collected: {len(all_stories)}")
            
            # Store each story as raw data
            for story in all_stories:
                try:
                    if self.store_raw_story_to_bronze(story):
                        stats['stored'] += 1
                    else:
                        stats['duplicates'] += 1
                
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Failed to store story: {e}")
                
                # Log progress every 10 stories
                if (stats['stored'] + stats['duplicates'] + stats['errors']) % 10 == 0:
                    logger.info(f"Progress: {stats}")
            
            logger.info(f"Reddit raw scraping completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Reddit scraping failed: {e}")
            raise
    
    def scrape_by_date_range(self, 
                            start_date: datetime = None,
                            end_date: datetime = None,
                            limit: int = 1000,
                            use_praw: bool = True) -> Dict[str, int]:
        """
        Scrape Reddit stories within a specific date range and store raw data.
        
        Args:
            start_date: Start of date range (defaults to 30 days ago)
            end_date: End of date range (defaults to now)
            limit: Maximum number of stories to scrape
            use_praw: Use PRAW (True) or direct HTTP requests (False)
        
        Returns:
            Dictionary with scraping statistics
        """
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
            
        logger.info(f"Starting Reddit date range scraping")
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        stats = {
            'discovered': 0,
            'stored': 0,
            'duplicates': 0,
            'errors': 0
        }
        
        try:
            # Choose scraping method based on use_praw parameter
            if use_praw and self.scraper.reddit:
                logger.info("Using PRAW for date range scraping (better rate limiting)")
                stories = self.scraper.get_stories_by_date_range_praw(
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
            else:
                if use_praw:
                    logger.warning("PRAW requested but not available - falling back to HTTP requests")
                logger.info("Using direct HTTP requests for date range scraping")
                stories = self.scraper.get_stories_by_date_range(
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
            
            stats['discovered'] = len(stories)
            logger.info(f"Total stories collected from date range: {len(stories)}")
            
            # Store each story as raw data
            for story in stories:
                try:
                    if self.store_raw_story_to_bronze(story):
                        stats['stored'] += 1
                    else:
                        stats['duplicates'] += 1
                
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Failed to store story: {e}")
                
                # Log progress every 25 stories
                if (stats['stored'] + stats['duplicates'] + stats['errors']) % 25 == 0:
                    logger.info(f"Progress: {stats}")
            
            logger.info(f"Reddit date range scraping completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Reddit date range scraping failed: {e}")
            raise


def main():
    """Main function for pure Reddit scraping."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pure Reddit Scraper (Phase 1: Extract Only)')
    parser.add_argument(
        '--target-count',
        type=int,
        default=30,
        help='Number of stories to scrape (default: 30)'
    )
    parser.add_argument(
        '--time-filters',
        nargs='+',
        choices=['hot', 'new', 'week', 'month', 'year', 'all'],
        default=['hot', 'new'],
        help='Time filters to use (default: hot new)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for scraping (YYYY-MM-DD format)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for scraping (YYYY-MM-DD format)'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=30,
        help='Number of days back to scrape (default: 30)'
    )
    
    args = parser.parse_args()
    
    print("🔥 Reddit Pure Scraper (Phase 1: Extract Only)")
    print("=" * 50)
    print(f"Target stories: {args.target_count}")
    
    # Determine scraping method
    use_date_range = args.start_date or args.end_date or args.days_back != 30
    
    if use_date_range:
        # Parse dates
        end_date = datetime.now(timezone.utc)
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            start_date = end_date - timedelta(days=args.days_back)
        
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Method: Date range scraping")
    else:
        print(f"Time filters: {', '.join(args.time_filters)}")
        print(f"Method: Filter-based scraping")
    
    print(f"Target: Bronze layer (raw storage)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize scraping manager
        manager = RedditPureScrapingManager()
        
        # Choose scraping method
        if use_date_range:
            # Use date range scraping
            stats = manager.scrape_by_date_range(
                start_date=start_date,
                end_date=end_date,
                limit=args.target_count
            )
        else:
            # Use traditional time filter scraping
            stats = manager.scrape_and_store_raw(
                target_count=args.target_count,
                time_filters=args.time_filters
            )
        
        # Print results
        print(f"\\n📊 Phase 1 (Extract) Results:")
        print(f"Stories discovered: {stats['discovered']}")
        print(f"Raw stories stored: {stats['stored']}")
        print(f"Duplicates skipped: {stats['duplicates']}")
        print(f"Errors: {stats['errors']}")
        
        if stats['stored'] > 0:
            print(f"\\n✅ Phase 1 Complete: {stats['stored']} raw Reddit stories stored in Bronze layer!")
            print(f"🔄 Next: Run ETL processor to transform Bronze → Silver")
        else:
            print(f"\\n⚠️  No new stories stored.")
    
    except Exception as e:
        print(f"\\n❌ Phase 1 failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
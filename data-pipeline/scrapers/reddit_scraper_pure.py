"""
Pure Reddit Scraper - Phase 1: Extract Only
Scrapes Reddit r/ghoststories and stores raw data in Bronze layer.
NO ETL processing - just pure extraction.
"""

import sys
import os
import logging
from datetime import datetime, timezone
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedditPureScrapingManager:
    """Pure Reddit scraper that only extracts and stores raw data."""
    
    def __init__(self, database_url: str = None):
        """Initialize Reddit pure scraping manager."""
        self.database_url = database_url or get_db_url()
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.scraper = RedditScraper()
        
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
            logger.error(f"Error storing raw story: {e}")
            db_session.rollback()
            raise
        finally:
            db_session.close()
    
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
    
    args = parser.parse_args()
    
    print("🔥 Reddit Pure Scraper (Phase 1: Extract Only)")
    print("=" * 50)
    print(f"Target stories: {args.target_count}")
    print(f"Time filters: {', '.join(args.time_filters)}")
    print(f"Target: Bronze layer (raw storage)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize scraping manager
        manager = RedditPureScrapingManager()
        
        # Run pure scraping (no ETL)
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
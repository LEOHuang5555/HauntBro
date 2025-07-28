"""
Pure PTT Scraper - Phase 1: Extract Only
Scrapes PTT Marvel board and stores raw data in Bronze layer.
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

# Import database models and PTT scraper
from app.database.models import BronzeStory
from app.database.connection import get_db_url
from scrapers.ptt_marvel_scraper import PTTMarvelScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PTTPureScrapingManager:
    """Pure PTT scraper that only extracts and stores raw data."""
    
    def __init__(self, database_url: str = None):
        """Initialize PTT pure scraping manager."""
        self.database_url = database_url or get_db_url()
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.scraper = PTTMarvelScraper()
        
        logger.info("PTT Pure Scraping Manager initialized")
    
    def store_raw_article_to_bronze(self, article: Dict) -> bool:
        """Store raw PTT article directly to Bronze layer without processing."""
        db_session = self.SessionLocal()
        
        try:
            # Create Bronze story with minimal processing (just raw storage)
            bronze_story = BronzeStory(
                title=article.get('title', 'Untitled'),
                content=article.get('content', ''),
                source='ptt_marvel',
                source_url=article.get('source_url', ''),
                author=article.get('author', 'unknown'),
                post_date=article.get('post_date'),
                raw_metadata={
                    'board': article.get('board', 'marvel'),
                    'raw_html': article.get('raw_html', ''),
                    'scraping_phase': 'raw_extraction',
                    'scraped_at': datetime.now(timezone.utc).isoformat(),
                    'processing_status': 'raw'  # Mark as needing ETL processing
                }
            )
            
            db_session.add(bronze_story)
            db_session.commit()
            
            logger.debug(f"Stored raw PTT article: {article.get('title', '')[:50]}...")
            return True
            
        except IntegrityError as e:
            if 'unique_source_url' in str(e):
                logger.debug(f"Duplicate article skipped: {article.get('source_url', '')}")
                db_session.rollback()
                return False  # Duplicate, not an error
            else:
                logger.error(f"Database integrity error: {e}")
                db_session.rollback()
                raise
        except Exception as e:
            logger.error(f"Error storing raw article: {e}")
            db_session.rollback()
            raise
        finally:
            db_session.close()
    
    def scrape_and_store_raw(self, max_pages: int = 5, max_articles: int = 50) -> Dict[str, int]:
        """
        Scrape PTT articles and store raw data in Bronze layer.
        
        Args:
            max_pages: Maximum pages to scrape
            max_articles: Maximum articles to collect
        
        Returns:
            Dictionary with scraping statistics
        """
        logger.info(f"Starting PTT raw scraping (max {max_pages} pages, {max_articles} articles)")
        
        stats = {
            'discovered': 0,
            'stored': 0,
            'duplicates': 0,
            'errors': 0
        }
        
        try:
            # Scrape articles using existing PTT scraper
            articles = self.scraper.scrape_board(
                max_pages=max_pages,
                max_articles=max_articles
            )
            
            stats['discovered'] = len(articles)
            logger.info(f"Discovered {len(articles)} PTT articles")
            
            # Store each article as raw data
            for article in articles:
                try:
                    if self.store_raw_article_to_bronze(article):
                        stats['stored'] += 1
                    else:
                        stats['duplicates'] += 1
                
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Failed to store article: {e}")
                
                # Log progress every 10 articles
                if (stats['stored'] + stats['duplicates'] + stats['errors']) % 10 == 0:
                    logger.info(f"Progress: {stats}")
            
            logger.info(f"PTT raw scraping completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"PTT scraping failed: {e}")
            raise


def main():
    """Main function for pure PTT scraping."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pure PTT Scraper (Phase 1: Extract Only)')
    parser.add_argument(
        '--max-pages',
        type=int,
        default=3,
        help='Maximum pages to scrape (default: 3)'
    )
    parser.add_argument(
        '--max-articles',
        type=int,
        default=20,
        help='Maximum articles to collect (default: 20)'
    )
    
    args = parser.parse_args()
    
    print("🏮 PTT Pure Scraper (Phase 1: Extract Only)")
    print("=" * 50)
    print(f"Max pages: {args.max_pages}")
    print(f"Max articles: {args.max_articles}")
    print(f"Target: Bronze layer (raw storage)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize scraping manager
        manager = PTTPureScrapingManager()
        
        # Run pure scraping (no ETL)
        stats = manager.scrape_and_store_raw(
            max_pages=args.max_pages,
            max_articles=args.max_articles
        )
        
        # Print results
        print(f"\\n📊 Phase 1 (Extract) Results:")
        print(f"Articles discovered: {stats['discovered']}")
        print(f"Raw articles stored: {stats['stored']}")
        print(f"Duplicates skipped: {stats['duplicates']}")
        print(f"Errors: {stats['errors']}")
        
        if stats['stored'] > 0:
            print(f"\\n✅ Phase 1 Complete: {stats['stored']} raw PTT articles stored in Bronze layer!")
            print(f"🔄 Next: Run ETL processor to transform Bronze → Silver")
        else:
            print(f"\\n⚠️  No new articles stored.")
    
    except Exception as e:
        print(f"\\n❌ Phase 1 failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
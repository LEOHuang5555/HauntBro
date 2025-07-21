#!/usr/bin/env python3
"""
Complete PTT Marvel Board Scraper
Combines batch processing, error recovery, and resume capability.
Scrapes all PTT Marvel pages with robust error handling.
"""

import sys
import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'backend'))
sys.path.append(str(project_root / 'data-pipeline'))

from scrapers.ptt_marvel_scraper import PTTMarvelScraper
from scrapers.ptt_scraper_pure import PTTPureScrapingManager

# Configure logging with both file and console output
log_dir = Path(__file__).parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f'ptt_scraper_{timestamp}.log'
failed_jobs_file = log_dir / f'failed_jobs_{timestamp}.json'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)


class RobustPTTScraper:
    """PTT Marvel scraper with batch processing and error recovery."""
    
    def __init__(self, batch_size: int = 100):
        """Initialize robust PTT scraper.
        
        Args:
            batch_size: Number of articles to store per batch
        """
        self.batch_size = batch_size
        self.scraper = PTTMarvelScraper()
        self.storage_manager = PTTPureScrapingManager()
        self.failed_jobs = []
        self.session_stats = {
            'pages_processed': 0,
            'articles_discovered': 0,
            'articles_stored': 0,
            'duplicates': 0,
            'errors': 0,
            'batches_completed': 0,
            'start_time': time.time()
        }
        
        logger.info(f"Robust PTT scraper initialized (batch_size: {batch_size})")
    
    def save_failed_jobs(self):
        """Save failed jobs to file for later recovery."""
        if self.failed_jobs:
            with open(failed_jobs_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'failed_jobs': self.failed_jobs,
                    'stats': self.session_stats
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.failed_jobs)} failed jobs to {failed_jobs_file}")
    
    def load_failed_jobs(self, failed_jobs_path: str) -> List[Dict]:
        """Load failed jobs from previous run."""
        try:
            with open(failed_jobs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                failed_jobs = data.get('failed_jobs', [])
                logger.info(f"Loaded {len(failed_jobs)} failed jobs from {failed_jobs_path}")
                return failed_jobs
        except Exception as e:
            logger.error(f"Failed to load failed jobs: {e}")
            return []
    
    def store_article_batch(self, articles: List[Dict]) -> Dict[str, int]:
        """Store a batch of articles with error handling."""
        batch_stats = {'stored': 0, 'duplicates': 0, 'errors': 0}
        
        for article in articles:
            try:
                if self.storage_manager.store_raw_article_to_bronze(article):
                    batch_stats['stored'] += 1
                else:
                    batch_stats['duplicates'] += 1
            except Exception as e:
                batch_stats['errors'] += 1
                # Record failed job for retry
                self.failed_jobs.append({
                    'article_url': article.get('source_url', 'unknown'),
                    'article_title': article.get('title', 'unknown')[:100],
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                logger.error(f"Failed to store article: {e}")
        
        return batch_stats
    
    def scrape_full_board_with_batching(self, 
                                       start_page: int = 2767, 
                                       end_page: int = 1, 
                                       max_articles: int = 50000) -> Dict[str, int]:
        """Scrape entire PTT Marvel board with batch processing and error recovery."""
        logger.info(f"Starting full PTT Marvel scraping: pages {start_page} to {end_page}")
        
        current_page = start_page
        article_batch = []
        total_pages = start_page - end_page + 1
        
        while current_page >= end_page and self.session_stats['articles_stored'] < max_articles:
            try:
                progress = self.session_stats['pages_processed'] + 1
                logger.info(f"Scraping page {current_page} ({progress}/{total_pages}) - {(progress/total_pages)*100:.1f}%")
                
                # Get page content
                page_url = self.scraper.generate_page_url(current_page)
                soup = self.scraper.get_board_page(page_url)
                
                if not soup:
                    logger.warning(f"Failed to get page {current_page}, skipping")
                    current_page -= 1
                    continue
                
                # Extract all articles (no filtering - PTT Marvel is all ghost stories)
                article_links = self.scraper.extract_article_links(soup)
                
                if article_links:
                    logger.info(f"Found {len(article_links)} articles on page {current_page}")
                    
                    # Get full content for each article
                    for article_info in article_links:
                        if len(article_batch) + self.session_stats['articles_stored'] >= max_articles:
                            break
                        
                        try:
                            article_data = self.scraper.get_article_content(article_info['url'])
                            if article_data:
                                article_data['source'] = 'ptt_marvel'
                                article_batch.append(article_data)
                                self.session_stats['articles_discovered'] += 1
                                
                                logger.debug(f"Collected article: {article_data['title'][:50]}...")
                        
                        except Exception as e:
                            self.failed_jobs.append({
                                'article_url': article_info.get('url', 'unknown'),
                                'article_title': article_info.get('title', 'unknown')[:100],
                                'error': str(e),
                                'timestamp': datetime.now().isoformat(),
                                'page': current_page
                            })
                            logger.error(f"Failed to scrape article {article_info.get('url')}: {e}")
                            self.session_stats['errors'] += 1
                        
                        # Rate limiting
                        time.sleep(self.scraper.request_delay)
                        
                        # Store batch when it reaches batch_size
                        if len(article_batch) >= self.batch_size:
                            logger.info(f"Storing batch of {len(article_batch)} articles...")
                            batch_stats = self.store_article_batch(article_batch)
                            
                            self.session_stats['articles_stored'] += batch_stats['stored']
                            self.session_stats['duplicates'] += batch_stats['duplicates']
                            self.session_stats['errors'] += batch_stats['errors']
                            self.session_stats['batches_completed'] += 1
                            
                            elapsed = time.time() - self.session_stats['start_time']
                            rate = self.session_stats['articles_stored'] / elapsed if elapsed > 0 else 0
                            
                            logger.info(f"Batch {self.session_stats['batches_completed']}: +{batch_stats['stored']} stored, "
                                      f"Total: {self.session_stats['articles_stored']}, Rate: {rate:.2f} articles/sec")
                            
                            # Clear batch for next round
                            article_batch = []
                            
                            # Save failed jobs periodically
                            if self.session_stats['batches_completed'] % 10 == 0:
                                self.save_failed_jobs()
                                elapsed_min = elapsed / 60
                                remaining_pages = current_page - end_page
                                est_time = (remaining_pages * elapsed_min / self.session_stats['pages_processed']) if self.session_stats['pages_processed'] > 0 else 0
                                logger.info(f"Progress checkpoint: {elapsed_min:.1f}min elapsed, ~{est_time:.1f}min remaining")
                else:
                    logger.info(f"No articles found on page {current_page}")
                
                self.session_stats['pages_processed'] += 1
                current_page -= 1
                
                # Progress reporting every 50 pages
                if self.session_stats['pages_processed'] % 50 == 0:
                    elapsed = time.time() - self.session_stats['start_time']
                    avg_time_per_page = elapsed / self.session_stats['pages_processed']
                    remaining_pages = current_page - end_page
                    est_completion = remaining_pages * avg_time_per_page / 3600  # hours
                    
                    logger.info(f"MILESTONE: {self.session_stats['pages_processed']} pages completed")
                    logger.info(f"Stats: {self.session_stats['articles_stored']} stored, "
                              f"{self.session_stats['duplicates']} duplicates, "
                              f"{self.session_stats['errors']} errors")
                    logger.info(f"Est. completion: {est_completion:.1f} hours")
                
                # Page-level rate limiting
                time.sleep(self.scraper.request_delay * 2)
                
            except Exception as e:
                logger.error(f"Error processing page {current_page}: {e}")
                current_page -= 1
                continue
        
        # Store remaining articles in final batch
        if article_batch:
            logger.info(f"Storing final batch of {len(article_batch)} articles...")
            batch_stats = self.store_article_batch(article_batch)
            
            self.session_stats['articles_stored'] += batch_stats['stored']
            self.session_stats['duplicates'] += batch_stats['duplicates']
            self.session_stats['errors'] += batch_stats['errors']
            self.session_stats['batches_completed'] += 1
            
            logger.info(f"Final batch stored: {batch_stats}")
        
        # Calculate final timing
        total_time = time.time() - self.session_stats['start_time']
        self.session_stats['total_time_seconds'] = total_time
        self.session_stats['total_time_hours'] = total_time / 3600
        
        # Save all failed jobs at the end
        self.save_failed_jobs()
        
        logger.info(f"Full scraping completed: {self.session_stats}")
        return self.session_stats
    
    def retry_failed_jobs(self, failed_jobs_path: str) -> Dict[str, int]:
        """Retry failed jobs from previous run."""
        failed_jobs = self.load_failed_jobs(failed_jobs_path)
        
        if not failed_jobs:
            logger.info("No failed jobs to retry")
            return {'retried': 0, 'succeeded': 0, 'failed': 0}
        
        retry_stats = {'retried': 0, 'succeeded': 0, 'failed': 0}
        
        for job in failed_jobs:
            try:
                article_url = job.get('article_url')
                if not article_url or article_url == 'unknown':
                    continue
                
                logger.info(f"Retrying failed article: {job.get('article_title', 'unknown')[:50]}...")
                
                # Retry scraping the article
                article_data = self.scraper.get_article_content(article_url)
                if article_data:
                    article_data['source'] = 'ptt_marvel'
                    
                    # Try to store it
                    if self.storage_manager.store_raw_article_to_bronze(article_data):
                        retry_stats['succeeded'] += 1
                        logger.info(f"Successfully retried: {article_data['title'][:50]}...")
                    else:
                        logger.info(f"Duplicate on retry: {article_data['title'][:50]}...")
                        retry_stats['succeeded'] += 1  # Count duplicates as success
                else:
                    retry_stats['failed'] += 1
                    logger.error(f"Failed to scrape on retry: {article_url}")
                
                retry_stats['retried'] += 1
                
                # Rate limiting for retries
                time.sleep(self.scraper.request_delay)
                
            except Exception as e:
                retry_stats['failed'] += 1
                logger.error(f"Retry failed for {job.get('article_url')}: {e}")
        
        logger.info(f"Retry completed: {retry_stats}")
        return retry_stats


def main():
    """Main function for robust PTT Marvel scraping."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete PTT Marvel Board Scraper')
    parser.add_argument('--start-page', type=int, default=2767, help='Starting page number')
    parser.add_argument('--end-page', type=int, default=1, help='Ending page number')
    parser.add_argument('--max-articles', type=int, default=50000, help='Maximum articles to collect')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for storage')
    parser.add_argument('--retry-failed', type=str, help='Path to failed jobs file to retry')
    
    args = parser.parse_args()
    
    print("🏮 Complete PTT Marvel Board Scraper")
    print("=" * 60)
    print(f"Pages: {args.start_page} to {args.end_page} ({args.start_page - args.end_page + 1} total)")
    print(f"Max articles: {args.max_articles}")
    print(f"Batch size: {args.batch_size}")
    print(f"Log file: {log_file}")
    print(f"Failed jobs file: {failed_jobs_file}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        scraper = RobustPTTScraper(batch_size=args.batch_size)
        
        # Handle retry mode
        if args.retry_failed:
            print(f"🔄 Retrying failed jobs from: {args.retry_failed}")
            retry_stats = scraper.retry_failed_jobs(args.retry_failed)
            print(f"\n📊 Retry Results:")
            print(f"  Jobs retried: {retry_stats['retried']}")
            print(f"  Succeeded: {retry_stats['succeeded']}")
            print(f"  Failed: {retry_stats['failed']}")
            return 0 if retry_stats['failed'] == 0 else 1
        
        # Normal scraping mode
        print("🚀 Starting complete PTT Marvel board scraping...")
        print("✅ Batch storage enabled - resilient to connection errors")
        print("✅ No filtering - collecting all PTT Marvel posts")
        print("✅ Failed job tracking and resume capability")
        print("✅ Progress checkpoints every 50 pages")
        print("⚠️  This will take several hours due to rate limiting")
        print()
        
        # Estimate completion time
        total_pages = args.start_page - args.end_page + 1
        est_hours = (total_pages * 3) / 3600  # ~3 seconds per page
        print(f"📊 Estimated completion time: {est_hours:.1f} hours")
        print()
        
        stats = scraper.scrape_full_board_with_batching(
            start_page=args.start_page,
            end_page=args.end_page,
            max_articles=args.max_articles
        )
        
        # Print final results
        print("\n" + "=" * 60)
        print("🎉 PTT Marvel Board Scraping Complete!")
        print(f"📊 Final Statistics:")
        print(f"  Pages processed: {stats['pages_processed']}")
        print(f"  Articles discovered: {stats['articles_discovered']}")
        print(f"  Articles stored: {stats['articles_stored']}")
        print(f"  Duplicates: {stats['duplicates']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Batches completed: {stats['batches_completed']}")
        print(f"  Total time: {stats.get('total_time_hours', 0):.2f} hours")
        print(f"  Average rate: {stats['articles_stored'] / stats.get('total_time_seconds', 1):.2f} articles/sec")
        
        if stats['articles_stored'] > 0:
            print(f"\n✅ Success! {stats['articles_stored']} PTT Marvel stories stored in Bronze layer")
            print(f"📁 Log file: {log_file}")
            if scraper.failed_jobs:
                print(f"⚠️  {len(scraper.failed_jobs)} failed jobs saved to: {failed_jobs_file}")
                print(f"🔄 To retry: python {__file__} --retry-failed {failed_jobs_file}")
            print(f"🔄 Next step: Run ETL processor to transform Bronze → Silver")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⏸️  Scraping interrupted by user")
        print(f"📊 Partial results saved to Bronze layer")
        print(f"📁 Check log file: {log_file}")
        return 1
        
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
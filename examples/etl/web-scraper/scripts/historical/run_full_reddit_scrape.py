"""
Full Reddit Scraper - Comprehensive historical data collection
Scrapes Reddit r/Ghoststories with date range support for historical data collection.
"""

import sys
import os
import argparse
import logging
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List

# Add scrapers to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from scrapers.reddit_scraper_pure import RedditPureScrapingManager

# Configure logging with file support
def setup_logging() -> tuple[logging.Logger, Path]:
    """Setup logging for full Reddit scraping."""
    # Create logs directory
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f'full_reddit_scrape_{timestamp}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ],
        force=True
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Full Reddit scrape logging initialized - log file: {log_file}")
    return logger, log_file


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)


def generate_date_ranges(start_date: datetime, end_date: datetime, chunk_days: int = 30) -> List[tuple[datetime, datetime]]:
    """Generate date ranges for chunked scraping."""
    ranges = []
    current_start = start_date
    
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=chunk_days), end_date)
        ranges.append((current_start, current_end))
        current_start = current_end
    
    return ranges


def main() -> int:
    """Main function for full Reddit scraping."""
    # Setup logging first
    logger, log_file = setup_logging()
    
    parser = argparse.ArgumentParser(description='Full Reddit Scraper with Date Range Support')
    
    # Date range options
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD). Default: 1 year ago'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD). Default: today'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=365,
        help='Number of days back to scrape (default: 365)'
    )
    
    # Scraping options
    parser.add_argument(
        '--limit',
        type=int,
        default=5000,
        help='Maximum number of stories to scrape (default: 5000)'
    )
    parser.add_argument(
        '--chunk-days',
        type=int,
        default=30,
        help='Days per scraping chunk (default: 30)'
    )
    parser.add_argument(
        '--chunk-limit',
        type=int,
        default=1000,
        help='Stories per chunk (default: 1000)'
    )
    
    # Mode options
    parser.add_argument(
        '--chunked',
        action='store_true',
        help='Use chunked scraping for large date ranges'
    )
    parser.add_argument(
        '--resume-from-failures',
        type=str,
        help='Resume from a failed jobs JSON file'
    )
    
    # Rate limiting options
    parser.add_argument(
        '--base-delay',
        type=float,
        default=2.0,
        help='Base delay between requests in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--batch-delay',
        type=float,
        default=10.0,
        help='Delay between chunks in seconds (default: 10.0)'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=5,
        help='Maximum retries for failed requests (default: 5)'
    )
    parser.add_argument(
        '--use-praw',
        action='store_true',
        default=True,
        help='Use PRAW for better rate limiting (default: True)'
    )
    parser.add_argument(
        '--use-http',
        action='store_true',
        help='Force use of direct HTTP requests instead of PRAW'
    )
    
    args = parser.parse_args()
    
    # Determine date range
    end_date = datetime.now(timezone.utc)
    if args.end_date:
        end_date = parse_date(args.end_date)
    
    if args.start_date:
        start_date = parse_date(args.start_date)
    else:
        start_date = end_date - timedelta(days=args.days_back)
    
    # Validate dates
    if start_date >= end_date:
        print("❌ Error: Start date must be before end date")
        return 1
    
    days_span = (end_date - start_date).days
    
    print("🚀 Full Reddit Scraper")
    print("=" * 50)
    print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"📊 Days span: {days_span}")
    print(f"🎯 Target limit: {args.limit:,} stories")
    print(f"⚡ Mode: {'Chunked' if args.chunked or days_span > 60 else 'Single range'}")
    print(f"🔧 Method: {'PRAW' if not args.use_http else 'Direct HTTP'} (better rate limiting)")
    print(f"📝 Log file: {log_file}")
    print(f"⏱️  Rate limiting: {args.base_delay}s base, {args.batch_delay}s batch, {args.max_retries} retries")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Set rate limiting environment variables
    os.environ['REDDIT_RATE_LIMIT_DELAY'] = str(args.base_delay)
    os.environ['REDDIT_BATCH_DELAY'] = str(args.batch_delay)
    os.environ['REDDIT_MAX_RETRIES'] = str(args.max_retries)
    
    try:
        # Handle resume functionality
        skip_ranges = set()
        if args.resume_from_failures:
            try:
                with open(args.resume_from_failures, 'r') as f:
                    failed_data = json.load(f)
                logger.info(f"Loaded failed jobs from {args.resume_from_failures}")
                print(f"📋 Resuming from {failed_data.get('total_failed_jobs', 0)} previous failures")
                
                # Extract date ranges that already failed to avoid repeating them immediately
                for job in failed_data.get('failed_jobs', []):
                    if 'start_date' in job and 'end_date' in job:
                        skip_ranges.add((job['start_date'], job['end_date']))
                        
            except Exception as e:
                logger.error(f"Failed to load resume file: {e}")
                print(f"❌ Could not load resume file: {e}")
        
        # Initialize scraper
        manager = RedditPureScrapingManager(log_to_file=True)
        logger.info("Reddit scraping manager initialized")
        logger.info(f"Rate limiting config: base={args.base_delay}s, batch={args.batch_delay}s, retries={args.max_retries}")
        total_stats = {
            'discovered': 0,
            'stored': 0,
            'duplicates': 0,
            'errors': 0
        }
        
        # Determine scraping strategy
        if args.chunked or days_span > 60:
            print(f"\\n📦 Using chunked scraping ({args.chunk_days} days per chunk)")
            
            # Generate date ranges
            date_ranges = generate_date_ranges(start_date, end_date, args.chunk_days)
            print(f"📈 Total chunks: {len(date_ranges)}")
            
            for i, (chunk_start, chunk_end) in enumerate(date_ranges, 1):
                print(f"\\n🔍 Chunk {i}/{len(date_ranges)}: {chunk_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")
                
                try:
                    chunk_stats = manager.scrape_by_date_range(
                        start_date=chunk_start,
                        end_date=chunk_end,
                        limit=args.chunk_limit,
                        use_praw=not args.use_http
                    )
                    
                    # Accumulate stats
                    for key in total_stats:
                        total_stats[key] += chunk_stats[key]
                    
                    print(f"✅ Chunk {i} complete: {chunk_stats}")
                    
                    # Stop if we've hit the total limit
                    if total_stats['stored'] >= args.limit:
                        print(f"🎯 Reached target limit of {args.limit:,} stories")
                        break
                        
                except Exception as e:
                    print(f"❌ Chunk {i} failed: {e}")
                    total_stats['errors'] += 1
                    continue
        
        else:
            print(f"\\n🔍 Single range scraping")
            total_stats = manager.scrape_by_date_range(
                start_date=start_date,
                end_date=end_date,
                limit=args.limit,
                use_praw=not args.use_http
            )
        
        # Final results
        print(f"\\n" + "=" * 50)
        print(f"📊 Final Results:")
        print(f"Stories discovered: {total_stats['discovered']:,}")
        print(f"Stories stored: {total_stats['stored']:,}")
        print(f"Duplicates skipped: {total_stats['duplicates']:,}")
        print(f"Errors: {total_stats['errors']:,}")
        print(f"🕐 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if total_stats['stored'] > 0:
            print(f"\\n✅ Success: {total_stats['stored']:,} Reddit stories collected from r/Ghoststories!")
            print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"💾 Stored in: Bronze layer (raw data)")
            print(f"🔄 Next step: Run ETL processor to transform Bronze → Silver")
        else:
            print(f"\\n⚠️  No new stories stored (all may have been duplicates)")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\\n⏹️  Scraping interrupted by user")
        return 1
    except Exception as e:
        print(f"\\n❌ Scraping failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
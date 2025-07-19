"""
Production script for collecting 1,000+ Reddit stories from r/nosleep.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'backend'))
sys.path.append(str(project_root / 'data-pipeline'))

from etl.reddit_etl import RedditETLPipeline
from config.reddit_config import get_config

def setup_logging(log_level: str = 'INFO'):
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / 'reddit_collection.log')
        ]
    )

def check_reddit_credentials():
    """Check if Reddit API credentials are available."""
    config = get_config()
    reddit_config = config['reddit']
    
    if not reddit_config['client_id'] or not reddit_config['client_secret']:
        print("❌ Reddit API credentials not found!")
        print("\nTo set up Reddit API credentials:")
        print("1. Go to https://www.reddit.com/prefs/apps")
        print("2. Create a new application (script type)")
        print("3. Set environment variables:")
        print("   export REDDIT_CLIENT_ID='your_client_id'")
        print("   export REDDIT_CLIENT_SECRET='your_client_secret'")
        print("   export REDDIT_USER_AGENT='YourApp:1.0.0 (by /u/yourusername)'")
        return False
    
    print("✅ Reddit API credentials found")
    return True

def run_collection(target_count: int, test_mode: bool = False):
    """Run the story collection process."""
    logger = logging.getLogger(__name__)
    
    # Initialize pipeline
    pipeline = RedditETLPipeline()
    
    print(f"\n🚀 Starting Reddit story collection")
    print(f"Target stories: {target_count}")
    print(f"Test mode: {'Yes' if test_mode else 'No'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    try:
        # Run ETL pipeline
        stats = pipeline.run_etl_pipeline(
            target_count=target_count,
            test_mode=test_mode
        )
        
        # Display results
        print(f"\n📊 Collection Results:")
        print(f"Total stories extracted: {stats['total']}")
        print(f"Successfully processed: {stats['processed']}")
        print(f"Skipped (duplicates/invalid): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        
        if stats['processed'] > 0:
            success_rate = (stats['processed'] / stats['total']) * 100
            print(f"Success rate: {success_rate:.1f}%")
            print(f"\n✅ Successfully collected {stats['processed']} stories!")
        else:
            print("\n❌ No stories were collected")
            
        return stats
        
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        print(f"\n❌ Collection failed: {e}")
        return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Collect Reddit stories from r/nosleep')
    parser.add_argument(
        '--count', 
        type=int, 
        default=100,
        help='Number of stories to collect (default: 100)'
    )
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Run in test mode (smaller batches, faster execution)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    print("🎃 HauntBro Reddit Story Collector")
    print("=" * 40)
    
    # Check credentials
    if not check_reddit_credentials():
        return 1
    
    # Run collection
    stats = run_collection(args.count, args.test)
    
    if stats and stats['processed'] > 0:
        print(f"\n🎉 Collection complete! Check your database for {stats['processed']} new stories.")
        return 0
    else:
        print("\n😞 Collection failed or no stories collected.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
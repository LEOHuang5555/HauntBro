"""
Pure Reddit ETL Processor - Phase 2: Transform & Load Only
Reads raw Reddit data from Bronze layer and processes to Silver layer.
NO scraping - just pure ETL processing.
"""

import sys
import os
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'backend'))

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database models
from app.database.models import BronzeStory, SilverStory
from app.database.connection import get_db_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedditPureETLProcessor:
    """Pure ETL processor for transforming raw Reddit data from Bronze to Silver."""
    
    def __init__(self, database_url: str = None):
        """Initialize Reddit pure ETL processor."""
        self.database_url = database_url or get_db_url()
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info("Reddit Pure ETL Processor initialized")
    
    def get_raw_reddit_stories(self, limit: int = 50) -> List[BronzeStory]:
        """Get raw Reddit stories from Bronze layer that need processing."""
        db_session = self.SessionLocal()
        
        try:
            # Find Reddit stories that haven't been processed to Silver yet
            raw_stories = db_session.query(BronzeStory).filter(
                and_(
                    BronzeStory.source == 'reddit_nosleep',
                    ~BronzeStory.silver_story.has()  # No corresponding Silver story
                )
            ).limit(limit).all()
            
            logger.info(f"Found {len(raw_stories)} raw Reddit stories needing ETL processing")
            return raw_stories
            
        finally:
            db_session.close()
    
    def clean_and_validate_reddit_story(self, bronze_story: BronzeStory) -> Optional[Dict]:
        """Clean and validate a Reddit story for Silver layer processing."""
        try:
            # Validate required fields
            if not bronze_story.title or not bronze_story.content:
                logger.warning(f"Reddit story {bronze_story.id} missing title or content")
                return None
            
            # Content quality checks
            content = bronze_story.content.strip()
            if len(content) < 100:  # Minimum content length for Reddit
                logger.debug(f"Reddit story {bronze_story.id} too short: {len(content)} characters")
                return None
            
            if len(content) > 50000:  # Maximum content length
                logger.warning(f"Reddit story {bronze_story.id} too long, truncating: {len(content)} characters")
                content = content[:50000] + "... [truncated]"
            
            # Clean title
            title = bronze_story.title.strip()
            if len(title) > 500:
                title = title[:497] + "..."
            
            # Clean author
            author = bronze_story.author or 'unknown'
            if author in ['[deleted]', '[removed]', None, '']:
                author = 'unknown'
            
            # Generate tags based on content analysis
            tags = self.generate_reddit_tags(title, content)
            
            # Calculate metrics
            word_count = len(content.split())
            reading_time = max(1, word_count // 200)  # 200 words per minute
            
            cleaned_data = {
                'title': title,
                'cleaned_content': content,
                'author': author[:100],  # Limit author length
                'post_date': bronze_story.post_date,
                'tags': tags,
                'word_count': word_count,
                'reading_time_minutes': reading_time
            }
            
            return cleaned_data
            
        except Exception as e:
            logger.error(f"Error cleaning Reddit story {bronze_story.id}: {e}")
            return None
    
    def generate_reddit_tags(self, title: str, content: str) -> List[str]:
        """Generate tags for Reddit stories based on content analysis."""
        tags = []
        text = (title + " " + content).lower()
        
        # Horror subgenres
        horror_tags = {
            'supernatural': ['ghost', 'spirit', 'haunted', 'paranormal', 'demon', 'entity'],
            'psychological': ['mental', 'mind', 'insane', 'crazy', 'psychological', 'therapy'],
            'monster': ['monster', 'creature', 'beast', 'thing'],
            'urban_legend': ['urban legend', 'legend', 'folklore', 'myth'],
            'body_horror': ['body', 'flesh', 'blood', 'gore', 'skin'],
            'cosmic_horror': ['cosmic', 'eldritch', 'lovecraft', 'void', 'dimension'],
            'stalker': ['stalker', 'following', 'watching', 'stalking'],
            'home': ['home', 'house', 'apartment', 'room', 'basement', 'attic'],
            'work': ['work', 'office', 'job', 'workplace', 'coworker'],
            'school': ['school', 'college', 'university', 'teacher', 'student'],
            'family': ['family', 'parents', 'brother', 'sister', 'mother', 'father', 'child'],
            'travel': ['travel', 'trip', 'vacation', 'hotel', 'road'],
            'medical': ['hospital', 'doctor', 'patient', 'medical', 'surgery'],
            'technology': ['phone', 'computer', 'internet', 'app', 'website', 'video'],
            'forest': ['forest', 'woods', 'trees', 'camping', 'hiking'],
            'water': ['lake', 'ocean', 'river', 'swimming', 'drowning']
        }
        
        # Detect horror subgenres
        for tag, keywords in horror_tags.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        
        # Reddit specific tags
        tags.append('reddit_nosleep')
        
        # Series detection
        if any(phrase in title.lower() for phrase in ['part', 'update', 'final', 'chapter', 'pt.']):
            tags.append('series')
        
        # POV detection
        if title.lower().startswith(('i ', 'my ', 'me ', 'we ')):
            tags.append('first_person')
        
        # Length-based tags
        word_count = len(content.split())
        if word_count < 500:
            tags.append('short')
        elif word_count > 2000:
            tags.append('long')
        else:
            tags.append('medium')
        
        return tags[:10]  # Limit to 10 tags
    
    def process_bronze_to_silver(self, bronze_story: BronzeStory, cleaned_data: Dict) -> bool:
        """Process a Bronze story to Silver layer."""
        db_session = self.SessionLocal()
        
        try:
            # Create Silver story
            silver_story = SilverStory(
                bronze_story_id=bronze_story.id,
                title=cleaned_data['title'],
                cleaned_content=cleaned_data['cleaned_content'],
                author=cleaned_data['author'],
                post_date=cleaned_data['post_date'],
                tags=cleaned_data['tags'],
                reading_time_minutes=cleaned_data['reading_time_minutes'],
                word_count=cleaned_data['word_count']
            )
            
            db_session.add(silver_story)
            db_session.commit()
            
            logger.debug(f"Processed Reddit story {bronze_story.id} to Silver layer")
            return True
            
        except IntegrityError as e:
            if 'unique_bronze_story' in str(e):
                logger.debug(f"Reddit story {bronze_story.id} already processed to Silver")
                db_session.rollback()
                return False  # Already processed, not an error
            else:
                logger.error(f"Silver layer integrity error for {bronze_story.id}: {e}")
                db_session.rollback()
                raise
        except Exception as e:
            logger.error(f"Error processing Reddit story {bronze_story.id} to Silver: {e}")
            db_session.rollback()
            raise
        finally:
            db_session.close()
    
    def process_batch(self, batch_size: int = 50) -> Dict[str, int]:
        """Process a batch of raw Reddit stories from Bronze to Silver."""
        logger.info(f"Starting Reddit ETL batch processing (batch_size: {batch_size})")
        
        # Get raw Reddit stories needing processing
        raw_stories = self.get_raw_reddit_stories(limit=batch_size)
        
        if not raw_stories:
            logger.info("No raw Reddit stories found needing ETL processing")
            return {'total': 0, 'processed': 0, 'skipped': 0, 'failed': 0}
        
        stats = {
            'total': len(raw_stories),
            'processed': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # Process each raw story
        for bronze_story in raw_stories:
            try:
                # Clean and validate
                cleaned_data = self.clean_and_validate_reddit_story(bronze_story)
                if not cleaned_data:
                    stats['skipped'] += 1
                    continue
                
                # Process to Silver layer
                if self.process_bronze_to_silver(bronze_story, cleaned_data):
                    stats['processed'] += 1
                else:
                    stats['skipped'] += 1  # Already processed
                
            except Exception as e:
                stats['failed'] += 1
                logger.error(f"Failed to process Reddit story {bronze_story.id}: {e}")
            
            # Log progress every 10 items
            if (stats['processed'] + stats['skipped'] + stats['failed']) % 10 == 0:
                logger.info(f"ETL Progress: {stats}")
        
        logger.info(f"Reddit ETL batch completed: {stats}")
        return stats


def main():
    """Main function for pure Reddit ETL processing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pure Reddit ETL Processor (Phase 2: Transform & Load Only)')
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of stories to process in each batch (default: 50)'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously until no raw data to process'
    )
    
    args = parser.parse_args()
    
    print("⚙️  Reddit Pure ETL Processor (Phase 2: Transform & Load Only)")
    print("=" * 60)
    print(f"Batch size: {args.batch_size}")
    print(f"Mode: {'continuous' if args.continuous else 'single batch'}")
    print(f"Source: Bronze layer (raw Reddit data)")
    print(f"Target: Silver layer (processed data)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize ETL processor
        processor = RedditPureETLProcessor()
        
        total_stats = {'total': 0, 'processed': 0, 'skipped': 0, 'failed': 0}
        
        if args.continuous:
            # Run continuously until no raw data
            batch_count = 0
            while True:
                stats = processor.process_batch(batch_size=args.batch_size)
                
                if stats['total'] == 0:
                    break
                
                batch_count += 1
                for key in total_stats:
                    total_stats[key] += stats[key]
                
                print(f"\\nBatch {batch_count} completed: {stats}")
        else:
            # Single batch processing
            total_stats = processor.process_batch(batch_size=args.batch_size)
        
        # Print final results
        print(f"\\n📊 Phase 2 (ETL) Results:")
        print(f"Raw stories processed: {total_stats['total']}")
        print(f"Successfully transformed: {total_stats['processed']}")
        print(f"Skipped (invalid/duplicate): {total_stats['skipped']}")
        print(f"Failed: {total_stats['failed']}")
        
        if total_stats['total'] > 0:
            success_rate = (total_stats['processed'] / total_stats['total'] * 100)
            print(f"Success rate: {success_rate:.1f}%")
        
        if total_stats['processed'] > 0:
            print(f"\\n✅ Phase 2 Complete: {total_stats['processed']} Reddit stories transformed to Silver layer!")
        else:
            print(f"\\n⚠️  No new stories transformed.")
    
    except Exception as e:
        print(f"\\n❌ Phase 2 failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
"""
ETL Pipeline for Reddit stories: Extract → Clean → Store
Integrates Reddit scraper with HauntBro medallion architecture database.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import re

# Add backend to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Import database models and scraper
from app.database.models import BronzeStory, SilverStory, SilverStoryChunk
from app.database.connection import get_db_url

# Import Reddit scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '../scrapers'))
from reddit_scraper import RedditScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedditETLPipeline:
    """ETL Pipeline for processing Reddit stories into medallion architecture."""
    
    def __init__(self, database_url: str = None):
        """Initialize ETL pipeline with database connection."""
        self.database_url = database_url or get_db_url()
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.scraper = RedditScraper()
        
        logger.info("Reddit ETL Pipeline initialized")
    
    def extract_stories(self, target_count: int = 100, test_mode: bool = False) -> List[Dict]:
        """
        Extract stories from Reddit r/nosleep.
        
        Args:
            target_count: Number of stories to extract
            test_mode: If True, use smaller batches for testing
        
        Returns:
            List of raw story dictionaries
        """
        logger.info(f"Starting extraction of {target_count} stories from r/nosleep")
        
        try:
            if test_mode:
                # For testing, fetch smaller batches
                stories = self.scraper.get_nosleep_stories(limit=min(target_count, 20), time_filter='hot')
            else:
                # For production, use bulk collection
                stories = self.scraper.get_bulk_stories(target_count=target_count)
            
            logger.info(f"Successfully extracted {len(stories)} stories")
            return stories
            
        except Exception as e:
            logger.error(f"Error during story extraction: {e}")
            return []
    
    def clean_and_validate_story(self, raw_story: Dict) -> Optional[Dict]:
        """
        Clean and validate a single story for database insertion.
        
        Args:
            raw_story: Raw story dictionary from scraper
        
        Returns:
            Cleaned story dictionary or None if invalid
        """
        try:
            # Validate required fields
            if not all([raw_story.get('title'), raw_story.get('content')]):
                logger.warning("Story missing required fields (title/content)")
                return None
            
            # Content quality checks
            content = raw_story['content']
            if len(content) < 200:  # Minimum content length
                logger.debug(f"Story too short: {len(content)} characters")
                return None
            
            if len(content) > 50000:  # Maximum content length
                logger.warning(f"Story too long, truncating: {len(content)} characters")
                content = content[:50000] + "... [truncated]"
            
            # Clean and validate title
            title = raw_story['title'].strip()
            if len(title) > 500:
                title = title[:497] + "..."
            
            # Validate author
            author = raw_story.get('author', 'unknown')
            if author in ['[deleted]', '[removed]', None]:
                author = 'unknown'
            
            # Generate tags based on content analysis
            tags = self.generate_story_tags(title, content)
            
            # Calculate metrics
            word_count = len(content.split())
            reading_time = max(1, word_count // 200)  # 200 words per minute
            
            cleaned_story = {
                'title': title,
                'content': content,
                'source': 'reddit_nosleep',
                'source_url': raw_story.get('source_url', ''),
                'author': author[:100],  # Limit author length
                'post_date': raw_story.get('post_date'),
                'raw_metadata': raw_story.get('raw_metadata', {}),
                'tags': tags,
                'word_count': word_count,
                'reading_time_minutes': reading_time
            }
            
            return cleaned_story
            
        except Exception as e:
            logger.error(f"Error cleaning story: {e}")
            return None
    
    def generate_story_tags(self, title: str, content: str) -> List[str]:
        """Generate tags based on story content analysis."""
        tags = []
        text = (title + " " + content).lower()
        
        # Horror subgenre detection
        horror_tags = {
            'supernatural': ['ghost', 'spirit', 'paranormal', 'haunted', 'possession'],
            'psychological': ['insane', 'crazy', 'mind', 'psycho', 'mental'],
            'monster': ['creature', 'beast', 'monster', 'thing', 'entity'],
            'survival': ['trapped', 'lost', 'survive', 'escape', 'alone'],
            'family': ['mother', 'father', 'sister', 'brother', 'family'],
            'work': ['office', 'job', 'coworker', 'boss', 'workplace'],
            'home': ['house', 'apartment', 'room', 'basement', 'attic'],
            'childhood': ['child', 'kid', 'school', 'playground', 'toy']
        }
        
        for tag, keywords in horror_tags.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        
        # Length-based tags
        word_count = len(content.split())
        if word_count < 500:
            tags.append('short')
        elif word_count > 2000:
            tags.append('long')
        else:
            tags.append('medium')
        
        # Series detection
        if any(phrase in title.lower() for phrase in ['part', 'update', 'final']):
            tags.append('series')
        
        return tags[:10]  # Limit to 10 tags
    
    def chunk_story_content(self, content: str, chunk_size: int = 1000) -> List[Dict]:
        """
        Split story content into chunks for RAG retrieval.
        
        Args:
            content: Full story content
            chunk_size: Target size for each chunk
        
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        current_chunk = ""
        chunk_order = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size, save current chunk
            if len(current_chunk + paragraph) > chunk_size and current_chunk:
                chunks.append({
                    'chunk_text': current_chunk.strip(),
                    'chunk_context': f"Story chunk {chunk_order + 1}",
                    'chunk_order': chunk_order
                })
                current_chunk = paragraph
                chunk_order += 1
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append({
                'chunk_text': current_chunk.strip(),
                'chunk_context': f"Story chunk {chunk_order + 1}",
                'chunk_order': chunk_order
            })
        
        return chunks
    
    def store_bronze_story(self, db_session, cleaned_story: Dict) -> Optional[str]:
        """
        Store story in Bronze layer (raw data).
        
        Args:
            db_session: Database session
            cleaned_story: Cleaned story dictionary
        
        Returns:
            Story ID if successful, None otherwise
        """
        try:
            bronze_story = BronzeStory(
                title=cleaned_story['title'],
                content=cleaned_story['content'],
                source=cleaned_story['source'],
                source_url=cleaned_story['source_url'],
                author=cleaned_story['author'],
                post_date=cleaned_story['post_date'],
                raw_metadata=cleaned_story['raw_metadata']
            )
            
            db_session.add(bronze_story)
            db_session.flush()  # Get the ID without committing
            
            logger.debug(f"Stored bronze story: {bronze_story.id}")
            return str(bronze_story.id)
            
        except IntegrityError as e:
            logger.warning(f"Story already exists (duplicate): {e}")
            db_session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error storing bronze story: {e}")
            db_session.rollback()
            return None
    
    def store_silver_story(self, db_session, bronze_story_id: str, cleaned_story: Dict) -> bool:
        """
        Store processed story in Silver layer.
        
        Args:
            db_session: Database session
            bronze_story_id: ID of the bronze story
            cleaned_story: Cleaned story dictionary
        
        Returns:
            True if successful, False otherwise
        """
        try:
            silver_story = SilverStory(
                bronze_story_id=bronze_story_id,
                title=cleaned_story['title'],
                cleaned_content=cleaned_story['content'],
                author=cleaned_story['author'],
                post_date=cleaned_story['post_date'],
                tags=cleaned_story['tags'],
                reading_time_minutes=cleaned_story['reading_time_minutes'],
                word_count=cleaned_story['word_count']
            )
            
            db_session.add(silver_story)
            
            # Create story chunks for RAG
            chunks = self.chunk_story_content(cleaned_story['content'])
            for chunk_data in chunks:
                chunk = SilverStoryChunk(
                    bronze_story_id=bronze_story_id,
                    chunk_text=chunk_data['chunk_text'],
                    chunk_context=chunk_data['chunk_context'],
                    chunk_order=chunk_data['chunk_order']
                )
                db_session.add(chunk)
            
            logger.debug(f"Stored silver story with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error storing silver story: {e}")
            db_session.rollback()
            return False
    
    def process_story_batch(self, raw_stories: List[Dict]) -> Dict[str, int]:
        """
        Process a batch of stories through the ETL pipeline.
        
        Args:
            raw_stories: List of raw story dictionaries
        
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'total': len(raw_stories),
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }
        
        db_session = self.SessionLocal()
        
        try:
            for raw_story in raw_stories:
                try:
                    # Clean and validate story
                    cleaned_story = self.clean_and_validate_story(raw_story)
                    if not cleaned_story:
                        stats['skipped'] += 1
                        continue
                    
                    # Store in Bronze layer
                    bronze_id = self.store_bronze_story(db_session, cleaned_story)
                    if not bronze_id:
                        stats['skipped'] += 1
                        continue
                    
                    # Store in Silver layer
                    if self.store_silver_story(db_session, bronze_id, cleaned_story):
                        stats['processed'] += 1
                        
                        # Commit every 10 stories
                        if stats['processed'] % 10 == 0:
                            db_session.commit()
                            logger.info(f"Committed {stats['processed']} stories")
                    else:
                        stats['errors'] += 1
                
                except Exception as e:
                    logger.error(f"Error processing individual story: {e}")
                    stats['errors'] += 1
                    db_session.rollback()
            
            # Final commit
            db_session.commit()
            logger.info(f"Final commit: {stats['processed']} stories processed")
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            db_session.rollback()
        finally:
            db_session.close()
        
        return stats
    
    def run_etl_pipeline(self, target_count: int = 100, test_mode: bool = False) -> Dict[str, int]:
        """
        Run the complete ETL pipeline.
        
        Args:
            target_count: Number of stories to process
            test_mode: If True, run in test mode with smaller batches
        
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Starting Reddit ETL pipeline (target: {target_count} stories)")
        
        start_time = datetime.now()
        
        # Extract
        raw_stories = self.extract_stories(target_count, test_mode)
        if not raw_stories:
            logger.error("No stories extracted, stopping pipeline")
            return {'total': 0, 'processed': 0, 'skipped': 0, 'errors': 0}
        
        # Transform and Load
        stats = self.process_story_batch(raw_stories)
        
        # Calculate processing time
        processing_time = datetime.now() - start_time
        
        logger.info(f"ETL Pipeline completed in {processing_time}")
        logger.info(f"Statistics: {stats}")
        
        return stats


def main():
    """Main function for running the Reddit ETL pipeline."""
    pipeline = RedditETLPipeline()
    
    # Test mode - process 20 stories
    print("Running Reddit ETL Pipeline in test mode...")
    stats = pipeline.run_etl_pipeline(target_count=20, test_mode=True)
    
    print(f"\nPipeline Results:")
    print(f"Total stories: {stats['total']}")
    print(f"Successfully processed: {stats['processed']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    
    if stats['processed'] > 0:
        print(f"\n✓ Successfully stored {stats['processed']} stories in database")
    else:
        print("\n✗ No stories were processed")


if __name__ == "__main__":
    main()
"""
Reddit scraper for r/nosleep ghost stories using PRAW.
Implements rate limiting, error handling, and data extraction.
"""

import os
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
import re

import praw
from tenacity import retry, stop_after_attempt, wait_exponential
from praw.exceptions import RedditAPIException, PRAWException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedditScraper:
    """Reddit scraper for r/nosleep stories."""
    
    def __init__(self, client_id: str = None, client_secret: str = None, user_agent: str = None):
        """Initialize Reddit scraper with PRAW client."""
        # Reddit API credentials - use environment variables for security
        self.client_id = client_id or os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('REDDIT_CLIENT_SECRET')
        self.user_agent = user_agent or os.getenv('REDDIT_USER_AGENT', 'HauntBro:1.0.0 (by /u/YOUR_USERNAME)')
        
        if not all([self.client_id, self.client_secret]):
            logger.warning("Reddit API credentials not found. Using read-only mode.")
            self.reddit = None
        else:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent
                )
                logger.info("Reddit API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit client: {e}")
                self.reddit = None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove Reddit markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'~~(.*?)~~', r'\1', text)      # Strikethrough
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Links
        
        # Remove multiple spaces and normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common Reddit artifacts
        text = re.sub(r'^EDIT:.*?$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^UPDATE:.*?$', '', text, flags=re.MULTILINE)
        
        return text
    
    def extract_story_metadata(self, submission) -> Dict:
        """Extract metadata from Reddit submission."""
        try:
            # Calculate reading time (average 200 words per minute)
            word_count = len(submission.selftext.split()) if submission.selftext else 0
            reading_time = max(1, word_count // 200)
            
            # Extract basic metadata
            metadata = {
                'reddit_id': submission.id,
                'url': f"https://reddit.com{submission.permalink}",
                'score': submission.score,
                'upvote_ratio': getattr(submission, 'upvote_ratio', None),
                'num_comments': submission.num_comments,
                'flair': submission.link_flair_text,
                'is_nsfw': submission.over_18,
                'is_spoiler': submission.spoiler,
                'word_count': word_count,
                'reading_time_minutes': reading_time,
                'created_utc': submission.created_utc,
                'awards': getattr(submission, 'total_awards_received', 0)
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from submission {submission.id}: {e}")
            return {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_nosleep_stories(self, limit: int = 100, time_filter: str = 'all') -> List[Dict]:
        """
        Fetch stories from r/nosleep with retry logic.
        
        Args:
            limit: Number of stories to fetch (max 1000 per request)
            time_filter: Time filter ('all', 'day', 'week', 'month', 'year')
        
        Returns:
            List of story dictionaries
        """
        if not self.reddit:
            logger.error("Reddit client not initialized")
            return []
        
        stories = []
        
        try:
            logger.info(f"Fetching {limit} stories from r/nosleep (time_filter: {time_filter})")
            
            # Get subreddit
            nosleep = self.reddit.subreddit('nosleep')
            
            # Fetch top stories based on time filter
            if time_filter == 'all':
                submissions = nosleep.top(limit=limit, time_filter='all')
            elif time_filter == 'hot':
                submissions = nosleep.hot(limit=limit)
            elif time_filter == 'new':
                submissions = nosleep.new(limit=limit)
            else:
                submissions = nosleep.top(limit=limit, time_filter=time_filter)
            
            for submission in submissions:
                try:
                    # Skip removed or deleted posts
                    if submission.selftext in ['[removed]', '[deleted]', '']:
                        continue
                    
                    # Extract and clean story data
                    story_data = {
                        'title': self.clean_text(submission.title),
                        'content': self.clean_text(submission.selftext),
                        'source': 'reddit_nosleep',
                        'source_url': f"https://reddit.com{submission.permalink}",
                        'author': str(submission.author) if submission.author else '[deleted]',
                        'post_date': datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                        'raw_metadata': self.extract_story_metadata(submission)
                    }
                    
                    # Only include stories with substantial content
                    if len(story_data['content']) > 100:  # Minimum 100 characters
                        stories.append(story_data)
                        logger.debug(f"Extracted story: {story_data['title'][:50]}...")
                    
                    # Rate limiting - be respectful to Reddit API
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing submission {submission.id}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(stories)} stories from r/nosleep")
            return stories
            
        except RedditAPIException as e:
            logger.error(f"Reddit API error: {e}")
            raise
        except PRAWException as e:
            logger.error(f"PRAW error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching nosleep stories: {e}")
            raise
    
    def get_bulk_stories(self, target_count: int = 1000) -> List[Dict]:
        """
        Fetch a large number of stories by combining different time filters.
        
        Args:
            target_count: Target number of stories to collect
        
        Returns:
            List of unique story dictionaries
        """
        if not self.reddit:
            logger.error("Reddit client not initialized")
            return []
        
        all_stories = []
        seen_ids = set()
        
        # Define fetch strategy to get diverse content
        fetch_strategy = [
            ('hot', 100),      # Current popular stories
            ('week', 200),     # Popular this week
            ('month', 300),    # Popular this month
            ('year', 400),     # Popular this year
            ('all', 500),      # All-time popular
            ('new', 200),      # Recent stories
        ]
        
        for time_filter, batch_size in fetch_strategy:
            if len(all_stories) >= target_count:
                break
            
            try:
                logger.info(f"Fetching {batch_size} stories with filter '{time_filter}'")
                batch_stories = self.get_nosleep_stories(limit=batch_size, time_filter=time_filter)
                
                # Deduplicate stories
                for story in batch_stories:
                    story_id = story['raw_metadata'].get('reddit_id')
                    if story_id and story_id not in seen_ids:
                        seen_ids.add(story_id)
                        all_stories.append(story)
                
                logger.info(f"Total unique stories collected: {len(all_stories)}")
                
                # Rate limiting between batches
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in batch fetch with filter '{time_filter}': {e}")
                continue
        
        logger.info(f"Bulk collection complete: {len(all_stories)} unique stories")
        return all_stories[:target_count]


# Test and demonstration functions
def test_reddit_connection():
    """Test Reddit API connection."""
    scraper = RedditScraper()
    if scraper.reddit:
        try:
            # Test with a small fetch
            stories = scraper.get_nosleep_stories(limit=5, time_filter='hot')
            print(f"✓ Successfully fetched {len(stories)} test stories")
            
            if stories:
                sample_story = stories[0]
                print(f"Sample story: '{sample_story['title'][:50]}...'")
                print(f"Author: {sample_story['author']}")
                print(f"Content length: {len(sample_story['content'])} characters")
            
            return True
        except Exception as e:
            print(f"✗ Reddit connection test failed: {e}")
            return False
    else:
        print("✗ Reddit client not initialized - check credentials")
        return False


if __name__ == "__main__":
    # Set up credentials (replace with your actual credentials)
    print("Reddit Scraper Test")
    print("==================")
    
    # Test connection
    if test_reddit_connection():
        print("\nReddit API integration successful!")
        print("\nTo use the scraper:")
        print("1. Set environment variables: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT")
        print("2. Import RedditScraper and call get_bulk_stories(1000) for full collection")
    else:
        print("\nPlease set up Reddit API credentials:")
        print("1. Go to https://www.reddit.com/prefs/apps")
        print("2. Create a new application")
        print("3. Set environment variables with your credentials")
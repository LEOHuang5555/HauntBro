"""
Reddit scraper for r/ghoststories ghost stories using PRAW.
Implements rate limiting, error handling, and data extraction.
"""

import os
import logging
import time
import requests
import json
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import re
from dotenv import load_dotenv

import praw
from tenacity import retry, stop_after_attempt, wait_exponential
from praw.exceptions import RedditAPIException, PRAWException

# Load environment variables
load_dotenv()

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
        log_file = log_dir / f'reddit_scraper_{timestamp}.log'
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


class RedditScraper:
    """Reddit scraper for r/ghoststories stories."""
    
    def __init__(self, client_id: str = None, client_secret: str = None, user_agent: str = None, log_to_file: bool = True):
        """Initialize Reddit scraper with PRAW client."""
        # Setup logging if requested
        if log_to_file:
            global logger
            logger = setup_logging(log_to_file)
        
        # Initialize failed jobs tracking
        self.failed_jobs = []
        if log_to_file:
            log_dir = Path(__file__).parent.parent / 'logs'
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.failed_jobs_file = log_dir / f'reddit_failed_jobs_{timestamp}.json'
        else:
            self.failed_jobs_file = None
        
        # Rate limiting configuration
        self.base_delay = float(os.getenv('REDDIT_RATE_LIMIT_DELAY', '1.0'))
        self.batch_delay = float(os.getenv('REDDIT_BATCH_DELAY', '2.0'))
        self.max_retries = int(os.getenv('REDDIT_MAX_RETRIES', '3'))
        self.backoff_base = float(os.getenv('REDDIT_BACKOFF_BASE', '60.0'))  # Base backoff in seconds
        
        # Rate limiting state
        self.consecutive_429s = 0
        self.last_request_time = 0
        
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
    
    def extract_story_metadata(self, submission: praw.models.Submission) -> Dict:
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
    def get_ghoststories_stories(self, limit: int = 100, time_filter: str = 'all') -> List[Dict]:
        """
        Fetch stories from r/ghoststories with retry logic.
        
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
            logger.info(f"Fetching {limit} stories from r/ghoststories (time_filter: {time_filter})")
            
            # Get subreddit
            ghoststories = self.reddit.subreddit('ghoststories')
            
            # Fetch top stories based on time filter
            if time_filter == 'all':
                submissions = ghoststories.top(limit=limit, time_filter='all')
            elif time_filter == 'hot':
                submissions = ghoststories.hot(limit=limit)
            elif time_filter == 'new':
                submissions = ghoststories.new(limit=limit)
            else:
                submissions = ghoststories.top(limit=limit, time_filter=time_filter)
            
            for submission in submissions:
                try:
                    # Skip removed or deleted posts
                    if submission.selftext in ['[removed]', '[deleted]', '']:
                        continue
                    
                    # Extract and clean story data
                    story_data = {
                        'title': self.clean_text(submission.title),
                        'content': self.clean_text(submission.selftext),
                        'source': 'reddit_ghoststories',
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
                    rate_delay = float(os.getenv('REDDIT_RATE_LIMIT_DELAY', '0.1'))
                    time.sleep(rate_delay)
                    
                except Exception as e:
                    error_info = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'error_type': 'submission_processing',
                        'submission_id': getattr(submission, 'id', 'unknown'),
                        'error_message': str(e),
                        'time_filter': time_filter,
                        'limit': limit
                    }
                    self.failed_jobs.append(error_info)
                    logger.error(f"Error processing submission {submission.id}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(stories)} stories from r/ghoststories")
            return stories
            
        except RedditAPIException as e:
            error_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': 'reddit_api_error',
                'error_message': str(e),
                'time_filter': time_filter,
                'limit': limit
            }
            self.failed_jobs.append(error_info)
            self._save_failed_jobs()
            logger.error(f"Reddit API error: {e}")
            raise
        except PRAWException as e:
            error_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': 'praw_error',
                'error_message': str(e),
                'time_filter': time_filter,
                'limit': limit
            }
            self.failed_jobs.append(error_info)
            self._save_failed_jobs()
            logger.error(f"PRAW error: {e}")
            raise
        except Exception as e:
            error_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': 'unexpected_error',
                'error_message': str(e),
                'time_filter': time_filter,
                'limit': limit
            }
            self.failed_jobs.append(error_info)
            self._save_failed_jobs()
            logger.error(f"Unexpected error fetching ghoststories stories: {e}")
            raise
    
    
    def get_stories_by_date_range(self, 
                                 start_date: datetime = None,
                                 end_date: datetime = None,
                                 limit: int = 1000) -> List[Dict]:
        """
        Get stories from r/ghoststories within a specific date range.
        Uses the /new endpoint and filters by timestamp.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of stories to collect
            
        Returns:
            List of stories within the date range
        """
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        start_ts = start_date.timestamp()
        end_ts = end_date.timestamp()
        
        logger.info(f"Collecting stories from r/ghoststories")
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        collected_stories = []
        
        # Use direct HTTP requests for date filtering with proper User-Agent
        # Reddit heavily rate limits default Python User-Agents
        user_agent = self.user_agent or os.getenv('REDDIT_USER_AGENT', 'HauntBro:v1.0.0 (by /u/hauntbro_dev)')
        headers = {
            'User-Agent': user_agent,
            'Accept': 'application/json',
            'Accept-Charset': 'utf-8'
        }
        base_url = "https://www.reddit.com"
        
        logger.info(f"Using User-Agent: {user_agent}")
        after = None
        batch_size = 25
        
        try:
            while len(collected_stories) < limit:
                # Build request parameters
                params = {
                    'limit': min(batch_size, limit - len(collected_stories)),
                    'raw_json': 1
                }
                
                if after:
                    params['after'] = after
                
                # Make request to /new endpoint with retry logic
                url = f"{base_url}/r/ghoststories/new.json"
                
                data = self._make_request_with_retry(url, headers, params)
                if not data:
                    logger.error(f"Failed to get data after {self.max_retries} retries")
                    break
                posts = data['data']['children']
                
                if not posts:
                    logger.info("No more posts available")
                    break
                
                # Filter posts by date range and convert to story format
                for post in posts:
                    post_data = post['data']
                    post_ts = post_data['created_utc']
                    
                    # Check if post is within our date range
                    if start_ts <= post_ts <= end_ts:
                        # Skip removed or deleted posts
                        if post_data.get('selftext') in ['[removed]', '[deleted]', '']:
                            continue
                        
                        # Convert to standard story format
                        story_data = {
                            'title': self.clean_text(post_data['title']),
                            'content': self.clean_text(post_data.get('selftext', '')),
                            'source': 'reddit_ghoststories',
                            'source_url': f"https://reddit.com{post_data['permalink']}",
                            'author': str(post_data.get('author', '[deleted]')),
                            'post_date': datetime.fromtimestamp(post_ts, tz=timezone.utc),
                            'raw_metadata': {
                                'reddit_id': post_data['id'],
                                'url': f"https://reddit.com{post_data['permalink']}",
                                'score': post_data['score'],
                                'upvote_ratio': post_data.get('upvote_ratio'),
                                'num_comments': post_data['num_comments'],
                                'flair': post_data.get('link_flair_text'),
                                'is_nsfw': post_data.get('over_18', False),
                                'is_spoiler': post_data.get('spoiler', False),
                                'word_count': len(post_data.get('selftext', '').split()) if post_data.get('selftext') else 0,
                                'created_utc': post_ts,
                                'awards': post_data.get('total_awards_received', 0)
                            }
                        }
                        
                        # Only include stories with substantial content
                        if len(story_data['content']) > 100:
                            collected_stories.append(story_data)
                            
                    elif post_ts < start_ts:
                        # We've gone past our date range (posts are sorted by new)
                        logger.info(f"Reached posts older than start date. Stopping.")
                        return collected_stories
                
                # Update 'after' for pagination
                after = data['data']['after']
                if not after:
                    logger.info("No more pages available")
                    break
                
                logger.info(f"Collected {len(collected_stories)} stories so far...")
                
                # Adaptive rate limiting
                self._apply_rate_limiting()
                
        except requests.exceptions.RequestException as e:
            error_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': 'request_error',
                'error_message': str(e),
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'limit': limit
            }
            self.failed_jobs.append(error_info)
            self._save_failed_jobs()
            logger.error(f"Request error: {e}")
        except Exception as e:
            error_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': 'date_range_error',
                'error_message': str(e),
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'limit': limit
            }
            self.failed_jobs.append(error_info)
            self._save_failed_jobs()
            logger.error(f"Error collecting stories by date range: {e}")
        
        logger.info(f"Date range collection complete: {len(collected_stories)} stories")
        self._save_failed_jobs()  # Save any accumulated errors
        return collected_stories
    
    def get_stories_by_date_range_praw(self, 
                                      start_date: datetime = None,
                                      end_date: datetime = None,
                                      limit: int = 1000) -> List[Dict]:
        """
        Get stories from r/ghoststories within a specific date range using PRAW.
        PRAW handles User-Agent and rate limiting automatically.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of stories to collect
            
        Returns:
            List of stories within the date range
        """
        if not self.reddit:
            logger.error("PRAW Reddit client not initialized - check credentials")
            return []
            
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        start_ts = start_date.timestamp()
        end_ts = end_date.timestamp()
        
        logger.info(f"Using PRAW to collect stories from r/ghoststories")
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        collected_stories = []
        
        try:
            ghoststories = self.reddit.subreddit('ghoststories')
            
            # Use PRAW's new() method to get posts in chronological order
            for submission in ghoststories.new(limit=None):  # Get all available
                try:
                    post_ts = submission.created_utc
                    
                    # Check if we've gone past our date range
                    if post_ts < start_ts:
                        logger.info(f"Reached posts older than start date. Stopping.")
                        break
                    
                    # Check if post is within our date range
                    if start_ts <= post_ts <= end_ts:
                        # Skip removed or deleted posts
                        if submission.selftext in ['[removed]', '[deleted]', '']:
                            continue
                        
                        # Convert to standard story format
                        story_data = {
                            'title': self.clean_text(submission.title),
                            'content': self.clean_text(submission.selftext),
                            'source': 'reddit_ghoststories',
                            'source_url': f"https://reddit.com{submission.permalink}",
                            'author': str(submission.author) if submission.author else '[deleted]',
                            'post_date': datetime.fromtimestamp(post_ts, tz=timezone.utc),
                            'raw_metadata': self.extract_story_metadata(submission)
                        }
                        
                        # Only include stories with substantial content
                        if len(story_data['content']) > 100:
                            collected_stories.append(story_data)
                            
                        # Stop if we've reached our limit
                        if len(collected_stories) >= limit:
                            logger.info(f"Reached limit of {limit} stories")
                            break
                    
                    # PRAW handles rate limiting automatically, but we can add a small delay
                    if len(collected_stories) % 25 == 0 and len(collected_stories) > 0:
                        logger.info(f"PRAW: Collected {len(collected_stories)} stories so far...")
                        time.sleep(0.1)  # Small delay every 25 stories
                        
                except Exception as e:
                    error_info = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'error_type': 'praw_submission_processing',
                        'submission_id': getattr(submission, 'id', 'unknown'),
                        'error_message': str(e),
                        'start_date': start_date.isoformat() if start_date else None,
                        'end_date': end_date.isoformat() if end_date else None
                    }
                    self.failed_jobs.append(error_info)
                    logger.error(f"Error processing PRAW submission {getattr(submission, 'id', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            error_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': 'praw_date_range_error',
                'error_message': str(e),
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'limit': limit
            }
            self.failed_jobs.append(error_info)
            self._save_failed_jobs()
            logger.error(f"Error in PRAW date range collection: {e}")
        
        logger.info(f"PRAW date range collection complete: {len(collected_stories)} stories")
        self._save_failed_jobs()
        return collected_stories
    
    def _apply_rate_limiting(self):
        """Apply intelligent rate limiting based on recent 429 errors."""
        current_time = time.time()
        
        # Base delay between requests
        base_delay = self.base_delay
        
        # Add exponential backoff if we've hit 429 errors recently
        if self.consecutive_429s > 0:
            backoff_delay = self.backoff_base * (2 ** (self.consecutive_429s - 1))
            total_delay = base_delay + backoff_delay
            logger.info(f"Rate limit backoff: waiting {total_delay:.1f}s (consecutive 429s: {self.consecutive_429s})")
        else:
            total_delay = base_delay
        
        # Add small random jitter to avoid thundering herd
        jitter = random.uniform(0, 0.5)
        total_delay += jitter
        
        # Ensure minimum time between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < total_delay:
            sleep_time = total_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request_with_retry(self, url: str, headers: dict, params: dict) -> Optional[dict]:
        """Make HTTP request with intelligent retry logic for rate limiting."""
        for attempt in range(self.max_retries + 1):
            try:
                # Apply rate limiting before request
                if attempt > 0:  # Don't delay on first attempt
                    self._apply_rate_limiting()
                
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    # Success - reset consecutive 429 counter
                    self.consecutive_429s = 0
                    return response.json()
                    
                elif response.status_code == 429:
                    # Rate limited
                    self.consecutive_429s += 1
                    retry_after = response.headers.get('Retry-After')
                    
                    if retry_after:
                        # Reddit told us exactly how long to wait
                        wait_time = float(retry_after)
                        logger.warning(f"Rate limited (429). Reddit says wait {wait_time}s. Attempt {attempt + 1}/{self.max_retries + 1}")
                    else:
                        # Calculate exponential backoff
                        wait_time = self.backoff_base * (2 ** self.consecutive_429s)
                        logger.warning(f"Rate limited (429). Backing off for {wait_time:.1f}s. Attempt {attempt + 1}/{self.max_retries + 1}")
                    
                    if attempt < self.max_retries:
                        logger.info(f"Waiting {wait_time:.1f} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # Max retries reached
                        raise requests.exceptions.RequestException(
                            f"429 Client Error: Too Many Requests for url: {url} (max retries reached)"
                        )
                
                else:
                    # Other HTTP error
                    response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Simple exponential backoff for other errors
                    logger.warning(f"Request failed: {e}. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries + 1})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        return None
    
    def _save_failed_jobs(self):
        """Save failed jobs to JSON file."""
        if self.failed_jobs_file and self.failed_jobs:
            try:
                with open(self.failed_jobs_file, 'w') as f:
                    json.dump({
                        'scraper_type': 'reddit_scraper',
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


# Test and demonstration functions
def test_reddit_connection():
    """Test Reddit API connection."""
    scraper = RedditScraper()
    if scraper.reddit:
        try:
            # Test with a small fetch
            stories = scraper.get_ghoststories_stories(limit=5, time_filter='hot')
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


def test_logging():
    """Test the logging functionality."""
    print("Testing Reddit Scraper Logging")
    print("=" * 40)
    
    scraper = RedditScraper(log_to_file=True)
    
    # Test with a small fetch to generate some logs
    try:
        stories = scraper.get_ghoststories_stories(limit=3, time_filter='hot')
        print(f"✓ Fetched {len(stories)} stories for logging test")
        
        # Get failed jobs summary
        summary = scraper.get_failed_jobs_summary()
        print(f"✓ Failed jobs: {summary}")
        
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        
    return scraper.get_failed_jobs_summary()


if __name__ == "__main__":
    # Set up credentials (replace with your actual credentials)
    print("Reddit Scraper Test")
    print("==================")
    
    # Test connection
    if test_reddit_connection():
        print("\nReddit API integration successful!")
        print("\nTesting logging functionality...")
        logging_summary = test_logging()
        print(f"Logging test summary: {logging_summary}")
        
        print("\nTo use the scraper:")
        print("1. Set environment variables: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT")
        print("2. Import RedditScraper and call get_bulk_stories(1000) for full collection")
        print("3. Check logs/ directory for detailed logs and failed job tracking")
    else:
        print("\nPlease set up Reddit API credentials:")
        print("1. Go to https://www.reddit.com/prefs/apps")
        print("2. Create a new application")
        print("3. Set environment variables with your credentials")
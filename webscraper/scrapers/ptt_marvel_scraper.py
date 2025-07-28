"""
PTT Marvel board scraper for ghost stories.
Scrapes PTT Marvel board and integrates with HauntBro medallion architecture.
"""

import os
import sys
import logging
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(project_root, 'backend'))

from sqlalchemy import create_engine, text
from app.database.connection import get_db_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PTTMarvelScraper:
    """PTT Marvel board scraper for ghost stories."""
    
    def __init__(self):
        """Initialize PTT Marvel scraper."""
        self.base_url = "https://www.ptt.cc"
        self.board_url = "https://www.ptt.cc/bbs/marvel/index.html"
        self.session = requests.Session()
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Rate limiting settings
        self.request_delay = float(os.getenv('PTT_REQUEST_DELAY', '1.0'))
        self.max_retries = int(os.getenv('PTT_MAX_RETRIES', '3'))
        
        logger.info("PTT Marvel scraper initialized")
    
    def handle_ptt_over18(self, url: str) -> requests.Response:
        """Handle PTT over-18 confirmation page."""
        try:
            response = self.session.get(url)
            
            # Check if we hit the over-18 confirmation page
            if 'ask/over18' in response.url:
                logger.info("Handling PTT over-18 confirmation")
                
                # Submit the over-18 form
                over18_url = urljoin(self.base_url, '/ask/over18')
                form_data = {'yes': 'yes'}
                
                self.session.post(over18_url, data=form_data)
                
                # Retry the original request
                response = self.session.get(url)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling PTT over-18 page: {e}")
            raise
    
    def get_board_page(self, page_url: str) -> Optional[BeautifulSoup]:
        """Get and parse a PTT board page."""
        try:
            response = self.handle_ptt_over18(page_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
            
        except Exception as e:
            logger.error(f"Error fetching board page {page_url}: {e}")
            return None
    
    def extract_article_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract article links from board page."""
        articles = []
        
        try:
            # Find all article entries
            entries = soup.find_all('div', class_='r-ent')
            
            for entry in entries:
                try:
                    # Get title link
                    title_link = entry.find('div', class_='title').find('a')
                    if not title_link:
                        continue
                    
                    # Extract article info
                    article_info = {
                        'title': title_link.text.strip(),
                        'url': urljoin(self.base_url, title_link.get('href')),
                        'author': entry.find('div', class_='author').text.strip() if entry.find('div', class_='author') else 'unknown',
                        'date': entry.find('div', class_='date').text.strip() if entry.find('div', class_='date') else ''
                    }
                    
                    articles.append(article_info)
                    logger.debug(f"Found article: {article_info['title']}")
                
                except Exception as e:
                    logger.warning(f"Error extracting article info: {e}")
                    continue
            
            logger.info(f"Found {len(articles)} articles on page")
            return articles
            
        except Exception as e:
            logger.error(f"Error extracting article links: {e}")
            return []
    
    def is_ghost_story(self, title: str) -> bool:
        """Check if title indicates a ghost/horror story."""
        ghost_keywords = [
            '靈異', '鬼', '恐怖', '驚悚', '詭異', '神秘', '超自然',
            '陰間', '地獄', '冥界', '異世界', '靈魂', '幽靈', '鬼魂',
            '詛咒', '邪靈', '妖怪', '怪談', '都市傳說', '校園怪談',
            '醫院', '廢墟', '古宅', '墓地', '深山', '隧道',
            # English keywords for mixed content
            'ghost', 'horror', 'supernatural', 'paranormal', 'scary',
            'creepy', 'haunted', 'spirit', 'demon', 'nightmare'
        ]
        
        title_lower = title.lower()
        return any(keyword in title or keyword in title_lower for keyword in ghost_keywords)
    
    def get_article_content(self, article_url: str) -> Optional[Dict]:
        """Scrape full article content."""
        try:
            response = self.handle_ptt_over18(article_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article metadata
            main_content = soup.find('div', id='main-content')
            if not main_content:
                logger.warning(f"No main content found for {article_url}")
                return None
            
            # Extract article info
            meta_spans = main_content.find_all('span', class_='article-meta-value')
            if len(meta_spans) < 4:
                logger.warning(f"Insufficient metadata for {article_url}")
                return None
            
            author = meta_spans[0].text.strip()
            board = meta_spans[1].text.strip()
            title = meta_spans[2].text.strip()
            post_time = meta_spans[3].text.strip()
            
            # Extract main content text
            # Remove metadata and push elements
            for elem in main_content.find_all(['span', 'div'], class_=['article-meta-tag', 'article-meta-value', 'push']):
                elem.decompose()
            
            # Get the remaining text
            content = main_content.get_text(separator='\n').strip()
            
            # Clean up content
            content = self.clean_content(content)
            
            # Parse post date
            post_date = self.parse_ptt_date(post_time)
            
            article_data = {
                'title': title,
                'content': content,
                'author': author,
                'board': board,
                'post_date': post_date,
                'source_url': article_url,
                'raw_html': str(main_content)
            }
            
            logger.debug(f"Extracted article: {title[:50]}...")
            return article_data
            
        except Exception as e:
            logger.error(f"Error extracting article content from {article_url}: {e}")
            return None
    
    def clean_content(self, content: str) -> str:
        """Clean article content."""
        if not content:
            return ""
        
        # Remove common PTT artifacts
        content = re.sub(r'※ 發信站.*?\n', '', content)
        content = re.sub(r'※ 文章網址.*?\n', '', content)
        content = re.sub(r'--\n.*', '', content, flags=re.DOTALL)
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        return content.strip()
    
    def parse_ptt_date(self, date_str: str) -> Optional[datetime]:
        """Parse PTT date format to datetime."""
        try:
            # PTT date format: "Fri Dec 15 14:30:25 2023"
            dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y")
            return dt.replace(tzinfo=timezone.utc)
        except:
            try:
                # Alternative format without year
                current_year = datetime.now().year
                dt = datetime.strptime(f"{date_str} {current_year}", "%m/%d %H:%M %Y")
                return dt.replace(tzinfo=timezone.utc)
            except:
                logger.warning(f"Could not parse date: {date_str}")
                return None
    
    def get_previous_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Get URL for previous page."""
        try:
            prev_link = soup.find('a', string='‹ 上頁')
            if prev_link and prev_link.get('href'):
                return urljoin(self.base_url, prev_link.get('href'))
            return None
        except:
            return None
    
    def generate_page_url(self, page_number: int) -> str:
        """Generate PTT page URL for specific page number."""
        if page_number == 1:
            return "https://www.ptt.cc/bbs/marvel/index.html"
        else:
            return f"https://www.ptt.cc/bbs/marvel/index{page_number}.html"
    
    def scrape_board(self, max_pages: int = 5, max_articles: int = 100, start_page: int = 2765) -> List[Dict]:
        """Scrape PTT Marvel board for ghost stories.
        
        Args:
            max_pages: Maximum number of pages to scrape
            max_articles: Maximum number of articles to collect
            start_page: Starting page number (defaults to latest page 2765)
        """
        all_articles = []
        pages_scraped = 0
        
        logger.info(f"Starting PTT Marvel scrape from page {start_page} (max {max_pages} pages, {max_articles} articles)")
        
        # Start from the specified page and work backwards
        current_page = start_page
        
        while pages_scraped < max_pages and len(all_articles) < max_articles and current_page > 0:
            try:
                current_url = self.generate_page_url(current_page)
                logger.info(f"Scraping page {pages_scraped + 1}/{max_pages}: {current_url}")
                
                # Get board page
                soup = self.get_board_page(current_url)
                if not soup:
                    logger.warning(f"Failed to get page {current_page}, skipping")
                    current_page -= 1
                    continue
                
                # Extract article links
                article_links = self.extract_article_links(soup)
                
                if not article_links:
                    logger.info(f"No ghost stories found on page {current_page}")
                    current_page -= 1
                    continue
                
                # Get full content for each article
                for article_info in article_links:
                    if len(all_articles) >= max_articles:
                        break
                    
                    try:
                        # Get full article content
                        article_data = self.get_article_content(article_info['url'])
                        if article_data:
                            # Add source info
                            article_data['source'] = 'ptt_marvel'
                            all_articles.append(article_data)
                            
                            logger.info(f"Scraped article {len(all_articles)}: {article_data['title'][:50]}...")
                    
                    except Exception as e:
                        logger.error(f"Error scraping article {article_info['url']}: {e}")
                        continue
                    
                    # Rate limiting
                    time.sleep(self.request_delay)
                
                pages_scraped += 1
                current_page -= 1  # Go to previous page (older posts)
                
                # Delay between pages
                time.sleep(self.request_delay * 2)
                
            except Exception as e:
                logger.error(f"Error scraping page {current_page}: {e}")
                current_page -= 1
                continue
        
        logger.info(f"PTT scraping complete: {len(all_articles)} articles collected from {pages_scraped} pages")
        return all_articles
    
    def scrape_board_range(self, start_page: int = 2765, end_page: int = 1, max_articles: int = 10000) -> List[Dict]:
        """Scrape a range of PTT pages.
        
        Args:
            start_page: Starting page number (latest)
            end_page: Ending page number (oldest)
            max_articles: Maximum articles to collect
        """
        all_articles = []
        total_pages = start_page - end_page + 1
        
        logger.info(f"Starting PTT Marvel range scrape: pages {start_page} to {end_page} ({total_pages} pages)")
        
        current_page = start_page
        pages_scraped = 0
        
        while current_page >= end_page and len(all_articles) < max_articles:
            try:
                current_url = self.generate_page_url(current_page)
                logger.info(f"Scraping page {pages_scraped + 1}/{total_pages}: page {current_page}")
                
                # Get board page
                soup = self.get_board_page(current_url)
                if not soup:
                    logger.warning(f"Failed to get page {current_page}, skipping")
                    current_page -= 1
                    continue
                
                # Extract article links
                article_links = self.extract_article_links(soup)
                
                if article_links:
                    logger.info(f"Found {len(article_links)} articles on page {current_page}")
                    
                    # Get full content for each article
                    for article_info in article_links:
                        if len(all_articles) >= max_articles:
                            break
                        
                        try:
                            # Get full article content
                            article_data = self.get_article_content(article_info['url'])
                            if article_data:
                                # Add source info
                                article_data['source'] = 'ptt_marvel'
                                all_articles.append(article_data)
                                
                                logger.info(f"Scraped article {len(all_articles)}: {article_data['title'][:50]}...")
                        
                        except Exception as e:
                            # Create a log file to track the failed jobs, and write a function to resume these failed jobs
                            logger.error(f"Error scraping article {article_info['url']}: {e}")
                            continue
                        
                        # Rate limiting
                        time.sleep(self.request_delay)
                else:
                    logger.info(f"No articles found on page {current_page}")
                
                pages_scraped += 1
                current_page -= 1
                
                # Progress reporting every 10 pages
                if pages_scraped % 10 == 0:
                    logger.info(f"Progress: {pages_scraped}/{total_pages} pages, {len(all_articles)} articles collected")
                
                # Delay between pages
                time.sleep(self.request_delay * 2)
                
            except Exception as e:
                logger.error(f"Error scraping page {current_page}: {e}")
                current_page -= 1
                continue
        
        logger.info(f"PTT range scraping complete: {len(all_articles)} articles collected from {pages_scraped} pages")
        return all_articles


def test_database_connection():
    """Test database connection."""
    try:
        db_url = get_db_url()
        engine = create_engine(db_url)
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            for row in result:
                print(f"✓ Connected to database: {row[0]}")
        return True
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_ptt_scraper():
    """Test PTT scraper functionality."""
    print("Testing PTT Marvel Scraper")
    print("=" * 30)
    
    # Test database connection
    if not test_database_connection():
        return False
    
    # Test scraper
    try:
        scraper = PTTMarvelScraper()
        
        # Test with small number of articles
        articles = scraper.scrape_board(max_pages=1, max_articles=3)
        
        if articles:
            print(f"✓ Successfully scraped {len(articles)} articles")
            
            # Show sample article
            sample = articles[0]
            print(f"\nSample article:")
            print(f"Title: {sample['title']}")
            print(f"Author: {sample['author']}")
            print(f"Content length: {len(sample['content'])} characters")
            print(f"URL: {sample['source_url']}")
            
            return True
        else:
            print("✗ No articles found")
            return False
            
    except Exception as e:
        print(f"✗ PTT scraper test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_ptt_scraper()
    if success:
        print("\n🎉 PTT scraper is working correctly!")
    else:
        print("\n😞 PTT scraper test failed")
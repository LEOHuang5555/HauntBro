"""
Configuration settings for Reddit scraping pipeline.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Reddit API Configuration
REDDIT_CONFIG = {
    'client_id': os.getenv('REDDIT_CLIENT_ID'),
    'client_secret': os.getenv('REDDIT_CLIENT_SECRET'),
    'user_agent': os.getenv('REDDIT_USER_AGENT', 'HauntBro:1.0.0 (by /u/YOUR_USERNAME)'),
}

# Scraping Configuration
SCRAPING_CONFIG = {
    'subreddit': 'nosleep',
    'rate_limit_delay': float(os.getenv('REDDIT_RATE_LIMIT_DELAY', '0.1')),
    'batch_delay': float(os.getenv('REDDIT_BATCH_DELAY', '2')),
    'max_retries': int(os.getenv('REDDIT_MAX_RETRIES', '3')),
    'min_content_length': int(os.getenv('MIN_CONTENT_LENGTH', '200')),
    'max_content_length': int(os.getenv('MAX_CONTENT_LENGTH', '50000')),
    'chunk_size': int(os.getenv('CHUNK_SIZE', '1000')),
}

# ETL Configuration
ETL_CONFIG = {
    'batch_size': 100,        # Stories per batch
    'commit_frequency': 10,   # Commit every N stories
    'target_collections': {
        'test': 20,
        'development': 100,
        'production': 1000,
    }
}

# Database Configuration
DATABASE_CONFIG = {
    'url': os.getenv('DATABASE_URL', 'postgresql+psycopg2://hbadmin:dj3jkp2jmrkfmlkweq@localhost/hbrawdata'),
    'pool_size': int(os.getenv('DATABASE_POOL_SIZE', '5')),
    'max_overflow': int(os.getenv('DATABASE_MAX_OVERFLOW', '10')),
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'handlers': ['console', 'file'],
    'log_file': os.getenv('LOG_FILE_PATH', 'logs/reddit_scraper.log')
}

def get_config() -> Dict[str, Any]:
    """Get complete configuration dictionary."""
    return {
        'reddit': REDDIT_CONFIG,
        'scraping': SCRAPING_CONFIG,
        'etl': ETL_CONFIG,
        'database': DATABASE_CONFIG,
        'logging': LOGGING_CONFIG
    }
"""
Configuration settings for Reddit scraping pipeline.
"""

import os
from typing import Dict, Any

# Reddit API Configuration
REDDIT_CONFIG = {
    'client_id': os.getenv('REDDIT_CLIENT_ID'),
    'client_secret': os.getenv('REDDIT_CLIENT_SECRET'),
    'user_agent': os.getenv('REDDIT_USER_AGENT', 'HauntBro:1.0.0 (by /u/YOUR_USERNAME)'),
}

# Scraping Configuration
SCRAPING_CONFIG = {
    'subreddit': 'nosleep',
    'rate_limit_delay': 0.1,  # Seconds between requests
    'batch_delay': 2,         # Seconds between batches
    'max_retries': 3,
    'min_content_length': 200,
    'max_content_length': 50000,
    'chunk_size': 1000,       # For RAG chunking
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
    'pool_size': 5,
    'max_overflow': 10,
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'handlers': ['console', 'file'],
    'log_file': 'logs/reddit_scraper.log'
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
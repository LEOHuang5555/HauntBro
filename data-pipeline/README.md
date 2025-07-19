# HauntBro Data Pipeline

Data processing pipeline for scraping and processing ghost stories from Reddit r/nosleep and PTT Marvel.

## Components

- **scrapers/**: Web scraping modules
  - `reddit_scraper.py`: Reddit API integration for r/nosleep
  - `get_data_from_ptt_marvel.py`: PTT Marvel scraper (legacy)
- **etl/**: Extract, Transform, Load scripts  
  - `reddit_etl.py`: Complete ETL pipeline for Reddit stories
- **config/**: Configuration files
  - `reddit_config.py`: Reddit scraping configuration
- **scripts/**: Production and utility scripts
  - `collect_reddit_stories.py`: Production story collection script
  - `test_reddit_setup.py`: Setup verification script
- **airflow/**: Apache Airflow DAGs (planned)

## Setup

### 1. Install Dependencies
```bash
cd ../backend
poetry install
# OR
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
# Copy environment template from project root
cp ../.env.example ../.env

# Edit .env with your Reddit API credentials
# Get these from https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=YourApp:1.0.0 (by /u/yourusername)
```

### 3. Database Setup
Ensure PostgreSQL is running and the HauntBro database is initialized:
```bash
cd ../backend
poetry run alembic upgrade head
```

## Usage

### Test Setup
```bash
# Verify everything is working
python scripts/test_reddit_setup.py
```

### Collect Stories

#### Test Mode (20 stories)
```bash
python scripts/collect_reddit_stories.py --test
```

#### Development Mode (100 stories)
```bash
python scripts/collect_reddit_stories.py --count 100
```

#### Production Mode (1,000+ stories)
```bash
python scripts/collect_reddit_stories.py --count 1000
```

### Manual ETL Pipeline
```bash
# Direct ETL usage
cd etl
python reddit_etl.py
```

## Features

### Reddit Scraper
- ✅ Rate limiting compliance (Reddit API guidelines)
- ✅ Error handling and retry logic
- ✅ Content cleaning and validation
- ✅ Metadata extraction (score, comments, awards)
- ✅ Duplicate detection
- ✅ Multiple fetch strategies (hot, new, top by time)

### ETL Pipeline
- ✅ Medallion architecture integration (Bronze → Silver layers)
- ✅ Content chunking for RAG retrieval
- ✅ Tag generation based on content analysis
- ✅ Data quality validation
- ✅ Batch processing with commit optimization
- ✅ Comprehensive logging and error tracking

### Story Processing
- ✅ Text cleaning (markdown removal, normalization)
- ✅ Content validation (length, quality checks)
- ✅ Tag generation (horror subgenres, length, series detection)
- ✅ Reading time calculation
- ✅ Chunking for search functionality

## Architecture

```
Extract (Reddit API) → Clean (Text processing) → Store (Bronze/Silver layers)
     ↓                      ↓                         ↓
- Rate limiting        - Markdown removal         - PostgreSQL
- Retry logic         - Content validation       - Medallion architecture  
- Metadata extraction - Tag generation          - Search chunking
- Deduplication       - Quality checks          - Relationship mapping
```

## Configuration

See `config/reddit_config.py` for:
- API rate limits and delays
- Content processing parameters
- Database settings
- Logging configuration

## Monitoring

Logs are written to:
- Console output (real-time)
- `logs/reddit_collection.log` (persistent)

Statistics tracked:
- Stories extracted vs processed
- Skip reasons (duplicates, quality)
- Error rates and types
- Processing time and performance
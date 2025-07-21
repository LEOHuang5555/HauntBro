# HauntBro Data Pipeline - Separated Architecture

A properly separated data extraction and transformation pipeline for the HauntBro ghost story search engine.

## 🏗️ Architecture Overview

```
Phase 1: EXTRACT          Phase 2: TRANSFORM & LOAD
[Scrapers] → [Bronze]  →  [ETL] → [Silver]
```

### Key Principles
- **✅ Separation of Concerns**: Scraping and ETL are completely independent
- **✅ Debuggable**: Clear error attribution (scraping vs ETL)
- **✅ Trackable**: Separate status monitoring for each phase
- **✅ Reprocessable**: Can re-run ETL without re-scraping
- **✅ Scalable**: Can scale scraping and ETL independently

## 📁 Directory Structure

```
data-pipeline/
├── scrapers/           # Phase 1: Pure extraction only
│   ├── ptt_scraper_pure.py       # PTT Marvel board scraper
│   ├── reddit_scraper_pure.py    # Reddit r/nosleep scraper
│   ├── ptt_marvel_scraper.py     # Core PTT scraping logic
│   └── reddit_scraper.py         # Core Reddit scraping logic
├── etl/               # Phase 2: Pure transformation only
│   ├── ptt_etl_pure.py          # PTT Bronze → Silver processing
│   └── reddit_etl_pure.py       # Reddit Bronze → Silver processing
├── scripts/           # Orchestration and testing
│   ├── extract_phase.py         # Phase 1 orchestrator
│   ├── transform_load_phase.py  # Phase 2 orchestrator
│   └── test_separated_workflow.py # Test complete workflow
└── config/            # Configuration files
    └── reddit_config.py
```

## 🚀 Usage

### Phase 1: Extract (Scraping Only)

Extract raw data from sources and store in Bronze layer:

```bash
# Extract from both sources
python scripts/extract_phase.py

# Extract from PTT only
python scripts/extract_phase.py --sources ptt --ptt-pages 5 --ptt-articles 30

# Extract from Reddit only  
python scripts/extract_phase.py --sources reddit --reddit-count 50 --reddit-filters hot new week
```

### Phase 2: Transform & Load (ETL Only)

Process raw Bronze data into clean Silver layer:

```bash
# Process all sources
python scripts/transform_load_phase.py

# Process PTT only
python scripts/transform_load_phase.py --sources ptt --batch-size 100

# Continuous processing until no raw data left
python scripts/transform_load_phase.py --continuous

# Check processing status
python scripts/transform_load_phase.py --status-only
```

### Individual Components

Run pure scrapers directly:

```bash
# PTT pure scraper
python scrapers/ptt_scraper_pure.py --max-pages 3 --max-articles 20

# Reddit pure scraper  
python scrapers/reddit_scraper_pure.py --target-count 30 --time-filters hot new
```

Run pure ETL processors directly:

```bash
# PTT pure ETL
python etl/ptt_etl_pure.py --batch-size 50 --continuous

# Reddit pure ETL
python etl/reddit_etl_pure.py --batch-size 50
```

### Testing

Test the complete separated workflow:

```bash
python scripts/test_separated_workflow.py
```

## 📊 Data Layers

### Bronze Layer (Raw Storage)
- **Purpose**: Immutable raw scraped data
- **Table**: `bronze_stories`
- **Content**: Unprocessed stories exactly as scraped
- **Source**: Direct from scrapers (Phase 1)

### Silver Layer (Processed Data)  
- **Purpose**: Cleaned and enriched data
- **Table**: `silver_stories`
- **Content**: Validated stories with tags, metrics, cleaned content
- **Source**: Processed from Bronze (Phase 2)

## 🔄 Workflow Examples

### Complete Workflow
```bash
# Step 1: Extract raw data
python scripts/extract_phase.py --sources ptt reddit

# Step 2: Process raw data
python scripts/transform_load_phase.py --sources ptt reddit --continuous
```

### Focused PTT Workflow
```bash
# Extract PTT data
python scripts/extract_phase.py --sources ptt --ptt-pages 5

# Process PTT data
python scripts/transform_load_phase.py --sources ptt
```

### Reprocessing Workflow
```bash
# Extract once
python scripts/extract_phase.py

# Can reprocess multiple times without re-scraping
python scripts/transform_load_phase.py
python scripts/transform_load_phase.py --continuous
```

## 🎯 Benefits of Separation

1. **Independent Scaling**: Scale scraping and ETL separately
2. **Error Isolation**: Know exactly where failures occur  
3. **Reprocessing**: Re-run ETL to fix data without re-scraping
4. **Testing**: Test scraping and ETL independently
5. **Monitoring**: Track scraping success vs ETL success separately
6. **Development**: Work on ETL logic without hitting APIs

## 🔧 Configuration

Environment variables are loaded from `.env` file:

- `REDDIT_CLIENT_ID`: Reddit API client ID
- `REDDIT_CLIENT_SECRET`: Reddit API client secret  
- `REDDIT_USER_AGENT`: Reddit API user agent
- `DATABASE_URL`: PostgreSQL connection string

## 📋 Current Focus

**PTT Marvel Board**: Primary focus due to Reddit API date range limitations
**Reddit r/nosleep**: Secondary, limited by API capabilities

## 🚀 Future Enhancements

- **Chunking**: Silver → Gold layer with embeddings
- **Historical Collection**: Systematic date-range collection
- **Streaming Updates**: Real-time processing with Kafka
- **Reddit Date Filtering**: Solve API limitations for historical data
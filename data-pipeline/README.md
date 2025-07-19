# HauntBro Data Pipeline

Data processing pipeline for scraping and processing ghost stories.

## Components

- **scrapers/**: Web scraping modules for PTT Marvel and Reddit
- **etl/**: Extract, Transform, Load scripts
- **airflow/**: Apache Airflow DAGs and workflow management

## Setup

```bash
cd ../backend
poetry install
```

## Usage

```bash
# Run Reddit scraper
python scrapers/reddit_scraper.py

# Run PTT Marvel scraper
python scrapers/get_data_from_ptt_marvel.py
```
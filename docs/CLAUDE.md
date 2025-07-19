# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
HauntBro is a search engine for ghost stories from PTT Marvel and Subreddit ghoststories. The project implements a **Medallion Architecture** (Bronze-Silver-Gold) for data processing with Apache Airflow. It utilizes Retrieval-Augmented Generation (RAG) and embeddings for accurate search results, with comprehensive analytics and a user-friendly front-end.

### Database Architecture
- **Bronze Layer**: Raw, immutable scraped data
- **Silver Layer**: Cleaned, processed data with story chunks for RAG
- **Gold Layer**: Business metrics and performance analytics
- **User Layer**: Authentication, favorites, ratings
- **Analytics Layer**: Search interactions, reading behavior
- **Pipeline Layer**: Data engineering metrics

## Development Setup

### Package Management
This project uses Poetry for dependency management. All dependencies are defined in `pyproject.toml`.

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Add new dependencies
poetry add <package-name>

# Add development dependencies
poetry add --group dev <package-name>
```

### Database Configuration
The project uses PostgreSQL for data storage. Database connection details are configured in the main Python files:
- Database URL: `postgresql+psycopg2://hbadmin:dj3jkp2jmrkfmlkweq@localhost/hbrawdata`
- Uses SQLAlchemy for database operations

## Key Dependencies
- **Web Scraping**: Scrapy, BeautifulSoup4, Requests
- **Data Processing**: Pandas, NumPy
- **Database**: SQLAlchemy, psycopg2-binary
- **Python**: 3.10+

## Project Structure
This is currently a minimal project with the following structure:
- `get_data_from_ptt_marvel.py` - Main database connection and testing script
- `pyproject.toml` - Poetry configuration and dependencies
- `README.md` - Project description
- Standard Python gitignore for development artifacts

## Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Or using pip
pip install -r requirements.txt
```

### Database Operations
```bash
# Initialize database and run migrations
poetry run alembic upgrade head

# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Seed medallion architecture database with test data
poetry run python database/seed.py

# Clear medallion architecture database
poetry run python database/seed.py --clear

# Force re-seed (clear and seed)
poetry run python database/seed.py --force

# Apply medallion architecture migration
poetry run alembic upgrade head
```

### Running the Application
```bash
# Start the FastAPI development server
poetry run uvicorn main:app --reload

# Or with Python
poetry run python main.py

# Test database connection
poetry run python database/connection.py
```

### Development Workflow
The project now includes:
1. ✅ **Medallion Architecture** (Bronze-Silver-Gold) database design
2. ✅ PostgreSQL schema with 9 core tables across 6 layers
3. ✅ SQLAlchemy models for all entities with proper relationships
4. ✅ Alembic migrations for database versioning
5. ✅ FastAPI-based REST API with CORS support
6. ✅ JWT-based authentication system
7. ✅ Comprehensive database seeding with realistic test data
8. ✅ Analytics layer for search interactions and user behavior
9. ✅ Pipeline metrics for data engineering monitoring
10. 🚧 Web scraping modules (next phase)
11. 🚧 RAG system with story chunking for search functionality
12. 🚧 Front-end interface

## Database Architecture Details

### Medallion Architecture Layers

**Bronze Layer (Raw Data)**
- `bronze_stories`: Immutable scraped content with raw metadata

**Silver Layer (Processed Data)**
- `silver_stories`: Cleaned story metadata with tags and metrics
- `silver_story_chunks`: Story chunks for RAG retrieval with embeddings

**Gold Layer (Business Metrics)**
- `gold_story_performance`: Aggregated performance metrics per story

**User Layer (Application Features)**
- `users`: Authentication and user profiles
- `user_favorites`: User bookmarks with notes
- `story_ratings`: 1-5 star ratings

**Analytics Layer (User Behavior)**
- `search_interactions`: Search queries with click tracking
- `user_reading_behavior`: Reading duration and engagement metrics

**Pipeline Layer (Data Engineering)**
- `scraping_pipeline_metrics`: Airflow DAG execution metrics

### Key Features
- **Immutable Bronze Layer**: Raw data preservation
- **Automatic Triggers**: Performance metrics update on user actions
- **Full-text Search**: TSVECTOR indexes for fast text search
- **Embedding Support**: Ready for pgvector when available
- **Comprehensive Analytics**: User behavior and search tracking

## Future Architecture Considerations
Based on the project description, the system will likely include:
- Web scraping modules for PTT Marvel and Reddit
- Data processing pipeline for cleaning scraped content
- Apache Airflow for workflow management
- Embedding and RAG system for search functionality
- Front-end interface for user interactions
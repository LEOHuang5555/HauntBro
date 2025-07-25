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

## Docker Development Environment

The project uses Docker Compose to orchestrate all services including databases, Airflow, and Ollama for local model serving.

### Service Architecture
- **hauntbro-db**: PostgreSQL database (port 5432)
- **backend**: FastAPI application (port 8000)
- **ollama**: Local LLM server with llama3.2 and deepseek-coder models (port 11434)
- **airflow-webserver**: Airflow web interface (port 8080)
- **airflow-scheduler**: Airflow task scheduler
- **airflow-worker**: Celery worker for task execution
- **airflow-db**: PostgreSQL for Airflow metadata
- **redis**: Message broker for Celery
- **kafka**: Streaming data processing (port 9092)
- **zookeeper**: Kafka coordination (port 2181)

### Docker Build Up Commands

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d hauntbro-db ollama airflow-webserver

# Check service status
docker-compose ps

# View logs for specific service
docker-compose logs -f ollama
docker-compose logs -f airflow-webserver

# Execute commands in containers
docker exec -it hauntbro-db psql -U postgres -d hauntbro
docker exec -it hauntbro-ollama-1 ollama list

# Stop all services
docker-compose down

# Stop and remove volumes (complete reset)
docker-compose down -v
```

### Service Health Checks
- **Ollama**: `curl http://localhost:11434/api/tags`
- **Airflow**: `curl http://localhost:8080/api/v2/dags`
- **Database**: `docker exec hauntbro-db pg_isready -U postgres`
- **Backend**: `curl http://localhost:8000/health`

### Available Models
The Ollama service automatically pulls:
- **llama3.2**: For English text processing and generation
- **deepseek-coder**: For Chinese text processing and code generation

### ETL Pipeline Execution
The medallion architecture ETL pipeline can be executed via:
1. **Airflow DAGs**: Scheduled execution through web interface
2. **Direct Python**: Manual execution of individual processors
3. **SQL-based**: Direct database processing for testing

Example ETL execution:
```bash
# Test database connection and verify medallion schema
docker exec hauntbro-db psql -U postgres -d hauntbro -c "SELECT COUNT(*) FROM bronze_stories;"

# Execute silver layer processing
docker exec hauntbro-db psql -U postgres -d hauntbro -c "SELECT COUNT(*) FROM silver_story_chunks;"
```

## Future Architecture Considerations
Based on the project description, the system will likely include:
- Web scraping modules for PTT Marvel and Reddit
- Data processing pipeline for cleaning scraped content
- Apache Airflow for workflow management
- Embedding and RAG system for search functionality
- Front-end interface for user interactions
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
HauntBro is a search engine for ghost stories from PTT Marvel and Subreddit ghoststories. The project includes web scraping, data cleaning, and management using Apache Airflow. It utilizes Retrieval-Augmented Generation (RAGs) and embeddings for accurate search results, with a simple front-end for searching and displaying results.

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

# Seed database with test data
poetry run python database/seed.py

# Clear database
poetry run python database/seed.py --clear

# Force re-seed (clear and seed)
poetry run python database/seed.py --force
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
1. ✅ PostgreSQL database schema with core tables
2. ✅ SQLAlchemy models for all entities
3. ✅ Alembic migrations for database versioning
4. ✅ FastAPI-based REST API
5. ✅ JWT-based authentication system
6. ✅ Database seeding for testing
7. 🚧 Web scraping modules (next phase)
8. 🚧 RAG system for search functionality
9. 🚧 Front-end interface

## Database Operations
The project uses SQLAlchemy for database operations. The main connection is established in `get_data_from_ptt_marvel.py:1-14` using a PostgreSQL database.

## Future Architecture Considerations
Based on the project description, the system will likely include:
- Web scraping modules for PTT Marvel and Reddit
- Data processing pipeline for cleaning scraped content
- Apache Airflow for workflow management
- Embedding and RAG system for search functionality
- Front-end interface for user interactions
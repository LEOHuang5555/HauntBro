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
- **ETL**: Airflow, OpenAI, ollama, Kafka
- **DevOps**: Docker

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
## CODING STANDARDS

### Python Backend
- Use FastAPI with async/await patterns for all endpoints
- SQLAlchemy ORM with Alembic migrations for database operations
- Pydantic models for data validation and serialization
- Type hints for all functions and class methods
- Comprehensive error handling with custom exceptions
- Follow PEP 8 style guidelines strictly
- **Poetry for dependency management** - use `pyproject.toml` for all dependencies
- Virtual environment activation required for all operations

### Package Management with Poetry
```bash
# Project initialization
poetry init
poetry add fastapi sqlalchemy alembic pydantic

# Development dependencies
poetry add --group dev pytest black flake8 mypy pre-commit

# Virtual environment activation
poetry shell
# OR
poetry run python main.py
```

### React Frontend
- TypeScript for type safety across all components
- Functional components with hooks (no class components)
- React Query for API state management and caching
- Tailwind CSS for styling (utility-first approach)
- Component composition over inheritance
- Accessibility-first design (ARIA labels, semantic HTML)

### Database Design (Medallion Architecture)
- Use snake_case for table and column names
- Include created_at/updated_at timestamps on all tables
- Proper foreign key relationships with cascading deletes where appropriate
- Database indexes for performance optimization
- Migration scripts for all schema changes
- Separate schemas for Bronze/Silver/Gold layers


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
### After Every Code Modification
Follow this exact sequence for every change:

1. **Complete the Implementation**
   ```bash
   # Ensure all code is written and functional
   poetry run python -m pytest tests/ -v
   ```

2. **Activate Virtual Environment** 
   ```bash
   poetry shell
   # Verify activation with:
   which python  # Should point to poetry venv
   ```

3. **Run Unit Tests**
   ```bash
   # Run tests for the specific feature modified
   poetry run pytest tests/test_[feature_name].py -v
   
   # Run full test suite if major changes
   poetry run pytest tests/ --cov=src --cov-report=html
   ```

4. **Code Quality Checks**
   ```bash
   # Coding style checking with Black
   poetry run black src/ tests/ --check --diff
   
   # If formatting needed:
   poetry run black src/ tests/
   ```

5. **Lint Checking**
   ```bash
   # Flake8 for linting
   poetry run flake8 src/ tests/ --max-line-length=88
   
   # MyPy for type checking
   poetry run mypy src/ --ignore-missing-imports
   ```

6. **Hardcode Detection & Environment Variables**
   ```bash
   # Check for hardcoded values (manual review)
   grep -r "localhost\|127.0.0.1\|password\|secret\|api_key" src/ || echo "No hardcoded values found"
   
   # If hardcoded values found:
   # 1. Move to .env file
   # 2. Update .env.example with placeholder values
   # 3. Use python-dotenv or pydantic BaseSettings to load
   ```

7. **Git Commit**
   ```bash
   # Stage all changes
   git add .
   
   # Commit with descriptive message
   git commit -m "feat: completed [feature-name-part] - [brief description]"
   
   # Examples:
   # git commit -m "feat: completed database-models - added User and Story models with relationships"
   # git commit -m "fix: completed reddit-scraper-auth - fixed OAuth2 token refresh mechanism"
   # git commit -m "refactor: completed search-engine-optimization - improved query performance by 40%"
   ```

8. **Update Documentation**
   ```bash
   # Create or update README.md in current directory
   # Include:
   # - What was changed
   # - How to test the changes
   # - Any new dependencies or setup required
   # - API changes or new endpoints
   ```

### Commit Message Convention
```
type: completed [feature-name-part] - [description]

Types:
- feat: new feature implementation
- fix: bug fix or issue resolution
- refactor: code refactoring without functional changes
- docs: documentation updates
- test: adding or updating tests
- style: code style/formatting changes
- perf: performance improvements
```

## PROJECT-SPECIFIC PATTERNS

### Environment Configuration
```python
# settings.py - Use Pydantic BaseSettings
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    openai_api_key: str
    jwt_secret: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Error Handling Pattern
```python
# exceptions.py
class GhostStoryException(Exception):
    """Base exception for ghost story application"""
    pass

class ScrapingError(GhostStoryException):
    """Raised when scraping operations fail"""
    pass

class SearchError(GhostStoryException):
    """Raised when search operations fail"""
    pass

# In FastAPI endpoints:
@app.exception_handler(GhostStoryException)
async def ghost_story_exception_handler(request: Request, exc: GhostStoryException):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "type": type(exc).__name__}
    )
```

### Database Model Pattern
```python
# models/base.py
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# models/story.py
class Story(Base, TimestampMixin):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True)
    title: str = Column(String(500), nullable=False)
    # ... rest of fields
```

### API Response Pattern
```python
# schemas/response.py
from pydantic import BaseModel
from typing import Optional, Any, Dict

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    meta: Optional[Dict] = None
    
class PaginatedResponse(APIResponse):
    data: List[Any]
    meta: Dict = Field(default_factory=lambda: {
        "page": 1,
        "per_page": 20,
        "total": 0,
        "pages": 0
    })
```

### Testing Patterns
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///./test.db")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    return TestClient(app)
```

## SECURITY REQUIREMENTS
- JWT tokens for authentication with proper expiration
- Rate limiting on all endpoints based on user tier
- Input validation and sanitization for all user inputs
- CORS configuration for frontend integration
- Environment variables for all secrets and API keys
- SQL injection prevention through ORM usage only
- Password hashing with bcrypt (minimum 12 rounds)

## PERFORMANCE REQUIREMENTS
- API response time: <500ms for search endpoints
- Database queries: Use indexes and analyze with EXPLAIN
- Frontend loading: <3 seconds initial load
- Caching strategy: Redis for frequently accessed data
- Async operations for all I/O bound tasks

## MEDALLION ARCHITECTURE COMPLIANCE
```python
# Bronze Layer - Raw data preservation
class BronzeStory(Base):
    __tablename__ = "bronze_stories"
    # Store raw, unprocessed data exactly as scraped

# Silver Layer - Processed and cleaned
class SilverStory(Base):
    __tablename__ = "silver_stories"
    # Store processed, chunked, and embedded data

# Gold Layer - Business intelligence
class GoldStoryAnalytics(Base):
    __tablename__ = "gold_story_analytics"
    # Store aggregated business metrics
```


## TESTING REQUIREMENTS
- Unit tests for all business logic (>80% coverage)
- Integration tests for API endpoints
- E2E tests for critical user flows
- Mock external API calls (Reddit, PTT, OpenAI)
- Performance tests for search functionality
- Test database isolation and cleanup

## DOCUMENTATION STANDARDS
- API documentation with OpenAPI/Swagger integration
- Database schema documentation with ERD diagrams
- README.md files in each major directory explaining:
  - Purpose and functionality
  - Setup and installation steps
  - Testing procedures
  - Dependencies and requirements
- Code comments for complex business logic
- Architecture decision records (ADRs) for major decisions

## PRE-COMMIT HOOKS
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.9
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
        args: [--max-line-length=88]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.950
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

## DEPLOYMENT STANDARDS
- Docker containers for all services with multi-stage builds
- Environment-based configuration (dev/staging/prod)
- Health check endpoints for all services
- Structured logging with JSON format for centralized logging
- Monitoring with Prometheus metrics collection
- Database backup and recovery procedures
- CI/CD pipeline with automated testing and deployment

When implementing features:
1. **Always follow the development workflow** step-by-step
2. **Write tests before or alongside implementation**
3. **Use Poetry for all dependency management**
4. **Activate virtual environment for every operation**
5. **Check for hardcoded values and use environment variables**
6. **Commit with descriptive messages following convention**
7. **Update documentation for every significant change**
8. **Run quality checks before every commit**
9. **Ensure medallion architecture compliance**
10. **Follow security and performance requirements**
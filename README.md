# HauntBro

A search engine for ghost stories from PTT Marvel and Reddit. This project includes web scraping, data cleaning, and management using Apache Airflow. Utilizing Retrieval-Augmented Generation (RAGs) and embeddings for accurate search results. Features a simple front-end for searching and displaying results.

## Project Structure

```
HauntBro/
├── backend/           # FastAPI application
│   ├── app/          # Main application code
│   │   ├── auth/     # Authentication modules
│   │   ├── database/ # Database models and operations
│   │   └── main.py   # FastAPI entry point
│   ├── data/         # Backend data processing
│   ├── tests/        # Backend tests
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/         # React web application
├── data-pipeline/    # Data processing and ETL
│   ├── scrapers/     # Web scraping modules
│   ├── etl/          # Extract, Transform, Load scripts
│   └── airflow/      # Airflow DAGs and tasks
├── infrastructure/   # Deployment and infrastructure
│   ├── docker/       # Docker configurations
│   └── terraform/    # Infrastructure as code
└── docs/            # Documentation
```

## Getting Started

### Backend Setup
```bash
cd backend
poetry install
poetry shell
poetry run uvicorn app.main:app --reload
```

### Database Setup
```bash
cd backend
poetry run alembic upgrade head
poetry run python app/database/seed.py
```

## Features

- **Medallion Architecture**: Bronze-Silver-Gold data layers
- **Reddit Integration**: Scrapes r/nosleep stories
- **PTT Marvel Integration**: Scrapes PTT Marvel ghost stories
- **RAG Search**: Semantic search with embeddings
- **User Authentication**: JWT-based auth system
- **Story Management**: Favorites, ratings, analytics

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React (planned)
- **Data Pipeline**: Apache Airflow, Scrapy
- **Search**: RAG with embeddings
- **Infrastructure**: Docker, AWS (planned)
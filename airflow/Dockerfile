# Use official Airflow 3.0.3 image as base
FROM apache/airflow:3.0.3

# Switch to root to install system dependencies
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Switch back to airflow user
USER airflow

# Install only essential Python packages (no FAB needed for Simple Auth)
RUN pip install --upgrade pip \
    && pip install psycopg2-binary \
    && pip install redis

# Set working directory
WORKDIR /opt/airflow

# The entrypoint and command will be set by docker-compose
"""
Database connection and session management for HauntBro.
"""

import os
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base

# Load environment variables
load_dotenv()


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self, database_url: str = None):
        """Initialize database manager with connection URL."""
        self.database_url = database_url or self._get_database_url()
        self.engine = create_engine(
            self.database_url,
            poolclass=StaticPool,
            pool_pre_ping=True,
            echo=os.getenv('DATABASE_DEBUG', 'false').lower() == 'true'
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def _get_database_url(self) -> str:
        """Get database URL from environment variables."""
        # Default to the existing connection string from the original file
        return os.getenv(
            'DATABASE_URL',
            'postgresql+psycopg2://hbadmin:dj3jkp2jmrkfmlkweq@localhost/hbrawdata'
        )
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT version();"))
                version = result.fetchone()[0]
                print(f"Successfully connected to PostgreSQL: {version}")
                return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get database session for synchronous use."""
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session in FastAPI."""
    with db_manager.get_session() as session:
        yield session


def get_db_url() -> str:
    """Get database URL for external use."""
    return db_manager.database_url


def init_database():
    """Initialize database with tables and basic setup."""
    print("Initializing database...")
    
    # Test connection
    if not db_manager.test_connection():
        raise Exception("Failed to connect to database")
    
    # Create tables
    db_manager.create_tables()
    print("Database tables created successfully")
    
    # Enable required extensions
    try:
        with db_manager.get_session() as session:
            # Enable UUID extension
            session.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
            
            # Enable vector extension if available (for embeddings)
            try:
                session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                print("Vector extension enabled")
            except Exception:
                print("Vector extension not available - embeddings will be stored as text")
            
            session.commit()
            print("Database extensions enabled")
            
    except Exception as e:
        print(f"Warning: Could not enable extensions: {e}")


if __name__ == "__main__":
    # Test the database connection
    init_database()
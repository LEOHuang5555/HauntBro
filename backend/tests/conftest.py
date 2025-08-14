"""
Test configuration and fixtures
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.app.main import app
from backend.app.core.security import security_service
from backend.app.core.config import backend_config
from infrastructure.database.connection import get_db, db_manager
from infrastructure.database.models import Base, User, BronzeStory, SilverStory


# Test database URL for SQLite in-memory
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db():
    """Create a test database session."""
    # Create test engine with SQLite in-memory database
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="function")
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database dependency override."""
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(test_db) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=security_service.hash_password("testpassword123"),
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
async def test_admin_user(test_db) -> User:
    """Create a test admin user."""
    admin_user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=security_service.hash_password("adminpassword123"),
        is_active=True
    )
    test_db.add(admin_user)
    test_db.commit()
    test_db.refresh(admin_user)
    return admin_user


@pytest.fixture
async def auth_headers(test_user) -> dict:
    """Create authentication headers for test user."""
    access_token = security_service.create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def admin_auth_headers(test_admin_user) -> dict:
    """Create authentication headers for admin user."""
    access_token = security_service.create_access_token(data={"sub": test_admin_user.username})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def sample_bronze_story(test_db) -> BronzeStory:
    """Create a sample bronze story for testing."""
    story = BronzeStory(
        title="Test Ghost Story",
        content="This is a test ghost story with spooky content.",
        author="Test Author",
        source="test_source",
        source_url="https://test.com/story1"
    )
    test_db.add(story)
    test_db.commit()
    test_db.refresh(story)
    return story


@pytest.fixture
async def sample_silver_story(test_db, sample_bronze_story) -> SilverStory:
    """Create a sample silver story for testing."""
    story = SilverStory(
        bronze_story_id=str(sample_bronze_story.id),
        cleaned_content="This is a test ghost story with spooky content.",
        word_count=10,
        reading_time_minutes=1,
        language_detected="en",
        tags=["test", "ghost", "story"]
    )
    test_db.add(story)
    test_db.commit()
    test_db.refresh(story)
    return story


@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    class MockRedis:
        def __init__(self):
            self.data = {}
        
        async def get(self, key):
            return self.data.get(key)
        
        async def set(self, key, value, ex=None):
            self.data[key] = value
            return True
        
        async def delete(self, key):
            return self.data.pop(key, None) is not None
        
        async def exists(self, key):
            return key in self.data
        
        async def incr(self, key):
            current = int(self.data.get(key, 0))
            self.data[key] = str(current + 1)
            return current + 1
        
        async def expire(self, key, seconds):
            return True
    
    return MockRedis()


@pytest.fixture
def mock_embedding_manager():
    """Mock embedding manager for testing."""
    class MockEmbeddingManager:
        async def generate_embeddings(self, texts):
            # Return mock embeddings (just zeros for testing)
            return [[0.0] * 384 for _ in texts]
        
        async def search_similar(self, query, limit=10):
            # Return mock search results
            return [
                {
                    "story_id": "test-story-1",
                    "similarity_score": 0.95,
                    "title": "Mock Story 1",
                    "content_preview": "Mock content preview..."
                }
            ]
    
    return MockEmbeddingManager()


# Async test markers
pytest_plugins = ('pytest_asyncio',)
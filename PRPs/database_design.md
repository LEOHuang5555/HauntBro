# PostgreSQL Database Schema for Ghost Story Search Engine - PRP

name: "Ghost Story Search Engine Database Design v1.0"
description: |
  Complete PostgreSQL database schema implementation for a freemium ghost story search platform with user management, story storage, search optimization, and analytics.

## Purpose
Implement a production-ready database architecture supporting a scalable ghost story search engine with freemium subscription model, full-text search, and comprehensive analytics.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Build a comprehensive PostgreSQL database schema with SQLAlchemy ORM models, Pydantic schemas, Alembic migrations, and FastAPI integration for a freemium ghost story search platform supporting 100K+ stories and 10K+ concurrent users with sub-200ms search performance.

## Why
- **Business value**: Enable freemium monetization model with subscription tiers
- **User impact**: Fast, reliable story search with personalized features
- **Integration**: Foundation for FastAPI-based story search API
- **Problems solved**: Scalable content management, user analytics, rate limiting enforcement

## What
A complete database system with:
- User management with authentication and subscription tiers
- Story storage with rich metadata and full-text search
- Analytics and engagement tracking
- Rate limiting and audit trails
- Migration management and performance optimization

### Success Criteria
- [ ] All database operations complete in <100ms (95th percentile)
- [ ] Search queries optimized with proper indexing (<200ms average)
- [ ] Schema supports freemium model with flexible tier management
- [ ] ACID compliance maintained for all critical transactions
- [ ] Scalable design supporting 100K+ stories and 10K+ concurrent users
- [ ] Zero data loss during migrations and updates
- [ ] 99.9% uptime with proper backup and recovery procedures
- [ ] Comprehensive test coverage (>90%) with unit and integration tests

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://docs.sqlalchemy.org/en/20/orm/
  why: SQLAlchemy 2.0 ORM patterns, async support, relationship handling
  
- url: https://fastapi.tiangolo.com/tutorial/sql-databases/
  why: FastAPI + SQLAlchemy integration patterns, dependency injection
  
- url: https://docs.pydantic.dev/latest/examples/orms/
  why: Pydantic ORM mode for SQLAlchemy model serialization
  
- url: https://alembic.sqlalchemy.org/en/latest/tutorial.html
  why: Database migration patterns, autogeneration, async configurations
  
- url: https://www.postgresql.org/docs/current/textsearch.html
  why: PostgreSQL full-text search, GIN indexes, performance optimization
  
- url: https://testdriven.io/blog/fastapi-jwt-auth/
  why: JWT authentication patterns with FastAPI and PostgreSQL
  
- file: use-cases/pydantic-ai/examples/main_agent_reference/settings.py
  why: Settings pattern with pydantic-settings and dotenv configuration
  
- file: use-cases/pydantic-ai/examples/main_agent_reference/models.py
  why: Pydantic model patterns, validation, type annotations
  
- file: use-cases/pydantic-ai/CLAUDE.md
  why: PydanticAI development standards, security patterns
  
- file: use-cases/mcp-server/src/database/security.ts
  why: SQL injection prevention patterns, query validation
  
- file: use-cases/mcp-server/src/database/connection.ts
  why: Connection pooling patterns for high-performance applications
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash
/Users/renkhunag/Desktop/Project/context-engineering-intro/
├── CLAUDE.md                    # Global development rules
├── INITIAL.md                   # Project overview
├── use-cases/
│   ├── pydantic-ai/            # Python/FastAPI patterns
│   │   ├── CLAUDE.md           # PydanticAI development standards
│   │   └── examples/
│   │       └── main_agent_reference/
│   │           ├── settings.py  # Configuration patterns
│   │           └── models.py    # Pydantic model examples
│   └── mcp-server/             # Database security patterns
│       └── src/database/
│           ├── connection.ts    # Connection pooling
│           └── security.ts      # SQL injection prevention
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
ghost_story_search/
├── database/
│   ├── __init__.py              # Database package initialization
│   ├── models.py                # SQLAlchemy ORM models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── connection.py            # Database connection and session management
│   ├── security.py              # Authentication, password hashing, JWT
│   └── utils.py                 # Database utilities, query helpers
├── migrations/                  # Alembic migration files
│   ├── versions/                # Auto-generated migration scripts
│   ├── env.py                   # Alembic environment configuration
│   └── script.py.mako          # Migration template
├── seeds/
│   ├── __init__.py
│   ├── users.py                 # User seed data
│   └── stories.py               # Story seed data
├── tests/
│   ├── __init__.py
│   ├── test_models.py           # Model unit tests
│   ├── test_schemas.py          # Schema validation tests
│   ├── test_auth.py             # Authentication tests
│   └── fixtures/                # Test fixtures and factories
├── alembic.ini                  # Alembic configuration
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variables template
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Use venv_linux for all Python commands per CLAUDE.md
# CRITICAL: Never create files longer than 500 lines - refactor into modules
# CRITICAL: Use python-dotenv and load_dotenv() for environment variables
# CRITICAL: Follow main_agent_reference settings.py pattern for configuration

# SQLAlchemy 2.0 async patterns
# - Use AsyncSession instead of Session for async operations
# - async with session.begin() for transaction management
# - Use asyncio.run() for running async functions in sync context

# Pydantic V2 changes
# - Use model_config = ConfigDict(from_attributes=True) instead of orm_mode=True
# - Field validation uses @field_validator decorator
# - from_attributes enables ORM object serialization

# PostgreSQL specific
# - Use JSONB for metadata storage (better performance than JSON)
# - GIN indexes for full-text search on tsvector columns
# - Connection pooling essential for 10K+ concurrent users
# - Use prepared statements to prevent SQL injection

# FastAPI integration
# - Separate models for Create/Read/Update operations
# - Use Depends() for database session injection
# - response_model parameter controls serialization
```

## Implementation Blueprint

### Data models and structure

Create the core data models to ensure type safety and consistency:

```python
# SQLAlchemy ORM models for database tables
# - User model with authentication and subscription management
# - Story model with rich metadata and full-text search
# - Category and Tag models for content organization
# - UserSession, SearchLog, Analytics models for tracking
# - Audit models for data integrity and compliance

# Pydantic schemas for API serialization
# - Request schemas for input validation
# - Response schemas for output serialization  
# - Separate Create/Read/Update schemas per model
# - Nested schemas for relationship handling

# Database utilities and security
# - Connection pooling for performance
# - Password hashing with bcrypt
# - JWT token management
# - Query validation and SQL injection prevention
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1 - Project Setup and Configuration:
CREATE ghost_story_search/ directory structure:
  - Setup Python virtual environment (venv_linux)
  - Install dependencies (SQLAlchemy, FastAPI, Pydantic, Alembic, etc.)
  - Configure environment variables and settings
  - Initialize Alembic for migrations

Task 2 - Database Connection and Configuration:
CREATE database/connection.py:
  - MIRROR pattern from: use-cases/pydantic-ai/examples/main_agent_reference/settings.py
  - Implement AsyncEngine and AsyncSession setup
  - Add connection pooling configuration
  - Include database URL validation

Task 3 - Core ORM Models:
CREATE database/models.py:
  - User model with authentication fields
  - Story model with metadata and search fields
  - Category and Tag models for organization
  - PRESERVE SQLAlchemy 2.0 async patterns
  - ADD full-text search tsvector columns

Task 4 - Authentication and Security:
CREATE database/security.py:
  - MIRROR pattern from: use-cases/mcp-server/src/database/security.ts (adapt to Python)
  - Implement bcrypt password hashing
  - JWT token creation and validation
  - User permission checking utilities

Task 5 - Pydantic Schemas:
CREATE database/schemas.py:
  - Request/Response schemas for all models
  - Separate Create/Read/Update schemas
  - KEEP from_attributes=True for ORM serialization
  - ADD field validation for business rules

Task 6 - Database Utilities:
CREATE database/utils.py:
  - Query helper functions
  - Full-text search utilities
  - Analytics aggregation functions
  - Soft delete management

Task 7 - Initial Database Migration:
CREATE migrations using Alembic:
  - Configure alembic.ini for async operations
  - Generate initial migration with all tables
  - ADD indexes for performance optimization
  - INCLUDE full-text search indexes

Task 8 - Seed Data:
CREATE seeds/ directory with sample data:
  - User accounts with different subscription tiers
  - Sample ghost stories with metadata
  - Categories and tags for testing
  - PRESERVE data relationships and constraints

Task 9 - Comprehensive Testing:
CREATE tests/ directory with full coverage:
  - Model unit tests with pytest
  - Schema validation tests
  - Authentication and security tests
  - Integration tests with database operations

Task 10 - Performance Optimization:
OPTIMIZE database for scale:
  - Review and optimize query patterns
  - Add missing indexes based on query analysis
  - Configure connection pool for 10K+ users
  - Implement query monitoring and logging
```

### Per task pseudocode as needed added to each task

```python
# Task 2 - Database Connection
# PATTERN: Follow main_agent_reference/settings.py structure
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    # CRITICAL: Use python-dotenv pattern
    database_url: str = Field(..., description="PostgreSQL connection string")
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )

async def get_db_session() -> AsyncSession:
    # PATTERN: Connection pooling for performance
    engine = create_async_engine(
        settings.database_url,
        pool_size=20,  # For 10K+ concurrent users
        max_overflow=40,
        pool_timeout=30
    )
    # GOTCHA: Use AsyncSession for async operations
    async with AsyncSession(engine) as session:
        yield session

# Task 3 - Core ORM Models
class User(Base):
    __tablename__ = "users"
    
    # PATTERN: Standard user fields with subscription management
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    subscription_tier: Mapped[str] = mapped_column(default="free")
    
    # GOTCHA: Use relationship() for foreign keys in SQLAlchemy 2.0
    stories: Mapped[List["Story"]] = relationship(back_populates="author")

class Story(Base):
    __tablename__ = "stories"
    
    # CRITICAL: Full-text search with tsvector
    search_vector: Mapped[str] = mapped_column(
        type_=postgresql.TSVECTOR,
        Computed("to_tsvector('english', title || ' ' || content)")
    )
    
    # PATTERN: JSONB for flexible metadata
    metadata: Mapped[dict] = mapped_column(postgresql.JSONB)

# Task 4 - Authentication and Security
from passlib.context import CryptContext
import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # PATTERN: bcrypt verification with proper error handling
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    # CRITICAL: JWT with expiration for security
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Task 5 - Pydantic Schemas
class StoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    scare_level: int = Field(..., ge=1, le=10)
    
    # PATTERN: Input validation with Pydantic V2
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

class StoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 pattern
    
    id: int
    title: str
    content: str
    created_at: datetime
    # GOTCHA: Nested relationships need separate schemas
    author: UserResponse
```

### Integration Points
```yaml
DATABASE:
  - migration: "Alembic autogenerate for all tables with proper indexes"
  - indexes: "GIN indexes for full-text search, B-tree for foreign keys"
  - constraints: "Foreign key constraints with CASCADE options"
  
CONFIG:
  - add to: database/connection.py
  - pattern: "DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://...')"
  
FASTAPI:
  - add to: main.py (when created)
  - pattern: "Dependency injection for database sessions"
  - middleware: "CORS, authentication, rate limiting"

TESTING:  
  - add to: tests/conftest.py
  - pattern: "Pytest fixtures for database setup and teardown"
  - database: "Separate test database with clean state per test"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check database/ --fix        # Auto-fix formatting issues
mypy database/                    # Type checking for all modules
ruff check tests/ --fix          # Test file formatting
mypy tests/                      # Type check test files

# Expected: No errors. If errors, READ the error message and fix.
```

### Level 2: Unit Tests for each new feature/file/function using existing test patterns
```python
# CREATE test_models.py with comprehensive model tests:
def test_user_creation():
    """Test user model creation with valid data"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        subscription_tier="premium"
    )
    assert user.email == "test@example.com"
    assert user.subscription_tier == "premium"

def test_story_search_vector():
    """Test full-text search vector generation"""
    story = Story(
        title="Haunted House",
        content="A scary ghost story about an old mansion"
    )
    # Test that search vector is automatically generated
    assert story.search_vector is not None

def test_user_password_hashing():
    """Test password hashing and verification"""
    plain_password = "secure_password123"
    hashed = hash_password(plain_password)
    assert verify_password(plain_password, hashed)
    assert not verify_password("wrong_password", hashed)

def test_jwt_token_creation():
    """Test JWT token creation and validation"""
    user_data = {"user_id": 1, "email": "test@example.com"}
    token = create_access_token(user_data)
    decoded = verify_token(token)
    assert decoded["user_id"] == 1
    assert decoded["email"] == "test@example.com"

# CREATE test_schemas.py for Pydantic validation:
def test_story_create_validation():
    """Test story creation schema validation"""
    valid_data = {
        "title": "Test Story",
        "content": "A test ghost story",
        "scare_level": 7
    }
    schema = StoryCreate(**valid_data)
    assert schema.title == "Test Story"
    assert schema.scare_level == 7

def test_story_create_validation_errors():
    """Test story creation with invalid data"""
    with pytest.raises(ValidationError):
        StoryCreate(title="", content="content", scare_level=7)
    
    with pytest.raises(ValidationError):
        StoryCreate(title="title", content="content", scare_level=11)
```

```bash
# Run and iterate until passing:
pytest tests/test_models.py -v
pytest tests/test_schemas.py -v  
pytest tests/test_auth.py -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test with Database
```bash
# Start PostgreSQL database (Docker recommended)
docker run --name postgres-test -e POSTGRES_PASSWORD=testpass -p 5432:5432 -d postgres:15

# Set test database URL
export DATABASE_URL="postgresql+asyncpg://postgres:testpass@localhost/test_db"

# Run Alembic migrations on test database
alembic upgrade head

# Test database operations
python -c "
import asyncio
from database.connection import get_db_session
from database.models import User

async def test_db():
    async for session in get_db_session():
        user = User(email='test@example.com', password_hash='hash')
        session.add(user)
        await session.commit()
        print('✓ Database connection and model creation successful')

asyncio.run(test_db())
"

# Expected: "✓ Database connection and model creation successful"
# If error: Check connection string, PostgreSQL status, migration status
```

## Final validation Checklist
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No linting errors: `ruff check database/ tests/`
- [ ] No type errors: `mypy database/ tests/`
- [ ] Database migrations work: `alembic upgrade head`
- [ ] Seed data loads successfully: `python seeds/users.py`
- [ ] Full-text search functional: Test story search queries
- [ ] Authentication flow complete: JWT creation and validation
- [ ] Performance benchmarks met: <100ms DB operations
- [ ] Security validated: SQL injection prevention, password hashing
- [ ] Documentation complete: Docstrings for all functions

---

## Anti-Patterns to Avoid
- ❌ Don't use sync SQLAlchemy patterns with async FastAPI
- ❌ Don't skip connection pooling - critical for 10K+ users  
- ❌ Don't use raw SQL without parameterization - SQL injection risk
- ❌ Don't store plaintext passwords - always use bcrypt hashing
- ❌ Don't ignore migration validation - can cause data loss
- ❌ Don't skip indexes on foreign keys - performance killer
- ❌ Don't use SELECT * in production queries - bandwidth waste
- ❌ Don't hardcode secrets in code - use environment variables
- ❌ Don't skip transaction management - ACID compliance required
- ❌ Don't create files >500 lines - violates CLAUDE.md rules

## PRP Confidence Score: 9/10

This PRP provides comprehensive context for one-pass implementation including:
✅ Complete external documentation with specific URLs
✅ Codebase patterns and existing examples  
✅ Detailed task breakdown with specific patterns to follow
✅ Executable validation loops with specific commands
✅ Security best practices and gotchas documented
✅ Performance requirements and optimization strategies
✅ Full test suite specification with examples
✅ Integration points clearly defined

The only minor gap is the absence of PLANNING.md and TASK.md files in the current codebase, but sufficient patterns exist in the use-cases to ensure successful implementation.
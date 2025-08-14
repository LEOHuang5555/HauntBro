# PRP: Comprehensive RESTful API Backend with Authentication and Analytics

## IMPLEMENTATION BLUEPRINT

### Feature Overview
Implement a production-ready FastAPI backend that serves as the central API gateway for the ghost story search engine, providing secure user authentication with JWT tokens, contextual search endpoints powered by RAG, comprehensive user behavior analytics, freemium tier management, and seamless integration with all system components including the medallion architecture, content moderation, and real-time features.

### Context Analysis from Existing Codebase
**Existing Foundation (80% of Infrastructure Ready):**
- ✅ **Database Models**: Comprehensive User, Story, Analytics models in `infrastructure/database/models.py`
- ✅ **Async Database Management**: Production-ready `DatabaseManager` with async patterns in `infrastructure/database/connection.py`
- ✅ **Configuration System**: Dataclass-based config in `etl/processing/config.py`
- ✅ **Embedding & Search**: Multi-language embedding system in `etl/models/embedding_manager.py`
- ✅ **Analytics Framework**: Real-time metrics dashboard in `monitoring/metrics_dashboard.py`
- ✅ **Background Processing**: Async pipeline patterns in `etl/processing/pipeline.py`
- ✅ **Poetry Dependencies**: FastAPI, SQLAlchemy, Pydantic already configured in `pyproject.toml`

**Key Integration Opportunities:**
- Extend existing `User` model for JWT authentication
- Integrate existing `DatabaseManager` for FastAPI dependencies
- Use existing `MetricsCollector` for API analytics
- Leverage existing `EmbeddingManager` for search endpoints
- Follow existing async patterns for WebSocket implementation
- Follow RESTful API design principle when developing APIs

## EXTERNAL RESEARCH INTEGRATION

### Production FastAPI Architecture (2024 Best Practices)
**Sources**: 
- TestDriven.io FastAPI JWT Auth: https://testdriven.io/blog/fastapi-jwt-auth/
- FastAPI Security Documentation: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Production Deployment Guide: https://betterstack.com/community/guides/scaling-python/authentication-fastapi/

**Key Patterns to Implement:**
```python
# JWT Authentication with async PostgreSQL
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import jwt

# Use existing User model from models.py
from examples.infrastructure.database.models import User

class AuthenticationService:
    def __init__(self, db_session, redis_client):
        self.db = db_session  # Use existing DatabaseManager
        self.redis = redis_client
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

### WebSocket Real-time Features (2024 Production Patterns)
**Sources**:
- Redis Streams for Reliable Messaging: https://dev.to/geetnsh2k1/building-a-real-time-notification-service-with-fastapi-redis-streams-and-websockets-52ib
- Scalable WebSocket Patterns: https://medium.com/@nandagopal05/scaling-websockets-with-pub-sub-using-python-redis-fastapi-b16392ffe291
- Production WebSocket Management: https://unfoldai.com/fastapi-and-websockets/

**Redis Streams Implementation** (2024 Standard):
```python
# Use Redis Streams instead of Pub/Sub for reliability
class WebSocketManager:
    async def send_notification(self, user_id: str, message: dict):
        # Add to Redis Stream for persistence
        await self.redis.xadd(f"notifications:{user_id}", message)
        # Send to active connections
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                await websocket.send_json(message)
```

### Security & Rate Limiting (Production Patterns)
**Sources**:
- SlowAPI with Redis: https://www.codingeasypeasy.com/blog/fastapi-rate-limiting-secure-your-api-with-slowapi-and-redis-comprehensive-guide
- Production Security: https://slashdev.io/-guide-to-building-secure-backends-in-fastapi-in-2024-2
- CORS Configuration: https://fastapi.tiangolo.com/tutorial/cors/

**Rate Limiting Strategy**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Redis-backed rate limiting for production
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Testing Patterns (2024 Best Practices)
**Sources**:
- Async Database Testing: https://testdriven.io/blog/fastapi-crud/
- Pytest Fixtures: https://pytest-with-eric.com/api-testing/pytest-api-testing-1/
- Database Mocking: https://www.codingeasypeasy.com/blog/how-to-mock-database-calls-in-fastapi-tests-a-comprehensive-guide

**Testing Architecture**:
```python
# Use existing DatabaseManager for test isolation
@pytest.fixture
async def test_db():
    # Create test database session using existing patterns
    db_manager = DatabaseManager("sqlite:///:memory:")
    async with db_manager.get_session() as session:
        yield session
```

## IMPLEMENTATION TASK SEQUENCE

### Task 1: FastAPI Application Foundation (2 hours)
**Objective:** Set up FastAPI application structure using existing patterns

**Implementation Steps:**
1. Create `backend/app/main.py` using existing config patterns from `examples/etl/processing/config.py`
2. Set up FastAPI app with middleware following 2024 security best practices
3. Integrate existing `DatabaseManager` from `examples/infrastructure/database/connection.py`
4. Configure CORS, security headers, and error handling middleware
5. Set up dependency injection for database sessions

**Code Integration Pattern:**
```python
# backend/app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from examples.infrastructure.database.connection import DatabaseManager, get_db
from examples.etl.processing.config import CONFIG

app = FastAPI(
    title="Ghost Story Search Engine API",
    description="Production API with authentication and analytics",
    version="1.0.0",
    docs_url="/api/docs"
)

# Use existing config patterns
db_manager = DatabaseManager(CONFIG["database"])
```

**Validation Gate 1:** FastAPI app starts successfully with health check endpoint returning 200

```bash
# Start app and test health endpoint
poetry run uvicorn backend.app.main:app --reload
curl http://localhost:8000/health
# Expected: {"status": "healthy", "timestamp": "..."}
```

### Task 2: JWT Authentication System (3 hours)
**Objective:** Implement production-ready JWT authentication using existing User model

**Implementation Steps:**
1. Create `backend/app/core/security.py` with JWT service using existing User model
2. Implement password hashing with bcrypt following 2024 security standards
3. Create authentication endpoints (register, login, refresh) in `backend/app/api/v1/auth.py`
4. Set up JWT middleware with proper token validation and blacklisting
5. Integrate with existing Redis for token storage and rate limiting

**Database Integration:**
```python
# Use existing User model directly
from examples.infrastructure.database.models import User

class AuthenticationService:
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        # Use existing database connection patterns
        async with self.db_manager.get_session() as session:
            user = await session.execute(
                select(User).where(User.username == username)
            )
            return user.scalar_one_or_none()
```

**Validation Gate 2:** Complete authentication flow with JWT tokens

```bash
# Test user registration and login
poetry run pytest tests/test_auth.py -v
# Test JWT token validation
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"testpass123"}'
```

### Task 3: Search API Integration (2.5 hours)
**Objective:** Create search endpoints that integrate with existing RAG engine

**Implementation Steps:**
1. Create `backend/app/api/v1/search.py` with search endpoints
2. Integrate existing `EmbeddingManager` from `examples/etl/models/embedding_manager.py`
3. Connect to existing chunking and similarity search systems
4. Implement freemium restrictions using existing user tier models
5. Add search analytics integration with existing metrics system

**Search Service Integration:**
```python
# Leverage existing embedding and search systems
from examples.etl.models.embedding_manager import EmbeddingManager
from examples.infrastructure.database.models import SearchInteraction

class SearchService:
    def __init__(self):
        self.embedding_manager = EmbeddingManager()  # Use existing system
        
    async def search_stories(self, query: str, user: User):
        # Use existing embedding generation
        query_embedding = await self.embedding_manager.generate_embeddings(query)
        
        # Perform similarity search using existing patterns
        # Record analytics using existing SearchInteraction model
```

**Validation Gate 3:** Search endpoints return relevant results with proper analytics

```bash
# Test search functionality
poetry run pytest tests/test_search.py -v
# Test search API endpoint
curl -X POST http://localhost:8000/api/v1/search/ \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query":"ghost story","language":"en","page":1,"per_page":10}'
```

### Task 4: User Analytics and Behavior Tracking (2 hours)
**Objective:** Implement analytics endpoints using existing metrics framework

**Implementation Steps:**
1. Create `backend/app/api/v1/analytics.py` with tracking endpoints
2. Integrate existing `MetricsCollector` from `examples/monitoring/metrics_dashboard.py`
3. Use existing analytics models for user behavior tracking
4. Implement real-time event tracking with proper data validation
5. Add dashboard endpoints for user insights

**Analytics Integration:**
```python
# Use existing analytics infrastructure
from examples.monitoring.metrics_dashboard import MetricsCollector
from examples.infrastructure.database.models import UserReadingBehavior

class AnalyticsService:
    def __init__(self):
        self.metrics_collector = MetricsCollector()  # Use existing system
        
    async def track_user_event(self, user_id: str, event_type: str, event_data: dict):
        # Use existing metrics collection patterns
        await self.metrics_collector._record_metric(
            f"user_event_{event_type}", 1.0, datetime.utcnow()
        )
```

**Validation Gate 4:** Analytics endpoints track and report user behavior

```bash
# Test analytics tracking
poetry run pytest tests/test_analytics.py -v
# Test analytics API
curl -X POST http://localhost:8000/api/v1/analytics/events \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d '{"event_type":"search_performed","event_data":{"query":"ghost"}}'
```

### Task 5: WebSocket Real-time Features (3 hours)
**Objective:** Implement WebSocket manager with Redis Streams for reliable messaging

**Implementation Steps:**
1. Create `backend/app/websocket/manager.py` with connection management
2. Implement Redis Streams for reliable message delivery (2024 best practice)
3. Add WebSocket authentication using JWT tokens
4. Create notification system with offline message handling
5. Implement heartbeat and connection monitoring

**WebSocket Architecture (Following 2024 Patterns):**
```python
# Use Redis Streams for reliable messaging
class WebSocketManager:
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        # Store connection
        self.active_connections[user_id] = websocket
        
        # Deliver any missed messages from Redis Stream
        messages = await self.redis.xread({f"notifications:{user_id}": "$"})
        for message in messages:
            await websocket.send_json(message)
```

**Validation Gate 5:** WebSocket connections handle real-time messaging reliably

```bash
# Test WebSocket connections
poetry run pytest tests/test_websocket.py -v
# Test WebSocket endpoint (manual verification)
# Connect to ws://localhost:8000/ws/{user_id}?token={jwt_token}
```

### Task 6: Security Middleware and Rate Limiting (1.5 hours)
**Objective:** Implement production-grade security and rate limiting

**Implementation Steps:**
1. Add SlowAPI rate limiting with Redis backend
2. Configure CORS for production domains
3. Implement security headers middleware
4. Add input validation and sanitization
5. Set up request logging and monitoring

**Security Configuration:**
```python
# Production-grade security setup
from slowapi import Limiter
from slowapi.util import get_remote_address

# Redis-backed rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)

# Apply rate limits based on user tier
@app.post("/api/v1/search/")
@limiter.limit("100/hour")  # Free tier
async def search_stories_free():
    pass

@app.post("/api/v1/search/premium")
@limiter.limit("1000/hour")  # Premium tier
async def search_stories_premium():
    pass
```

**Validation Gate 6:** Security middleware blocks excessive requests and validates input

```bash
# Test rate limiting
poetry run pytest tests/test_security.py -v
# Test rate limit enforcement
for i in {1..20}; do curl http://localhost:8000/api/v1/search/; done
# Should return 429 after limit exceeded
```

### Task 7: Content Management API (2 hours)
**Objective:** Implement CRUD operations for stories, bookmarks, and user preferences

**Implementation Steps:**
1. Create `backend/app/api/v1/content.py` with story management endpoints
2. Use existing Story models from database
3. Implement bookmark and rating systems using existing models
4. Add user preference management
5. Integrate with existing content moderation workflows

**Content Integration:**
```python
# Use existing models directly
from examples.infrastructure.database.models import Story, UserBookmark, UserRating

class ContentService:
    async def get_story_detail(self, story_id: str, user: User) -> StoryDetail:
        # Use existing database connection patterns
        async with self.db_manager.get_session() as session:
            story = await session.execute(
                select(Story).where(Story.id == story_id)
            )
            return story.scalar_one_or_none()
```

**Validation Gate 7:** Content endpoints perform CRUD operations correctly

```bash
# Test content management
poetry run pytest tests/test_content.py -v
# Test story retrieval
curl http://localhost:8000/api/v1/content/stories/{story_id} \
  -H "Authorization: Bearer ${JWT_TOKEN}"
```

### Task 8: Admin API and Moderation (1.5 hours)
**Objective:** Create admin endpoints for content moderation and system management

**Implementation Steps:**
1. Create `backend/app/api/v1/admin.py` with admin-only endpoints
2. Implement role-based access control using existing User model
3. Add content moderation workflow endpoints
4. Create system statistics and health monitoring endpoints
5. Integrate with existing analytics dashboard

**Admin Service:**
```python
# Admin functionality using existing patterns
class AdminService:
    async def get_system_statistics(self) -> SystemStats:
        # Use existing metrics collector
        current_metrics = self.metrics_collector.get_all_current_metrics()
        return SystemStats(
            total_users=current_metrics.get("total_users", 0),
            # ... other stats from existing analytics
        )
```

**Validation Gate 8:** Admin endpoints enforce role-based access and provide system insights

```bash
# Test admin functionality
poetry run pytest tests/test_admin.py -v
# Test admin stats endpoint
curl http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer ${ADMIN_JWT_TOKEN}"
```

### Task 9: Comprehensive Testing Suite (2 hours)
**Objective:** Implement full test coverage using 2024 pytest patterns

**Implementation Steps:**
1. Set up `tests/conftest.py` with database fixtures using existing DatabaseManager
2. Create integration tests for all API endpoints
3. Implement async database testing with proper isolation
4. Add WebSocket testing with mock Redis
5. Create performance tests for search endpoints

**Testing Setup:**
```python
# tests/conftest.py - Use existing database patterns
@pytest.fixture
async def test_db():
    # Use existing DatabaseManager for test isolation
    db_manager = DatabaseManager("sqlite:///:memory:")
    # Create all tables using existing models
    from examples.infrastructure.database.models import Base
    Base.metadata.create_all(bind=db_manager.engine)
    yield db_manager

@pytest.fixture
def test_client(test_db):
    # Override database dependency
    app.dependency_overrides[get_db] = lambda: test_db.get_session()
    return TestClient(app)
```

**Validation Gate 9:** Full test suite passes with >90% coverage

```bash
# Run comprehensive test suite
poetry run pytest tests/ -v --cov=backend --cov-report=html
# Coverage should be >90%
poetry run pytest tests/ --cov=backend --cov-fail-under=90
```

### Task 10: Documentation and Deployment Preparation (1 hour)
**Objective:** Complete API documentation and prepare for production deployment

**Implementation Steps:**
1. Configure OpenAPI documentation with examples
2. Create API integration guides and SDK documentation
3. Set up Docker configuration for containerized deployment
4. Configure environment-based settings for dev/staging/prod
5. Create deployment health checks and monitoring endpoints

**Documentation Setup:**
```python
# Enhanced OpenAPI configuration
app = FastAPI(
    title="Ghost Story Search Engine API",
    description="Production API with authentication and analytics",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_tags=[
        {"name": "Authentication", "description": "User authentication and JWT management"},
        {"name": "Search", "description": "RAG-powered contextual search"},
        {"name": "Analytics", "description": "User behavior tracking and insights"}
    ]
)
```

**Validation Gate 10:** Documentation is complete and deployment ready

```bash
# Verify OpenAPI documentation
curl http://localhost:8000/openapi.json | jq .
# Test production build
poetry run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# Verify health check
curl http://localhost:8000/health
```

## QUALITY CHECKLIST

### Performance Requirements ✓
- [ ] API response time <200ms for 95% of requests
- [ ] WebSocket latency <100ms for real-time features
- [ ] Database connection pooling with async operations
- [ ] Redis caching for frequently accessed data

### Security Requirements ✓
- [ ] JWT authentication with proper token validation
- [ ] Rate limiting with Redis backend (SlowAPI)
- [ ] CORS configuration for production domains
- [ ] Input validation and SQL injection prevention
- [ ] Security headers and middleware

### Integration Requirements ✓
- [ ] Seamless integration with existing User and Story models
- [ ] Use existing DatabaseManager and async patterns
- [ ] Integration with existing metrics and analytics systems
- [ ] Compatible with existing embedding and search infrastructure

### Testing Requirements ✓
- [ ] >90% test coverage with pytest
- [ ] Async database testing with proper isolation
- [ ] Integration tests for all API endpoints
- [ ] WebSocket testing with mock Redis
- [ ] Performance tests for critical endpoints

### Documentation Requirements ✓
- [ ] Complete OpenAPI documentation with examples
- [ ] API integration guides and SDK documentation
- [ ] Production deployment guide
- [ ] Authentication and security documentation

## EXTERNAL DOCUMENTATION REFERENCES

### FastAPI Production Patterns
- **JWT Authentication Guide**: https://testdriven.io/blog/fastapi-jwt-auth/
- **Security Best Practices**: https://betterstack.com/community/guides/scaling-python/authentication-fastapi/
- **Official FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/

### WebSocket & Real-time Features
- **Redis Streams Implementation**: https://dev.to/geetnsh2k1/building-a-real-time-notification-service-with-fastapi-redis-streams-and-websockets-52ib
- **Scalable WebSocket Patterns**: https://medium.com/@nandagopal05/scaling-websockets-with-pub-sub-using-python-redis-fastapi-b16392ffe291
- **Production WebSocket Management**: https://unfoldai.com/fastapi-and-websockets/

### Security & Rate Limiting
- **SlowAPI Rate Limiting**: https://www.codingeasypeasy.com/blog/fastapi-rate-limiting-secure-your-api-with-slowapi-and-redis-comprehensive-guide
- **Production Security Guide**: https://slashdev.io/-guide-to-building-secure-backends-in-fastapi-in-2024-2
- **CORS Configuration**: https://fastapi.tiangolo.com/tutorial/cors/

### Testing & Quality Assurance
- **Async Database Testing**: https://testdriven.io/blog/fastapi-crud/
- **Pytest Best Practices**: https://pytest-with-eric.com/api-testing/pytest-api-testing-1/
- **Database Mocking Strategies**: https://www.codingeasypeasy.com/blog/how-to-mock-database-calls-in-fastapi-tests-a-comprehensive-guide

## RISK MITIGATION

### High-Priority Risks
1. **Database Connection Management**: Mitigated by using existing proven DatabaseManager patterns
2. **Authentication Security**: Mitigated by following 2024 JWT best practices with proper token validation
3. **WebSocket Scalability**: Mitigated by Redis Streams for reliable message delivery
4. **Rate Limiting Effectiveness**: Mitigated by Redis-backed SlowAPI implementation

### Integration Dependencies
- Existing database models and connection management
- Current embedding and search infrastructure  
- Established metrics and analytics framework
- Redis instance for caching and WebSocket messaging

## CONFIDENCE SCORE: 9/10

**Rationale for High Confidence:**
- **Strong Foundation**: 80% of required infrastructure already exists in codebase
- **Proven Patterns**: Following 2024 production best practices from authoritative sources
- **Clear Integration Path**: Detailed integration with existing systems rather than rebuilding
- **Comprehensive Testing**: Modern async testing patterns with proper database isolation
- **Production-Ready**: Security, monitoring, and scalability considerations built-in from start

**Success Indicators:**
- Leverages existing models, database connections, and analytics systems
- Follows current FastAPI production patterns from industry sources
- Comprehensive validation gates ensure each component works correctly
- Clear documentation and testing strategy for maintainability

## IMPLEMENTATION TIMELINE: 18-20 hours total

This PRP provides a comprehensive blueprint for implementing a production-ready FastAPI backend with high confidence in successful one-pass implementation due to strong existing infrastructure and detailed integration with proven patterns.
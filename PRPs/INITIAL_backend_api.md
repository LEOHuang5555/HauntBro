INITIAL_backend_api.md

## FEATURE: Comprehensive RESTful API Backend with Authentication and Analytics

Implement a production-ready FastAPI backend that serves as the central API gateway for the ghost story search engine, providing secure user authentication with JWT tokens, contextual search endpoints powered by RAG, comprehensive user behavior analytics, freemium tier management, and seamless integration with all system components including the medallion architecture, content moderation, and real-time features.

## PRIMARY FUNCTIONALITY:
- **User Authentication System:** Secure JWT-based authentication with registration, login, password reset, and session management
- **RESTful API Design:** Comprehensive REST endpoints following OpenAPI specifications with proper HTTP status codes and error handling
- **Contextual Search API:** RAG-powered search endpoints with query processing, similarity search, and intelligent result ranking
- **User Behavior Analytics:** Real-time tracking of search patterns, reading completion rates, engagement metrics, and conversion funnels
- **Freemium Management:** Subscription tier enforcement, usage tracking, rate limiting, and upgrade flow integration
- **Content Management:** CRUD operations for stories, user preferences, bookmarks, and reading history
- **Real-Time Features:** WebSocket connections for live notifications, real-time search suggestions, and system status updates

## ADDITIONAL FEATURES:
- **Advanced Security:** Rate limiting, CORS configuration, input validation, SQL injection prevention, and security headers
- **API Versioning:** Structured API versioning strategy with backward compatibility and deprecation management
- **Comprehensive Monitoring:** Health checks, performance metrics, error tracking, and integration with Prometheus/Grafana
- **Async Processing:** Background task management for heavy operations like embedding generation and data processing
- **Multi-Language Support:** Internationalization for API responses, error messages, and user communications
- **Admin Dashboard API:** Administrative endpoints for content moderation, user management, and system analytics
- **Integration Hub:** Seamless integration with all system components including Kafka, Airflow, and external services

## TECHNICAL REQUIREMENTS:
- **FastAPI Framework:** Modern async Python web framework with automatic OpenAPI documentation and type hints
- **JWT Authentication:** Secure token-based authentication with refresh tokens and proper expiration handling
- **SQLAlchemy ORM:** Database operations with async support, connection pooling, and transaction management
- **Pydantic Models:** Comprehensive data validation and serialization with type safety
- **Redis Integration:** Caching, session storage, rate limiting, and real-time features
- **WebSocket Support:** Real-time bidirectional communication for live features
- **Background Tasks:** Celery integration for async processing and scheduled jobs
- **Comprehensive Testing:** Unit tests, integration tests, and API endpoint testing with high coverage
- **Docker Deployment:** Containerized deployment with multi-stage builds and production optimization

## API ARCHITECTURE:

### Core API Structure:
```python
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

# Initialize FastAPI application
app = FastAPI(
    title="Ghost Story Search Engine API",
    description="Comprehensive API for contextual ghost story search with multi-language support",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Security and middleware configuration
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ghoststory.com", "https://app.ghoststory.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["ghoststory.com", "*.ghoststory.com", "localhost"]
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# API Response Models
class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    meta: Optional[Dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PaginatedResponse(APIResponse):
    data: List[Any]
    meta: Dict = Field(default_factory=lambda: {
        "page": 1,
        "per_page": 20,
        "total": 0,
        "pages": 0,
        "has_next": False,
        "has_prev": False
    })

# API Router Organization
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])
app.include_router(user_router, prefix="/api/v1/users", tags=["User Management"])
app.include_router(content_router, prefix="/api/v1/content", tags=["Content"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Administration"])
app.include_router(webhook_router, prefix="/api/v1/webhooks", tags=["Webhooks"])
```

### Authentication System:
```python
# Authentication Router
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta

auth_router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Authentication Models
class UserRegistration(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=100)
    language_preference: Optional[str] = "en"
    marketing_consent: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: Dict[str, Any]

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

# Authentication Service
class AuthenticationService:
    def __init__(self, db_session, redis_client, email_service):
        self.db = db_session
        self.redis = redis_client
        self.email_service = email_service
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.jwt_algorithm = settings.JWT_ALGORITHM
        
    async def register_user(self, user_data: UserRegistration) -> TokenResponse:
        """Register new user with email verification"""
        
        # Check if user already exists
        existing_user = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create new user
        hashed_password = pwd_context.hash(user_data.password)
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            full_name=user_data.full_name,
            language_preference=user_data.language_preference,
            marketing_consent=user_data.marketing_consent,
            is_email_verified=False,
            subscription_tier="free",
            created_at=datetime.utcnow()
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        # Send verification email
        verification_token = await self.generate_verification_token(new_user.id)
        await self.email_service.send_verification_email(
            user_data.email, 
            user_data.full_name, 
            verification_token
        )
        
        # Generate JWT tokens
        tokens = await self.generate_tokens(new_user)
        
        # Track registration event
        await self.track_user_event(new_user.id, "user_registered", {
            "registration_method": "email",
            "language_preference": user_data.language_preference
        })
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"],
            user_info={
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "subscription_tier": new_user.subscription_tier,
                "is_email_verified": new_user.is_email_verified
            }
        )
    
    async def authenticate_user(self, login_data: UserLogin) -> TokenResponse:
        """Authenticate user and return JWT tokens"""
        
        # Find user by email
        result = await self.db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()
        
        if not user or not pwd_context.verify(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Check for account lockout
        failed_attempts = await self.redis.get(f"failed_login:{user.email}")
        if failed_attempts and int(failed_attempts) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked due to too many failed attempts"
            )
        
        # Clear failed attempts on successful login
        await self.redis.delete(f"failed_login:{user.email}")
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        # Generate tokens
        tokens = await self.generate_tokens(user, remember_me=login_data.remember_me)
        
        # Track login event
        await self.track_user_event(user.id, "user_login", {
            "login_method": "email",
            "remember_me": login_data.remember_me
        })
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"],
            user_info={
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "subscription_tier": user.subscription_tier,
                "is_email_verified": user.is_email_verified
            }
        )
    
    async def generate_tokens(self, user: User, remember_me: bool = False) -> Dict[str, Any]:
        """Generate JWT access and refresh tokens"""
        
        # Token expiration times
        access_token_expires = timedelta(hours=1)
        refresh_token_expires = timedelta(days=30 if remember_me else 7)
        
        # Access token payload
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "subscription_tier": user.subscription_tier,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + access_token_expires,
            "type": "access"
        }
        
        # Refresh token payload
        refresh_payload = {
            "sub": str(user.id),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + refresh_token_expires,
            "type": "refresh"
        }
        
        # Generate tokens
        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store refresh token in Redis
        await self.redis.setex(
            f"refresh_token:{user.id}",
            int(refresh_token_expires.total_seconds()),
            refresh_token
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": int(access_token_expires.total_seconds())
        }

# Authentication Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> User:
    """Get current authenticated user from JWT token"""
    
    try:
        # Decode JWT token
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Check if token is blacklisted
        is_blacklisted = await redis.get(f"blacklisted_token:{credentials.credentials}")
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Authentication Endpoints
@auth_router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserRegistration,
    background_tasks: BackgroundTasks,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """Register a new user account"""
    return await auth_service.register_user(user_data)

@auth_router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """Authenticate user and return access tokens"""
    return await auth_service.authenticate_user(login_data)

@auth_router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: Redis = Depends(get_redis)
):
    """Logout user and blacklist token"""
    
    # Blacklist the current token
    await redis.setex(
        f"blacklisted_token:{credentials.credentials}",
        3600,  # 1 hour (token expiry time)
        "true"
    )
    
    # Remove refresh token
    await redis.delete(f"refresh_token:{current_user.id}")
    
    return APIResponse(success=True, data={"message": "Successfully logged out"})

@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """Refresh access token using refresh token"""
    return await auth_service.refresh_access_token(refresh_token)
```

### Search API Endpoints:
```python
# Search Router
search_router = APIRouter()

# Search Models
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    language: Optional[str] = None
    filters: Optional[Dict[str, Any]] = {}
    sort_by: Optional[str] = "relevance"
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

class SearchFilters(BaseModel):
    source: Optional[List[str]] = None
    language: Optional[List[str]] = None
    scare_level: Optional[List[int]] = None
    reading_time_min: Optional[int] = None
    reading_time_max: Optional[int] = None
    quality_score_min: Optional[float] = None
    date_range: Optional[Dict[str, str]] = None

class SearchResult(BaseModel):
    story_id: str
    title: str
    content_preview: str
    source: str
    language: str
    author: Optional[str]
    scare_level: Optional[int]
    quality_score: float
    similarity_score: float
    reading_time_minutes: int
    created_at: datetime
    tags: List[str]
    ai_summary: Optional[str] = None

class SearchResponse(PaginatedResponse):
    data: List[SearchResult]
    meta: Dict = Field(default_factory=lambda: {
        "query_info": {},
        "search_stats": {},
        "recommendations": []
    })

# Search Service
class SearchService:
    def __init__(self, rag_engine, user_analytics, freemium_manager):
        self.rag_engine = rag_engine
        self.user_analytics = user_analytics
        self.freemium_manager = freemium_manager
        
    async def search_stories(
        self, 
        search_query: SearchQuery, 
        user: User,
        request_context: Dict[str, Any]
    ) -> SearchResponse:
        """Perform contextual search for ghost stories"""
        
        # Check user search limits
        usage_check = await self.freemium_manager.check_search_usage(user)
        if not usage_check["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=usage_check["message"],
                headers={"X-Upgrade-URL": usage_check["upgrade_url"]}
            )
        
        # Prepare user context for search
        user_context = {
            "user_id": user.id,
            "subscription_tier": user.subscription_tier,
            "language_preference": user.language_preference,
            "search_history": await self.user_analytics.get_recent_searches(user.id),
            "preferences": await self.get_user_preferences(user.id)
        }
        
        # Prepare search options
        search_options = {
            "filters": search_query.filters,
            "sort_by": search_query.sort_by,
            "page": search_query.page,
            "per_page": search_query.per_page
        }
        
        # Perform RAG search
        search_results = await self.rag_engine.search_stories(
            query=search_query.query,
            user_context=user_context,
            search_options=search_options
        )
        
        # Apply freemium restrictions
        filtered_results = await self.freemium_manager.apply_search_restrictions(
            search_results, user
        )
        
        # Convert to API response format
        api_results = []
        for result in filtered_results["results"]:
            api_result = SearchResult(
                story_id=result["story_id"],
                title=result["title"],
                content_preview=result["content_preview"],
                source=result["source"],
                language=result["language"],
                author=result.get("author"),
                scare_level=result.get("scare_level"),
                quality_score=result["quality_score"],
                similarity_score=result["similarity_score"],
                reading_time_minutes=result["reading_time_minutes"],
                created_at=result["created_at"],
                tags=result.get("tags", []),
                ai_summary=result.get("ai_summary") if user.subscription_tier != "free" else None
            )
            api_results.append(api_result)
        
        # Calculate pagination
        total_results = filtered_results.get("total_count", len(api_results))
        total_pages = (total_results + search_query.per_page - 1) // search_query.per_page
        
        # Record search analytics
        await self.user_analytics.record_search(
            user_id=user.id,
            query=search_query.query,
            results_count=len(api_results),
            search_context=user_context,
            request_context=request_context
        )
        
        # Prepare response metadata
        response_meta = {
            "page": search_query.page,
            "per_page": search_query.per_page,
            "total": total_results,
            "pages": total_pages,
            "has_next": search_query.page < total_pages,
            "has_prev": search_query.page > 1,
            "query_info": {
                "enhanced_query": search_results.get("enhanced_query"),
                "language_detected": search_results.get("language_detected"),
                "processing_time_ms": search_results.get("processing_time_ms")
            },
            "search_stats": {
                "total_available": search_results.get("total_available"),
                "quality_filtered": search_results.get("quality_filtered"),
                "similarity_threshold": search_results.get("similarity_threshold")
            }
        }
        
        # Add upgrade prompt if applicable
        if filtered_results.get("limited"):
            response_meta["upgrade_prompt"] = filtered_results["upgrade_prompt"]
            response_meta["remaining_searches"] = filtered_results.get("remaining_searches")
        
        return SearchResponse(
            success=True,
            data=api_results,
            meta=response_meta
        )

# Search Endpoints
@search_router.post("/", response_model=SearchResponse)
async def search_stories(
    search_query: SearchQuery,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    search_service: SearchService = Depends(get_search_service)
):
    """Search for ghost stories using advanced RAG-powered search"""
    
    request_context = {
        "ip_address": request.client.host if request else None,
        "user_agent": request.headers.get("user-agent") if request else None,
        "timestamp": datetime.utcnow()
    }
    
    return await search_service.search_stories(search_query, current_user, request_context)

@search_router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service)
):
    """Get search suggestions based on partial query"""
    
    suggestions = await search_service.get_search_suggestions(
        partial_query=q,
        user_id=current_user.id,
        limit=limit
    )
    
    return APIResponse(
        success=True,
        data=suggestions
    )

@search_router.get("/trending")
async def get_trending_searches(
    time_period: str = Query(default="24h", regex="^(1h|24h|7d|30d)$"),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service)
):
    """Get trending search queries"""
    
    trending = await search_service.get_trending_searches(
        time_period=time_period,
        limit=limit,
        user_tier=current_user.subscription_tier
    )
    
    return APIResponse(
        success=True,
        data=trending
    )
```

### User Analytics and Behavior Tracking:
```python
# Analytics Router
analytics_router = APIRouter()

# Analytics Models
class UserEvent(BaseModel):
    event_type: str
    event_data: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None

class ReadingSession(BaseModel):
    story_id: str
    started_at: datetime
    reading_progress: float = Field(ge=0.0, le=1.0)
    reading_time_seconds: int
    completed: bool = False

class UserAnalytics(BaseModel):
    user_id: str
    total_searches: int
    total_stories_read: int
    average_reading_completion: float
    favorite_sources: List[str]
    favorite_languages: List[str]
    reading_time_distribution: Dict[str, int]
    engagement_score: float

# Analytics Service
class AnalyticsService:
    def __init__(self, db_session, redis_client, event_processor):
        self.db = db_session
        self.redis = redis_client
        self.event_processor = event_processor
        
    async def track_user_event(
        self, 
        user_id: str, 
        event_type: str, 
        event_data: Dict[str, Any],
        request_context: Dict[str, Any] = None
    ):
        """Track user behavior events for analytics"""
        
        event_record = {
            "user_id": user_id,
            "event_type": event_type,
            "event_data": event_data,
            "request_context": request_context or {},
            "timestamp": datetime.utcnow(),
            "session_id": request_context.get("session_id") if request_context else None
        }
        
        # Store event in database
        user_event = UserEvent_DB(
            user_id=user_id,
            event_type=event_type,
            event_data=event_record["event_data"],
            request_context=event_record["request_context"],
            timestamp=event_record["timestamp"],
            session_id=event_record["session_id"]
        )
        
        self.db.add(user_event)
        await self.db.commit()
        
        # Send to real-time analytics
        await self.event_processor.process_event(event_record)
        
        # Update user metrics in Redis
        await self.update_user_metrics(user_id, event_type, event_data)
        
        return event_record
    
    async def track_reading_session(
        self, 
        user_id: str, 
        reading_session: ReadingSession
    ):
        """Track reading session with completion rate"""
        
        # Store reading session
        session_record = ReadingSession_DB(
            user_id=user_id,
            story_id=reading_session.story_id,
            started_at=reading_session.started_at,
            reading_progress=reading_session.reading_progress,
            reading_time_seconds=reading_session.reading_time_seconds,
            completed=reading_session.completed,
            timestamp=datetime.utcnow()
        )
        
        self.db.add(session_record)
        await self.db.commit()
        
        # Update reading analytics
        await self.update_reading_analytics(user_id, reading_session)
        
        # Check for reading milestones
        await self.check_reading_milestones(user_id)
        
        return session_record
    
    async def get_user_analytics(self, user_id: str, time_period: str = "30d") -> UserAnalytics:
        """Get comprehensive user analytics"""
        
        # Define time range
        end_date = datetime.utcnow()
        if time_period == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_period == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_period == "90d":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Get search analytics
        search_stats = await self.get_search_analytics(user_id, start_date, end_date)
        
        # Get reading analytics
        reading_stats = await self.get_reading_analytics(user_id, start_date, end_date)
        
        # Calculate engagement score
        engagement_score = await self.calculate_engagement_score(user_id, start_date, end_date)
        
        return UserAnalytics(
            user_id=user_id,
            total_searches=search_stats["total_searches"],
            total_stories_read=reading_stats["total_stories_read"],
            average_reading_completion=reading_stats["average_completion"],
            favorite_sources=reading_stats["favorite_sources"],
            favorite_languages=reading_stats["favorite_languages"],
            reading_time_distribution=reading_stats["time_distribution"],
            engagement_score=engagement_score
        )

# Analytics Endpoints
@analytics_router.post("/events")
async def track_event(
    event: UserEvent,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Track user behavior event"""
    
    request_context = {
        "ip_address": request.client.host if request else None,
        "user_agent": request.headers.get("user-agent") if request else None,
        "session_id": request.headers.get("x-session-id") if request else None
    }
    
    await analytics_service.track_user_event(
        user_id=current_user.id,
        event_type=event.event_type,
        event_data=event.event_data,
        request_context=request_context
    )
    
    return APIResponse(success=True, data={"message": "Event tracked successfully"})

@analytics_router.post("/reading-session")
async def track_reading_session(
    session: ReadingSession,
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Track reading session with progress and completion"""
    
    await analytics_service.track_reading_session(current_user.id, session)
    
    return APIResponse(success=True, data={"message": "Reading session tracked successfully"})

@analytics_router.get("/dashboard", response_model=UserAnalytics)
async def get_user_dashboard(
    time_period: str = Query(default="30d", regex="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get user analytics dashboard data"""
    
    analytics = await analytics_service.get_user_analytics(
        user_id=current_user.id,
        time_period=time_period
    )
    
    return analytics

@analytics_router.get("/reading-progress/{story_id}")
async def get_reading_progress(
    story_id: str,
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get reading progress for a specific story"""
    
    progress = await analytics_service.get_story_reading_progress(
        user_id=current_user.id,
        story_id=story_id
    )
    
    return APIResponse(success=True, data=progress)
```

### Content Management API:
```python
# Content Router
content_router = APIRouter()

# Content Models
class StoryDetail(BaseModel):
    id: str
    title: str
    content: str
    content_preview: str
    source: str
    source_url: str
    language: str
    author: Optional[str]
    scare_level: Optional[int]
    quality_score: float
    word_count: int
    reading_time_minutes: int
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    is_bookmarked: bool = False
    user_rating: Optional[int] = None
    average_rating: Optional[float] = None
    view_count: int = 0

class BookmarkRequest(BaseModel):
    story_id: str
    folder_name: Optional[str] = "default"

class RatingRequest(BaseModel):
    story_id: str
    rating: int = Field(ge=1, le=5)
    review_text: Optional[str] = None

class UserPreferences(BaseModel):
    preferred_languages: List[str] = ["en"]
    preferred_sources: List[str] = []
    preferred_scare_levels: List[int] = []
    content_filters: Dict[str, Any] = {}
    notification_settings: Dict[str, bool] = {}

# Content Service
class ContentService:
    def __init__(self, db_session, cache_manager, analytics_service):
        self.db = db_session
        self.cache = cache_manager
        self.analytics = analytics_service
        
    async def get_story_detail(self, story_id: str, user: User) -> StoryDetail:
        """Get detailed story information with user-specific data"""
        
        # Check cache first
        cache_key = f"story_detail:{story_id}:{user.id}"
        cached_story = await self.cache.get(cache_key)
        if cached_story:
            return StoryDetail.parse_obj(cached_story)
        
        # Get story from database
        story_query = await self.db.execute(
            select(Story)
            .options(selectinload(Story.tags))
            .where(Story.id == story_id, Story.is_active == True)
        )
        story = story_query.scalar_one_or_none()
        
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found"
            )
        
        # Get user-specific data
        user_bookmark = await self.get_user_bookmark(user.id, story_id)
        user_rating = await self.get_user_rating(user.id, story_id)
        
        # Get story statistics
        story_stats = await self.get_story_statistics(story_id)
        
        # Increment view count
        await self.increment_view_count(story_id, user.id)
        
        # Build response
        story_detail = StoryDetail(
            id=story.id,
            title=story.title,
            content=story.content,
            content_preview=story.content[:500] + "..." if len(story.content) > 500 else story.content,
            source=story.source,
            source_url=story.source_url,
            language=story.language,
            author=story.author,
            scare_level=story.scare_level,
            quality_score=story.quality_score,
            word_count=story.word_count,
            reading_time_minutes=story.reading_time_minutes,
            created_at=story.created_at,
            updated_at=story.updated_at,
            tags=[tag.name for tag in story.tags],
            is_bookmarked=bool(user_bookmark),
            user_rating=user_rating.rating if user_rating else None,
            average_rating=story_stats.get("average_rating"),
            view_count=story_stats.get("view_count", 0)
        )
        
        # Cache the result
        await self.cache.set(cache_key, story_detail.dict(), expiry=3600)
        
        return story_detail
    
    async def bookmark_story(self, user_id: str, bookmark_request: BookmarkRequest):
        """Add or remove story bookmark"""
        
        # Check if bookmark already exists
        existing_bookmark = await self.db.execute(
            select(UserBookmark).where(
                UserBookmark.user_id == user_id,
                UserBookmark.story_id == bookmark_request.story_id
            )
        )
        bookmark = existing_bookmark.scalar_one_or_none()
        
        if bookmark:
            # Remove bookmark
            await self.db.delete(bookmark)
            action = "removed"
        else:
            # Add bookmark
            new_bookmark = UserBookmark(
                user_id=user_id,
                story_id=bookmark_request.story_id,
                folder_name=bookmark_request.folder_name,
                created_at=datetime.utcnow()
            )
            self.db.add(new_bookmark)
            action = "added"
        
        await self.db.commit()
        
        # Track analytics event
        await self.analytics.track_user_event(
            user_id=user_id,
            event_type="bookmark_" + action,
            event_data={
                "story_id": bookmark_request.story_id,
                "folder_name": bookmark_request.folder_name
            }
        )
        
        # Clear cache
        await self.cache.delete(f"story_detail:{bookmark_request.story_id}:{user_id}")
        
        return {"action": action, "story_id": bookmark_request.story_id}
    
    async def rate_story(self, user_id: str, rating_request: RatingRequest):
        """Rate a story"""
        
        # Check if rating already exists
        existing_rating = await self.db.execute(
            select(UserRating).where(
                UserRating.user_id == user_id,
                UserRating.story_id == rating_request.story_id
            )
        )
        rating = existing_rating.scalar_one_or_none()
        
        if rating:
            # Update existing rating
            rating.rating = rating_request.rating
            rating.review_text = rating_request.review_text
            rating.updated_at = datetime.utcnow()
            action = "updated"
        else:
            # Create new rating
            rating = UserRating(
                user_id=user_id,
                story_id=rating_request.story_id,
                rating=rating_request.rating,
                review_text=rating_request.review_text,
                created_at=datetime.utcnow()
            )
            self.db.add(rating)
            action = "created"
        
        await self.db.commit()
        
        # Update story average rating
        await self.update_story_average_rating(rating_request.story_id)
        
        # Track analytics event
        await self.analytics.track_user_event(
            user_id=user_id,
            event_type="story_rated",
            event_data={
                "story_id": rating_request.story_id,
                "rating": rating_request.rating,
                "action": action
            }
        )
        
        return {"action": action, "rating": rating_request.rating}

# Content Endpoints
@content_router.get("/stories/{story_id}", response_model=StoryDetail)
async def get_story(
    story_id: str,
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
):
    """Get detailed story information"""
    
    return await content_service.get_story_detail(story_id, current_user)

@content_router.post("/bookmarks")
async def bookmark_story(
    bookmark_request: BookmarkRequest,
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
):
    """Bookmark or unbookmark a story"""
    
    result = await content_service.bookmark_story(current_user.id, bookmark_request)
    
    return APIResponse(success=True, data=result)

@content_router.get("/bookmarks")
async def get_user_bookmarks(
    folder: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
):
    """Get user's bookmarked stories"""
    
    bookmarks = await content_service.get_user_bookmarks(
        user_id=current_user.id,
        folder=folder,
        page=page,
        per_page=per_page
    )
    
    return bookmarks

@content_router.post("/ratings")
async def rate_story(
    rating_request: RatingRequest,
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
):
    """Rate a story"""
    
    result = await content_service.rate_story(current_user.id, rating_request)
    
    return APIResponse(success=True, data=result)

@content_router.get("/recommendations")
async def get_personalized_recommendations(
    count: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends(get_content_service)
):
    """Get personalized story recommendations"""
    
    recommendations = await content_service.get_personalized_recommendations(
        user_id=current_user.id,
        count=count
    )
    
    return APIResponse(success=True, data=recommendations)
```

### WebSocket Real-Time Features:
```python
# WebSocket Manager
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}  # user_id -> connection_ids
        
    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Associate with user
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "message": "Connected to Ghost Story Search Engine",
            "connection_id": connection_id
        }, websocket)
    
    def disconnect(self, connection_id: str, user_id: str):
        """Handle WebSocket disconnection"""
        # Remove connection
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove user association
        if user_id in self.user_connections:
            self.user_connections[user_id] = [
                conn_id for conn_id in self.user_connections[user_id] 
                if conn_id != connection_id
            ]
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
    
    async def send_user_message(self, message: dict, user_id: str):
        """Send message to all user's connections"""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.active_connections:
                    await self.send_personal_message(
                        message, 
                        self.active_connections[connection_id]
                    )
    
    async def broadcast_message(self, message: dict):
        """Broadcast message to all connected users"""
        for websocket in self.active_connections.values():
            await self.send_personal_message(message, websocket)

# WebSocket endpoint
websocket_manager = WebSocketManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    user_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time features"""
    
    # Validate JWT token
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_user_id = payload.get("sub")
        
        if token_user_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    except jwt.PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Generate connection ID
    connection_id = str(uuid.uuid4())
    
    # Connect user
    await websocket_manager.connect(websocket, user_id, connection_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "search_suggestion_request":
                # Handle real-time search suggestions
                suggestions = await get_real_time_suggestions(
                    data.get("query", ""),
                    user_id
                )
                await websocket_manager.send_personal_message({
                    "type": "search_suggestions",
                    "suggestions": suggestions
                }, websocket)
                
            elif message_type == "reading_progress":
                # Handle reading progress updates
                await handle_reading_progress_update(data, user_id)
                
            elif message_type == "heartbeat":
                # Handle heartbeat
                await websocket_manager.send_personal_message({
                    "type": "heartbeat_response",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(connection_id, user_id)
        logger.info(f"WebSocket disconnected: user_id={user_id}, connection_id={connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(connection_id, user_id)

# Real-time notification system
async def send_notification_to_user(user_id: str, notification: dict):
    """Send real-time notification to user"""
    await websocket_manager.send_user_message(notification, user_id)

# Background task for sending notifications
async def process_notification_queue():
    """Process notification queue and send to users"""
    while True:
        try:
            # Get notifications from queue (Redis, database, etc.)
            notifications = await get_pending_notifications()
            
            for notification in notifications:
                await send_notification_to_user(
                    notification["user_id"],
                    notification["message"]
                )
                
            await asyncio.sleep(1)  # Check every second
            
        except Exception as e:
            logger.error(f"Notification processing error: {e}")
            await asyncio.sleep(5)
```

### Admin API Endpoints:
```python
# Admin Router (Protected by admin role)
admin_router = APIRouter()

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Verify user has admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# Admin Models
class ContentModerationRequest(BaseModel):
    action: str = Field(..., regex="^(approve|reject|flag)$")
    reason: Optional[str] = None
    moderator_notes: Optional[str] = None

class SystemStats(BaseModel):
    total_users: int
    active_users_24h: int
    total_stories: int
    stories_added_24h: int
    total_searches_24h: int
    average_response_time: float
    system_health: Dict[str, Any]

# Admin Service
class AdminService:
    def __init__(self, db_session, analytics_service, moderation_service):
        self.db = db_session
        self.analytics = analytics_service
        self.moderation = moderation_service
        
    async def get_system_statistics(self) -> SystemStats:
        """Get comprehensive system statistics"""
        
        current_time = datetime.utcnow()
        yesterday = current_time - timedelta(days=1)
        
        # User statistics
        total_users = await self.get_total_users()
        active_users_24h = await self.get_active_users(yesterday)
        
        # Content statistics
        total_stories = await self.get_total_stories()
        stories_added_24h = await self.get_stories_added_since(yesterday)
        
        # Search statistics
        total_searches_24h = await self.get_searches_since(yesterday)
        
        # Performance statistics
        avg_response_time = await self.get_average_response_time(yesterday)
        
        # System health
        system_health = await self.get_system_health()
        
        return SystemStats(
            total_users=total_users,
            active_users_24h=active_users_24h,
            total_stories=total_stories,
            stories_added_24h=stories_added_24h,
            total_searches_24h=total_searches_24h,
            average_response_time=avg_response_time,
            system_health=system_health
        )

# Admin Endpoints
@admin_router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    admin_user: User = Depends(get_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Get system statistics and health metrics"""
    
    return await admin_service.get_system_statistics()

@admin_router.get("/moderation/queue")
async def get_moderation_queue(
    status: Optional[str] = Query(default="pending", regex="^(pending|in_progress|completed)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    admin_user: User = Depends(get_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Get content moderation queue"""
    
    queue = await admin_service.get_moderation_queue(
        status=status,
        page=page,
        per_page=per_page
    )
    
    return queue

@admin_router.post("/moderation/{content_id}")
async def moderate_content(
    content_id: str,
    moderation_request: ContentModerationRequest,
    admin_user: User = Depends(get_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Process content moderation decision"""
    
    result = await admin_service.process_moderation_decision(
        content_id=content_id,
        moderator_id=admin_user.id,
        action=moderation_request.action,
        reason=moderation_request.reason,
        notes=moderation_request.moderator_notes
    )
    
    return APIResponse(success=True, data=result)
```

### Health Check and Monitoring:
```python
# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Detailed health check with dependency status"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database health check
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Redis health check
    try:
        await redis.ping()
        health_status["checks"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Search engine health check
    try:
        # Perform a simple search test
        search_health = await test_search_engine_health()
        health_status["checks"]["search_engine"] = search_health
        if search_health["status"] != "healthy":
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["search_engine"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    return health_status

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint"""
    
    # This would return metrics in Prometheus format
    # Implementation depends on prometheus_client library
    pass

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    
    # Initialize database connections
    await init_database()
    
    # Initialize Redis connections
    await init_redis()
    
    # Start background tasks
    asyncio.create_task(process_notification_queue())
    
    # Initialize monitoring
    await init_monitoring()
    
    logger.info("Ghost Story Search Engine API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    
    # Close database connections
    await close_database()
    
    # Close Redis connections
    await close_redis()
    
    # Clean up background tasks
    await cleanup_background_tasks()
    
    logger.info("Ghost Story Search Engine API shutdown completed")
```

## USER STORIES:
- As a **mobile app developer**, I can integrate with a well-documented REST API that provides all necessary endpoints for the ghost story search functionality
- As a **frontend developer**, I can use WebSocket connections for real-time search suggestions and user notifications
- As a **user**, I can register, login, search stories, bookmark favorites, and track my reading progress through intuitive API endpoints
- As a **premium subscriber**, I can access advanced features through the API with proper tier enforcement and upgrade prompts
- As a **data analyst**, I can track user behavior and engagement through comprehensive analytics endpoints
- As a **system administrator**, I can monitor API health, performance metrics, and manage content moderation through admin endpoints

## SUCCESS CRITERIA:
- **API Response Time:** <200ms for 95% of requests with proper caching and optimization
- **Authentication Security:** Zero security vulnerabilities with proper JWT implementation and rate limiting
- **API Reliability:** >99.9% uptime with comprehensive error handling and graceful degradation
- **Real-time Performance:** <100ms latency for WebSocket communications and live features
- **Documentation Quality:** Complete OpenAPI documentation with examples and integration guides
- **Scalability:** Support 10,000+ concurrent users with horizontal scaling capabilities
- **Monitoring Coverage:** 100% endpoint coverage with metrics, logging, and alerting

## INTEGRATION POINTS:
- **RAG Search Engine:** Direct integration for contextual search and query processing
- **User Authentication:** JWT-based auth with freemium tier management and usage tracking
- **Content Moderation:** Real-time integration with AI moderation and human review workflows
- **Analytics System:** Comprehensive user behavior tracking and business intelligence
- **WebSocket Manager:** Real-time features for notifications, suggestions, and live updates
- **Background Tasks:** Celery integration for async processing and scheduled jobs
- **Monitoring Systems:** Prometheus metrics, health checks, and performance monitoring

## OTHER CONSIDERATIONS:
- **API Versioning:** Structured versioning strategy with backward compatibility and deprecation cycles
- **Rate Limiting:** Intelligent rate limiting based on user tiers and endpoint sensitivity
- **Security Headers:** Comprehensive security headers including CORS, CSP, and HSTS
- **Input Validation:** Strict input validation and sanitization to prevent injection attacks
- **Error Handling:** Consistent error responses with proper HTTP status codes and error details
- **Performance Optimization:** Database query optimization, caching strategies, and async processing
- **Testing Strategy:** Comprehensive test coverage including unit, integration, and load testing
- **Documentation:** Complete API documentation with examples, SDKs, and integration guides
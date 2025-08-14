"""
Centralized dependency injection for the backend application
Simplifies service instantiation and reduces coupling between modules
"""

from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from .auth import AuthService, get_current_user, get_current_user_optional
from .search import SearchService
from .content import ContentService

# Service dependencies
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get authentication service instance"""
    return AuthService(db)

def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    """Get search service instance"""
    return SearchService(db)

def get_content_service(db: Session = Depends(get_db)) -> ContentService:
    """Get content service instance"""
    return ContentService(db)

# User dependencies (re-exported for convenience)
async def current_user(user: User = Depends(get_current_user)) -> User:
    """Get current authenticated user"""
    return user

async def current_user_optional(user: Optional[User] = Depends(get_current_user_optional)) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    return user

# Combined service and user dependencies
class ServiceContext:
    """Service context with database session and optional user"""
    
    def __init__(
        self,
        db: Session = Depends(get_db),
        user: Optional[User] = Depends(get_current_user_optional)
    ):
        self.db = db
        self.user = user
        self.auth = AuthService(db)
        self.search = SearchService(db)
        self.content = ContentService(db)

def get_service_context() -> ServiceContext:
    """Get service context with all services initialized"""
    return Depends(ServiceContext)
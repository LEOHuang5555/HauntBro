"""
Unified authentication and security service
Consolidated from separate auth and security modules
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.models import User
from infrastructure.database.connection import get_db
from backend.app.core.security import SecurityService

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security_scheme = HTTPBearer(auto_error=False)


class AuthService:
    """Unified authentication and security service"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.security = SecurityService()
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/email and password"""
        try:
            # Query user by username or email
            stmt = select(User).where(
                (User.username == username) | (User.email == username)
            )
            result = self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.info(f"Authentication failed: User '{username}' not found")
                return None
            
            if not user.is_active:
                logger.info(f"Authentication failed: User '{username}' is inactive")
                return None
            
            # Verify password
            if not self.security.verify_password(password, user.password_hash):
                logger.info(f"Authentication failed: Invalid password for user '{username}'")
                return None
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(f"Authentication successful for user '{username}'")
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.db.rollback()
            return None
    
    async def create_user(
        self, 
        username: str, 
        email: str, 
        password: str
    ) -> User:
        """Create a new user"""
        try:
            # Check if username exists
            stmt = select(User).where(User.username == username)
            existing_user = self.db.execute(stmt).scalar_one_or_none()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
            
            # Check if email exists
            stmt = select(User).where(User.email == email)
            existing_email = self.db.execute(stmt).scalar_one_or_none()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Hash password
            password_hash = self.security.hash_password(password)
            
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                is_active=True
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Created new user: '{username}' ({email})")
            return user
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"User creation error: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            stmt = select(User).where(User.id == user_id)
            result = self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            stmt = select(User).where(User.username == username)
            result = self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username '{username}': {e}")
            return None
    
    async def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user password"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            password_hash = self.security.hash_password(new_password)
            user.password_hash = password_hash
            user.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            logger.info(f"Password updated for user ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {e}")
            self.db.rollback()
            return False
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            logger.info(f"Deactivated user ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            self.db.rollback()
            return False


# Dependency to get current user from JWT token
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify token
        payload = SecurityService().verify_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # Get user from database
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


# Dependency to get current user (optional)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    try:
        if not credentials:
            return None
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# Dependency to get authentication service
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get authentication service instance"""
    return AuthService(db)
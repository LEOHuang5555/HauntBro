"""
Authentication endpoints for user registration, login, and token management
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from infrastructure.database.connection import get_db
from backend.app.core.auth import AuthService, get_current_user, get_auth_service
from backend.app.core.security import security_service
from backend.app.core.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    PasswordChangeRequest,
    UserResponse,
    MessageResponse,
    ErrorResponse
)
from backend.app.core.config import backend_config
from backend.app.core.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Get rate limiter if available
limiter = get_rate_limiter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user account with username, email, and password"
)
async def register_user(
    user_data: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    request: Request = None
) -> Any:
    """Register a new user"""
    try:
        # Validate password strength
        if len(user_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Create user
        user = await auth_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        
        logger.info(f"New user registered: {user.username}")
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user and return JWT tokens"
)
async def login(
    login_data: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """Authenticate user and return JWT tokens"""
    try:
        # Authenticate user
        user = await auth_service.authenticate_user(
            username=login_data.username,
            password=login_data.password
        )
        
        if not user:
            logger.warning(f"Failed login attempt for: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        
        # Create tokens
        access_token_expires = timedelta(
            minutes=backend_config.security.access_token_expire_minutes
        )
        
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email
        }
        
        access_token = security_service.create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        refresh_token = security_service.create_refresh_token(
            data={"sub": str(user.id), "username": user.username}
        )
        
        logger.info(f"Successful login for user: {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=backend_config.security.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Refresh access token using refresh token"
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = security_service.verify_token(
            refresh_data.refresh_token,
            expected_type="refresh_token"
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Get user from database
        user = await auth_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        
        # Create new access token
        access_token_expires = timedelta(
            minutes=backend_config.security.access_token_expire_minutes
        )
        
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email
        }
        
        access_token = security_service.create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        # Create new refresh token
        refresh_token = security_service.create_refresh_token(
            data={"sub": str(user.id), "username": user.username}
        )
        
        logger.info(f"Token refreshed for user: {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=backend_config.security.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user information"
)
async def get_current_user_info(
    current_user = Depends(get_current_user)
) -> Any:
    """Get current authenticated user information"""
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change current user's password"
)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """Change current user's password"""
    try:
        # Verify current password
        if not security_service.verify_password(
            password_data.current_password, 
            current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password
        if len(password_data.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )
        
        # Update password
        success = await auth_service.update_user_password(
            str(current_user.id),
            password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        logger.info(f"Password changed for user: {current_user.username}")
        
        return MessageResponse(
            message="Password changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
    description="Logout current user (token invalidation placeholder)"
)
async def logout(
    current_user = Depends(get_current_user)
) -> Any:
    """Logout current user"""
    # In a production environment, you would:
    # 1. Add token to Redis blacklist
    # 2. Implement token revocation
    # For now, we'll just return a success message
    
    logger.info(f"User logged out: {current_user.username}")
    
    return MessageResponse(
        message="Logged out successfully"
    )


@router.post(
    "/verify-token",
    response_model=UserResponse,
    summary="Verify token",
    description="Verify JWT token and return user information"
)
async def verify_token(
    current_user = Depends(get_current_user)
) -> Any:
    """Verify JWT token and return user information"""
    return UserResponse.model_validate(current_user)
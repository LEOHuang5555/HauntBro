"""
Authentication models and utilities for HauntBro.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from dotenv import load_dotenv

from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from database.models import User

# Load environment variables
load_dotenv()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings from environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-for-development-only")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


class UserCreate(BaseModel):
    """User creation schema."""
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login schema."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data schema."""
    username: Optional[str] = None


class AuthManager:
    """Authentication manager for user operations."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """Verify JWT token and return token data."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return TokenData(username=username)
        except JWTError:
            return None
    
    @staticmethod
    def create_user(user_data: UserCreate) -> dict:
        """Create a new user with hashed password."""
        return {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": AuthManager.get_password_hash(user_data.password)
        }
    
    @staticmethod
    def authenticate_user(username: str, password: str, user: User) -> bool:
        """Authenticate user with username and password."""
        if not user:
            return False
        if not AuthManager.verify_password(password, user.password_hash):
            return False
        return True
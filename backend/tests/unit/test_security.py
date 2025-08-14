"""
Unit tests for security service
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from backend.app.core.security import security_service, SecurityService
from infrastructure.database.models import User


@pytest.mark.unit
class TestSecurityService:
    """Test security service functionality"""

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = security_service.hash_password(password)
        
        assert hashed != password
        assert security_service.verify_password(password, hashed) is True
        assert security_service.verify_password("wrongpassword", hashed) is False
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser"}
        token = security_service.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = security_service.create_access_token(data, expires_delta)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        data = {"sub": "testuser"}
        token = security_service.create_access_token(data)
        
        payload = security_service.verify_token(token)
        assert payload["sub"] == "testuser"
        assert "exp" in payload
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token"""
        from fastapi import HTTPException
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException):
            security_service.verify_token(invalid_token)
    
    def test_verify_token_expired(self):
        """Test token verification with expired token"""
        from fastapi import HTTPException
        data = {"sub": "testuser"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = security_service.create_access_token(data, expires_delta)
        
        with pytest.raises(HTTPException):
            security_service.verify_token(token)
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "testuser", "type": "refresh"}
        token = security_service.create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_token_payload(self):
        """Test token payload decoding without verification"""
        data = {"sub": "testuser", "role": "user"}
        token = security_service.create_access_token(data)
        
        payload = security_service.decode_token_payload(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["role"] == "user"
    
    def test_security_service_initialization(self):
        """Test security service initialization"""
        service = SecurityService()
        
        assert hasattr(service, 'secret_key')
        assert hasattr(service, 'algorithm')
        assert hasattr(service, 'access_token_expire_minutes')
        assert hasattr(service, 'refresh_token_expire_days')
    
    def test_password_strength_validation(self):
        """Test different password strengths"""
        # Strong passwords should hash successfully
        strong_passwords = [
            "MyStrongPassword123!",
            "ComplexP@ssw0rd",
            "SuperSecure2023#"
        ]
        
        for password in strong_passwords:
            hashed = security_service.hash_password(password)
            assert security_service.verify_password(password, hashed) is True
        
        # Weak passwords should still work (validation is done at API level)
        weak_passwords = ["123", "password", "abc"]
        
        for password in weak_passwords:
            hashed = security_service.hash_password(password)
            assert security_service.verify_password(password, hashed) is True
    
    def test_token_data_integrity(self):
        """Test that token data is preserved correctly"""
        original_data = {
            "sub": "testuser",
            "user_id": "123",
            "role": "user",
            "permissions": ["read", "write"]
        }
        
        token = security_service.create_access_token(original_data)
        decoded_data = security_service.verify_token(token)
        
        assert decoded_data["sub"] == original_data["sub"]
        assert decoded_data["user_id"] == original_data["user_id"]
        assert decoded_data["role"] == original_data["role"]
        assert decoded_data["permissions"] == original_data["permissions"]
    
    def test_multiple_tokens_different_users(self):
        """Test creating tokens for different users"""
        users = ["user1", "user2", "user3"]
        tokens = {}
        
        for user in users:
            data = {"sub": user}
            token = security_service.create_access_token(data)
            tokens[user] = token
        
        # Verify each token decodes to the correct user
        for user, token in tokens.items():
            decoded = security_service.verify_token(token)
            assert decoded["sub"] == user
    
    def test_token_expiration_timing(self):
        """Test token expiration timing"""
        # Create token with very short expiration
        short_expiry = timedelta(seconds=1)
        data = {"sub": "testuser"}
        token = security_service.create_access_token(data, short_expiry)
        
        # Should be valid immediately
        payload = security_service.verify_token(token)
        assert payload is not None
        
        # After expiration, should be invalid (we can't easily test this without waiting)
        # This is more of a conceptual test
        assert "exp" in payload
        assert payload["exp"] > datetime.utcnow().timestamp()
"""
Authentication API tests
"""

import pytest
from httpx import AsyncClient
from backend.app.core.security import security_service


@pytest.mark.api
@pytest.mark.auth
class TestAuthAPI:
    """Test authentication endpoints"""

    async def test_register_user_success(self, client: AsyncClient):
        """Test successful user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned
    
    async def test_register_user_duplicate_username(self, client: AsyncClient, test_user):
        """Test registration with duplicate username"""
        user_data = {
            "username": test_user.username,
            "email": "different@example.com",
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    async def test_register_user_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email"""
        user_data = {
            "username": "differentuser",
            "email": test_user.email,
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    async def test_register_user_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        user_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
    
    async def test_register_user_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"  # Too short
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422
    
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login"""
        login_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == test_user.username
    
    async def test_login_invalid_username(self, client: AsyncClient):
        """Test login with invalid username"""
        login_data = {
            "username": "nonexistentuser",
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        """Test login with invalid password"""
        login_data = {
            "username": test_user.username,
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    async def test_login_inactive_user(self, client: AsyncClient, test_user, test_db):
        """Test login with inactive user"""
        # Deactivate user
        test_user.is_active = False
        test_db.commit()
        
        login_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        assert "Inactive user" in response.json()["detail"]
    
    async def test_get_current_user_success(self, client: AsyncClient, auth_headers):
        """Test getting current user info"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
    
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting current user without token"""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
    
    async def test_refresh_token_success(self, client: AsyncClient, auth_headers):
        """Test token refresh"""
        response = await client.post("/api/v1/auth/refresh", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_refresh_token_no_auth(self, client: AsyncClient):
        """Test token refresh without authentication"""
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 401
    
    async def test_logout_success(self, client: AsyncClient, auth_headers):
        """Test logout"""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "logged out successfully" in data["message"]
    
    async def test_logout_no_auth(self, client: AsyncClient):
        """Test logout without authentication"""
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401
    
    async def test_update_profile_success(self, client: AsyncClient, auth_headers):
        """Test profile update"""
        update_data = {
            "email": "updated@example.com"
        }
        
        response = await client.put("/api/v1/auth/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["email"] == update_data["email"]
    
    async def test_update_profile_duplicate_email(self, client: AsyncClient, auth_headers, test_admin_user):
        """Test profile update with duplicate email"""
        update_data = {
            "email": test_admin_user.email
        }
        
        response = await client.put("/api/v1/auth/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]
    
    async def test_change_password_success(self, client: AsyncClient, auth_headers, test_user):
        """Test password change"""
        change_data = {
            "current_password": "testpassword123",
            "new_password": "newtestpassword123"
        }
        
        response = await client.post("/api/v1/auth/change-password", json=change_data, headers=auth_headers)
        assert response.status_code == 200
        
        # Verify password was actually changed
        assert security_service.verify_password("newtestpassword123", test_user.hashed_password)
    
    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers):
        """Test password change with wrong current password"""
        change_data = {
            "current_password": "wrongpassword",
            "new_password": "newtestpassword123"
        }
        
        response = await client.post("/api/v1/auth/change-password", json=change_data, headers=auth_headers)
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]
    
    async def test_auth_health_check(self, client: AsyncClient):
        """Test auth service health check"""
        response = await client.get("/api/v1/auth/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "capabilities" in data
        assert data["capabilities"]["user_registration"] is True
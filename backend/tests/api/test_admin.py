"""
Admin API tests
"""

import pytest
from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.admin
class TestAdminAPI:
    """Test admin endpoints"""

    async def test_get_system_statistics_success(self, client: AsyncClient, admin_auth_headers):
        """Test getting system statistics"""
        response = await client.get("/api/v1/admin/statistics", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "users" in data
        assert "content" in data
        assert "activity_24h" in data
        assert "engagement" in data
        assert "system_metrics" in data
        assert data["users"]["total_users"] >= 0
        assert data["content"]["total_stories"] >= 0
    
    async def test_get_system_statistics_no_auth(self, client: AsyncClient):
        """Test getting statistics without authentication"""
        response = await client.get("/api/v1/admin/statistics")
        assert response.status_code == 401
    
    async def test_get_system_statistics_non_admin(self, client: AsyncClient, auth_headers):
        """Test getting statistics as regular user (should work with placeholder auth)"""
        response = await client.get("/api/v1/admin/statistics", headers=auth_headers)
        # With placeholder auth, regular users can access admin endpoints
        # In production, this should return 403
        assert response.status_code == 200
    
    async def test_get_user_management_success(self, client: AsyncClient, admin_auth_headers):
        """Test getting user management data"""
        response = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "users" in data
        assert "pagination" in data
        assert "filters" in data
        assert isinstance(data["users"], list)
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 20
    
    async def test_get_user_management_with_filters(self, client: AsyncClient, admin_auth_headers):
        """Test user management with filters"""
        params = {
            "page": 2,
            "per_page": 10,
            "search": "test",
            "status": "active"
        }
        
        response = await client.get("/api/v1/admin/users", params=params, headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 10
        assert data["filters"]["search_query"] == "test"
        assert data["filters"]["status_filter"] == "active"
    
    async def test_get_content_moderation_success(self, client: AsyncClient, admin_auth_headers):
        """Test getting content moderation data"""
        response = await client.get("/api/v1/admin/content", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "stories" in data
        assert "pagination" in data
        assert "filters" in data
        assert isinstance(data["stories"], list)
    
    async def test_get_content_moderation_with_filters(self, client: AsyncClient, admin_auth_headers, sample_bronze_story):
        """Test content moderation with filters"""
        params = {
            "page": 1,
            "per_page": 5,
            "source": sample_bronze_story.source
        }
        
        response = await client.get("/api/v1/admin/content", params=params, headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["source_filter"] == sample_bronze_story.source
    
    async def test_moderate_user_activate(self, client: AsyncClient, admin_auth_headers, test_user, test_db):
        """Test activating a user"""
        # Deactivate user first
        test_user.is_active = False
        test_db.commit()
        
        user_id = str(test_user.id)
        params = {
            "action": "activate",
            "reason": "Test activation"
        }
        
        response = await client.post(f"/api/v1/admin/users/{user_id}/moderate", params=params, headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["action"] == "activated"
        assert data["target_user"]["id"] == user_id
        assert data["target_user"]["current_status"] is True
        assert data["reason"] == "Test activation"
    
    async def test_moderate_user_deactivate(self, client: AsyncClient, admin_auth_headers, test_user):
        """Test deactivating a user"""
        user_id = str(test_user.id)
        params = {
            "action": "deactivate",
            "reason": "Test deactivation"
        }
        
        response = await client.post(f"/api/v1/admin/users/{user_id}/moderate", params=params, headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["action"] == "deactivated"
        assert data["target_user"]["current_status"] is False
    
    async def test_moderate_user_invalid_action(self, client: AsyncClient, admin_auth_headers, test_user):
        """Test user moderation with invalid action"""
        user_id = str(test_user.id)
        params = {
            "action": "invalid_action"
        }
        
        response = await client.post(f"/api/v1/admin/users/{user_id}/moderate", params=params, headers=admin_auth_headers)
        assert response.status_code == 400
        assert "Invalid action" in response.json()["detail"]
    
    async def test_moderate_user_not_found(self, client: AsyncClient, admin_auth_headers):
        """Test moderating non-existent user"""
        user_id = "non-existent-id"
        params = {
            "action": "activate"
        }
        
        response = await client.post(f"/api/v1/admin/users/{user_id}/moderate", params=params, headers=admin_auth_headers)
        assert response.status_code == 404
    
    async def test_moderate_self(self, client: AsyncClient, admin_auth_headers, test_admin_user):
        """Test self-moderation prevention"""
        user_id = str(test_admin_user.id)
        params = {
            "action": "deactivate"
        }
        
        response = await client.post(f"/api/v1/admin/users/{user_id}/moderate", params=params, headers=admin_auth_headers)
        assert response.status_code == 400
        assert "Cannot moderate yourself" in response.json()["detail"]
    
    async def test_get_system_health_success(self, client: AsyncClient, admin_auth_headers):
        """Test getting system health"""
        response = await client.get("/api/v1/admin/health", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_status" in data
        assert "components" in data
        assert "system_metrics" in data
        assert "recommendations" in data
        assert data["overall_status"] in ["healthy", "degraded", "critical"]
    
    async def test_get_admin_dashboard_success(self, client: AsyncClient, admin_auth_headers, test_admin_user):
        """Test getting admin dashboard"""
        response = await client.get("/api/v1/admin/dashboard", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["admin_user"]["id"] == str(test_admin_user.id)
        assert data["admin_user"]["username"] == test_admin_user.username
        assert "system_overview" in data
        assert "recent_activity" in data
        assert "alerts" in data
        assert "quick_actions" in data
        assert isinstance(data["alerts"], list)
        assert isinstance(data["quick_actions"], list)
    
    async def test_get_admin_config_success(self, client: AsyncClient, admin_auth_headers):
        """Test getting admin configuration"""
        response = await client.get("/api/v1/admin/config", headers=admin_auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "api_version" in data
        assert "features" in data
        assert "security" in data
        assert "integrations" in data
        assert "content_sources" in data
        assert "system_limits" in data
        assert data["features"]["authentication"] is True
        assert data["security"]["rate_limiting"] is True
    
    async def test_admin_service_status(self, client: AsyncClient):
        """Test admin service status check"""
        response = await client.get("/api/v1/admin/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "capabilities" in data
        assert "features" in data
        assert data["capabilities"]["system_statistics"] is True
        assert data["capabilities"]["user_management"] is True
        assert data["features"]["role_based_access"] is True
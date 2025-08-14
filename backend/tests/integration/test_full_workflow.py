"""
Integration tests for full user workflows
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.integration
class TestFullWorkflow:
    """Test complete user workflows end-to-end"""

    async def test_user_registration_to_search_workflow(self, client: AsyncClient, mock_embedding_manager):
        """Test complete workflow: register user -> login -> search stories"""
        
        # Step 1: Register user
        user_data = {
            "username": "workflowuser",
            "email": "workflow@example.com",
            "password": "workflowpassword123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        user_id = response.json()["id"]
        
        # Step 2: Login
        login_data = {
            "username": "workflowuser",
            "password": "workflowpassword123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Search stories
        with patch('backend.app.core.search.embedding_manager', mock_embedding_manager):
            search_params = {"query": "ghost story", "limit": 5}
            response = await client.get("/api/v1/search/stories", params=search_params, headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "results" in data
            assert data["query_info"]["query"] == "ghost story"
    
    async def test_content_interaction_workflow(self, client: AsyncClient, sample_bronze_story):
        """Test content interaction workflow: register -> login -> favorite -> rate -> view history"""
        
        # Step 1: Register and login
        user_data = {
            "username": "contentuser",
            "email": "content@example.com",
            "password": "contentpassword123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_data = {
            "username": "contentuser",
            "password": "contentpassword123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        story_id = str(sample_bronze_story.id)
        
        # Step 2: Get story details
        response = await client.get(f"/api/v1/content/stories/{story_id}", headers=headers)
        assert response.status_code == 200
        
        # Step 3: Add to favorites
        response = await client.post(f"/api/v1/content/stories/{story_id}/favorite", headers=headers)
        assert response.status_code == 200
        
        # Step 4: Rate story
        response = await client.post(f"/api/v1/content/stories/{story_id}/rating?rating=5", headers=headers)
        assert response.status_code == 200
        
        # Step 5: Check favorites
        response = await client.get("/api/v1/content/favorites", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["favorites"]) == 1
        assert data["favorites"][0]["story"]["id"] == story_id
        
        # Step 6: Check ratings
        response = await client.get("/api/v1/content/ratings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["ratings"]) == 1
        assert data["ratings"][0]["rating"] == 5
        
        # Step 7: View dashboard
        response = await client.get("/api/v1/content/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_favorites"] == 1
        assert data["summary"]["total_ratings"] == 1
    
    async def test_admin_workflow(self, client: AsyncClient, sample_bronze_story):
        """Test admin workflow: login as admin -> view statistics -> moderate user"""
        
        # Step 1: Register admin user
        admin_data = {
            "username": "adminworkflow",
            "email": "adminworkflow@example.com",
            "password": "adminpassword123"
        }
        
        response = await client.post("/api/v1/auth/register", json=admin_data)
        assert response.status_code == 201
        
        # Step 2: Login as admin
        login_data = {
            "username": "adminworkflow",
            "password": "adminpassword123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: View system statistics
        response = await client.get("/api/v1/admin/statistics", headers=headers)
        assert response.status_code == 200
        
        # Step 4: View system health
        response = await client.get("/api/v1/admin/health", headers=headers)
        assert response.status_code == 200
        
        # Step 5: View admin dashboard
        response = await client.get("/api/v1/admin/dashboard", headers=headers)
        assert response.status_code == 200
        
        # Step 6: View user management
        response = await client.get("/api/v1/admin/users", headers=headers)
        assert response.status_code == 200
        
        # Step 7: View content moderation
        response = await client.get("/api/v1/admin/content", headers=headers)
        assert response.status_code == 200
    
    async def test_authentication_error_handling(self, client: AsyncClient):
        """Test authentication error handling throughout the system"""
        
        # Test accessing protected endpoints without auth
        protected_endpoints = [
            ("/api/v1/auth/me", "GET"),
            ("/api/v1/search/stories?query=test", "GET"),
            ("/api/v1/content/favorites", "GET"),
            ("/api/v1/admin/statistics", "GET"),
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "POST":
                response = await client.post(endpoint)
            
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
        
        # Test with invalid token
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = await client.get(endpoint, headers=invalid_headers)
            elif method == "POST":
                response = await client.post(endpoint, headers=invalid_headers)
            
            assert response.status_code == 401, f"Endpoint {endpoint} should reject invalid tokens"
    
    async def test_data_consistency_workflow(self, client: AsyncClient, sample_bronze_story):
        """Test data consistency across different API calls"""
        
        # Register and login user
        user_data = {
            "username": "consistencyuser",
            "email": "consistency@example.com",
            "password": "consistencypass123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        user_info = response.json()
        
        login_data = {
            "username": "consistencyuser",
            "password": "consistencypass123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        story_id = str(sample_bronze_story.id)
        
        # Add story to favorites
        response = await client.post(f"/api/v1/content/stories/{story_id}/favorite", headers=headers)
        assert response.status_code == 200
        
        # Check story details show it's favorited
        response = await client.get(f"/api/v1/content/stories/{story_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_data"]["is_favorited"] is True
        
        # Check favorites list contains the story
        response = await client.get("/api/v1/content/favorites", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["favorites"]) == 1
        assert data["favorites"][0]["story"]["id"] == story_id
        
        # Check dashboard reflects the favorite
        response = await client.get("/api/v1/content/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_favorites"] == 1
        
        # Remove from favorites
        response = await client.delete(f"/api/v1/content/stories/{story_id}/favorite", headers=headers)
        assert response.status_code == 200
        
        # Verify all endpoints reflect the removal
        response = await client.get(f"/api/v1/content/stories/{story_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_data"]["is_favorited"] is False
        
        response = await client.get("/api/v1/content/favorites", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["favorites"]) == 0
        
        response = await client.get("/api/v1/content/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_favorites"] == 0
    
    @pytest.mark.slow
    async def test_concurrent_user_actions(self, client: AsyncClient, sample_bronze_story):
        """Test concurrent user actions for race conditions"""
        import asyncio
        
        # Register user
        user_data = {
            "username": "concurrentuser",
            "email": "concurrent@example.com",
            "password": "concurrentpass123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_data = {
            "username": "concurrentuser",
            "password": "concurrentpass123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        story_id = str(sample_bronze_story.id)
        
        # Concurrent favorite/unfavorite operations
        async def toggle_favorite():
            await client.post(f"/api/v1/content/stories/{story_id}/favorite", headers=headers)
            await client.delete(f"/api/v1/content/stories/{story_id}/favorite", headers=headers)
        
        # Run multiple concurrent operations
        tasks = [toggle_favorite() for _ in range(5)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check final state is consistent
        response = await client.get("/api/v1/content/favorites", headers=headers)
        assert response.status_code == 200
        # Final state should be consistent (either favorited or not)
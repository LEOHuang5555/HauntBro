"""
Content management API tests
"""

import pytest
from httpx import AsyncClient
from infrastructure.database.models import UserFavorite, StoryRating


@pytest.mark.api
class TestContentAPI:
    """Test content management endpoints"""

    async def test_get_story_details_success(self, client: AsyncClient, sample_bronze_story):
        """Test getting story details without authentication"""
        story_id = str(sample_bronze_story.id)
        
        response = await client.get(f"/api/v1/content/stories/{story_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == story_id
        assert data["title"] == sample_bronze_story.title
        assert data["content"] == sample_bronze_story.content
        assert data["author"] == sample_bronze_story.author
        assert data["source"] == sample_bronze_story.source
        assert "user_data" in data
        assert "content_preview" in data
    
    async def test_get_story_details_with_auth(self, client: AsyncClient, auth_headers, sample_bronze_story, test_user, test_db):
        """Test getting story details with authentication"""
        story_id = str(sample_bronze_story.id)
        
        # Add a favorite for this user
        favorite = UserFavorite(user_id=str(test_user.id), story_id=story_id)
        test_db.add(favorite)
        test_db.commit()
        
        response = await client.get(f"/api/v1/content/stories/{story_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["user_data"]["is_favorited"] is True
    
    async def test_get_story_details_not_found(self, client: AsyncClient):
        """Test getting details for non-existent story"""
        story_id = "non-existent-id"
        
        response = await client.get(f"/api/v1/content/stories/{story_id}")
        assert response.status_code == 404
    
    async def test_get_user_favorites_success(self, client: AsyncClient, auth_headers, test_user, sample_bronze_story, test_db):
        """Test getting user favorites"""
        # Add favorite
        favorite = UserFavorite(user_id=str(test_user.id), story_id=str(sample_bronze_story.id))
        test_db.add(favorite)
        test_db.commit()
        
        response = await client.get("/api/v1/content/favorites", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "favorites" in data
        assert "pagination" in data
        assert len(data["favorites"]) == 1
        assert data["favorites"][0]["story"]["id"] == str(sample_bronze_story.id)
    
    async def test_get_user_favorites_no_auth(self, client: AsyncClient):
        """Test getting favorites without authentication"""
        response = await client.get("/api/v1/content/favorites")
        assert response.status_code == 401
    
    async def test_get_user_favorites_pagination(self, client: AsyncClient, auth_headers):
        """Test favorites pagination"""
        response = await client.get("/api/v1/content/favorites?page=1&per_page=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 5
    
    async def test_add_to_favorites_success(self, client: AsyncClient, auth_headers, sample_bronze_story):
        """Test adding story to favorites"""
        story_id = str(sample_bronze_story.id)
        
        response = await client.post(f"/api/v1/content/stories/{story_id}/favorite", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "added to favorites" in data["message"]
    
    async def test_add_to_favorites_already_favorited(self, client: AsyncClient, auth_headers, sample_bronze_story, test_user, test_db):
        """Test adding already favorited story"""
        story_id = str(sample_bronze_story.id)
        
        # Add favorite first
        favorite = UserFavorite(user_id=str(test_user.id), story_id=story_id)
        test_db.add(favorite)
        test_db.commit()
        
        response = await client.post(f"/api/v1/content/stories/{story_id}/favorite", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "already in favorites" in data["message"]
    
    async def test_add_to_favorites_not_found(self, client: AsyncClient, auth_headers):
        """Test adding non-existent story to favorites"""
        story_id = "non-existent-id"
        
        response = await client.post(f"/api/v1/content/stories/{story_id}/favorite", headers=auth_headers)
        assert response.status_code == 404
    
    async def test_remove_from_favorites_success(self, client: AsyncClient, auth_headers, sample_bronze_story, test_user, test_db):
        """Test removing story from favorites"""
        story_id = str(sample_bronze_story.id)
        
        # Add favorite first
        favorite = UserFavorite(user_id=str(test_user.id), story_id=story_id)
        test_db.add(favorite)
        test_db.commit()
        
        response = await client.delete(f"/api/v1/content/stories/{story_id}/favorite", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "removed from favorites" in data["message"]
    
    async def test_remove_from_favorites_not_favorited(self, client: AsyncClient, auth_headers, sample_bronze_story):
        """Test removing non-favorited story"""
        story_id = str(sample_bronze_story.id)
        
        response = await client.delete(f"/api/v1/content/stories/{story_id}/favorite", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "was not in favorites" in data["message"]
    
    async def test_rate_story_success(self, client: AsyncClient, auth_headers, sample_bronze_story):
        """Test rating a story"""
        story_id = str(sample_bronze_story.id)
        
        response = await client.post(f"/api/v1/content/stories/{story_id}/rating?rating=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["action"] == "created"
        assert data["rating"] == 5
        assert data["story_id"] == story_id
    
    async def test_rate_story_update_existing(self, client: AsyncClient, auth_headers, sample_bronze_story, test_user, test_db):
        """Test updating existing story rating"""
        story_id = str(sample_bronze_story.id)
        
        # Add existing rating
        rating = StoryRating(user_id=str(test_user.id), story_id=story_id, rating=3)
        test_db.add(rating)
        test_db.commit()
        
        response = await client.post(f"/api/v1/content/stories/{story_id}/rating?rating=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["action"] == "updated"
        assert data["rating"] == 5
        assert data["previous_rating"] == 3
    
    async def test_rate_story_invalid_rating(self, client: AsyncClient, auth_headers, sample_bronze_story):
        """Test rating story with invalid rating"""
        story_id = str(sample_bronze_story.id)
        
        response = await client.post(f"/api/v1/content/stories/{story_id}/rating?rating=6", headers=auth_headers)
        assert response.status_code == 422  # Validation error
    
    async def test_rate_story_not_found(self, client: AsyncClient, auth_headers):
        """Test rating non-existent story"""
        story_id = "non-existent-id"
        
        response = await client.post(f"/api/v1/content/stories/{story_id}/rating?rating=5", headers=auth_headers)
        assert response.status_code == 404
    
    async def test_get_user_ratings_success(self, client: AsyncClient, auth_headers, test_user, sample_bronze_story, test_db):
        """Test getting user ratings"""
        # Add rating
        rating = StoryRating(user_id=str(test_user.id), story_id=str(sample_bronze_story.id), rating=4)
        test_db.add(rating)
        test_db.commit()
        
        response = await client.get("/api/v1/content/ratings", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "ratings" in data
        assert "pagination" in data
        assert len(data["ratings"]) == 1
        assert data["ratings"][0]["rating"] == 4
    
    async def test_get_reading_history_success(self, client: AsyncClient, auth_headers):
        """Test getting reading history"""
        response = await client.get("/api/v1/content/reading-history", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "reading_history" in data
        assert "pagination" in data
    
    async def test_get_content_dashboard_success(self, client: AsyncClient, auth_headers, test_user):
        """Test getting content dashboard"""
        response = await client.get("/api/v1/content/dashboard", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["username"] == test_user.username
        assert "summary" in data
        assert "recent_activity" in data
        assert "preferences" in data
        assert data["summary"]["total_favorites"] >= 0
        assert data["summary"]["total_ratings"] >= 0
        assert data["summary"]["total_reading_sessions"] >= 0
    
    async def test_content_health_check(self, client: AsyncClient):
        """Test content service health check"""
        response = await client.get("/api/v1/content/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "capabilities" in data
        assert data["capabilities"]["story_details"] is True
        assert data["capabilities"]["user_favorites"] is True
        assert data["capabilities"]["story_ratings"] is True
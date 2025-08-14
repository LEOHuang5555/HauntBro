"""
Search API tests
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.api
class TestSearchAPI:
    """Test search endpoints"""

    async def test_search_stories_success(self, client: AsyncClient, auth_headers, mock_embedding_manager):
        """Test successful story search"""
        with patch('backend.app.core.search.embedding_manager', mock_embedding_manager):
            search_params = {
                "query": "ghost story",
                "limit": 10
            }
            
            response = await client.get("/api/v1/search/stories", params=search_params, headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "results" in data
            assert "total_count" in data
            assert "query_info" in data
            assert data["query_info"]["query"] == "ghost story"
    
    async def test_search_stories_no_auth(self, client: AsyncClient):
        """Test search without authentication"""
        search_params = {
            "query": "ghost story",
            "limit": 10
        }
        
        response = await client.get("/api/v1/search/stories", params=search_params)
        assert response.status_code == 401
    
    async def test_search_stories_empty_query(self, client: AsyncClient, auth_headers):
        """Test search with empty query"""
        search_params = {
            "query": "",
            "limit": 10
        }
        
        response = await client.get("/api/v1/search/stories", params=search_params, headers=auth_headers)
        assert response.status_code == 422  # Validation error
    
    async def test_search_stories_with_filters(self, client: AsyncClient, auth_headers, mock_embedding_manager):
        """Test search with filters"""
        with patch('backend.app.core.search.embedding_manager', mock_embedding_manager):
            search_params = {
                "query": "haunted house",
                "limit": 5,
                "source": "reddit_ghoststories",
                "language": "en",
                "min_rating": 4.0
            }
            
            response = await client.get("/api/v1/search/stories", params=search_params, headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["query_info"]["filters"]["source"] == "reddit_ghoststories"
            assert data["query_info"]["filters"]["language"] == "en"
            assert data["query_info"]["filters"]["min_rating"] == 4.0
    
    async def test_search_stories_pagination(self, client: AsyncClient, auth_headers, mock_embedding_manager):
        """Test search with pagination"""
        with patch('backend.app.core.search.embedding_manager', mock_embedding_manager):
            search_params = {
                "query": "ghost",
                "limit": 5,
                "offset": 10
            }
            
            response = await client.get("/api/v1/search/stories", params=search_params, headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["query_info"]["limit"] == 5
            assert data["query_info"]["offset"] == 10
    
    async def test_search_suggestions_success(self, client: AsyncClient, auth_headers):
        """Test search suggestions"""
        search_params = {
            "partial_query": "ghost"
        }
        
        response = await client.get("/api/v1/search/suggestions", params=search_params, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
    
    async def test_search_suggestions_no_auth(self, client: AsyncClient):
        """Test search suggestions without authentication"""
        search_params = {
            "partial_query": "ghost"
        }
        
        response = await client.get("/api/v1/search/suggestions", params=search_params)
        assert response.status_code == 401
    
    async def test_search_advanced_success(self, client: AsyncClient, auth_headers, mock_embedding_manager):
        """Test advanced search"""
        with patch('backend.app.core.search.embedding_manager', mock_embedding_manager):
            search_data = {
                "query": "haunted mansion",
                "search_type": "semantic",
                "filters": {
                    "sources": ["reddit_ghoststories", "ptt_marvel"],
                    "date_range": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-12-31"
                    },
                    "word_count_range": {
                        "min_words": 100,
                        "max_words": 5000
                    },
                    "tags": ["horror", "supernatural"]
                },
                "sort_by": "relevance",
                "limit": 20
            }
            
            response = await client.post("/api/v1/search/advanced", json=search_data, headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "results" in data
            assert "search_metadata" in data
            assert data["search_metadata"]["search_type"] == "semantic"
    
    async def test_search_advanced_no_auth(self, client: AsyncClient):
        """Test advanced search without authentication"""
        search_data = {
            "query": "ghost story",
            "search_type": "semantic"
        }
        
        response = await client.post("/api/v1/search/advanced", json=search_data)
        assert response.status_code == 401
    
    async def test_search_similar_stories_success(self, client: AsyncClient, auth_headers, sample_bronze_story, mock_embedding_manager):
        """Test finding similar stories"""
        with patch('backend.app.core.search.embedding_manager', mock_embedding_manager):
            story_id = str(sample_bronze_story.id)
            search_params = {
                "limit": 5
            }
            
            response = await client.get(f"/api/v1/search/similar/{story_id}", params=search_params, headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "similar_stories" in data
            assert "reference_story" in data
            assert data["reference_story"]["id"] == story_id
    
    async def test_search_similar_stories_not_found(self, client: AsyncClient, auth_headers):
        """Test finding similar stories for non-existent story"""
        story_id = "non-existent-id"
        
        response = await client.get(f"/api/v1/search/similar/{story_id}", headers=auth_headers)
        assert response.status_code == 404
    
    async def test_search_by_tags_success(self, client: AsyncClient, auth_headers):
        """Test search by tags"""
        search_params = {
            "tags": "horror,supernatural,ghost",
            "limit": 10
        }
        
        response = await client.get("/api/v1/search/by-tags", params=search_params, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "tags_searched" in data
        assert "horror" in data["tags_searched"]
        assert "supernatural" in data["tags_searched"]
        assert "ghost" in data["tags_searched"]
    
    async def test_search_by_author_success(self, client: AsyncClient, auth_headers, sample_bronze_story):
        """Test search by author"""
        search_params = {
            "author": sample_bronze_story.author,
            "limit": 10
        }
        
        response = await client.get("/api/v1/search/by-author", params=search_params, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "author_searched" in data
        assert data["author_searched"] == sample_bronze_story.author
    
    async def test_search_trends_success(self, client: AsyncClient, auth_headers):
        """Test search trends"""
        response = await client.get("/api/v1/search/trends", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "trending_queries" in data
        assert "popular_tags" in data
        assert "trending_authors" in data
        assert "generated_at" in data
    
    async def test_search_health_check(self, client: AsyncClient):
        """Test search service health check"""
        response = await client.get("/api/v1/search/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "capabilities" in data
        assert data["capabilities"]["semantic_search"] is True
    
    @pytest.mark.slow
    async def test_search_performance(self, client: AsyncClient, auth_headers, mock_embedding_manager):
        """Test search response time"""
        import time
        
        with patch('backend.app.core.search.embedding_manager', mock_embedding_manager):
            search_params = {
                "query": "performance test query",
                "limit": 50
            }
            
            start_time = time.time()
            response = await client.get("/api/v1/search/stories", params=search_params, headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            
            # Search should complete within 2 seconds
            response_time = end_time - start_time
            assert response_time < 2.0, f"Search took {response_time:.2f} seconds, expected < 2.0"
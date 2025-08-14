"""
Unified service layer for the backend application
Consolidates all business logic services into a single module for easier management
"""

from .auth import AuthService
from .search import SearchService
from .content import ContentService
from .analytics import AnalyticsService
from .admin import AdminService

# Re-export services for convenience
__all__ = [
    'AuthService',
    'SearchService', 
    'ContentService',
    'AnalyticsService',
    'AdminService'
]
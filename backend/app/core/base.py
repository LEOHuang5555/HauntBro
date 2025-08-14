"""
Base classes and common patterns for services
Eliminates code duplication across service modules
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class BaseService:
    """
    Base service class with common functionality
    All service classes should inherit from this
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _handle_db_error(self, operation: str, error: Exception) -> None:
        """Standard database error handling"""
        self.logger.error(f"{operation} error: {error}")
        self.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {operation}"
        )
    
    def _validate_pagination(self, page: int, per_page: int, max_per_page: int = 100) -> tuple[int, int]:
        """Validate and normalize pagination parameters"""
        page = max(1, page)
        per_page = min(max(1, per_page), max_per_page)
        offset = (page - 1) * per_page
        return offset, per_page
    
    def _build_pagination_response(
        self, 
        page: int, 
        per_page: int, 
        total_count: int
    ) -> Dict[str, Any]:
        """Build standardized pagination response"""
        return {
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": (total_count + per_page - 1) // per_page
        }
    
    async def _get_total_count(self, query) -> int:
        """Get total count for a query"""
        try:
            count_query = select(func.count()).select_from(query.subquery())
            result = self.db.execute(count_query).scalar()
            return result or 0
        except Exception as e:
            self.logger.warning(f"Failed to get total count: {e}")
            return 0


class PaginatedResponse:
    """Standard paginated response structure"""
    
    @staticmethod
    def create(
        items: List[Any],
        page: int,
        per_page: int,
        total_count: int,
        item_key: str = "items"
    ) -> Dict[str, Any]:
        """Create a standardized paginated response"""
        return {
            item_key: items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": (total_count + per_page - 1) // per_page
            }
        }


class ServiceError(Exception):
    """Custom service error with HTTP status code"""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException"""
        return HTTPException(
            status_code=self.status_code,
            detail=self.message
        )


class TimestampMixin:
    """Mixin for adding timestamp utilities"""
    
    @staticmethod
    def utc_now() -> datetime:
        """Get current UTC timestamp"""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def to_iso_string(dt: Optional[datetime]) -> Optional[str]:
        """Convert datetime to ISO string"""
        return dt.isoformat() if dt else None
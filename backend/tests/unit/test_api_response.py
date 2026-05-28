"""
Tests for API Response Schemas

Tests standardized API response formats and helpers.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.core.schemas.api_response import (
    ErrorResponse,
    ErrorDetail,
    SuccessResponse,
    PaginationMeta,
    PaginatedResponse,
    ListResponse,
    DeleteResponse,
    create_success_response,
    create_error_response,
    create_paginated_response,
)


class TestErrorDetail:
    """Tests for ErrorDetail schema."""
    
    def test_error_detail_creation(self):
        """Test creating ErrorDetail."""
        detail = ErrorDetail(
            code="TEST_ERROR",
            message="Test error message",
        )
        
        assert detail.code == "TEST_ERROR"
        assert detail.message == "Test error message"
        assert detail.details is None
    
    def test_error_detail_with_details(self):
        """Test ErrorDetail with additional details."""
        detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Validation failed",
            details={"field": "email", "reason": "invalid format"},
        )
        
        assert detail.details["field"] == "email"
        assert detail.details["reason"] == "invalid format"


class TestErrorResponse:
    """Tests for ErrorResponse schema."""
    
    def test_error_response_structure(self):
        """Test ErrorResponse has correct structure."""
        response = ErrorResponse(
            error=ErrorDetail(code="NOT_FOUND", message="Resource not found"),
            request_id="req-123",
        )
        
        assert response.success is False
        assert response.error.code == "NOT_FOUND"
        assert response.request_id == "req-123"
        assert "timestamp" in response.model_dump()
    
    def test_error_response_to_dict(self):
        """Test ErrorResponse serialization."""
        response = ErrorResponse(
            error=ErrorDetail(code="ERROR", message="Error occurred"),
        )
        
        data = response.model_dump()
        assert data["success"] is False
        assert "error" in data


class TestSuccessResponse:
    """Tests for SuccessResponse schema."""
    
    def test_success_response_with_data(self):
        """Test SuccessResponse with data."""
        data = {"id": str(uuid4()), "name": "Test Agent"}
        response = SuccessResponse(data=data)
        
        assert response.success is True
        assert response.data == data
        assert "timestamp" in response.model_dump()
    
    def test_success_response_without_data(self):
        """Test SuccessResponse without data."""
        response = SuccessResponse()
        
        assert response.success is True
        assert response.data is None
    
    def test_success_response_with_metadata(self):
        """Test SuccessResponse with metadata."""
        from app.core.schemas.api_response import SuccessMeta
        
        meta = SuccessMeta(action="created", resource="agent")
        response = SuccessResponse(
            data={"id": "123"},
            meta=meta,
        )
        
        assert response.meta.action == "created"
        assert response.meta.resource == "agent"


class TestPaginationMeta:
    """Tests for PaginationMeta schema."""
    
    def test_pagination_meta_first_page(self):
        """Test pagination metadata for first page."""
        meta = PaginationMeta(
            page=1,
            per_page=20,
            total=100,
            total_pages=5,
            has_next=True,
            has_prev=False,
        )
        
        assert meta.page == 1
        assert meta.has_next is True
        assert meta.has_prev is False
    
    def test_pagination_meta_middle_page(self):
        """Test pagination metadata for middle page."""
        meta = PaginationMeta(
            page=3,
            per_page=20,
            total=100,
            total_pages=5,
            has_next=True,
            has_prev=True,
        )
        
        assert meta.page == 3
        assert meta.has_next is True
        assert meta.has_prev is True
    
    def test_pagination_meta_last_page(self):
        """Test pagination metadata for last page."""
        meta = PaginationMeta(
            page=5,
            per_page=20,
            total=100,
            total_pages=5,
            has_next=False,
            has_prev=True,
        )
        
        assert meta.page == 5
        assert meta.has_next is False
        assert meta.has_prev is True


class TestPaginatedResponse:
    """Tests for PaginatedResponse schema."""
    
    def test_paginated_response_structure(self):
        """Test PaginatedResponse has correct structure."""
        items = [
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
        ]
        pagination = PaginationMeta(
            page=1,
            per_page=20,
            total=2,
            total_pages=1,
            has_next=False,
            has_prev=False,
        )
        
        response = PaginatedResponse(
            data=items,
            pagination=pagination,
        )
        
        assert response.success is True
        assert len(response.data) == 2
        assert response.pagination.total == 2
    
    def test_paginated_response_serialization(self):
        """Test PaginatedResponse serialization."""
        response = PaginatedResponse(
            data=[{"id": "1"}],
            pagination=PaginationMeta(
                page=1,
                per_page=10,
                total=1,
                total_pages=1,
                has_next=False,
                has_prev=False,
            ),
        )
        
        data = response.model_dump()
        assert data["success"] is True
        assert "pagination" in data


class TestListResponse:
    """Tests for ListResponse schema."""
    
    def test_list_response_structure(self):
        """Test ListResponse has correct structure."""
        items = ["item1", "item2", "item3"]
        
        response = ListResponse(
            data=items,
            count=len(items),
        )
        
        assert response.success is True
        assert len(response.data) == 3
        assert response.count == 3
    
    def test_list_response_empty(self):
        """Test ListResponse with empty list."""
        response = ListResponse(data=[], count=0)
        
        assert response.success is True
        assert len(response.data) == 0
        assert response.count == 0


class TestDeleteResponse:
    """Tests for DeleteResponse schema."""
    
    def test_delete_response_structure(self):
        """Test DeleteResponse has correct structure."""
        response = DeleteResponse()
        
        assert response.success is True
        assert response.data["deleted"] is True
        assert response.meta.action == "deleted"


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_create_success_response_default(self):
        """Test create_success_response with defaults."""
        response = create_success_response()
        
        assert isinstance(response, SuccessResponse)
        assert response.success is True
        assert response.data is None
    
    def test_create_success_response_with_params(self):
        """Test create_success_response with parameters."""
        response = create_success_response(
            data={"id": "123"},
            action="created",
            resource="agent",
            request_id="req-456",
        )
        
        assert response.data == {"id": "123"}
        assert response.meta.action == "created"
        assert response.meta.resource == "agent"
        assert response.request_id == "req-456"
    
    def test_create_error_response(self):
        """Test create_error_response."""
        response = create_error_response(
            code="ERROR_CODE",
            message="Error message",
            details={"key": "value"},
            request_id="req-789",
        )
        
        assert isinstance(response, ErrorResponse)
        assert response.success is False
        assert response.error.code == "ERROR_CODE"
        assert response.error.message == "Error message"
        assert response.error.details == {"key": "value"}
        assert response.request_id == "req-789"
    
    def test_create_paginated_response(self):
        """Test create_paginated_response."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        
        response = create_paginated_response(
            data=items,
            page=2,
            per_page=10,
            total=25,
            request_id="req-123",
        )
        
        assert isinstance(response, PaginatedResponse)
        assert len(response.data) == 3
        assert response.pagination.page == 2
        assert response.pagination.per_page == 10
        assert response.pagination.total == 25
        assert response.pagination.total_pages == 3
        assert response.pagination.has_next is True
        assert response.pagination.has_prev is True
        assert response.request_id == "req-123"
    
    def test_create_paginated_response_last_page(self):
        """Test create_paginated_response for last page."""
        items = [{"id": "1"}, {"id": "2"}]
        
        response = create_paginated_response(
            data=items,
            page=3,
            per_page=10,
            total=25,
        )
        
        assert response.pagination.page == 3
        assert response.pagination.has_next is False
        assert response.pagination.has_prev is True
    
    def test_create_paginated_response_single_page(self):
        """Test create_paginated_response for single page."""
        items = [{"id": "1"}]
        
        response = create_paginated_response(
            data=items,
            page=1,
            per_page=10,
            total=5,
        )
        
        assert response.pagination.total_pages == 1
        assert response.pagination.has_next is False
        assert response.pagination.has_prev is False


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_error_response_with_none_request_id(self):
        """Test ErrorResponse with None request_id."""
        response = ErrorResponse(
            error=ErrorDetail(code="ERROR", message="Error"),
            request_id=None,
        )
        
        data = response.model_dump()
        assert data["request_id"] is None
    
    def test_success_response_with_complex_data(self):
        """Test SuccessResponse with complex nested data."""
        complex_data = {
            "agents": [
                {"id": "1", "settings": {"temperature": 0.7}},
                {"id": "2", "settings": {"temperature": 0.9}},
            ],
            "metadata": {
                "total": 2,
                "page": 1,
            },
        }
        
        response = SuccessResponse(data=complex_data)
        
        assert response.data == complex_data
        assert response.data["agents"][0]["settings"]["temperature"] == 0.7
    
    def test_pagination_math(self):
        """Test pagination calculation logic."""
        def calculate_total_pages(total: int, per_page: int) -> int:
            return (total + per_page - 1) // per_page if per_page > 0 else 0
        
        assert calculate_total_pages(100, 20) == 5
        assert calculate_total_pages(101, 20) == 6
        assert calculate_total_pages(0, 20) == 0
        assert calculate_total_pages(20, 20) == 1
        assert calculate_total_pages(1, 20) == 1

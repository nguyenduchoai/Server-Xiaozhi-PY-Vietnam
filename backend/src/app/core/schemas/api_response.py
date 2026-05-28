"""
Standardized API Response Schemas

Provides consistent response format for all API endpoints.
Includes success responses, error responses, pagination, and metadata.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error: ErrorDetail
    request_id: str | None = Field(default=None, description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorDetail(ErrorDetail):
    """Validation error with field-level details."""
    code: str = "VALIDATION_ERROR"
    
    class FieldError(BaseModel):
        """Individual field error."""
        field: str = Field(..., description="Field path (e.g., 'body.username')")
        message: str = Field(..., description="Error message")
        type: str = Field(..., description="Error type (e.g., 'missing', 'string_too_short')")
        value: Any = Field(default=None, description="Invalid value provided")
    
    details: dict[str, list[FieldError]] | None = None


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class SuccessMeta(BaseModel):
    """Metadata for success responses."""
    action: str | None = Field(default=None, description="Action performed")
    resource: str | None = Field(default=None, description="Resource type")
    created_at: datetime | None = Field(default=None, description="When resource was created")
    modified_at: datetime | None = Field(default=None, description="When resource was modified")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response format with optional data."""
    success: bool = True
    data: T | None = Field(default=None, description="Response data")
    meta: SuccessMeta | None = Field(default=None, description="Response metadata")
    request_id: str | None = Field(default=None, description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": "uuid", "name": "example"},
                "meta": {"action": "created"},
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response format."""
    success: bool = True
    data: list[T] = Field(..., description="List of items for current page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    request_id: str | None = Field(default=None, description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": [{"id": "uuid-1", "name": "Item 1"}, {"id": "uuid-2", "name": "Item 2"}],
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    )


class ListResponse(BaseModel, Generic[T]):
    """Non-paginated list response format."""
    success: bool = True
    data: list[T] = Field(..., description="List of items")
    count: int = Field(..., ge=0, description="Total number of items")
    request_id: str | None = Field(default=None, description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DeleteResponse(BaseModel):
    """Standard delete response."""
    success: bool = True
    data: dict[str, Any] = Field(
        default_factory=lambda: {"deleted": True},
        description="Deletion confirmation"
    )
    meta: SuccessMeta = Field(
        default_factory=lambda: SuccessMeta(action="deleted"),
        description="Response metadata"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BulkOperationResponse(BaseModel):
    """Response for bulk operations (create, update, delete)."""
    success: bool = True
    data: dict[str, Any] = Field(
        ...,
        description="Operation results",
        examples=[{
            "succeeded": 5,
            "failed": 2,
            "total": 7,
            "errors": [
                {"index": 2, "error": "Validation failed"},
                {"index": 5, "error": "Duplicate entry"}
            ]
        }]
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: dict[str, Any] | None = Field(
        default=None,
        description="Individual component health checks"
    )


class ReadyResponse(BaseModel):
    """Readiness check response."""
    status: str = Field(..., description="Overall readiness status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    checks: dict[str, str] = Field(
        ...,
        description="Component readiness status",
        examples=[{"database": "ready", "redis": "ready", "mqtt": "ready"}]
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


def create_success_response(
    data: Any = None,
    action: str | None = None,
    resource: str | None = None,
    request_id: str | None = None,
) -> SuccessResponse:
    """Helper to create a standardized success response."""
    meta = SuccessMeta(action=action, resource=resource) if action or resource else None
    return SuccessResponse(
        data=data,
        meta=meta,
        request_id=request_id,
    )


def create_error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> ErrorResponse:
    """Helper to create a standardized error response."""
    return ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
        ),
        request_id=request_id,
    )


def create_paginated_response(
    data: list[Any],
    page: int,
    per_page: int,
    total: int,
    request_id: str | None = None,
) -> PaginatedResponse:
    """Helper to create a standardized paginated response."""
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    pagination = PaginationMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
    
    return PaginatedResponse(
        data=data,
        pagination=pagination,
        request_id=request_id,
    )

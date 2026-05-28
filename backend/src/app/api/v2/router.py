"""
API Versioning Module

Provides API versioning support with:
- Version detection (header, query param, URL path)
- Deprecation warnings
- Version-specific middleware
- Graceful migration support
"""

from enum import Enum
from typing import Callable, Optional
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logger import get_logger


logger = get_logger(__name__)


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    V2 = "v2"


class VersionHeader(str, Enum):
    """API version header names."""
    HEADER_NAME = "X-API-Version"
    DEPRECATED_HEADER = "API-Version"


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling API versioning.
    
    Supports three versioning strategies:
    1. URL Path: /api/v1/..., /api/v2/...
    2. Header: X-API-Version: v1, X-API-Version: v2
    3. Query Parameter: ?api_version=v1
    
    Priority: URL Path > Query > Header
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_version: APIVersion = APIVersion.V1,
        deprecated_versions: Optional[list[APIVersion]] = None,
        deprecation_warning_threshold_days: int = 30,
    ):
        super().__init__(app)
        self.default_version = default_version
        self.deprecated_versions = deprecated_versions or []
        self.deprecation_threshold_days = deprecation_warning_threshold_days
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with API versioning."""
        version = self._detect_version(request)
        
        request.state.api_version = version
        request.state.is_deprecated = version in self.deprecated_versions
        
        response = await call_next(request)
        
        if request.state.is_deprecated:
            response.headers["X-API-Deprecation"] = "true"
            response.headers["X-API-Sunset-Date"] = self._get_sunset_date()
        
        response.headers["X-API-Version"] = version.value
        
        return response
    
    def _detect_version(self, request: Request) -> APIVersion:
        """Detect API version from request."""
        path = request.url.path
        
        if "/api/v2/" in path:
            return APIVersion.V2
        elif "/api/v1/" in path:
            return APIVersion.V1
        
        api_version = request.query_params.get("api_version")
        if api_version:
            try:
                return APIVersion(api_version.lower())
            except ValueError:
                logger.warning(f"Invalid API version in query: {api_version}")
        
        header_version = request.headers.get(VersionHeader.HEADER_NAME.value)
        if header_version:
            try:
                return APIVersion(header_version.lower())
            except ValueError:
                logger.warning(f"Invalid API version in header: {header_version}")
        
        return self.default_version
    
    def _get_sunset_date(self) -> str:
        """Get deprecation sunset date."""
        from datetime import datetime, timedelta
        sunset = datetime.utcnow() + timedelta(days=self.deprecation_threshold_days)
        return sunset.strftime("%Y-%m-%d")


class VersionedResponseMixin:
    """Mixin for adding version information to responses."""
    
    def add_version_headers(self, response: Response, request: Request):
        """Add version-related headers to response."""
        response.headers["X-API-Version"] = getattr(
            request.state, "api_version", APIVersion.V1
        ).value
        
        if getattr(request.state, "is_deprecated", False):
            response.headers["X-API-Deprecation"] = "true"


def create_versioned_router(
    version: APIVersion,
    prefix: Optional[str] = None,
) -> APIRouter:
    """Create a versioned API router."""
    version_prefix = prefix or f"/api/{version.value}"
    
    router = APIRouter(prefix=version_prefix)
    router.tags = [version.value.upper()]
    
    return router


def get_deprecated_response(
    message: str = "This endpoint is deprecated",
    alternative: Optional[str] = None,
) -> JSONResponse:
    """Create a deprecation response."""
    content = {
        "success": False,
        "error": {
            "code": "ENDPOINT_DEPRECATED",
            "message": message,
        }
    }
    
    if alternative:
        content["error"]["alternative"] = alternative
        content["error"]["migration_guide"] = f"Use {alternative} instead"
    
    return JSONResponse(
        status_code=410,
        content=content,
        headers={
            "Deprecation": "true",
            "Sunset": "Sat, 31 Dec 2025 23:59:59 GMT",
        },
    )


def get_version_info(request: Request) -> dict:
    """Get version information from request."""
    return {
        "version": getattr(request.state, "api_version", APIVersion.V1).value,
        "is_deprecated": getattr(request.state, "is_deprecated", False),
        "supported_versions": [v.value for v in APIVersion],
    }

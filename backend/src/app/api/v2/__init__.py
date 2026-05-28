"""
API v2 Module

Enhanced API endpoints with improved response format, versioning, and features.
"""

from fastapi import APIRouter

from .router import APIVersioningMiddleware, create_versioned_router, get_version_info
from .agents import router as agents_router


v2_router = APIRouter(prefix="/api/v2", tags=["API v2"])

v2_router.include_router(agents_router)


__all__ = [
    "v2_router",
    "APIVersioningMiddleware",
    "create_versioned_router",
    "get_version_info",
]

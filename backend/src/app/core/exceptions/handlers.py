"""
Global Exception Handlers Module

Provides exception handlers for FastAPI to ensure consistent error responses.
Includes handlers for all custom exceptions and common framework exceptions.
"""

import traceback
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose.exceptions import JWTError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError

from .base import (
    XiaozhiBaseException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    DuplicateResourceError,
    RateLimitExceededError,
    ServiceUnavailableError,
    ExternalServiceError,
    BusinessLogicError,
    DatabaseError,
)
from ..logger import setup_logging


TAG = __name__
logger = setup_logging()


class ExceptionHandlerRegistry:
    """Registry for mapping exceptions to handlers."""
    
    _handlers: dict[type[Exception], Callable[..., Any]] = {}
    _fallback_handler: Optional[Callable[..., Any]] = None
    
    @classmethod
    def register(
        cls,
        exception_type: type[Exception],
        handler: Callable[..., Any],
    ) -> None:
        """Register an exception handler for a specific exception type."""
        cls._handlers[exception_type] = handler
    
    @classmethod
    def register_fallback(cls, handler: Callable[..., Any]) -> None:
        """Register a fallback handler for unregistered exceptions."""
        cls._fallback_handler = handler
    
    @classmethod
    def get_handler(cls, exception_type: type[Exception]) -> Optional[Callable[..., Any]]:
        """Get handler for the given exception type."""
        for exc_type, handler in cls._handlers.items():
            if issubclass(exception_type, exc_type):
                return handler
        return cls._fallback_handler


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
    include_traceback: bool = False,
) -> dict[str, Any]:
    """Create a standardized error response dictionary."""
    error_response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    if request_id:
        error_response["request_id"] = request_id
    
    return error_response


def get_request_id(request: Request) -> Optional[str]:
    """Extract request ID from request headers or state."""
    return (
        request.state.request_id
        if hasattr(request.state, "request_id")
        else request.headers.get("X-Request-ID")
    )


async def xiaozhi_exception_handler(
    request: Request,
    exc: XiaozhiBaseException,
) -> JSONResponse:
    """Handle XiaozhiBaseException and its subclasses."""
    request_id = get_request_id(request)
    
    log_data = {
        "tag": TAG,
        "error_code": exc.error_code,
        "path": request.url.path,
        "method": request.method,
        "request_id": request_id,
    }
    
    if exc.cause:
        log_data["cause"] = str(exc.cause)
    
    logger.error(f"[{exc.error_code}] {exc.message}", **log_data)
    
    response_data = exc.to_dict()
    response_data["success"] = False
    
    if request_id:
        response_data["request_id"] = request_id
    
    return JSONResponse(
        status_code=exc.HTTP_STATUS_CODE,
        content=response_data,
        headers={"X-Request-ID": request_id} if request_id else None,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle FastAPI RequestValidationError."""
    request_id = get_request_id(request)
    
    logger.warning(
        f"[VALIDATION_ERROR] {request.method} {request.url.path}",
        tag=TAG,
        errors=exc.errors(),
        request_id=request_id,
    )
    
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        error_details.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"fields": error_details},
            },
            "request_id": request_id,
        },
    )


async def pydantic_validation_exception_handler(
    request: Request,
    exc: PydanticValidationError,
) -> JSONResponse:
    """Handle Pydantic ValidationError."""
    request_id = get_request_id(request)
    
    logger.warning(
        f"[PYDANTIC_VALIDATION_ERROR] {request.method} {request.url.path}",
        tag=TAG,
        errors=exc.errors(),
        request_id=request_id,
    )
    
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        error_details.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Data validation failed",
                "details": {"fields": error_details},
            },
            "request_id": request_id,
        },
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    request_id = get_request_id(request)
    
    logger.error(
        f"[DATABASE_ERROR] {request.method} {request.url.path}",
        tag=TAG,
        error=str(exc),
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Database operation failed",
                "details": {"reason": "A database error occurred"},
            },
            "request_id": request_id,
        },
    )


async def jwt_exception_handler(
    request: Request,
    exc: JWTError,
) -> JSONResponse:
    """Handle JWT errors."""
    request_id = get_request_id(request)
    
    logger.warning(
        f"[JWT_ERROR] {request.method} {request.url.path}",
        tag=TAG,
        error=str(exc),
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "success": False,
            "error": {
                "code": "AUTHENTICATION_ERROR",
                "message": "Invalid or expired token",
            },
            "request_id": request_id,
        },
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    request_id = get_request_id(request)
    
    exc_type = type(exc).__name__
    exc_traceback = "".join(traceback.format_tb(exc.__traceback__))
    
    logger.error(
        f"[UNHANDLED_EXCEPTION] {request.method} {request.url.path}",
        tag=TAG,
        exception_type=exc_type,
        exception_message=str(exc),
        traceback=exc_traceback,
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {
                    "type": exc_type,
                },
            },
            "request_id": request_id,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    app.add_exception_handler(XiaozhiBaseException, xiaozhi_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(JWTError, jwt_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("[ExceptionHandlers] All exception handlers registered", tag=TAG)

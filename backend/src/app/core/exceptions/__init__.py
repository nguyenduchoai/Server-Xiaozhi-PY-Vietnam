"""
Xiaozhi Platform Exceptions Module

Comprehensive exception system for consistent error handling across the platform.

Exports:
    - Base exceptions (XiaozhiBaseException and subclasses)
    - HTTP exceptions (for FastAPI compatibility)
    - Exception handlers (for FastAPI registration)
"""

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
    ConfigurationError,
    DatabaseError,
    CacheError,
    WebSocketError,
    AIProviderError,
    DeviceConnectionError,
    PaymentError,
    SubscriptionError,
    QuotaExceededError,
)

from .http_exceptions import (
    CustomException,
    BadRequestException,
    NotFoundException,
    ForbiddenException,
    UnauthorizedException,
    UnprocessableEntityException,
    DuplicateValueException,
    RateLimitException,
    ServiceUnavailableException,
)

from .cache_exceptions import (
    CacheIdentificationInferenceError,
    InvalidRequestError,
    MissingClientError,
)

from .handlers import (
    register_exception_handlers,
    ExceptionHandlerRegistry,
    xiaozhi_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    jwt_exception_handler,
    generic_exception_handler,
    create_error_response,
)


__all__ = [
    # Base exceptions
    "XiaozhiBaseException",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "DuplicateResourceError",
    "RateLimitExceededError",
    "ServiceUnavailableError",
    "ExternalServiceError",
    "BusinessLogicError",
    "ConfigurationError",
    "DatabaseError",
    "CacheError",
    "WebSocketError",
    "AIProviderError",
    "DeviceConnectionError",
    "PaymentError",
    "SubscriptionError",
    "QuotaExceededError",
    # HTTP exceptions (FastAPI compatibility)
    "CustomException",
    "BadRequestException",
    "NotFoundException",
    "ForbiddenException",
    "UnauthorizedException",
    "UnprocessableEntityException",
    "DuplicateValueException",
    "RateLimitException",
    "ServiceUnavailableException",
    # Cache exceptions
    "CacheIdentificationInferenceError",
    "InvalidRequestError",
    "MissingClientError",
    # Handlers
    "register_exception_handlers",
    "ExceptionHandlerRegistry",
    "xiaozhi_exception_handler",
    "validation_exception_handler",
    "sqlalchemy_exception_handler",
    "jwt_exception_handler",
    "generic_exception_handler",
    "create_error_response",
]

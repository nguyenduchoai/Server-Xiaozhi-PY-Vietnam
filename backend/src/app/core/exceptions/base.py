"""
Base Exceptions Module

Comprehensive exception hierarchy for Xiaozhi platform.
All custom exceptions should inherit from these base classes.
"""

from typing import Any, Optional
from fastapi import status


class XiaozhiBaseException(Exception):
    """Base exception for all Xiaozhi platform exceptions.
    
    Provides consistent structure for all exceptions including:
    - Error code for programmatic handling
    - User-friendly message
    - HTTP status code mapping
    - Extra data for debugging
    """
    
    ERROR_CODE: str = "XIAOZHI_ERROR"
    DEFAULT_MESSAGE: str = "An error occurred"
    HTTP_STATUS_CODE: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.message = message or self.DEFAULT_MESSAGE
        self.error_code = error_code or self.ERROR_CODE
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        response = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }
        if self.details:
            response["error"]["details"] = self.details
        if self.cause and hasattr(self.cause, '__traceback__'):
            import traceback
            response["error"]["debug"] = {
                "traceback": "".join(traceback.format_tb(self.cause.__traceback__))
            }
        return response


class ValidationError(XiaozhiBaseException):
    """Raised when input validation fails."""
    ERROR_CODE = "VALIDATION_ERROR"
    DEFAULT_MESSAGE = "Input validation failed"
    HTTP_STATUS_CODE = status.HTTP_422_UNPROCESSABLE_ENTITY


class AuthenticationError(XiaozhiBaseException):
    """Raised when authentication fails."""
    ERROR_CODE = "AUTHENTICATION_ERROR"
    DEFAULT_MESSAGE = "Authentication failed"
    HTTP_STATUS_CODE = status.HTTP_401_UNAUTHORIZED


class AuthorizationError(XiaozhiBaseException):
    """Raised when user lacks required permissions."""
    ERROR_CODE = "AUTHORIZATION_ERROR"
    DEFAULT_MESSAGE = "You do not have permission to perform this action"
    HTTP_STATUS_CODE = status.HTTP_403_FORBIDDEN


class ResourceNotFoundError(XiaozhiBaseException):
    """Raised when a requested resource is not found."""
    ERROR_CODE = "RESOURCE_NOT_FOUND"
    DEFAULT_MESSAGE = "The requested resource was not found"
    HTTP_STATUS_CODE = status.HTTP_404_NOT_FOUND


class DuplicateResourceError(XiaozhiBaseException):
    """Raised when attempting to create a duplicate resource."""
    ERROR_CODE = "DUPLICATE_RESOURCE"
    DEFAULT_MESSAGE = "A resource with this identifier already exists"
    HTTP_STATUS_CODE = status.HTTP_409_CONFLICT


class RateLimitExceededError(XiaozhiBaseException):
    """Raised when rate limit is exceeded."""
    ERROR_CODE = "RATE_LIMIT_EXCEEDED"
    DEFAULT_MESSAGE = "Rate limit exceeded. Please try again later"
    HTTP_STATUS_CODE = status.HTTP_429_TOO_MANY_REQUESTS
    
    def __init__(
        self,
        message: Optional[str] = None,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message=message, **kwargs)
        self.retry_after = retry_after
        self.limit = limit
        if retry_after:
            self.details["retry_after"] = retry_after
        if limit:
            self.details["limit"] = limit


class ServiceUnavailableError(XiaozhiBaseException):
    """Raised when a required service is unavailable."""
    ERROR_CODE = "SERVICE_UNAVAILABLE"
    DEFAULT_MESSAGE = "Service temporarily unavailable"
    HTTP_STATUS_CODE = status.HTTP_503_SERVICE_UNAVAILABLE


class ExternalServiceError(XiaozhiBaseException):
    """Raised when an external service (API, DB, etc.) fails."""
    ERROR_CODE = "EXTERNAL_SERVICE_ERROR"
    DEFAULT_MESSAGE = "External service error"
    HTTP_STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    
    def __init__(
        self,
        message: Optional[str] = None,
        service_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message=message, **kwargs)
        self.service_name = service_name
        if service_name:
            self.details["service"] = service_name


class BusinessLogicError(XiaozhiBaseException):
    """Raised when business logic constraints are violated."""
    ERROR_CODE = "BUSINESS_LOGIC_ERROR"
    DEFAULT_MESSAGE = "Operation not allowed"
    HTTP_STATUS_CODE = status.HTTP_400_BAD_REQUEST


class ConfigurationError(XiaozhiBaseException):
    """Raised when there's a configuration problem."""
    ERROR_CODE = "CONFIGURATION_ERROR"
    DEFAULT_MESSAGE = "Invalid configuration"
    HTTP_STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR


class DatabaseError(XiaozhiBaseException):
    """Raised when database operations fail."""
    ERROR_CODE = "DATABASE_ERROR"
    DEFAULT_MESSAGE = "Database operation failed"
    HTTP_STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR


class CacheError(XiaozhiBaseException):
    """Raised when cache operations fail."""
    ERROR_CODE = "CACHE_ERROR"
    DEFAULT_MESSAGE = "Cache operation failed"
    HTTP_STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR


class WebSocketError(XiaozhiBaseException):
    """Raised when WebSocket operations fail."""
    ERROR_CODE = "WEBSOCKET_ERROR"
    DEFAULT_MESSAGE = "WebSocket operation failed"
    HTTP_STATUS_CODE = status.WS_1008_POLICY_VIOLATION


class AIProviderError(XiaozhiBaseException):
    """Raised when AI provider (LLM, ASR, TTS) operations fail."""
    ERROR_CODE = "AI_PROVIDER_ERROR"
    DEFAULT_MESSAGE = "AI service error"
    HTTP_STATUS_CODE = status.HTTP_502_BAD_GATEWAY
    
    def __init__(
        self,
        message: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message=message, **kwargs)
        self.provider = provider
        if provider:
            self.details["provider"] = provider


class DeviceConnectionError(XiaozhiBaseException):
    """Raised when device connection fails."""
    ERROR_CODE = "DEVICE_CONNECTION_ERROR"
    DEFAULT_MESSAGE = "Device connection failed"
    HTTP_STATUS_CODE = status.HTTP_503_SERVICE_UNAVAILABLE


class PaymentError(XiaozhiBaseException):
    """Raised when payment processing fails."""
    ERROR_CODE = "PAYMENT_ERROR"
    DEFAULT_MESSAGE = "Payment processing failed"
    HTTP_STATUS_CODE = status.HTTP_402_PAYMENT_REQUIRED


class SubscriptionError(XiaozhiBaseException):
    """Raised when subscription-related operations fail."""
    ERROR_CODE = "SUBSCRIPTION_ERROR"
    DEFAULT_MESSAGE = "Subscription error"
    HTTP_STATUS_CODE = status.HTTP_403_FORBIDDEN


class QuotaExceededError(XiaozhiBaseException):
    """Raised when user quota is exceeded."""
    ERROR_CODE = "QUOTA_EXCEEDED"
    DEFAULT_MESSAGE = "Quota exceeded"
    HTTP_STATUS_CODE = status.HTTP_403_FORBIDDEN
    
    def __init__(
        self,
        message: Optional[str] = None,
        quota_type: Optional[str] = None,
        current: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message=message, **kwargs)
        self.quota_type = quota_type
        self.current = current
        self.limit = limit
        if quota_type:
            self.details["quota_type"] = quota_type
        if current is not None:
            self.details["current"] = current
        if limit is not None:
            self.details["limit"] = limit

"""
Tests for Exception System

Tests comprehensive exception handling, error responses, and handlers.
"""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.core.exceptions import (
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
    register_exception_handlers,
)


@pytest.fixture
def app_with_handlers():
    """Create FastAPI app with exception handlers registered."""
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.fixture
def client(app_with_handlers):
    """Create test client."""
    return TestClient(app_with_handlers)


class TestXiaozhiBaseException:
    """Tests for XiaozhiBaseException and its subclasses."""
    
    def test_base_exception_to_dict(self):
        """Test exception to_dict method."""
        exc = XiaozhiBaseException(
            message="Test error",
            error_code="TEST_ERROR",
        )
        result = exc.to_dict()
        
        assert "error" in result
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Test error"
    
    def test_base_exception_with_details(self):
        """Test exception with details."""
        exc = XiaozhiBaseException(
            message="Error with details",
            details={"field": "value", "count": 5},
        )
        result = exc.to_dict()
        
        assert result["error"]["details"]["field"] == "value"
        assert result["error"]["details"]["count"] == 5
    
    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError(message="Invalid input")
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.HTTP_STATUS_CODE == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError()
        assert exc.error_code == "AUTHENTICATION_ERROR"
        assert exc.HTTP_STATUS_CODE == status.HTTP_401_UNAUTHORIZED
    
    def test_authorization_error(self):
        """Test AuthorizationError."""
        exc = AuthorizationError()
        assert exc.error_code == "AUTHORIZATION_ERROR"
        assert exc.HTTP_STATUS_CODE == status.HTTP_403_FORBIDDEN
    
    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError."""
        exc = ResourceNotFoundError(message="User not found")
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.HTTP_STATUS_CODE == status.HTTP_404_NOT_FOUND
    
    def test_duplicate_resource_error(self):
        """Test DuplicateResourceError."""
        exc = DuplicateResourceError()
        assert exc.error_code == "DUPLICATE_RESOURCE"
        assert exc.HTTP_STATUS_CODE == status.HTTP_409_CONFLICT
    
    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceededError with retry info."""
        exc = RateLimitExceededError(
            message="Too many requests",
            retry_after=60,
            limit=100,
        )
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.HTTP_STATUS_CODE == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc.retry_after == 60
        assert exc.limit == 100
        assert exc.details["retry_after"] == 60
        assert exc.details["limit"] == 100
    
    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        exc = ServiceUnavailableError()
        assert exc.error_code == "SERVICE_UNAVAILABLE"
        assert exc.HTTP_STATUS_CODE == status.HTTP_503_SERVICE_UNAVAILABLE
    
    def test_external_service_error(self):
        """Test ExternalServiceError with service name."""
        exc = ExternalServiceError(
            message="OpenAI API failed",
            service_name="openai",
        )
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
        assert exc.service_name == "openai"
        assert exc.details["service"] == "openai"
    
    def test_business_logic_error(self):
        """Test BusinessLogicError."""
        exc = BusinessLogicError(message="Cannot delete active resource")
        assert exc.error_code == "BUSINESS_LOGIC_ERROR"
        assert exc.HTTP_STATUS_CODE == status.HTTP_400_BAD_REQUEST
    
    def test_exception_inheritance(self):
        """Test that all exceptions inherit from XiaozhiBaseException."""
        exceptions = [
            ValidationError(),
            AuthenticationError(),
            AuthorizationError(),
            ResourceNotFoundError(),
            DuplicateResourceError(),
            RateLimitExceededError(),
            ServiceUnavailableError(),
            ExternalServiceError(),
            BusinessLogicError(),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, XiaozhiBaseException)


class TestExceptionHandlers:
    """Tests for exception handlers."""
    
    def test_raise_validation_error(self, client):
        """Test raising ValidationError."""
        @client.app.get("/test-validation")
        async def test_validation():
            raise ValidationError(message="Invalid field")
        
        response = client.get("/test-validation")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_raise_authentication_error(self, client):
        """Test raising AuthenticationError."""
        @client.app.get("/test-auth")
        async def test_auth():
            raise AuthenticationError()
        
        response = client.get("/test-auth")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"
    
    def test_raise_not_found_error(self, client):
        """Test raising ResourceNotFoundError."""
        @client.app.get("/test-not-found")
        async def test_not_found():
            raise ResourceNotFoundError(message="User not found")
        
        response = client.get("/test-not-found")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    
    def test_raise_rate_limit_error(self, client):
        """Test raising RateLimitExceededError."""
        @client.app.get("/test-rate-limit")
        async def test_rate_limit():
            raise RateLimitExceededError(retry_after=30)
        
        response = client.get("/test-rate-limit")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in data["error"]["details"]
    
    def test_raise_custom_error_with_details(self, client):
        """Test raising exception with custom details."""
        @client.app.get("/test-custom")
        async def test_custom():
            raise ExternalServiceError(
                message="AI provider failed",
                service_name="openai",
                details={"endpoint": "/chat", "status": 500},
            )
        
        response = client.get("/test-custom")
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert data["error"]["details"]["service"] == "openai"
        assert data["error"]["details"]["endpoint"] == "/chat"


class TestErrorResponseFormat:
    """Tests for standardized error response format."""
    
    def test_error_response_has_success_false(self, client):
        """Test that all error responses have success=False."""
        @client.app.get("/test-error-format")
        async def test_error():
            raise ValidationError()
        
        response = client.get("/test-error-format")
        assert response.json()["success"] is False
    
    def test_error_response_has_error_object(self, client):
        """Test that error responses have error object."""
        @client.app.get("/test-error-object")
        async def test_error():
            raise AuthenticationError()
        
        response = client.get("/test-error-object")
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
    
    def test_error_response_has_timestamp(self, client):
        """Test that error responses include timestamp."""
        @client.app.get("/test-timestamp")
        async def test_timestamp():
            raise ResourceNotFoundError()
        
        response = client.get("/test-timestamp")
        data = response.json()
        assert "timestamp" in data


class TestExceptionHandlerRegistration:
    """Tests for exception handler registration."""
    
    def test_handlers_registered(self, app_with_handlers):
        """Test that exception handlers are properly registered."""
        from app.core.exceptions.handlers import ExceptionHandlerRegistry
        
        assert ExceptionHandlerRegistry.get_handler(XiaozhiBaseException) is not None
    
    def test_multiple_exception_types_handled(self, client):
        """Test that multiple exception types are handled correctly."""
        exceptions_and_codes = [
            (ValidationError(), "VALIDATION_ERROR"),
            (AuthenticationError(), "AUTHENTICATION_ERROR"),
            (AuthorizationError(), "AUTHORIZATION_ERROR"),
            (ResourceNotFoundError(), "RESOURCE_NOT_FOUND"),
            (RateLimitExceededError(), "RATE_LIMIT_EXCEEDED"),
        ]
        
        for exc, expected_code in exceptions_and_codes:
            @client.app.get(f"/test-{expected_code.lower()}")
            async def raise_exc():
                raise exc.__class__()
            
            response = client.get(f"/test-{expected_code.lower()}")
            assert response.json()["error"]["code"] == expected_code

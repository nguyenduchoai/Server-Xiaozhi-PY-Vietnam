"""
Health & Infrastructure Tests

Tests cover:
- Health endpoint availability
- Response format validation
- Schema validation for health responses
- Config validation
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Health check endpoint tests."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient):
        """Health endpoint should always return 200."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_format(self, client: AsyncClient):
        """Health response should have required fields."""
        response = await client.get("/api/v1/health")
        data = response.json()
        
        assert "status" in data, "Missing 'status' field"
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "environment" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_status_healthy(self, client: AsyncClient):
        """In test env, health should be healthy."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"


class TestSchemaValidation:
    """Pydantic schema validation tests."""

    def test_component_health_schema(self):
        """ComponentHealth schema should validate correctly."""
        from app.schemas.health import ComponentHealth
        
        # Valid data
        health = ComponentHealth(status="healthy", latency_ms=5.2, details="OK")
        assert health.status == "healthy"
        assert health.latency_ms == 5.2

    def test_component_health_invalid_status(self):
        """ComponentHealth should reject invalid status values."""
        from app.schemas.health import ComponentHealth
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ComponentHealth(status="invalid_status")

    def test_detailed_health_schema(self):
        """DetailedHealthCheck schema should validate correctly."""
        from app.schemas.health import DetailedHealthCheck, ComponentHealth
        from datetime import datetime, timezone
        
        health = DetailedHealthCheck(
            status="healthy",
            environment="test",
            version="1.0",
            uptime_seconds=100,
            timestamp=datetime.now(timezone.utc),
            components={
                "database": ComponentHealth(status="healthy", latency_ms=5.0),
            }
        )
        assert health.status == "healthy"
        assert "database" in health.components


class TestConfigValidation:
    """Configuration validation tests."""

    def test_settings_loaded(self):
        """Settings should load without error."""
        from app.core.config import settings
        assert settings is not None
        assert settings.APP_NAME is not None

    def test_secret_key_is_secret(self):
        """SECRET_KEY should be SecretStr type."""
        from app.core.config import settings
        from pydantic import SecretStr
        assert isinstance(settings.SECRET_KEY, SecretStr)
        # Should not be the default
        assert len(settings.SECRET_KEY.get_secret_value()) >= 32

    def test_environment_is_valid(self):
        """ENVIRONMENT should be a valid option."""
        from app.core.config import settings, EnvironmentOption
        assert settings.ENVIRONMENT in EnvironmentOption

    def test_cors_origins_configured(self):
        """CORS origins should be configured (not empty)."""
        from app.core.config import settings
        cors = settings.CORS_ALLOW_ORIGINS
        assert cors, "CORS origins should not be empty"
        assert "xiaozhi" in cors.lower() or "*" in cors, "CORS should include project domain"

    def test_database_connection_string(self):
        """PostgreSQL URI should be properly formed."""
        from app.core.config import settings
        uri = settings.POSTGRES_URI
        assert "@" in uri, "URI should contain auth"
        assert ":" in uri, "URI should contain port"

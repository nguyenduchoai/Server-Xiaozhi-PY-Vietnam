"""
Tests for Health API endpoints.

Tests:
- GET /health - Basic health check
- GET /ready - Readiness check with dependencies
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, client: AsyncClient):
        """Test basic health endpoint returns healthy status."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "environment" in data
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_check_no_auth_required(self, client: AsyncClient):
        """Test health endpoint works without authentication."""
        # No auth headers provided
        response = await client.get("/api/v1/health")
        
        # Should still return 200
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ready_check_returns_dependencies(self, client: AsyncClient):
        """Test readiness endpoint returns dependency status."""
        response = await client.get("/api/v1/ready")
        
        # In test environment with mocked DB, expect 200
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert "status" in data
        assert "database" in data
        assert "redis" in data
        assert data["status"] in ["healthy", "unhealthy"]


class TestHealthMetadata:
    """Tests for health response metadata."""

    @pytest.mark.asyncio
    async def test_health_includes_version(self, client: AsyncClient):
        """Test health response includes app version."""
        response = await client.get("/api/v1/health")
        data = response.json()
        
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    @pytest.mark.asyncio
    async def test_health_includes_valid_timestamp(self, client: AsyncClient):
        """Test health response includes valid ISO timestamp."""
        response = await client.get("/api/v1/health")
        data = response.json()
        
        assert "timestamp" in data
        # Validate ISO format - should not raise
        from datetime import datetime
        try:
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Invalid timestamp format")

    @pytest.mark.asyncio
    async def test_health_environment_values(self, client: AsyncClient):
        """Test health response has valid environment value."""
        response = await client.get("/api/v1/health")
        data = response.json()
        
        valid_environments = ["development", "staging", "production"]
        assert data["environment"] in valid_environments

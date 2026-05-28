"""
Tests for Providers API endpoints.

Tests:
- Provider schema endpoints
- Provider validation
- Provider CRUD operations
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestProviderSchemaEndpoints:
    """Tests for provider schema endpoints."""

    @pytest.mark.asyncio
    async def test_get_all_schemas(self, client: AsyncClient, auth_headers: dict):
        """Test getting all provider schemas."""
        response = await client.get(
            "/api/v1/providers/schemas",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have common categories
        expected_categories = ["LLM", "TTS", "ASR"]
        for cat in expected_categories:
            assert cat in data, f"Missing category: {cat}"

    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient, auth_headers: dict):
        """Test getting provider categories."""
        response = await client.get(
            "/api/v1/providers/categories",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "categories" in data
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) > 0

    @pytest.mark.asyncio
    async def test_schemas_require_auth(self, client: AsyncClient):
        """Test schema endpoints require authentication."""
        response = await client.get("/api/v1/providers/schemas")
        assert response.status_code == 401


class TestProviderValidationEndpoints:
    """Tests for provider validation."""

    @pytest.fixture
    def valid_openai_config(self) -> dict:
        """Sample valid OpenAI config."""
        return {
            "category": "LLM",
            "type": "openai",
            "config": {
                "api_key": "sk-test-key-12345",
                "model": "gpt-4",
            }
        }

    @pytest.fixture
    def invalid_config(self) -> dict:
        """Sample invalid config."""
        return {
            "category": "LLM",
            "type": "openai",
            "config": {
                # Missing required api_key
                "model": "gpt-4",
            }
        }

    @pytest.mark.asyncio
    async def test_validate_valid_config(
        self, client: AsyncClient, auth_headers: dict, valid_openai_config: dict
    ):
        """Test validation of valid provider config."""
        response = await client.post(
            "/api/v1/providers/validate",
            headers=auth_headers,
            json=valid_openai_config
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("valid") is True

    @pytest.mark.asyncio
    async def test_validate_invalid_config(
        self, client: AsyncClient, auth_headers: dict, invalid_config: dict
    ):
        """Test validation of invalid provider config."""
        response = await client.post(
            "/api/v1/providers/validate",
            headers=auth_headers,
            json=invalid_config
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should indicate invalid
        assert data.get("valid") is False or "error" in data


class TestProviderCRUDEndpoints:
    """Tests for provider CRUD operations."""

    @pytest.fixture
    def provider_data(self) -> dict:
        """Sample provider creation data."""
        return {
            "name": f"Test Provider {uuid4().hex[:8]}",
            "category": "LLM",
            "type": "openai",
            "config": {
                "api_key": "sk-test-key-12345",
                "model": "gpt-4",
            }
        }

    @pytest.mark.asyncio
    async def test_list_providers_requires_auth(self, client: AsyncClient):
        """Test listing providers requires authentication."""
        response = await client.get("/api/v1/providers")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_providers(self, client: AsyncClient, auth_headers: dict):
        """Test listing user providers."""
        response = await client.get(
            "/api/v1/providers",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination structure
        assert "items" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_providers_with_category_filter(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test filtering providers by category."""
        response = await client.get(
            "/api/v1/providers?category=LLM",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_provider(
        self, client: AsyncClient, auth_headers: dict, provider_data: dict
    ):
        """Test creating a new provider."""
        response = await client.post(
            "/api/v1/providers",
            headers=auth_headers,
            json=provider_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == provider_data["name"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_provider_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent provider returns 404."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/providers/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_provider_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting non-existent provider returns 404."""
        fake_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/providers/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestConfigModulesEndpoint:
    """Tests for config modules endpoint."""

    @pytest.mark.asyncio
    async def test_get_config_modules(self, client: AsyncClient, auth_headers: dict):
        """Test getting config modules."""
        response = await client.get(
            "/api/v1/providers/config-modules",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_config_modules_include_defaults(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test including default modules."""
        response = await client.get(
            "/api/v1/providers/config-modules?include_defaults=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200

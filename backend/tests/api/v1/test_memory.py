"""
Tests for Memory API endpoints.

Tests:
- Device memory CRUD operations
- Memory context retrieval
- Emotion logging
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestDeviceMemoryEndpoints:
    """Tests for device memory CRUD operations."""

    @pytest.fixture
    def test_device_id(self) -> str:
        """Generate test device ID."""
        return f"test-device-{uuid4().hex[:8]}"

    @pytest.fixture
    def test_memory_data(self) -> dict:
        """Sample memory creation data."""
        return {
            "key": "user_name",
            "value": "John Doe",
            "memory_type": "fact",
            "category": "personal",
        }

    @pytest.mark.asyncio
    async def test_get_memories_requires_auth(self, client: AsyncClient, test_device_id: str):
        """Test getting memories requires authentication."""
        response = await client.get(f"/api/v1/memory/device/{test_device_id}")
        
        # Should return 401 without auth
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_memories_empty_device(
        self, client: AsyncClient, auth_headers: dict, test_device_id: str
    ):
        """Test getting memories for device with no memories."""
        response = await client.get(
            f"/api/v1/memory/device/{test_device_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_create_memory(
        self, client: AsyncClient, auth_headers: dict, 
        test_device_id: str, test_memory_data: dict
    ):
        """Test creating a new memory."""
        response = await client.post(
            f"/api/v1/memory/device/{test_device_id}",
            headers=auth_headers,
            json=test_memory_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["key"] == test_memory_data["key"]
        assert data["value"] == test_memory_data["value"]

    @pytest.mark.asyncio
    async def test_create_memory_invalid_data(
        self, client: AsyncClient, auth_headers: dict, test_device_id: str
    ):
        """Test creating memory with invalid data fails."""
        invalid_data = {
            # Missing required fields
            "key": "test_key"
            # No value
        }
        
        response = await client.post(
            f"/api/v1/memory/device/{test_device_id}",
            headers=auth_headers,
            json=invalid_data
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_delete_memory(
        self, client: AsyncClient, auth_headers: dict,
        test_device_id: str, test_memory_data: dict
    ):
        """Test deleting a memory."""
        # First create
        await client.post(
            f"/api/v1/memory/device/{test_device_id}",
            headers=auth_headers,
            json=test_memory_data
        )
        
        # Then delete
        response = await client.delete(
            f"/api/v1/memory/device/{test_device_id}/{test_memory_data['key']}",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 204]


class TestMemoryContextEndpoints:
    """Tests for memory context retrieval."""

    @pytest.fixture
    def test_device_id(self) -> str:
        return f"context-device-{uuid4().hex[:8]}"

    @pytest.mark.asyncio
    async def test_get_context_requires_auth(
        self, client: AsyncClient, test_device_id: str
    ):
        """Test context endpoint requires auth."""
        response = await client.get(
            f"/api/v1/memory/device/{test_device_id}/context"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_context_empty_device(
        self, client: AsyncClient, auth_headers: dict, test_device_id: str
    ):
        """Test getting context for device with no memories."""
        response = await client.get(
            f"/api/v1/memory/device/{test_device_id}/context",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return empty context structure
        assert isinstance(data, dict)


class TestEmotionEndpoints:
    """Tests for emotion logging endpoints."""

    @pytest.fixture
    def test_device_id(self) -> str:
        return f"emotion-device-{uuid4().hex[:8]}"

    @pytest.fixture
    def emotion_data(self) -> dict:
        return {
            "emotion": "happy",
            "intensity": 0.8,
            "trigger": "greeting",
        }

    @pytest.mark.asyncio
    async def test_log_emotion_requires_auth(
        self, client: AsyncClient, test_device_id: str, emotion_data: dict
    ):
        """Test emotion logging requires auth."""
        response = await client.post(
            f"/api/v1/memory/device/{test_device_id}/emotion",
            json=emotion_data
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_emotions_requires_auth(
        self, client: AsyncClient, test_device_id: str
    ):
        """Test getting emotions requires auth."""
        response = await client.get(
            f"/api/v1/memory/device/{test_device_id}/emotions"
        )
        assert response.status_code == 401

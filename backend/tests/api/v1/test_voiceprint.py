"""
Unit tests for Voiceprint API endpoints.

Tests:
- GET /v1/voiceprint/config
- GET /v1/voiceprint/speakers
- POST /v1/voiceprint/register (mocked)
- POST /v1/voiceprint/test (mocked)
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient
from io import BytesIO

# Import for testing


class TestVoiceprintConfig:
    """Tests for voiceprint configuration endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_config_disabled(self, client: AsyncClient, auth_headers: dict):
        """Test config when voiceprint is disabled."""
        with patch("app.api.v1.voiceprint.load_config") as mock_config:
            mock_config.return_value = {"Voiceprint": {}}
            
            response = await client.get(
                "/v1/voiceprint/config",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is False
            assert data["speakers_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_config_enabled(self, client: AsyncClient, auth_headers: dict):
        """Test config when voiceprint is enabled."""
        with patch("app.api.v1.voiceprint.load_config") as mock_config:
            mock_config.return_value = {
                "Voiceprint": {
                    "enabled": True,
                    "url": "http://voiceprint-api:8200?key=test_key",
                    "speakers": ["speaker1,John,Developer", "speaker2,Jane,Manager"],
                    "similarity_threshold": 0.5,
                }
            }
            
            response = await client.get(
                "/v1/voiceprint/config",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is True
            assert data["speakers_count"] == 2
            assert data["similarity_threshold"] == 0.5
            assert data["service_url"] == "http://voiceprint-api:8200"


class TestVoiceprintSpeakers:
    """Tests for speakers listing endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_speakers_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing speakers when none configured."""
        with patch("app.api.v1.voiceprint.load_config") as mock_config:
            mock_config.return_value = {"Voiceprint": {"speakers": []}}
            
            response = await client.get(
                "/v1/voiceprint/speakers",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["voiceprints"] == []
    
    @pytest.mark.asyncio
    async def test_list_speakers_with_data(self, client: AsyncClient, auth_headers: dict):
        """Test listing configured speakers."""
        with patch("app.api.v1.voiceprint.load_config") as mock_config:
            mock_config.return_value = {
                "Voiceprint": {
                    "speakers": [
                        "spk_001,Alice,Marketing Lead",
                        "spk_002,Bob,Engineer",
                    ]
                }
            }
            
            response = await client.get(
                "/v1/voiceprint/speakers",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["voiceprints"]) == 2
            
            # Check first speaker
            assert data["voiceprints"][0]["speaker_id"] == "spk_001"
            assert data["voiceprints"][0]["speaker_name"] == "Alice"
            assert data["voiceprints"][0]["description"] == "Marketing Lead"


class TestVoiceprintRegister:
    """Tests for voiceprint registration endpoint."""
    
    @pytest.mark.asyncio
    async def test_register_without_service(self, client: AsyncClient, auth_headers: dict):
        """Test registration when service not configured."""
        with patch("app.api.v1.voiceprint.load_config") as mock_config:
            mock_config.return_value = {"Voiceprint": {}}
            
            # Create fake audio file
            audio_content = b"fake_audio_data"
            files = {"audio_file": ("test.wav", BytesIO(audio_content), "audio/wav")}
            data = {"speaker_name": "Test Speaker"}
            
            response = await client.post(
                "/v1/voiceprint/register",
                headers=auth_headers,
                files=files,
                data=data,
            )
            
            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_file_too_large(self, client: AsyncClient, auth_headers: dict):
        """Test registration with file exceeding size limit."""
        with patch("app.api.v1.voiceprint.load_config") as mock_config:
            mock_config.return_value = {
                "Voiceprint": {
                    "url": "http://voiceprint-api:8200?key=test_key",
                }
            }
            
            # Create file larger than 10MB
            large_content = b"x" * (11 * 1024 * 1024)
            files = {"audio_file": ("test.wav", BytesIO(large_content), "audio/wav")}
            data = {"speaker_name": "Test Speaker"}
            
            response = await client.post(
                "/v1/voiceprint/register",
                headers=auth_headers,
                files=files,
                data=data,
            )
            
            assert response.status_code == 413


class TestVoiceprintTest:
    """Tests for voiceprint test identification endpoint."""
    
    @pytest.mark.asyncio
    async def test_identification_no_speakers(self, client: AsyncClient, auth_headers: dict):
        """Test identification when no speakers configured."""
        with patch("app.api.v1.voiceprint.load_config") as mock_config:
            mock_config.return_value = {
                "Voiceprint": {
                    "url": "http://voiceprint-api:8200?key=test_key",
                    "speakers": [],
                }
            }
            
            audio_content = b"fake_audio_data"
            files = {"audio_file": ("test.wav", BytesIO(audio_content), "audio/wav")}
            
            response = await client.post(
                "/v1/voiceprint/test",
                headers=auth_headers,
                files=files,
            )
            
            assert response.status_code == 400
            assert "No speakers configured" in response.json()["detail"]


# Fixture placeholder for integration tests
@pytest.fixture
def client():
    """AsyncClient fixture - to be configured in conftest.py."""
    pass


@pytest.fixture
def auth_headers():
    """Auth headers fixture - to be configured in conftest.py."""
    return {"Authorization": "Bearer test_token"}

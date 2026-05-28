import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_agent_banner_sync_endpoint(async_client: AsyncClient, token_headers: dict, test_db_session):
    # This tests the banner sync flow and caching MD5 mechanism
    agent_id = "550e8400-e29b-41d4-a716-446655440001" 
    
    response = await async_client.get(
        f"/api/v2/agents/{agent_id}/banners",
        headers=token_headers
    )
    assert response.status_code == 200
    data = response.json().get("data")
    assert "version" in data
    assert "banners" in data
    assert "sync_interval" in data
    assert data["sync_interval"] == 3600

from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

@pytest.mark.asyncio
async def test_trigger_initial_banners():
    """Test that banners are trigger on Agent initialization with endless loop"""
    from app.ai.connection import Connection
    mock_conn = MagicMock(spec=Connection)
    mock_conn.logger = MagicMock()
    mock_conn.agent = {
        "banner_images": [
            {"url": "img1.png", "duration": 5},
            {"url": "img2.png", "duration": 5}
        ]
    }
    mock_conn.mqtt_service = MagicMock()
    mock_conn.mqtt_service.is_available.return_value = True
    mock_conn.mqtt_service.publish = AsyncMock()
    mock_conn.device_id = "MAC123"
    mock_conn._closing = False
    mock_conn.server_is_playing = False
    mock_conn.client_is_speaking = False
    mock_conn.llm_task = None
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Simulate closing the connection after the first sleep
        async def side_effect(*args):
            mock_conn._closing = True
        mock_sleep.side_effect = side_effect
        
        import types
        _trigger_initial_banners = Connection._trigger_initial_banners
        bound_method = types.MethodType(_trigger_initial_banners, mock_conn)
        
        await bound_method()
        
        # Verify MQTT was called to push banner
        assert mock_conn.mqtt_service.publish.call_count == 1
        args, _ = mock_conn.mqtt_service.publish.call_args
        assert args[0] == "device/MAC123/server"
        assert args[1]["type"] == "display"
        assert args[1]["action"] == "display_carousel"

@pytest.mark.asyncio
async def test_trigger_initial_banners_no_banners():
    """Test that banners don't trigger if no banners exist"""
    from app.ai.connection import Connection
    mock_conn = MagicMock(spec=Connection)
    mock_conn.logger = MagicMock()
    mock_conn.agent = {
        "banner_images": []
    }
    mock_conn.mqtt_service = MagicMock()
    mock_conn.mqtt_service.publish = AsyncMock()
    
    import types
    _trigger_initial_banners = Connection._trigger_initial_banners
    bound_method = types.MethodType(_trigger_initial_banners, mock_conn)
    
    await bound_method()
    
    # Verify it skips successfully without raising exception
    mock_conn.mqtt_service.publish.assert_not_called()

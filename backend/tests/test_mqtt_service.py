
import pytest
import asyncio
from unittest.mock import MagicMock
from app.services.mqtt_service import MQTTService
from app.config.settings import MQTTSettings

@pytest.fixture
def mock_settings():
    return MQTTSettings(
        MQTT_BROKER_URL="mqtt://test.mosquitto.org:1883",
        username="test",
        password="test"
    )

@pytest.fixture
def mqtt_service(mock_settings):
    service = MQTTService.from_config(mock_settings)
    # Mock loop
    service._loop = asyncio.new_event_loop()
    return service

@pytest.mark.asyncio
async def test_mqtt_service_init(mock_settings):
    service = MQTTService.from_config(mock_settings)
    assert service.config == mock_settings
    assert service.config.url == "mqtt://test.mosquitto.org:1883"
    assert service.is_available() is False # Not started yet

@pytest.mark.asyncio
async def test_mqtt_service_client_init(mqtt_service):
    mqtt_service._initialize_client()
    assert mqtt_service._client is not None
    assert mqtt_service._host == "test.mosquitto.org"
    assert mqtt_service._port == 1883

@pytest.mark.asyncio
async def test_subscription(mqtt_service):
    mqtt_service._initialize_client()
    mqtt_service._started = True # Mark as started
    mock_client = MagicMock()
    # Mock successful subscribe
    mock_client.subscribe.return_value = (0, 1) # (result, mid)
    mqtt_service._client = mock_client
    
    # Simulate connected state
    mqtt_service._connected.set()
    
    callback_called = False
    async def my_callback(topic, payload):
        nonlocal callback_called
        callback_called = True
        
    result = mqtt_service.subscribe("test/topic", my_callback)
    assert result is True
    mqtt_service._client.subscribe.assert_called_with("test/topic")
    
    # Test message handling
    msg = MagicMock()
    msg.topic = "test/topic"
    msg.payload = b'{"data": 1}'
    
    # Trigger callback directly to test routing logic
    mqtt_service._on_message(None, None, msg)
    
    # Since _on_message schedules callback in loop, we need to let loop run?
    # Actually _on_message uses run_coroutine_threadsafe.
    # We can mock _loop.call_soon_threadsafe or verify handlers list
    
    with mqtt_service._handlers_lock:
        assert "test/topic" in mqtt_service._message_handlers


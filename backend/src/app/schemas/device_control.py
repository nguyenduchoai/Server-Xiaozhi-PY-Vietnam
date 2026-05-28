"""
Device Control Schemas - MQTT commands for device control.

Commands:
- Radio control (play, stop, next, prev)
- Agent switch (change active agent on device)
- Volume control
- TTS speak command
"""

from typing import Literal, Optional, Annotated
from pydantic import BaseModel, Field


class RadioControlCommand(BaseModel):
    """Command to control radio on device via MQTT.
    
    Actions:
    - play: Start playing a specific station
    - stop: Stop current radio playback
    - next: Switch to next station
    - prev: Switch to previous station
    - volume: Adjust volume
    
    Example:
        {
            "action": "play",
            "station_id": "vov1",
            "volume": 4.5
        }
    """
    action: Literal["play", "stop", "next", "prev", "volume"] = Field(
        description="Radio control action"
    )
    station_id: Annotated[
        Optional[str], 
        Field(max_length=50, description="Station ID (required for 'play' action)")
    ] = None
    volume: Annotated[
        Optional[float],
        Field(ge=0.0, le=10.0, description="Volume level (0-10)")
    ] = None


class AgentSwitchCommand(BaseModel):
    """Command to switch active agent on device via MQTT.
    
    This allows changing the AI personality/template on the device
    without requiring WebSocket connection.
    
    Example:
        {
            "action": "switch",
            "template_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """
    action: Literal["switch", "reload"] = Field(
        default="switch",
        description="Agent control action: 'switch' to change template, 'reload' to refresh config"
    )
    template_id: Annotated[
        Optional[str],
        Field(max_length=36, description="Template ID to switch to (required for 'switch' action)")
    ] = None


class TTSCommand(BaseModel):
    """Command to speak text on device via MQTT.
    
    Example:
        {
            "text": "Hello world!",
            "voice": "vi-VN-HoaiMyNeural"
        }
    """
    text: Annotated[
        str,
        Field(min_length=1, max_length=1000, description="Text to speak")
    ]
    voice: Annotated[
        Optional[str],
        Field(max_length=100, description="Voice ID (optional, uses default if not provided)")
    ] = None


class DeviceControlRequest(BaseModel):
    """Generic device control request.
    
    Commands are sent to device via MQTT topic:
    device/{device_id}/control
    
    Device will respond (if online) via:
    device/{device_id}/status
    """
    type: Literal["radio", "agent", "tts", "restart", "ping"] = Field(
        description="Command type"
    )
    radio: Optional[RadioControlCommand] = None
    agent: Optional[AgentSwitchCommand] = None
    tts: Optional[TTSCommand] = None


class DeviceControlResponse(BaseModel):
    """Response from device control command."""
    success: bool
    message: str
    device_id: str
    mqtt_topic: Optional[str] = None

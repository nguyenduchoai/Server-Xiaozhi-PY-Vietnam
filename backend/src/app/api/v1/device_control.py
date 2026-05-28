"""
Device Control API - MQTT commands for remote device control.

Endpoints:
- POST /devices/{device_id}/control - Send control command to device
- POST /devices/{device_id}/radio - Control radio (shortcut)
- POST /devices/{device_id}/agent - Switch agent (shortcut)
- POST /devices/{device_id}/tts - Speak text (shortcut)

These endpoints publish commands to MQTT topics that the device subscribes to,
allowing control even when WebSocket is not active (device is in idle state).

MQTT Topics:
- device/{mac_address}/mcp - MCP control commands (firmware understands this)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.db.database import async_get_db
from app.core.logger import setup_logging
from app.models import Device
from app.schemas.device_control import (
    DeviceControlRequest,
    DeviceControlResponse,
    RadioControlCommand,
    AgentSwitchCommand,
    TTSCommand,
)
from app.services.mqtt_service import MQTTService
from app.services.notification_service import get_notification_service
from sqlalchemy import select

router = APIRouter()
logger = setup_logging()
TAG = __name__


def get_mqtt_service(request: Request) -> Optional[MQTTService]:
    """Get MQTT service from app state."""
    return getattr(request.app.state, "mqtt_service", None)


async def verify_device_ownership(
    device_id: str,
    user: dict,  # current_user returns dict, not User model
    session: AsyncSession,
) -> Device:
    """Verify that user owns this device."""
    
    # Handle both dict and User object
    user_id = user.get("id") if isinstance(user, dict) else user.id
    
    stmt = select(Device).where(
        Device.id == device_id,
        Device.user_id == user_id,
    )
    result = await session.execute(stmt)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or not owned by user"
        )
    
    return device


@router.post(
    "/{device_id}/control",
    response_model=DeviceControlResponse,
    summary="Send control command to device via MQTT",
    description="""
    Send a control command to a device via MQTT.
    
    This works even when device is in idle mode (not connected via WebSocket).
    Device must be online and connected to MQTT broker.
    
    Command types:
    - **radio**: Control radio playback (play, stop, next, prev, volume)
    - **agent**: Switch active agent/template
    - **tts**: Speak text on device
    - **restart**: Restart device
    - **ping**: Check if device is online
    """,
)
async def send_control_command(
    device_id: str,
    command: DeviceControlRequest,
    request: Request,
    session: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send control command to device via MQTT."""
    # Verify device ownership
    device = await verify_device_ownership(device_id, current_user, session)
    
    # Get MQTT service
    mqtt = get_mqtt_service(request)
    if not mqtt or not mqtt.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT service not available"
        )
    
    # Build MCP command (firmware understands this format)
    mqtt_topic = f"device/{device.mac_address}/mcp"
    
    if command.type == "radio" and command.radio:
        mqtt_payload = {
            "type": "mcp",
            "tool_name": f"self.radio.{command.radio.action}",
            "parameters": {
                "station_id": command.radio.station_id,
                "volume": command.radio.volume,
            }
        }
    elif command.type == "agent" and command.agent:
        mqtt_payload = {
            "type": "mcp",
            "tool_name": f"self.agent.{command.agent.action}",
            "parameters": {
                "template_id": command.agent.template_id,
            }
        }
    elif command.type == "tts" and command.tts:
        mqtt_payload = {
            "type": "mcp",
            "tool_name": "self.speaker.speak",
            "parameters": {
                "text": command.tts.text,
                "voice": command.tts.voice,
            }
        }
    else:
        mqtt_payload = {
            "type": "mcp",
            "tool_name": f"self.device.{command.type}",
            "parameters": {}
        }
    
    # Publish to MQTT
    success = await mqtt.publish(mqtt_topic, mqtt_payload)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish MQTT message"
        )
    
    logger.bind(tag=TAG).info(
        f"Sent {command.type} command to device {device.mac_address} via MQTT/MCP"
    )
    
    return DeviceControlResponse(
        success=True,
        message=f"{command.type.capitalize()} command sent successfully",
        device_id=device_id,
        mqtt_topic=mqtt_topic,
    )


@router.post(
    "/{device_id}/radio",
    response_model=DeviceControlResponse,
    summary="Control radio on device",
    description="""
    Shortcut endpoint for radio control.
    
    Actions:
    - **play**: Start playing a station (requires station_id)
    - **stop**: Stop current playback
    - **next**: Switch to next station
    - **prev**: Switch to previous station
    - **volume**: Adjust volume (requires volume parameter)
    """,
)
async def control_radio(
    device_id: str,
    command: RadioControlCommand,
    request: Request,
    session: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Control radio on device via MQTT."""
    # Verify device ownership
    device = await verify_device_ownership(device_id, current_user, session)
    
    # Validate play action has station_id
    if command.action == "play" and not command.station_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="station_id is required for 'play' action"
        )
    
    # Get MQTT service
    mqtt = get_mqtt_service(request)
    if not mqtt or not mqtt.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT service not available"
        )
    
    # Build MCP message (firmware understands this!)
    mqtt_topic = f"device/{device.mac_address}/mcp"
    mqtt_payload = {
        "type": "mcp",
        "tool_name": f"self.radio.{command.action}",
        "parameters": {
            k: v for k, v in command.model_dump(exclude_none=True).items() 
            if k != "action"
        }
    }
    
    # Publish to MQTT
    success = await mqtt.publish(mqtt_topic, mqtt_payload)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish MQTT message"
        )
    
    action_desc = {
        "play": f"Playing station {command.station_id}",
        "stop": "Radio stopped",
        "next": "Switching to next station",
        "prev": "Switching to previous station",
        "volume": f"Volume set to {command.volume}",
    }
    
    logger.bind(tag=TAG).info(
        f"Radio command '{command.action}' sent to device {device.mac_address}"
    )
    
    return DeviceControlResponse(
        success=True,
        message=action_desc.get(command.action, "Radio command sent"),
        device_id=device_id,
        mqtt_topic=mqtt_topic,
    )


@router.post(
    "/{device_id}/agent",
    response_model=DeviceControlResponse,
    summary="Switch agent on device",
    description="""
    Switch the active agent/template on device via MQTT.
    
    Actions:
    - **switch**: Change to a different template (requires template_id)
    - **reload**: Reload current configuration
    """,
)
async def switch_agent(
    device_id: str,
    command: AgentSwitchCommand,
    request: Request,
    session: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Switch agent on device via MQTT."""
    
    # Verify device ownership
    device = await verify_device_ownership(device_id, current_user, session)
    
    # Validate switch action has template_id
    if command.action == "switch" and not command.template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="template_id is required for 'switch' action"
        )
    
    # Get MQTT service
    mqtt = get_mqtt_service(request)
    if not mqtt or not mqtt.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT service not available"
        )
    
    # Build MCP message
    mqtt_topic = f"device/{device.mac_address}/mcp"
    mqtt_payload = {
        "type": "mcp",
        "tool_name": f"self.agent.{command.action}",
        "parameters": {
            "template_id": command.template_id,
        }
    }
    
    # Publish to MQTT
    success = await mqtt.publish(mqtt_topic, mqtt_payload)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish MQTT message"
        )
    
    action_desc = {
        "switch": f"Switching to template {command.template_id}",
        "reload": "Reloading configuration",
    }
    
    logger.bind(tag=TAG).info(
        f"Agent command '{command.action}' sent to device {device.mac_address}"
    )
    
    return DeviceControlResponse(
        success=True,
        message=action_desc.get(command.action, "Agent command sent"),
        device_id=device_id,
        mqtt_topic=mqtt_topic,
    )


@router.post(
    "/{device_id}/tts",
    response_model=DeviceControlResponse,
    summary="Speak text on device",
    description="""
    Make the device speak text via MQTT.
    
    This is useful for:
    - Sending announcements to device
    - Testing TTS without voice command
    - Remote notifications with custom voice
    """,
)
async def speak_text(
    device_id: str,
    command: TTSCommand,
    request: Request,
    session: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Speak text on device via WebSocket notification (primary) or MQTT (fallback)."""
    
    # Verify device ownership
    device = await verify_device_ownership(device_id, current_user, session)
    
    # Try WebSocket notification first (this is the working method)
    notification_service = get_notification_service()
    
    # Check if device is connected via WebSocket
    if device_id in notification_service.get_active_devices():
        # Send via WebSocket - this triggers TTS on device!
        success = await notification_service.send_notification(
            device_id=device_id,
            message=command.text,
            notification_type="tts",  # Custom type for pure TTS
            speak=True,  # This triggers the TTS!
        )
        
        if success:
            logger.bind(tag=TAG).info(
                f"TTS sent via WebSocket to {device.mac_address}: '{command.text[:50]}...'"
            )
            return DeviceControlResponse(
                success=True,
                message=f"TTS sent via WebSocket: {command.text[:50]}...",
                device_id=device_id,
                mqtt_topic=None,
            )
    
    # Fallback to MQTT notification if no WebSocket connection
    mqtt = get_mqtt_service(request)
    if not mqtt or not mqtt.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device not connected (no WebSocket) and MQTT service not available"
        )
    
    # Build notification message - firmware handles 'notification' type and displays text
    # Note: TTS audio requires active UDP session which idle devices don't have
    mqtt_topic = f"device/{device.mac_address}/server"
    mqtt_payload = {
        "type": "notification",
        "notification_type": "tts",
        "title": "Tin nhắn",
        "content": command.text,
        "useLLM": False,  # Direct TTS, no LLM processing
    }
    
    # Publish to MQTT
    success = await mqtt.publish(mqtt_topic, mqtt_payload)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish MQTT message"
        )
    
    logger.bind(tag=TAG).info(
        f"TTS notification sent via MQTT to {device.mac_address}: '{command.text[:50]}...'"
    )
    
    return DeviceControlResponse(
        success=True,
        message=f"Notification sent via MQTT (text display only, TTS requires active session): {command.text[:50]}...",
        device_id=device_id,
        mqtt_topic=mqtt_topic,
    )


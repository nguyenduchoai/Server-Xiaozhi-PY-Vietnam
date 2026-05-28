"""
Notifications API - Send and manage push notifications to devices.
"""

from typing import Annotated, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user, async_get_db
from ...core.logger import get_logger
from ...services.notification_service import get_notification_service
from ...crud.crud_device import crud_device
from ...services.mqtt_presence_tracker import get_presence_tracker

logger = get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationRequest(BaseModel):
    """Request body for sending notification."""
    message: str = Field(..., min_length=1, max_length=500)
    notification_type: str = Field(default="info", pattern="^(info|warning|alert|reminder)$")
    speak: bool = Field(default=True, description="Whether device should speak the message")
    data: dict = Field(default_factory=dict, description="Additional data payload")


class BroadcastRequest(BaseModel):
    """Request body for broadcasting to multiple devices."""
    message: str = Field(..., min_length=1, max_length=500)
    notification_type: str = Field(default="info")
    speak: bool = Field(default=True)
    device_ids: Optional[List[str]] = Field(default=None, description="List of device IDs (null = all devices)")


@router.post("/send/{device_id}")
async def send_notification(
    device_id: str,
    request_body: NotificationRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    request: Request,
):
    """
    Send notification to a specific device + external channels (Telegram/Zalo OA).

    Device delivery:
    1. WebSocket (if device is actively connected)
    2. MQTT (if device is idle but connected via MQTT)

    External channels (per agent config):
    - Telegram Bot
    - Zalo OA (Official Account)
    """
    
    notification_service = get_notification_service()
    result = {"device_id": device_id, "sent_at": datetime.now(timezone.utc).isoformat()}
    
    # Check WebSocket first
    active_devices = notification_service.get_active_devices()
    if device_id in active_devices:
        success = await notification_service.send_notification(
            device_id=device_id,
            message=request_body.message,
            notification_type=request_body.notification_type,
            speak=request_body.speak,
            data=request_body.data,
        )
        result.update({"success": success, "method": "websocket"})
    else:
        # Try MQTT fallback
        try:
            device = await crud_device.get(db=db, id=device_id)
            if not device:
                raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
            
            mac_address = device.get("mac_address") if isinstance(device, dict) else device.mac_address
            if not mac_address:
                raise HTTPException(status_code=400, detail="Device has no MAC address")
            
            tracker = get_presence_tracker()
            if not tracker.is_device_online(mac_address):
                raise HTTPException(
                    status_code=404,
                    detail=f"Device {device_id} is not connected (neither WebSocket nor MQTT)"
                )
            
            mqtt_service = getattr(request.app.state, 'mqtt_service', None)
            if not mqtt_service or not mqtt_service.is_available():
                raise HTTPException(status_code=503, detail="MQTT service not available")
            
            topic = f"device/{mac_address}/server"
            payload = {
                "type": "notification",
                "title": request_body.notification_type,
                "content": request_body.message,
                "useLLM": request_body.speak,
            }
            
            success = await mqtt_service.publish(topic, payload)
            result.update({"success": success, "method": "mqtt", "topic": topic})
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send notification via MQTT: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")
    
    # Also route to external channels (Telegram, Zalo) if agent has them configured
    try:
        from ...models.agent import Agent
        from sqlalchemy import select as sql_select
        
        agent_result = await db.execute(
            sql_select(Agent).where(Agent.user_id == current_user["id"]).limit(1)
        )
        agent = agent_result.scalar_one_or_none()
        
        if agent and agent.notification_channels:
            from ...services.notification_channel_router import get_notification_router
            router = get_notification_router()
            
            channel_result = await router.send_notification(
                notification_channels=agent.notification_channels,
                message=request_body.message,
                level=request_body.notification_type,
                agent_name=agent.agent_name,
                agent_id=str(agent.id),
                notification_type="alert",
            )
            result["external_channels"] = channel_result
    except Exception as e:
        logger.warning(f"External channel delivery failed: {e}")
        result["external_channels_error"] = str(e)
    
    result["message"] = request_body.message[:50] + "..." if len(request_body.message) > 50 else request_body.message
    return result


@router.post("/broadcast")
async def broadcast_notification(
    request: BroadcastRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    fastapi_request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """
    Broadcast notification to multiple devices.
    
    If device_ids is null, sends to all connected devices (WebSocket + MQTT).
    Priority: WebSocket first, then MQTT fallback.
    """
    
    notification_service = get_notification_service()
    mqtt_service = getattr(fastapi_request.app.state, 'mqtt_service', None)
    tracker = get_presence_tracker()
    
    results = {}
    
    # Get WebSocket connected devices
    ws_devices = set(notification_service.get_active_devices())
    
    # Get MQTT connected devices  
    mqtt_devices = set()
    try:
        mqtt_devices = await tracker.get_online_devices()
    except Exception:
        pass
    
    # Determine target devices
    if request.device_ids:
        target_devices = set(request.device_ids)
    else:
        # All available devices (WebSocket + MQTT)
        target_devices = ws_devices | mqtt_devices
    
    for device_id in target_devices:
        # Try WebSocket first
        if device_id in ws_devices:
            success = await notification_service.send_notification(
                device_id=device_id,
                message=request.message,
                notification_type=request.notification_type,
                speak=request.speak,
            )
            results[device_id] = {"success": success, "method": "websocket"}
            continue
        
        # MQTT fallback - try active session first for TTS support
        if device_id in mqtt_devices and mqtt_service and mqtt_service.is_available():
            try:
                mac_address = device_id
                
                # Check if device has an active MQTT session with TTS capability
                from ...services.mqtt_connection_handler import get_mqtt_connection_manager
                from ...ai.handle.textHandler.notificationMessageHandler import NotificationMessageHandler
                
                manager = get_mqtt_connection_manager()
                handler = manager.get_connection_by_mac(mac_address) if manager else None
                
                if handler and hasattr(handler, 'tts') and handler.tts:
                    # Device has active session with TTS - send with voice
                    try:
                        notification_handler = NotificationMessageHandler()
                        msg_json = {
                            "type": "notification",
                            "title": request.notification_type,
                            "content": request.message,
                            "useLLM": False,  # Direct TTS, no LLM
                        }
                        await notification_handler.handle(handler, msg_json)
                        results[device_id] = {"success": True, "method": "mqtt_tts"}
                    except Exception as tts_err:
                        logger.warning(f"MQTT TTS failed for {device_id}: {tts_err}, falling back to alert")
                        # Fall through to alert
                        raise
                else:
                    # No active session - send notification type, device will initiate TTS
                    topic = f"device/{mac_address}/server"
                    payload = {
                        "type": "notification",
                        "title": request.notification_type,
                        "content": request.message,
                        "useLLM": request.speak,
                    }
                    success = await mqtt_service.publish(topic, payload)
                    results[device_id] = {"success": success, "method": "mqtt_notify"}
            except Exception as e:
                logger.error(f"MQTT broadcast failed for {device_id}: {e}")
                results[device_id] = {"success": False, "method": "mqtt", "error": str(e)}
            continue
        
        # Device not available
        results[device_id] = {"success": False, "method": "none", "error": "Device not connected"}
    
    # Also route to external channels (Telegram, Zalo) per-agent
    external_channels_result = None
    try:
        from ...models.agent import Agent
        from sqlalchemy import select as sql_select
        
        agent_result = await db.execute(
            sql_select(Agent).where(Agent.user_id == current_user["id"]).limit(1)
        )
        agent = agent_result.scalar_one_or_none()
        
        if agent and agent.notification_channels:
            from ...services.notification_channel_router import get_notification_router
            channel_router = get_notification_router()
            
            external_channels_result = await channel_router.send_notification(
                notification_channels=agent.notification_channels,
                message=request.message,
                level=request.notification_type,
                agent_name=agent.agent_name,
                agent_id=str(agent.id),
                notification_type="alert",
            )
    except Exception as e:
        logger.warning(f"External channel broadcast failed: {e}")
        external_channels_result = {"error": str(e)}
    
    return {
        "total": len(results),
        "successful": sum(1 for v in results.values() if v.get("success")),
        "failed": sum(1 for v in results.values() if not v.get("success")),
        "results": results,
        "external_channels": external_channels_result,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/devices/connected")
async def get_connected_devices(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Get list of currently connected devices that can receive notifications.
    """
    notification_service = get_notification_service()
    active_devices = notification_service.get_active_devices()
    
    return {
        "connected_devices": active_devices,
        "count": len(active_devices),
    }


@router.post("/speak/{device_id}")
async def speak_to_device(
    device_id: str,
    message: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Make device speak a message via TTS (shortcut endpoint).
    
    Useful for quick voice messages without full notification payload.
    """
    notification_service = get_notification_service()
    
    success = await notification_service.send_notification(
        device_id=device_id,
        message=message,
        notification_type="info",
        speak=True,
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} is not connected or failed to send"
        )
    
    return {
        "success": True,
        "device_id": device_id,
        "message": message,
    }


@router.get("/devices/mqtt")
async def get_mqtt_connected_devices(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Get list of devices connected via MQTT (including idle devices).
    
    These devices can receive push notifications even when not actively speaking.
    """
    try:
        from ...services.mqtt_presence_tracker import get_presence_tracker
        
        tracker = get_presence_tracker()
        online_macs = await tracker.get_online_devices()
        
        return {
            "mqtt_connected_devices": list(online_macs),
            "count": len(online_macs),
            "tracking_active": tracker._started,
        }
    except Exception as e:
        logger.warning(f"Failed to get MQTT connected devices: {e}")
        return {
            "mqtt_connected_devices": [],
            "count": 0,
            "tracking_active": False,
            "error": str(e),
        }


@router.get("/devices/all")
async def get_all_available_devices(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Get all available devices (WebSocket connected + MQTT connected).
    
    Returns combined list showing which connection type each device has.
    """
    notification_service = get_notification_service()
    ws_devices = notification_service.get_active_devices()
    
    mqtt_devices = set()
    try:
        from ...services.mqtt_presence_tracker import get_presence_tracker
        tracker = get_presence_tracker()
        mqtt_devices = await tracker.get_online_devices()
    except Exception:
        pass
    
    # Combine results
    all_devices = {}
    for device_id in ws_devices:
        all_devices[device_id] = {"websocket": True, "mqtt": False}
    
    for mac in mqtt_devices:
        if mac in all_devices:
            all_devices[mac]["mqtt"] = True
        else:
            all_devices[mac] = {"websocket": False, "mqtt": True}
    
    return {
        "devices": all_devices,
        "websocket_count": len(ws_devices),
        "mqtt_count": len(mqtt_devices),
        "total_unique": len(all_devices),
    }


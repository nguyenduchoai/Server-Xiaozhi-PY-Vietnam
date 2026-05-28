"""
Device Display API - Sync display config and push custom screens
Provides endpoints for:
- Display configuration sync
- Custom screen push
- Theme management
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.db.database import async_get_db
from app.core.logger import get_logger
from app.api.dependencies import get_current_user
from app.crud.crud_device import crud_device
from app.schemas.device import DeviceRead
from app.services.mqtt_service import MQTTService
from app.models.emoji_pack import EmojiPack
from sqlalchemy import select

logger = get_logger(__name__)
router = APIRouter(prefix="/devices", tags=["Device Display"])


# ============ Schemas ============

class DisplayConfigRequest(BaseModel):
    """Display configuration sync request"""
    brightness: int | None = Field(None, ge=0, le=100, description="Brightness 0-100")
    theme: str | None = Field(None, description="Theme name: dark, light, auto")
    rotation: int | None = Field(None, description="Rotation: 0, 90, 180, 270")
    backlight_timeout: int | None = Field(None, ge=0, description="Backlight timeout in seconds")
    show_clock: bool | None = Field(None, description="Show clock on idle")
    show_weather: bool | None = Field(None, description="Show weather on idle")


class DisplayConfigResponse(BaseModel):
    """Display configuration response"""
    device_id: str
    brightness: int = 80
    theme: str = "auto"
    rotation: int = 0
    backlight_timeout: int = 30
    show_clock: bool = True
    show_weather: bool = True


class CustomScreenRequest(BaseModel):
    """Custom screen push request"""
    screen_type: str = Field(..., description="Screen type: text, image, widget, notification")
    title: str | None = Field(None, description="Title text")
    content: str | None = Field(None, description="Content text or image URL")
    duration: int = Field(5, ge=1, le=60, description="Display duration in seconds")
    priority: int = Field(1, ge=1, le=10, description="Priority 1-10, higher = more important")
    icon: str | None = Field(None, description="Icon name or URL")
    background_color: str | None = Field(None, description="Background color hex")
    text_color: str | None = Field(None, description="Text color hex")


class EmojiPackInfo(BaseModel):
    """Emoji pack information"""
    pack_id: str
    name: str
    version: str
    download_url: str
    checksum: str
    size: int


# ============ Display Config API ============

@router.get(
    "/{device_id}/display/config",
    response_model=DisplayConfigResponse,
    summary="Get display configuration"
)
async def get_display_config(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get current display configuration for a device"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # TODO: Get from device metadata or cache
    # For now return defaults
    return DisplayConfigResponse(
        device_id=device_id,
        brightness=80,
        theme="auto",
        rotation=0,
        backlight_timeout=30,
        show_clock=True,
        show_weather=True,
    )


@router.put(
    "/{device_id}/display/config",
    summary="Update display configuration"
)
async def update_display_config(
    device_id: str,
    config: DisplayConfigRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update display configuration and push to device via MQTT"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Build MCP command
    mcp_commands = []
    
    if config.brightness is not None:
        mcp_commands.append({
            "tool": "self.screen.set_brightness",
            "params": {"brightness": config.brightness}
        })
    
    if config.theme is not None:
        mcp_commands.append({
            "tool": "self.screen.set_theme",
            "params": {"theme": config.theme}
        })
    
    if config.rotation is not None:
        mcp_commands.append({
            "tool": "self.screen.set_rotation",
            "params": {"rotation": config.rotation}
        })
    
    # Push via MQTT
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            for cmd in mcp_commands:
                await mqtt_service.publish(
                    f"device/{device.mac_address}/mcp",
                    {
                        "type": "mcp",
                        "tool_name": cmd["tool"],
                        "parameters": cmd["params"]
                    }
                )
            logger.info(f"Pushed {len(mcp_commands)} display config commands to {device_id}")
    except Exception as e:
        logger.warning(f"Failed to push display config via MQTT: {e}")
    
    return {
        "success": True,
        "message": f"Display config updated, {len(mcp_commands)} commands pushed",
        "device_id": device_id,
        "updated_fields": [k for k, v in config.model_dump().items() if v is not None]
    }


# ============ Custom Screen Push API ============

@router.post(
    "/{device_id}/display/push",
    summary="Push custom screen to device"
)
async def push_custom_screen(
    device_id: str,
    screen: CustomScreenRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Push a custom screen/notification to device display"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Build display payload
    display_payload = {
        "type": "display_push",
        "screen_type": screen.screen_type,
        "title": screen.title,
        "content": screen.content,
        "duration": screen.duration,
        "priority": screen.priority,
        "icon": screen.icon,
        "background_color": screen.background_color,
        "text_color": screen.text_color,
    }
    
    # Push via MQTT
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/display",
                display_payload
            )
            logger.info(f"Pushed custom screen to {device_id}: {screen.screen_type}")
            return {
                "success": True,
                "message": "Custom screen pushed",
                "device_id": device_id,
                "screen_type": screen.screen_type
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="MQTT service not available"
            )
    except Exception as e:
        logger.error(f"Failed to push custom screen: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to push screen: {str(e)}"
        )


# ============ Emoji Pack OTA API ============

@router.get(
    "/{device_id}/emoji-packs/available",
    summary="List available emoji packs for OTA"
)
async def list_available_emoji_packs(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List emoji packs available for download via OTA"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get emoji packs from database
    
    result = await db.execute(
        select(EmojiPack).where(EmojiPack.is_active == True).limit(200)
    )
    packs = result.scalars().all()
    
    return {
        "device_id": device_id,
        "emoji_packs": [
            {
                "pack_id": str(pack.id),
                "name": pack.name,
                "version": getattr(pack, "version", "1.0.0"),
                "download_url": f"/api/v1/devices/{device_id}/emoji-packs/{pack.id}/download",
                "preview_url": pack.preview_url if hasattr(pack, "preview_url") else None,
            }
            for pack in packs
        ]
    }


@router.post(
    "/{device_id}/emoji-packs/{pack_id}/install",
    summary="Push emoji pack install command to device"
)
async def install_emoji_pack(
    device_id: str,
    pack_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Push command to device to download and install emoji pack"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get pack info
    
    result = await db.execute(
        select(EmojiPack).where(EmojiPack.id == pack_id)
    )
    pack = result.scalar_one_or_none()
    
    if not pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    # Build OTA install command
    install_payload = {
        "type": "emoji_ota",
        "action": "install",
        "pack_id": pack_id,
        "pack_name": pack.name,
        "download_url": f"/api/v1/emoji-packs/{pack_id}/assets",
    }
    
    # Push via MQTT
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/ota",
                install_payload
            )
            logger.info(f"Pushed emoji pack install to {device_id}: {pack.name}")
            return {
                "success": True,
                "message": f"Emoji pack '{pack.name}' install command sent",
                "device_id": device_id,
                "pack_id": pack_id
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="MQTT service not available"
            )
    except Exception as e:
        logger.error(f"Failed to push emoji install: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to push install command: {str(e)}"
        )

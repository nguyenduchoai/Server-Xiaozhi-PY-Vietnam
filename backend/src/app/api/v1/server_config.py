"""
Server Configuration API - Manage multi-server settings for devices
Enables devices to switch between different server configurations (e.g., dev, staging, production)
"""

from typing import Annotated, Optional, List
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.db.database import async_get_db
from app.core.logger import get_logger
from app.api.dependencies import get_current_user
from app.crud.crud_device import crud_device
from app.schemas.device import DeviceRead
from app.services.mqtt_service import MQTTService

logger = get_logger(__name__)
router = APIRouter(prefix="/servers", tags=["Server Configuration"])


# ============ Schemas ============

class ServerConfig(BaseModel):
    """Server configuration"""
    id: str
    name: str
    description: Optional[str] = None
    websocket_url: str
    api_url: str
    mqtt_host: Optional[str] = None
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    region: Optional[str] = None
    created_at: Optional[str] = None


class ServerConfigCreate(BaseModel):
    """Create server config request"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    websocket_url: str = Field(..., min_length=10)
    api_url: str = Field(..., min_length=10)
    mqtt_host: Optional[str] = None
    mqtt_port: int = Field(default=1883)
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    region: Optional[str] = None


class ServerConfigUpdate(BaseModel):
    """Update server config request"""
    name: Optional[str] = None
    description: Optional[str] = None
    websocket_url: Optional[str] = None
    api_url: Optional[str] = None
    mqtt_host: Optional[str] = None
    mqtt_port: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    region: Optional[str] = None


class DeviceServerAssignment(BaseModel):
    """Assign device to server"""
    server_id: str


# ============ In-Memory Storage (TODO: Move to Database) ============
# For now, using memory. Should be migrated to database table later.

import os as _os

_SITE_DOMAIN = _os.environ.get("SITE_DOMAIN", "")
_STAGING_DOMAIN = _os.environ.get("STAGING_DOMAIN", "")

_server_configs: dict[str, ServerConfig] = {}

# Only populate if domain is configured via env
if _SITE_DOMAIN:
    _server_configs["prod-vn"] = ServerConfig(
        id="prod-vn",
        name="Production Vietnam",
        description="Server sản phẩm tại Việt Nam",
        websocket_url=f"wss://{_SITE_DOMAIN}/ws",
        api_url=f"https://{_SITE_DOMAIN}/api/v1",
        mqtt_host=f"mqtt.{_SITE_DOMAIN}",
        mqtt_port=1883,
        is_default=True,
        is_active=True,
        region="VN",
        created_at=datetime.utcnow().isoformat(),
    )

if _STAGING_DOMAIN:
    _server_configs["staging-vn"] = ServerConfig(
        id="staging-vn",
        name="Staging Vietnam",
        description="Server thử nghiệm",
        websocket_url=f"wss://{_STAGING_DOMAIN}/ws",
        api_url=f"https://{_STAGING_DOMAIN}/api/v1",
        mqtt_host=f"mqtt-staging.{_STAGING_DOMAIN}",
        mqtt_port=1883,
        is_default=False,
        is_active=True,
        region="VN",
        created_at=datetime.utcnow().isoformat(),
    )

_device_server_map: dict[str, str] = {}  # device_id -> server_id


# ============ Endpoints ============

@router.get(
    "",
    response_model=List[ServerConfig],
    summary="List available servers"
)
async def list_servers(
    region: Optional[str] = Query(None, description="Filter by region"),
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """
    List all available server configurations.
    Only admins can see inactive servers.
    """
    servers = list(_server_configs.values())
    
    # Filter inactive for non-admins
    if not current_user.get("is_superuser"):
        servers = [s for s in servers if s.is_active]
    
    # Filter by region
    if region:
        servers = [s for s in servers if s.region == region]
    
    return servers


@router.get(
    "/{server_id}",
    response_model=ServerConfig,
    summary="Get server details"
)
async def get_server(
    server_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get server configuration by ID"""
    if server_id not in _server_configs:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = _server_configs[server_id]
    
    if not server.is_active and not current_user.get("is_superuser"):
        raise HTTPException(status_code=404, detail="Server not found")
    
    return server


@router.post(
    "",
    response_model=ServerConfig,
    summary="Create server config"
)
async def create_server(
    request: ServerConfigCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new server configuration (Admin only)"""
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    server_id = str(uuid.uuid4())[:8]
    
    server = ServerConfig(
        id=server_id,
        name=request.name,
        description=request.description,
        websocket_url=request.websocket_url,
        api_url=request.api_url,
        mqtt_host=request.mqtt_host,
        mqtt_port=request.mqtt_port,
        mqtt_username=request.mqtt_username,
        mqtt_password=request.mqtt_password,
        is_default=False,
        is_active=True,
        region=request.region,
        created_at=datetime.utcnow().isoformat(),
    )
    
    _server_configs[server_id] = server
    logger.info(f"Created server config: {server_id}")
    
    return server


@router.put(
    "/{server_id}",
    response_model=ServerConfig,
    summary="Update server config"
)
async def update_server(
    server_id: str,
    request: ServerConfigUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update server configuration (Admin only)"""
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if server_id not in _server_configs:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = _server_configs[server_id]
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(server, key):
            setattr(server, key, value)
    
    _server_configs[server_id] = server
    logger.info(f"Updated server config: {server_id}")
    
    return server


@router.delete(
    "/{server_id}",
    summary="Delete server config"
)
async def delete_server(
    server_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete server configuration (Admin only)"""
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if server_id not in _server_configs:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = _server_configs[server_id]
    if server.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default server")
    
    del _server_configs[server_id]
    logger.info(f"Deleted server config: {server_id}")
    
    return {"success": True, "message": "Server deleted"}


# ============ Device Server Assignment ============

@router.get(
    "/devices/{device_id}/server",
    summary="Get device's server assignment"
)
async def get_device_server(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get the server a device is assigned to"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    server_id = _device_server_map.get(device_id)
    
    if not server_id:
        # Return default server
        default = next((s for s in _server_configs.values() if s.is_default), None)
        return {
            "device_id": device_id,
            "server": default,
            "is_default": True,
        }
    
    server = _server_configs.get(server_id)
    return {
        "device_id": device_id,
        "server": server,
        "is_default": False,
    }


@router.put(
    "/devices/{device_id}/server",
    summary="Assign device to server"
)
async def assign_device_server(
    device_id: str,
    assignment: DeviceServerAssignment,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Assign a device to a specific server.
    Pushes new server config to device via MQTT.
    """
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify server exists
    if assignment.server_id not in _server_configs:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = _server_configs[assignment.server_id]
    if not server.is_active:
        raise HTTPException(status_code=400, detail="Server is not active")
    
    # Update assignment
    _device_server_map[device_id] = assignment.server_id
    logger.info(f"Device {device_id} assigned to server {assignment.server_id}")
    
    # Push to device via MQTT
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/server",
                {
                    "type": "server_switch",
                    "server_id": server.id,
                    "server_name": server.name,
                    "websocket_url": server.websocket_url,
                    "api_url": server.api_url,
                    "mqtt_host": server.mqtt_host,
                    "mqtt_port": server.mqtt_port,
                    "mqtt_username": server.mqtt_username,
                    # Note: Password should be encrypted in production
                }
            )
            logger.info(f"Server config pushed to device {device_id}")
    except Exception as e:
        logger.warning(f"Failed to push server config via MQTT: {e}")
    
    return {
        "success": True,
        "message": f"Device assigned to {server.name}",
        "device_id": device_id,
        "server_id": server.id,
    }


@router.post(
    "/devices/{device_id}/reset-server",
    summary="Reset device to default server"
)
async def reset_device_server(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Reset device to use default server"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Remove custom assignment
    if device_id in _device_server_map:
        del _device_server_map[device_id]
    
    # Get default server
    default = next((s for s in _server_configs.values() if s.is_default), None)
    if not default:
        raise HTTPException(status_code=500, detail="No default server configured")
    
    # Push to device
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/server",
                {
                    "type": "server_reset",
                    "use_default": True,
                    "server_id": default.id,
                    "websocket_url": default.websocket_url,
                }
            )
    except Exception as e:
        logger.warning(f"Failed to reset server via MQTT: {e}")
    
    return {
        "success": True,
        "message": "Device reset to default server",
        "device_id": device_id,
        "server": default,
    }

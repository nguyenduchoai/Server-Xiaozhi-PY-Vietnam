"""
Device Camera API - Receive and manage images from IoT devices
Provides endpoints for:
- Image upload from device
- Image storage and retrieval
- Camera snapshot trigger
- Image analysis (optional AI vision)
"""

import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Header
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.db.database import async_get_db
from app.core.logger import get_logger
from app.api.dependencies import get_current_user
from app.crud.crud_device import crud_device
from app.services.mqtt_service import MQTTService

logger = get_logger(__name__)
router = APIRouter(prefix="/devices", tags=["Device Camera"])

# Storage path for device images
CAMERA_STORAGE_PATH = Path("/app/data/assets/camera")
CAMERA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Max file size: 10MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# Allowed image types
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


# ============ Schemas ============

class CameraImageInfo(BaseModel):
    """Camera image information"""
    image_id: str
    device_id: str
    filename: str
    size: int
    content_type: str
    captured_at: datetime
    url: str
    thumbnail_url: Optional[str] = None
    metadata: Optional[dict] = None


class CameraSnapshotRequest(BaseModel):
    """Request to trigger camera snapshot"""
    quality: int = Field(80, ge=10, le=100, description="JPEG quality 10-100")
    resolution: Optional[str] = Field(None, description="Resolution: 320x240, 640x480, 1280x720")


class ImageAnalysisResult(BaseModel):
    """Image analysis result from AI vision"""
    image_id: str
    description: str
    objects: list[str] = []
    text_detected: Optional[str] = None
    confidence: float = 0.0


# ============ In-memory image registry (TODO: move to DB) ============
# Simple dict to track uploaded images
_image_registry: dict[str, dict] = {}


# ============ Camera Image Upload API ============

@router.post(
    "/{device_id}/camera/upload",
    summary="Upload image from device camera"
)
async def upload_camera_image(
    device_id: str,
    file: UploadFile = File(...),
    captured_at: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    authorization: str = Header(...),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
):
    """
    Upload image from device camera.

    Auth (hardened): requires the device's bearer token in Authorization
    header. Previously this endpoint had no auth and accepted uploads from
    anyone who knew (or guessed) a device_id — allowing flooding of /uploads/
    storage with arbitrary images.
    """
    # === Auth: verify device token, ensure header device_id matches claim ===
    from ...config.config_loader import load_config
    from ...ai.utils import AuthToken
    cfg = load_config()
    auth_key = cfg.get("server", {}).get("auth_key", "") or ""
    if not auth_key or (isinstance(auth_key, str) and auth_key.startswith("${")):
        raise HTTPException(status_code=500, detail="Server auth key not configured")

    token = authorization or ""
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization")

    auth_token = AuthToken(secret_key=auth_key)
    is_valid, extracted = auth_token.verify_token(token)
    if not is_valid or extracted != device_id:
        raise HTTPException(status_code=401, detail="Invalid or mismatched token")

    # Verify device exists in DB and is not deleted
    device = await crud_device.get_by_mac(db, device_id) if db else None
    if not device:
        device = await crud_device.get(db=db, id=device_id) if db else None
    if not device:
        raise HTTPException(status_code=404, detail="Device not registered")

    # Capability gate: refuse if FW reported no camera hardware
    caps = device.capabilities or {}
    if caps and not caps.get("can_camera", caps.get("has_camera", True)):
        raise HTTPException(
            status_code=400,
            detail="Device hardware does not support camera",
        )

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_IMAGE_SIZE // 1024 // 1024}MB"
        )
    
    # Generate unique image ID
    image_id = str(uuid.uuid4())
    
    # Calculate checksum
    checksum = hashlib.md5(content).hexdigest()
    
    # Create device folder
    device_folder = CAMERA_STORAGE_PATH / device_id
    device_folder.mkdir(parents=True, exist_ok=True)
    
    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{image_id[:8]}{ext}"
    filepath = device_folder / filename
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    logger.info(f"Saved camera image from {device_id}: {filename} ({len(content)} bytes)")
    
    # Register image
    image_info = {
        "image_id": image_id,
        "device_id": device_id,
        "filename": filename,
        "filepath": str(filepath),
        "size": len(content),
        "content_type": file.content_type or "image/jpeg",
        "checksum": checksum,
        "captured_at": captured_at or datetime.now().isoformat(),
        "metadata": metadata,
    }
    _image_registry[image_id] = image_info
    
    return {
        "success": True,
        "image_id": image_id,
        "filename": filename,
        "size": len(content),
        "url": f"/api/v1/devices/{device_id}/camera/images/{image_id}",
    }


@router.get(
    "/{device_id}/camera/images",
    summary="List camera images from device"
)
async def list_camera_images(
    device_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """List all camera images from a device"""
    # Verify device ownership
    if db and current_user:
        device = await crud_device.get(db=db, id=device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get images from registry
    device_images = [
        img for img in _image_registry.values()
        if img["device_id"] == device_id
    ]
    
    # Sort by captured_at descending
    device_images.sort(key=lambda x: x.get("captured_at", ""), reverse=True)
    
    # Apply pagination
    paginated = device_images[offset:offset + limit]
    
    return {
        "device_id": device_id,
        "total": len(device_images),
        "images": [
            {
                "image_id": img["image_id"],
                "filename": img["filename"],
                "size": img["size"],
                "captured_at": img["captured_at"],
                "url": f"/api/v1/devices/{device_id}/camera/images/{img['image_id']}",
            }
            for img in paginated
        ]
    }


@router.get(
    "/{device_id}/camera/images/{image_id}",
    summary="Get camera image"
)
async def get_camera_image(
    device_id: str,
    image_id: str,
):
    """Get a specific camera image file"""
    if image_id not in _image_registry:
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_info = _image_registry[image_id]
    if image_info["device_id"] != device_id:
        raise HTTPException(status_code=404, detail="Image not found for this device")
    
    filepath = Path(image_info["filepath"])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(
        filepath,
        media_type=image_info["content_type"],
        filename=image_info["filename"]
    )


@router.delete(
    "/{device_id}/camera/images/{image_id}",
    summary="Delete camera image"
)
async def delete_camera_image(
    device_id: str,
    image_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a camera image"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if image_id not in _image_registry:
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_info = _image_registry[image_id]
    if image_info["device_id"] != device_id:
        raise HTTPException(status_code=404, detail="Image not found for this device")
    
    # Delete file
    filepath = Path(image_info["filepath"])
    if filepath.exists():
        filepath.unlink()
    
    # Remove from registry
    del _image_registry[image_id]
    
    logger.info(f"Deleted camera image {image_id} from {device_id}")
    
    return {
        "success": True,
        "message": "Image deleted",
        "image_id": image_id
    }


# ============ Camera Control API ============

@router.post(
    "/{device_id}/camera/snapshot",
    summary="Trigger camera snapshot on device"
)
async def trigger_camera_snapshot(
    device_id: str,
    request: CameraSnapshotRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Send command to device to take a camera snapshot"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Build MCP command
    snapshot_command = {
        "type": "mcp",
        "tool_name": "self.camera.take_photo",
        "parameters": {
            "quality": request.quality,
            "resolution": request.resolution,
            "upload_url": f"/api/v1/devices/{device_id}/camera/upload"
        }
    }
    
    # Push via MQTT
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/mcp",
                snapshot_command
            )
            logger.info(f"Triggered camera snapshot on {device_id}")
            return {
                "success": True,
                "message": "Snapshot command sent",
                "device_id": device_id,
                "quality": request.quality,
                "resolution": request.resolution
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="MQTT service not available"
            )
    except Exception as e:
        logger.error(f"Failed to trigger snapshot: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send snapshot command: {str(e)}"
        )


# ============ Image Analysis API (Optional AI Vision) ============

@router.post(
    "/{device_id}/camera/images/{image_id}/analyze",
    response_model=ImageAnalysisResult,
    summary="Analyze camera image with AI vision"
)
async def analyze_camera_image(
    device_id: str,
    image_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Analyze image using AI vision model"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if image_id not in _image_registry:
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_info = _image_registry[image_id]
    filepath = Path(image_info["filepath"])
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # TODO: Integrate with vision model (Gemini, GPT-4V, etc.)
    # For now, return placeholder
    return ImageAnalysisResult(
        image_id=image_id,
        description="Image analysis is not yet implemented. Please configure a vision model.",
        objects=[],
        text_detected=None,
        confidence=0.0
    )

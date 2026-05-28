"""
Device Background API - Upload and manage custom backgrounds for device displays
"""

import os
import uuid
import hashlib
from datetime import datetime
from typing import Annotated, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.db.database import async_get_db
from app.core.logger import get_logger
from app.api.dependencies import get_current_user
from app.crud.crud_device import crud_device
from app.schemas.device import DeviceRead
from app.services.mqtt_service import MQTTService

logger = get_logger(__name__)
router = APIRouter(prefix="/devices", tags=["Device Backgrounds"])

# Storage path (created lazily)
BACKGROUNDS_PATH = Path("/app/data/assets/backgrounds")


def ensure_backgrounds_dir():
    """Create backgrounds directory if not exists"""
    try:
        BACKGROUNDS_PATH.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pass  # Will fail later with better error message

# Allowed formats
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Screen sizes
SCREEN_SIZES = {
    "240x240": (240, 240),
    "284x240": (284, 240),
    "320x240": (320, 240),
    "128x64": (128, 64),
}


class BackgroundInfo(BaseModel):
    """Background info response"""
    id: str
    device_id: str
    background_type: str
    file_url: str
    file_size: int
    width: int
    height: int
    uploaded_at: str


class BackgroundListResponse(BaseModel):
    """List backgrounds response"""
    backgrounds: List[BackgroundInfo]
    total: int


@router.post(
    "/{device_id}/backgrounds/upload",
    summary="Upload custom background image"
)
async def upload_background(
    device_id: str,
    file: UploadFile = File(...),
    background_type: str = Form("idle"),  # idle, listening, speaking, custom1, custom2
    screen_type: str = Form("240x240"),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """
    Upload and process custom background image for device.
    Automatically resizes to device screen size.
    """
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Get target screen size
    target_size = SCREEN_SIZES.get(screen_type, (240, 240))
    
    # Process image
    try:
        from PIL import Image
        import io
        
        # Open and resize
        img = Image.open(io.BytesIO(content))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Calculate resize dimensions (maintain aspect ratio)
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]
        
        if img_ratio > target_ratio:
            new_width = target_size[0]
            new_height = int(target_size[0] / img_ratio)
        else:
            new_height = target_size[1]
            new_width = int(target_size[1] * img_ratio)
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create canvas with black background
        canvas = Image.new("RGB", target_size, (0, 0, 0))
        x_offset = (target_size[0] - new_width) // 2
        y_offset = (target_size[1] - new_height) // 2
        canvas.paste(img, (x_offset, y_offset))
        
        # Save processed image
        output = io.BytesIO()
        canvas.save(output, format="PNG", quality=90, optimize=True)
        processed_content = output.getvalue()
        
    except Exception as e:
        logger.error(f"Failed to process image: {e}")
        raise HTTPException(status_code=400, detail="Failed to process image")
    
    # Generate file ID and path
    file_id = str(uuid.uuid4())[:8]
    checksum = hashlib.md5(processed_content).hexdigest()[:8]
    filename = f"{background_type}_{file_id}_{checksum}.png"
    
    # Create device folder
    device_folder = BACKGROUNDS_PATH / device_id
    device_folder.mkdir(parents=True, exist_ok=True)
    
    # Save file
    filepath = device_folder / filename
    with open(filepath, "wb") as f:
        f.write(processed_content)
    
    # Generate URL
    file_url = f"/assets/backgrounds/{device_id}/{filename}"
    absolute_url = f"https://xiaozhi-ai-iot.vn{file_url}"
    
    logger.info(f"Saved background for device {device_id}: {filename}")
    
    # Optionally push to device via MQTT
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/server",
                {
                    "type": "display",
                    "action": "display_banner",
                    "cmd": "show_image",
                    "session_id": "background",
                    "message_id": file_id,
                    "image": {
                        "url": absolute_url,
                        "caption": "Background",
                        "position": "center",
                        "duration": 3600000
                    },
                    "media": {
                        "type": "image",
                        "url": absolute_url,
                        "duration": 3600000
                    }
                }
            )
            logger.info(f"Background pushed to device {device_id}")
    except Exception as e:
        logger.warning(f"Failed to push background via MQTT: {e}")
    
    return {
        "success": True,
        "message": "Background uploaded successfully",
        "background": {
            "id": file_id,
            "device_id": device_id,
            "background_type": background_type,
            "file_url": file_url,
            "file_size": len(processed_content),
            "width": target_size[0],
            "height": target_size[1],
            "uploaded_at": datetime.utcnow().isoformat(),
        }
    }


@router.get(
    "/{device_id}/backgrounds",
    response_model=BackgroundListResponse,
    summary="List device backgrounds"
)
async def list_backgrounds(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all uploaded backgrounds for a device"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get files from storage
    device_folder = BACKGROUNDS_PATH / device_id
    backgrounds = []
    
    if device_folder.exists():
        for filepath in device_folder.glob("*.png"):
            try:
                stat = filepath.stat()
                
                # Parse filename
                parts = filepath.stem.split("_")
                background_type = parts[0] if parts else "unknown"
                file_id = parts[1] if len(parts) > 1 else filepath.stem[:8]
                
                # Get image dimensions
                try:
                    from PIL import Image
                    with Image.open(filepath) as img:
                        width, height = img.size
                except Exception:
                    width, height = 240, 240
                
                backgrounds.append(BackgroundInfo(
                    id=file_id,
                    device_id=device_id,
                    background_type=background_type,
                    file_url=f"/assets/backgrounds/{device_id}/{filepath.name}",
                    file_size=stat.st_size,
                    width=width,
                    height=height,
                    uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                ))
            except Exception as e:
                logger.warning(f"Failed to read background file {filepath}: {e}")
    
    return BackgroundListResponse(
        backgrounds=backgrounds,
        total=len(backgrounds),
    )


@router.delete(
    "/{device_id}/backgrounds/{background_id}",
    summary="Delete background"
)
async def delete_background(
    device_id: str,
    background_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete uploaded background"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Find and delete file
    device_folder = BACKGROUNDS_PATH / device_id
    deleted = False
    
    if device_folder.exists():
        for filepath in device_folder.glob(f"*_{background_id}_*.png"):
            try:
                os.remove(filepath)
                deleted = True
                logger.info(f"Deleted background: {filepath}")
            except Exception as e:
                logger.error(f"Failed to delete {filepath}: {e}")
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Background not found")
    
    return {"success": True, "message": "Background deleted"}


@router.post(
    "/{device_id}/backgrounds/apply",
    summary="Apply background to device"
)
async def apply_background(
    device_id: str,
    background_type: str = Form("idle"),
    file_url: str = Form(...),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Push existing background to device via MQTT"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Ensure URL is absolute
    absolute_url = file_url
    if absolute_url.startswith("/"):
        absolute_url = f"https://xiaozhi-ai-iot.vn{absolute_url}"
    elif absolute_url.startswith("http://"):
        absolute_url = absolute_url.replace("http://", "https://")
        
    # Push to device
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/server",
                {
                    "type": "display",
                    "action": "display_banner",
                    "cmd": "show_image",
                    "session_id": "background",
                    "message_id": "apply",
                    "image": {
                        "url": absolute_url,
                        "caption": "Background",
                        "position": "center",
                        "duration": 3600000
                    },
                    "media": {
                        "type": "image",
                        "url": absolute_url,
                        "duration": 3600000
                    }
                }
            )
            logger.info(f"Applied background to device {device_id}: {file_url}")
            return {"success": True, "message": "Background applied"}
        else:
            raise HTTPException(status_code=503, detail="MQTT service unavailable")
    except Exception as e:
        logger.error(f"Failed to apply background: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply background")

"""
Agent and Template Avatar Upload API.

Handles image upload for agents and templates.
Images are optimized for device display (max 256x256).
"""

import uuid
from pathlib import Path
from PIL import Image
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ...core.db.database import async_get_db
from app.api.dependencies import get_current_user
from ...models.agent import Agent
from ...models.template import Template

router = APIRouter()

# Storage path for avatars
AVATAR_STORAGE_PATH = Path("/app/data/avatars")

# Max image dimensions for device display
MAX_WIDTH = 256
MAX_HEIGHT = 256
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


async def _process_and_save_image(
    file: UploadFile, 
    entity_type: str, 
    entity_id: str
) -> str:
    """
    Process uploaded image and save to storage.
    Returns the URL path to access the image.
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {ext} not allowed. Use: {ALLOWED_EXTENSIONS}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
    
    # Process image with Pillow
    try:
        img = Image.open(BytesIO(content))
        
        # Convert to RGB if needed (for PNG with transparency)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Resize to fit device screen while maintaining aspect ratio
        img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{entity_type}_{entity_id}_{unique_id}.jpg"
        
        # Ensure directory exists
        AVATAR_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        filepath = AVATAR_STORAGE_PATH / filename
        
        # Save as optimized JPEG
        img.save(filepath, "JPEG", quality=85, optimize=True)
        
        # Return URL path
        return f"/api/v1/avatars/{filename}"
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process image: {str(e)}"
        )


@router.post("/agents/{agent_id}/avatar")
async def upload_agent_avatar(
    agent_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Upload avatar image for an agent.
    
    - Image is resized to 256x256 max (optimized for device display)
    - Converted to JPEG for smaller size
    - Returns the public URL to the avatar
    """
    user_id = current_user["id"]
    
    # Verify agent ownership
    result = await db.execute(
        select(Agent.id, Agent.avatar_url).where(
            Agent.id == agent_id,
            Agent.user_id == user_id,
            Agent.is_deleted == False,
        )
    )
    agent = result.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Delete old avatar if exists
    if agent.avatar_url:
        old_filename = agent.avatar_url.split("/")[-1]
        old_path = AVATAR_STORAGE_PATH / old_filename
        if old_path.exists():
            old_path.unlink()
    
    # Process and save new avatar
    avatar_url = await _process_and_save_image(file, "agent", agent_id)
    
    # Update agent with new avatar URL
    await db.execute(
        update(Agent).where(Agent.id == agent_id).values(avatar_url=avatar_url)
    )
    await db.commit()
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url,
    }


@router.delete("/agents/{agent_id}/avatar")
async def delete_agent_avatar(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """Delete avatar for an agent."""
    user_id = current_user["id"]
    
    result = await db.execute(
        select(Agent.id, Agent.avatar_url).where(
            Agent.id == agent_id,
            Agent.user_id == user_id,
            Agent.is_deleted == False,
        )
    )
    agent = result.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Delete avatar file
    if agent.avatar_url:
        filename = agent.avatar_url.split("/")[-1]
        filepath = AVATAR_STORAGE_PATH / filename
        if filepath.exists():
            filepath.unlink()
    
    # Clear avatar URL
    await db.execute(
        update(Agent).where(Agent.id == agent_id).values(avatar_url=None)
    )
    await db.commit()
    
    return {"message": "Avatar deleted successfully"}


@router.post("/templates/{template_id}/avatar")
async def upload_template_avatar(
    template_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Upload avatar image for a template.
    
    - Image is resized to 256x256 max (optimized for device display)
    - Converted to JPEG for smaller size
    - Returns the public URL to the avatar
    """
    user_id = current_user["id"]
    
    # Verify template ownership
    result = await db.execute(
        select(Template.id, Template.avatar_url).where(
            Template.id == template_id,
            Template.user_id == user_id,
            Template.is_deleted == False,
        )
    )
    template = result.first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Delete old avatar if exists
    if template.avatar_url:
        old_filename = template.avatar_url.split("/")[-1]
        old_path = AVATAR_STORAGE_PATH / old_filename
        if old_path.exists():
            old_path.unlink()
    
    # Process and save new avatar
    avatar_url = await _process_and_save_image(file, "template", template_id)
    
    # Update template with new avatar URL
    await db.execute(
        update(Template).where(Template.id == template_id).values(avatar_url=avatar_url)
    )
    await db.commit()
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url,
    }


@router.delete("/templates/{template_id}/avatar")
async def delete_template_avatar(
    template_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """Delete avatar for a template."""
    user_id = current_user["id"]
    
    result = await db.execute(
        select(Template.id, Template.avatar_url).where(
            Template.id == template_id,
            Template.user_id == user_id,
            Template.is_deleted == False,
        )
    )
    template = result.first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Delete avatar file
    if template.avatar_url:
        filename = template.avatar_url.split("/")[-1]
        filepath = AVATAR_STORAGE_PATH / filename
        if filepath.exists():
            filepath.unlink()
    
    # Clear avatar URL
    await db.execute(
        update(Template).where(Template.id == template_id).values(avatar_url=None)
    )
    await db.commit()
    
    return {"message": "Avatar deleted successfully"}

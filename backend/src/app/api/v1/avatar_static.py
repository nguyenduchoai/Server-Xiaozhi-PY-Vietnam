"""
Static File Server for Avatars.

Serves avatar images for agents and templates.
No authentication required - avatars are public.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter(prefix="/avatars", tags=["Avatars"])

AVATAR_STORAGE_PATH = Path("/app/data/avatars")


@router.get("/{filename}")
async def get_avatar(filename: str):
    """
    Serve avatar image by filename.
    
    Returns the image file directly.
    Supports caching via ETag.
    """
    # Validate filename to prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    filepath = AVATAR_STORAGE_PATH / filename
    
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found"
        )
    
    return FileResponse(
        path=filepath,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
        }
    )

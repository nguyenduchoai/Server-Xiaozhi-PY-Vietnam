"""Voice API endpoints for voice cloning management."""

from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.voice import VoiceCreate, VoicePublic, VoiceListResponse, VoiceDetail
from app.services.voice_service import VoiceService
from app.core.logger import setup_logging

logger = setup_logging()
router = APIRouter(tags=["voices"], prefix="/voices")


@router.post("/upload", response_model=VoicePublic, status_code=201)
async def upload_voice(
    file: UploadFile = File(..., description="Audio file (WAV/MP3/M4A, 3-30s, max 10MB)"),
    name: str = Form(..., min_length=1, max_length=255, description="Voice name"),
    description: Optional[str] = Form(None, description="Voice description"),
    set_as_default: bool = Form(False, description="Set as default voice"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """
    Upload audio sample and clone voice.
    
    **Requirements:**
    - Audio file: WAV, MP3, or M4A format
    - Duration: 3-30 seconds (recommended: 10-15s for best quality)
    - File size: Max 10MB
    - User quota: Max 10 voices per user
    
    **Returns:**
    - Voice object with ID, name, duration, sample_rate, etc.
    - Embeddings are stored internally (not returned in response)
    """
    voice_data = VoiceCreate(
        name=name,
        description=description,
        set_as_default=set_as_default
    )
    
    try:
        voice = await VoiceService.create_voice(
            db=db,
            user_id=current_user["id"] if isinstance(current_user, dict) else current_user.id,
            audio_file=file,
            voice_data=voice_data
        )
        return voice
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(tag="VoiceAPI").error(f"Voice upload failed: {e}")
        raise HTTPException(status_code=500, detail="Voice upload failed")


@router.get("/", response_model=VoiceListResponse)
async def list_voices(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """
    List user's voices with pagination and search.
    
    **Query Parameters:**
    - page: Page number (starts from 1)
    - page_size: Items per page (default: 20, max: 100)
    - search: Search by voice name (case-insensitive)
    
    **Returns:**
    - Paginated list of voices
    - Total count and page info
    """
    if page_size > 100:
        page_size = 100
    
    return await VoiceService.get_voices(
        db=db,
        user_id=current_user["id"] if isinstance(current_user, dict) else current_user.id,
        page=page,
        page_size=page_size,
        search=search
    )


@router.get("/{voice_id}", response_model=VoiceDetail)
async def get_voice(
    voice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """
    Get voice detail by ID.
    
    **Returns:**
    - Voice object with audio_url for preview
    """
    voice = await VoiceService.get_voice(db, voice_id, current_user["id"] if isinstance(current_user, dict) else current_user.id)
    
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    # Add audio URL for preview
    voice_public = VoicePublic.model_validate(voice)
    return VoiceDetail(
        **voice_public.model_dump(),
        audio_url=f"/api/v1/voices/{voice_id}/audio"
    )


@router.delete("/{voice_id}", status_code=204)
async def delete_voice(
    voice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """
    Delete voice (soft delete).
    
    **Side effects:**
    - Voice is marked as deleted (is_deleted=true)
    - Agents using this voice will fallback to default TTS
    - Audio file is retained for audit/recovery purposes
    """
    success = await VoiceService.delete_voice(db, voice_id, current_user["id"] if isinstance(current_user, dict) else current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    return Response(status_code=204)


@router.patch("/{voice_id}/set-default", response_model=VoicePublic)
async def set_default_voice(
    voice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """
    Set voice as user's default.
    
    **Logic:**
    - Unset all other voices' is_default flag
    - Set this voice as default
    - Default voice is used when agent has no explicit voice_id
    """
    success = await VoiceService.set_default_voice(db, voice_id, current_user["id"] if isinstance(current_user, dict) else current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    # Return updated voice
    voice = await VoiceService.get_voice(db, voice_id, current_user["id"] if isinstance(current_user, dict) else current_user.id)
    return VoicePublic.model_validate(voice)


@router.get("/{voice_id}/audio")
async def get_voice_audio(
    voice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """
    Get voice audio file for preview.
    
    **Returns:**
    - Audio file stream (WAV/MP3/M4A)
    - Content-Type header based on file extension
    """
    voice = await VoiceService.get_voice(db, voice_id, current_user["id"] if isinstance(current_user, dict) else current_user.id)
    
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    # Check if audio file exists
    import os
    if not os.path.exists(voice.audio_file_path):
        logger.bind(tag="VoiceAPI").error(f"Audio file not found: {voice.audio_file_path}")
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Determine content type
    ext = os.path.splitext(voice.audio_file_path)[1].lower()
    content_type_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/x-m4a"
    }
    content_type = content_type_map.get(ext, "application/octet-stream")
    
    # Read and return audio file
    with open(voice.audio_file_path, "rb") as f:
        audio_data = f.read()
    
    return Response(
        content=audio_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{voice.name}{ext}"'
        }
    )

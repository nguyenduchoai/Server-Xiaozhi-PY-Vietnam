"""Voice service - business logic for voice cloning management."""

import os
import base64
import httpx
from typing import Optional
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException

from app.models.voice import Voice
from app.schemas.voice import VoiceCreate, VoicePublic, VoiceListResponse
from app.core.config import settings
from app.core.logger import setup_logging

logger = setup_logging()


class QuotaExceededError(HTTPException):
    """Exception raised when user exceeds voice quota."""
    def __init__(self, message: str):
        super().__init__(status_code=403, detail=message)


class VoiceService:
    """Service for voice cloning operations."""
    
    @staticmethod
    async def create_voice(
        db: AsyncSession,
        user_id: str,
        audio_file: UploadFile,
        voice_data: VoiceCreate
    ) -> VoicePublic:
        """
        Upload and clone voice from audio sample.
        
        Steps:
        1. Validate audio file (format, duration, size)
        2. Check user quota (max 10 voices per user)
        3. Save audio to disk
        4. Call Valtec-TTS /clone endpoint to generate embeddings
        5. Store voice in database
        
        Args:
            db: Database session
            user_id: User ID who owns this voice
            audio_file: Audio file upload (WAV/MP3/M4A)
            voice_data: Voice creation data (name, description, set_as_default)
            
        Returns:
            VoicePublic schema
            
        Raises:
            QuotaExceededError: User has reached maximum voices limit
            HTTPException: Audio validation failed or Valtec-TTS service error
        """
        # 1. Read audio file
        audio_bytes = await audio_file.read()
        await audio_file.seek(0)  # Reset for potential re-use
        
        # 2. Validate audio file
        await VoiceService._validate_audio_file(audio_file, audio_bytes)
        
        # 3. Check user quota
        voice_count = await db.scalar(
            select(func.count(Voice.id))
            .where(Voice.user_id == user_id, Voice.is_deleted == False)
        )
        
        max_voices = getattr(settings, 'MAX_VOICES_PER_USER', 10)
        if voice_count >= max_voices:
            raise QuotaExceededError(
                f"Maximum {max_voices} voices allowed. Delete unused voices to upload new ones."
            )
        
        # 4. Check unique name
        existing = await db.scalar(
            select(Voice.id)
            .where(
                Voice.user_id == user_id,
                Voice.name == voice_data.name,
                Voice.is_deleted == False
            )
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Voice name '{voice_data.name}' already exists. Please use a different name."
            )
        
        # 5. Generate voice ID and save audio file
        from uuid6 import uuid7
        voice_id = str(uuid7())
        
        voices_dir = getattr(settings, 'VOICES_STORAGE_PATH', '/app/data/backend/voices')
        user_voices_dir = os.path.join(voices_dir, user_id)
        os.makedirs(user_voices_dir, exist_ok=True)
        
        # Determine file extension
        filename = audio_file.filename or "audio.wav"
        ext = os.path.splitext(filename)[1] or ".wav"
        audio_path = os.path.join(user_voices_dir, f"{voice_id}{ext}")
        
        # Save audio file
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        
        logger.info(f"Audio saved: {audio_path} ({len(audio_bytes)} bytes)")
        
        # 6. Clone voice via Valtec-TTS /clone endpoint
        clone_success = False
        valtec_url = getattr(settings, 'VALTEC_TTS_URL', 'http://valtec-tts:8101')
        
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{valtec_url}/clone",
                    json={
                        "voice_id": voice_id,
                        "audio_base64": audio_b64,
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    clone_success = result.get("success", False)
                    logger.info(
                        f"Voice cloned successfully via Valtec-TTS: {voice_id}, "
                        f"path={result.get('audio_path')}"
                    )
                elif response.status_code == 422:
                    # Validation failed — audio not suitable for cloning
                    error_detail = response.json().get("detail", "Unknown error")
                    logger.warning(f"Voice clone validation failed: {error_detail}")
                    # Still save the voice record (audio is saved locally)
                else:
                    logger.warning(
                        f"Voice clone failed: HTTP {response.status_code} - {response.text}"
                    )
        except httpx.ConnectError:
            logger.warning("Valtec-TTS service not reachable, voice saved as reference only")
        except Exception as e:
            logger.warning(f"Voice clone error (non-fatal): {e}")
        
        # Generate embeddings marker if clone was successful
        embeddings = b"valtec_cloned" if clone_success else None
        if not clone_success:
            logger.info("Voice saved as reference audio (clone pending or unavailable)")
        
        # 7. Get audio duration
        audio_duration = await VoiceService._get_audio_duration(audio_path)
        
        # 8. Create Voice record in database
        voice = Voice(
            id=voice_id,
            user_id=user_id,
            name=voice_data.name,
            description=voice_data.description,
            audio_file_path=audio_path,
            audio_duration=audio_duration,
            audio_size=len(audio_bytes),
            sample_rate=24000,
            embeddings=embeddings,
            is_default=voice_data.set_as_default
        )
        
        # If set_as_default, unset other defaults
        if voice_data.set_as_default:
            await db.execute(
                update(Voice)
                .where(Voice.user_id == user_id, Voice.is_deleted == False)
                .values(is_default=False)
            )
        
        db.add(voice)
        await db.commit()
        await db.refresh(voice)
        
        logger.info(f"Voice created: id={voice_id}, name={voice_data.name}, user_id={user_id}")
        
        return VoicePublic.model_validate(voice)
    
    @staticmethod
    async def get_voices(
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> VoiceListResponse:
        """Get user's voices with pagination."""
        query = select(Voice).where(Voice.user_id == user_id, Voice.is_deleted == False)
        
        if search:
            query = query.where(Voice.name.ilike(f"%{search}%"))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0
        
        # Get page
        query = query.order_by(Voice.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        voices = result.scalars().all()
        
        return VoiceListResponse(
            items=[VoicePublic.model_validate(v) for v in voices],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
    
    @staticmethod
    async def get_voice(
        db: AsyncSession,
        voice_id: str,
        user_id: str
    ) -> Optional[Voice]:
        """Get voice by ID (owner only)."""
        result = await db.execute(
            select(Voice)
            .where(
                Voice.id == voice_id,
                Voice.user_id == user_id,
                Voice.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_voice(
        db: AsyncSession,
        voice_id: str,
        user_id: str
    ) -> bool:
        """Soft delete voice (owner only)."""
        voice = await VoiceService.get_voice(db, voice_id, user_id)
        if not voice:
            return False
        
        voice.is_deleted = True
        await db.commit()
        
        logger.info(f"Voice deleted: id={voice_id}, name={voice.name}")
        return True
    
    @staticmethod
    async def set_default_voice(
        db: AsyncSession,
        voice_id: str,
        user_id: str
    ) -> bool:
        """Set voice as user's default."""
        voice = await VoiceService.get_voice(db, voice_id, user_id)
        if not voice:
            return False
        
        # Unset all defaults
        await db.execute(
            update(Voice)
            .where(Voice.user_id == user_id, Voice.is_deleted == False)
            .values(is_default=False)
        )
        
        # Set this voice as default
        voice.is_default = True
        await db.commit()
        
        logger.info(f"Default voice set: id={voice_id}, name={voice.name}")
        return True
    
    # --- Helper methods ---
    
    @staticmethod
    async def _validate_audio_file(file: UploadFile, audio_bytes: bytes):
        """Validate audio file constraints."""
        # Check file size
        max_size = getattr(settings, 'MAX_VOICE_FILE_SIZE', 10 * 1024 * 1024)  # 10MB
        if len(audio_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {len(audio_bytes)} bytes (max {max_size} bytes / {max_size // (1024 * 1024)}MB)"
            )
        
        # Check MIME type
        content_type = file.content_type or ""
        allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/m4a", "audio/x-m4a"]
        
        if not any(t in content_type.lower() for t in allowed_types):
            # Also check file extension
            filename = file.filename or ""
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.wav', '.mp3', '.m4a']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file format. Allowed: WAV, MP3, M4A. Got: {content_type or ext}"
                )
    

    
    @staticmethod
    async def _get_audio_duration(audio_path: str) -> float:
        """Get audio duration in seconds using ffprobe."""
        try:
            import subprocess
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path
                ],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                
                # Validate duration (3-30 seconds as per PRD)
                min_duration = getattr(settings, 'MIN_VOICE_DURATION', 3.0)
                max_duration = getattr(settings, 'MAX_VOICE_DURATION', 30.0)
                
                if not (min_duration <= duration <= max_duration):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Audio duration must be {min_duration}-{max_duration}s, got {duration:.1f}s"
                    )
                
                return duration
            else:
                logger.warning(f"ffprobe failed: {result.stderr}")
                return 10.0  # Default fallback
                
        except FileNotFoundError:
            logger.warning("ffprobe not found, using fallback duration")
            return 10.0  # Fallback if ffprobe not installed
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return 10.0  # Fallback

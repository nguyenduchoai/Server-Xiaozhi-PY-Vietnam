"""Voice schemas for request/response validation."""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class VoiceBase(BaseModel):
    """Base voice schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Voice name")
    description: Optional[str] = Field(None, description="Voice description")


class VoiceCreate(VoiceBase):
    """Schema for voice upload request (via Form)."""
    set_as_default: bool = Field(False, description="Set this voice as user's default")


class VoicePublic(VoiceBase):
    """Public voice schema (without embeddings)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    audio_duration: float = Field(..., description="Audio duration in seconds")
    audio_size: int = Field(..., description="File size in bytes")
    sample_rate: int = Field(..., description="Audio sample rate (Hz)")
    is_default: bool = Field(..., description="Is this user's default voice")
    created_at: datetime


class VoiceDetail(VoicePublic):
    """Detailed voice with audio URL for preview."""
    audio_url: str = Field(..., description="URL to preview audio file")


class VoiceInternal(VoicePublic):
    """Internal schema with embeddings (for TTS provider)."""
    embeddings: Optional[bytes] = Field(None, description="Voice embeddings (BYTEA)")


class VoiceListResponse(BaseModel):
    """Response for voice list endpoint."""
    items: list[VoicePublic]
    total: int
    page: int
    page_size: int
    total_pages: int

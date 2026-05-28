"""
Emoji Pack Pydantic Schemas

Request/Response schemas for emoji pack API endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator



# ============ Emotion Asset Schemas ============

class EmotionAssetInfo(BaseModel):
    """Info about a single emotion's asset"""
    url: str
    file_type: str = "png"
    is_custom: bool = False
    has_animation: bool = False
    frame_count: int = 1
    file_size: Optional[int] = None


class EmotionUploadResponse(BaseModel):
    """Response after uploading an emoji"""
    emotion: str
    url: str
    file_type: str
    has_animation: bool
    frame_count: int
    file_size: int


# ============ Emoji Pack Schemas ============

class EmojiPackBase(BaseModel):
    """Base emoji pack fields"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class EmojiPackCreate(EmojiPackBase):
    """Request to create a new emoji pack"""
    target_size: int = Field(default=64, ge=32, le=128)
    base_pack: str = Field(default="twemoji", max_length=50)
    
    @field_validator('target_size')
    @classmethod
    def validate_target_size(cls, v: int) -> int:
        if v not in [32, 64, 128]:
            raise ValueError("target_size must be 32, 64, or 128")
        return v


class EmojiPackUpdate(BaseModel):
    """Request to update emoji pack metadata"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class EmojiPackAuthor(BaseModel):
    """Author info for public packs"""
    id: str
    name: str


class EmojiPackSummary(BaseModel):
    """Emoji pack summary for list views"""
    id: str
    name: str
    description: Optional[str] = None
    target_size: int
    base_pack: str
    emotion_count: int = 21
    is_public: bool = False
    is_featured: bool = False
    download_count: int = 0
    preview_url: Optional[str] = None
    created_at: datetime
    author: Optional[EmojiPackAuthor] = None
    
    class Config:
        from_attributes = True


class EmojiPackDetail(BaseModel):
    """Full emoji pack details including all emotions"""
    id: str
    name: str
    description: Optional[str] = None
    target_size: int
    base_pack: str
    is_public: bool = False
    is_featured: bool = False
    approval_status: str = "private"
    download_count: int = 0
    emotions: Dict[str, EmotionAssetInfo] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmojiPackListResponse(BaseModel):
    """Paginated list of emoji packs"""
    success: bool = True
    data: List[EmojiPackSummary]
    total: int
    page: int
    page_size: int


# ============ Emoji Library Schemas ============

class EmojiLibraryInfo(BaseModel):
    """Info about an emoji library"""
    id: str
    name: str
    sizes: List[int]
    license: str
    preview_url: Optional[str] = None


class EmojiLibraryListResponse(BaseModel):
    """List of available emoji libraries"""
    libraries: List[EmojiLibraryInfo]


class EmojiLibraryEmotions(BaseModel):
    """Emotions from a specific library"""
    library: str
    size: int
    emotions: Dict[str, str]  # emotion_name -> url


# ============ Flash Job Schemas ============

class FlashJobCreate(BaseModel):
    """Request to start OTA flash"""
    device_id: str


class FlashJobStatus(BaseModel):
    """Flash job status response"""
    job_id: str
    status: str = "queued"
    progress: int = 0
    message: Optional[str] = None
    

class FlashJobResponse(BaseModel):
    """Response after creating flash job"""
    success: bool = True
    flash_job_id: str
    message: str = "Flash job queued"


# ============ Share Schemas ============

class ShareRequest(BaseModel):
    """Request to share pack publicly"""
    share_type: str = Field(default="public", pattern="^(public|private)$")


class ShareResponse(BaseModel):
    """Response after share request"""
    success: bool = True
    approval_status: str
    message: str


# ============ Binary Download ============

class BinaryDownloadParams(BaseModel):
    """Params for binary download"""
    format: str = Field(default="bin", pattern="^(bin|zip)$")

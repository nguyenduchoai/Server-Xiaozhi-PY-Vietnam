"""
Firmware schemas for API validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class BoardType(str, Enum):
    """Supported board types."""
    ESP32 = "esp32"
    ESP32_S3 = "esp32s3"
    ESP32_C3 = "esp32c3"
    ALL = "all"


class DeploymentStatus(str, Enum):
    """Deployment status."""
    PENDING = "pending"
    ROLLING_OUT = "rolling_out"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DeploymentTargetType(str, Enum):
    """Target type for deployment."""
    ALL = "all"
    BOARD = "board"
    USER = "user"
    DEVICE = "device"


# ============ Firmware Schemas ============

class FirmwareBase(BaseModel):
    """Base firmware schema."""
    version: str = Field(..., min_length=1, max_length=50, examples=["1.0.0", "2.1.3"])
    board_type: BoardType = Field(default=BoardType.ALL)
    release_notes: Optional[str] = Field(default=None, max_length=5000)
    is_active: bool = Field(default=True)
    features: Optional[Dict[str, bool]] = Field(default=None, description="Feature toggles")
    firmware_variant: str = Field(default="common", max_length=100)
    custom_variant_label: Optional[str] = Field(default=None, max_length=255)


class FirmwareCreate(FirmwareBase):
    """Schema for creating firmware (file uploaded separately)."""
    model_config = ConfigDict(extra="forbid")


class FirmwareUpdate(BaseModel):
    """Schema for updating firmware metadata."""
    model_config = ConfigDict(extra="forbid")
    
    release_notes: Optional[str] = Field(default=None, max_length=5000)
    is_active: Optional[bool] = None
    is_latest: Optional[bool] = None
    features: Optional[Dict[str, bool]] = None
    firmware_variant: Optional[str] = None
    custom_variant_label: Optional[str] = None


class FirmwareRead(FirmwareBase):
    """Schema for reading firmware data."""
    id: str
    file_name: str
    checksum: str
    size: int
    is_latest: bool
    download_count: int
    features: Optional[Dict[str, bool]] = None
    firmware_variant: str = "common"
    custom_variant_label: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class FirmwareList(BaseModel):
    """Schema for firmware list response."""
    items: List[FirmwareRead]
    total: int
    page: int
    page_size: int


# ============ Deployment Schemas ============

class DeploymentCreate(BaseModel):
    """Schema for creating a deployment."""
    model_config = ConfigDict(extra="forbid")
    
    firmware_id: str
    target_type: DeploymentTargetType = Field(default=DeploymentTargetType.ALL)
    target_value: Optional[str] = Field(
        default=None,
        description="Board type, user ID, or comma-separated device MACs"
    )
    rollout_percentage: int = Field(default=100, ge=1, le=100)
    scheduled_at: Optional[datetime] = Field(
        default=None,
        description="Schedule deployment for later (null = immediate)"
    )


class DeploymentUpdate(BaseModel):
    """Schema for updating deployment."""
    model_config = ConfigDict(extra="forbid")
    
    status: Optional[DeploymentStatus] = None
    rollout_percentage: Optional[int] = Field(default=None, ge=1, le=100)


class DeploymentRead(BaseModel):
    """Schema for reading deployment data."""
    id: str
    firmware_id: str
    firmware_version: Optional[str] = None
    target_type: DeploymentTargetType
    target_value: Optional[str] = None
    status: DeploymentStatus
    rollout_percentage: int
    deployed_count: int
    failed_count: int
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class DeploymentList(BaseModel):
    """Schema for deployment list response."""
    items: List[DeploymentRead]
    total: int
    page: int
    page_size: int


# ============ Device Update Check Schema ============

class DeviceUpdateCheck(BaseModel):
    """Schema for device to check for updates."""
    mac_address: str
    board_type: str
    current_version: str


class DeviceUpdateResponse(BaseModel):
    """Response for device update check."""
    has_update: bool
    current_version: str
    latest_version: Optional[str] = None
    download_url: Optional[str] = None
    checksum: Optional[str] = None
    size: Optional[int] = None
    release_notes: Optional[str] = None

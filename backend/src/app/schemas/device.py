"""
Device schemas - Pydantic models for validation and serialization.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


# Default feature toggles (all enabled)
DEFAULT_FEATURES = {
    "music": True,
    "radio": True,
    "weather": True,
    "sdCardMusic": True,
    "alarm": True,
    "reminder": True,
    "voiceRecording": True,
    "bluetooth": True,
    "homeAssistant": True,
    # Agent-level features (gated by subscription plan)
    "memory": True,
    "intercom": True,
    "education": True,
    "knowledge_base": True,
    "sales": True,
    "meeting": True,
}


class DeviceBase(BaseModel):
    """Base device schema."""

    user_id: str
    mac_address: Annotated[
        str, Field(min_length=1, max_length=50, examples=["00:1A:2B:3C:4D:5E"])
    ]
    device_name: str | None = Field(default=None, max_length=255)
    board: str | None = Field(
        default=None, max_length=100, examples=["ESP32", "Raspberry Pi"]
    )
    firmware_version: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)


class DeviceCreate(DeviceBase):
    """Schema for creating a new device."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str | None = None
    user_id: str  # Auto-populated from current user in API, but required in schema


class DeviceRead(DeviceBase):
    """Schema for reading device data."""

    id: str
    user_id: str
    agent_id: str | None = None
    intercom_enabled: bool = True
    last_connected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # License fields
    license_type: str = "unlimited"
    license_value: int | None = None
    license_expiration_date: datetime | None = None
    license_activated_at: datetime | None = None
    # Feature toggles
    features: dict | None = None
    # Custom firmware
    custom_firmware: str | None = None
    # Background image
    background_image_url: str | None = None


class DeviceUpdate(BaseModel):
    """Schema for updating device."""

    model_config = ConfigDict(extra="forbid")

    device_name: str | None = Field(default=None, max_length=255)
    board: str | None = Field(default=None, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    agent_id: str | None = None
    last_connected_at: datetime | None = None
    user_id: str | None = None
    # License fields
    license_type: str | None = None
    license_value: int | None = None
    license_expiration_date: datetime | None = None
    license_activated_at: datetime | None = None
    # Feature toggles
    features: dict | None = None
    # Custom firmware
    custom_firmware: str | None = None
    # Background image
    background_image_url: str | None = None


class DeviceUpdateInternal(DeviceUpdate):
    """Internal schema for updating device (includes timestamp)."""

    updated_at: datetime


class LicenseInfo(BaseModel):
    """License status info returned in OTA response."""
    is_valid: bool
    activated_at: datetime | None = None
    expires_at: datetime | None = None
    remaining_days: int | None = None
    license_type: str = "unlimited"
    message: str = ""


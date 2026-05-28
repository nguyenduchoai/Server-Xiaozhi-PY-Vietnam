"""Pydantic schemas for Board Type and Screen Type."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Board Type Schemas
# =============================================================================

class BoardTypeBase(BaseModel):
    """Base schema for Board Type."""
    code: str = Field(..., min_length=1, max_length=50, description="Unique code for the board")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    description: Optional[str] = Field(None, description="Optional description")
    chip_family: str = Field("ESP32", max_length=50, description="Chip family (ESP32, ESP32-S3, etc.)")
    flash_size_mb: int = Field(4, ge=1, le=32, description="Flash size in MB")
    psram_size_mb: int = Field(0, ge=0, le=16, description="PSRAM size in MB")
    is_active: bool = Field(True, description="Whether this board type is active")
    sort_order: int = Field(0, ge=0, description="Sort order for display")


class BoardTypeCreate(BoardTypeBase):
    """Schema for creating a Board Type."""
    pass


class BoardTypeUpdate(BaseModel):
    """Schema for updating a Board Type."""
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    chip_family: Optional[str] = Field(None, max_length=50)
    flash_size_mb: Optional[int] = Field(None, ge=1, le=32)
    psram_size_mb: Optional[int] = Field(None, ge=0, le=16)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)


class BoardTypeRead(BoardTypeBase):
    """Schema for reading a Board Type."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BoardTypeList(BaseModel):
    """Schema for listing Board Types."""
    id: int
    code: str
    name: str
    chip_family: str
    flash_size_mb: int
    psram_size_mb: int
    is_active: bool
    sort_order: int

    model_config = {"from_attributes": True}


# =============================================================================
# Screen Type Schemas
# =============================================================================

class ScreenTypeBase(BaseModel):
    """Base schema for Screen Type."""
    code: str = Field(..., min_length=1, max_length=50, description="Unique code for the screen")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    description: Optional[str] = Field(None, description="Optional description")
    driver: str = Field("none", max_length=50, description="Display driver (ssd1306, st7789, etc.)")
    width: int = Field(0, ge=0, le=2048, description="Screen width in pixels")
    height: int = Field(0, ge=0, le=2048, description="Screen height in pixels")
    color_depth: int = Field(1, ge=1, le=32, description="Color depth (1=mono, 16=RGB565, 24=RGB888)")
    is_active: bool = Field(True, description="Whether this screen type is active")
    sort_order: int = Field(0, ge=0, description="Sort order for display")


class ScreenTypeCreate(ScreenTypeBase):
    """Schema for creating a Screen Type."""
    pass


class ScreenTypeUpdate(BaseModel):
    """Schema for updating a Screen Type."""
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    driver: Optional[str] = Field(None, max_length=50)
    width: Optional[int] = Field(None, ge=0, le=2048)
    height: Optional[int] = Field(None, ge=0, le=2048)
    color_depth: Optional[int] = Field(None, ge=1, le=32)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)


class ScreenTypeRead(ScreenTypeBase):
    """Schema for reading a Screen Type."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScreenTypeList(BaseModel):
    """Schema for listing Screen Types."""
    id: int
    code: str
    name: str
    driver: str
    width: int
    height: int
    color_depth: int
    is_active: bool
    sort_order: int

    model_config = {"from_attributes": True}


# =============================================================================
# Combined Response for dropdowns
# =============================================================================

class HardwareTypesResponse(BaseModel):
    """Combined response with all board and screen types for dropdowns."""
    board_types: list[BoardTypeList]
    screen_types: list[ScreenTypeList]

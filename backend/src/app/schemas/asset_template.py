"""
Asset Template Schemas

Pydantic schemas for Asset Template API.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class BoardTypeEnum(str, Enum):
    ESP32 = "esp32"
    ESP32S3 = "esp32s3"
    ESP32C3 = "esp32c3"
    ESP32C6 = "esp32c6"


class ScreenTypeEnum(str, Enum):
    NONE = "none"
    SSD1306_128x64 = "ssd1306_128x64"
    SSD1306_128x32 = "ssd1306_128x32"
    ST7789_240x240 = "st7789_240x240"
    ST7789_240x320 = "st7789_240x320"
    ST7789_172x320 = "st7789_172x320"
    ILI9341_240x320 = "ili9341_240x320"


class AssetTemplateBase(BaseModel):
    """Base schema for Asset Template"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    board_type: BoardTypeEnum
    screen_type: ScreenTypeEnum = ScreenTypeEnum.NONE
    screen_width: int = Field(default=0, ge=0)
    screen_height: int = Field(default=0, ge=0)
    wake_word: Optional[str] = None
    font_name: Optional[str] = None
    emoji_style: Optional[str] = None


class AssetTemplateCreate(AssetTemplateBase):
    """Schema for creating Asset Template"""
    asset_file_base64: Optional[str] = None  # Base64 encoded .bin file
    preview_image_base64: Optional[str] = None
    is_default: bool = False


class AssetTemplateUpdate(BaseModel):
    """Schema for updating Asset Template"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    board_type: Optional[BoardTypeEnum] = None
    screen_type: Optional[ScreenTypeEnum] = None
    screen_width: Optional[int] = Field(None, ge=0)
    screen_height: Optional[int] = Field(None, ge=0)
    wake_word: Optional[str] = None
    font_name: Optional[str] = None
    emoji_style: Optional[str] = None
    asset_file_base64: Optional[str] = None
    preview_image_base64: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class AssetTemplateRead(AssetTemplateBase):
    """Schema for reading Asset Template (list view)"""
    id: str
    asset_file_size: int
    preview_image_base64: Optional[str] = None
    is_active: bool
    is_default: bool
    download_count: int
    created_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssetTemplateDetail(AssetTemplateRead):
    """Schema for detailed Asset Template view"""
    # Include download URL instead of raw file
    download_url: Optional[str] = None

    class Config:
        from_attributes = True


class AssetTemplateListResponse(BaseModel):
    """Response for listing templates"""
    success: bool = True
    data: list[AssetTemplateRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AssetTemplateDownloadResponse(BaseModel):
    """Response for downloading template"""
    filename: str
    content_type: str = "application/octet-stream"
    file_base64: str  # Base64 encoded file content

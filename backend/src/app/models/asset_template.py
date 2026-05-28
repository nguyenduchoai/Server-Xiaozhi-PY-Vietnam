"""
Asset Template Model

Stores pre-built asset templates for ESP32 devices.
Admin can upload templates, users can download based on their device type.
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
import enum

from ..core.db.database import Base


class BoardType(str, enum.Enum):
    """Supported ESP32 board types"""
    ESP32 = "esp32"
    ESP32S3 = "esp32s3"
    ESP32C3 = "esp32c3"
    ESP32C6 = "esp32c6"


class ScreenType(str, enum.Enum):
    """Supported screen types"""
    NONE = "none"
    SSD1306_128x64 = "ssd1306_128x64"
    SSD1306_128x32 = "ssd1306_128x32"
    ST7789_240x240 = "st7789_240x240"
    ST7789_240x320 = "st7789_240x320"
    ST7789_172x320 = "st7789_172x320"
    ILI9341_240x320 = "ili9341_240x320"


class AssetTemplate(Base):
    """
    Asset Template for ESP32 devices.
    
    Each template contains:
    - Metadata about compatible board/screen
    - The actual assets.bin file (stored as base64 or file path)
    - Preview image
    """
    __tablename__ = "asset_template"

    # Primary key - no default, required
    id: Mapped[str] = mapped_column(String, primary_key=True, init=True)
    
    # Required fields - no default
    name: Mapped[str] = mapped_column(String(100), nullable=False, init=True)
    board_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True, init=True)
    
    # Optional/default fields
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None, init=False)
    screen_type: Mapped[str] = mapped_column(String(30), default="none", nullable=False, index=True, init=False)
    screen_width: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)
    screen_height: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)
    
    # Asset file
    asset_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None, init=False)
    asset_file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)
    
    # Preview image
    preview_image_base64: Mapped[str | None] = mapped_column(Text, nullable=True, default=None, init=False)
    
    # Features
    wake_word: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None, init=False)
    font_name: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None, init=False)
    emoji_style: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None, init=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, init=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)
    
    # Ownership
    created_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None, index=True, init=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
        init=False
    )

    def __repr__(self) -> str:
        return f"<AssetTemplate {self.name} ({self.board_type})>"

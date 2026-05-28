"""Board Type and Screen Type models for centralized hardware configuration.

These models serve as the single source of truth for:
- Device registration
- Asset Templates
- Firmware OTA
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


@dataclass
class BoardType(Base):
    """Board Type model - defines supported ESP32 board variants."""

    __tablename__ = "board_type"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, init=False
    )
    
    # Board identification
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    
    # Technical specs
    chip_family: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ESP32"
    )  # ESP32, ESP32-S3, ESP32-C3, etc.
    flash_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    psram_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        init=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        init=False,
        default=None,
    )


@dataclass
class ScreenType(Base):
    """Screen Type model - defines supported display configurations."""

    __tablename__ = "screen_type"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, init=False
    )
    
    # Screen identification
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    
    # Display specs
    driver: Mapped[str] = mapped_column(
        String(50), nullable=False, default="none"
    )  # ssd1306, st7789, ili9341, none
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    color_depth: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # 1=monochrome, 16=RGB565, 24=RGB888
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        init=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        init=False,
        default=None,
    )

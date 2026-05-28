"""
Device Theme Model - Store theme configurations for ESP32 devices
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.database import Base


class DeviceTheme(Base):
    """Theme configuration for device displays"""
    
    __tablename__ = "device_theme"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, init=False, default_factory=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Preview and assets
    preview_url = Column(String(500), nullable=True)  # Preview image URL
    thumbnail_url = Column(String(500), nullable=True)  # Small thumbnail
    
    # Theme configuration data
    theme_data = Column(JSON, nullable=True)  # Full theme config
    
    # Screen compatibility
    screen_type = Column(String(50), default="240x240")  # 240x240, 284x240, 320x240
    screen_width = Column(Integer, default=240)
    screen_height = Column(Integer, default=240)
    
    # Categorization
    category = Column(String(50), default="default")  # default, anime, minimal, custom, seasonal
    tags = Column(JSON, nullable=True)  # ["cute", "dark", "colorful"]
    
    # Ownership
    is_system = Column(Boolean, default=False)  # Built-in system themes
    created_by = Column(String(36), ForeignKey("user.id"), nullable=True)  # User ID for custom
    is_public = Column(Boolean, default=True)  # Visible to all users
    
    # Stats
    download_count = Column(Integer, default=0)
    rating = Column(Integer, default=0)  # 1-5 stars
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True)


class DeviceThemeAsset(Base):
    """Individual assets for a theme (backgrounds, animations, etc.)"""
    
    __tablename__ = "device_theme_asset"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, init=False, default_factory=lambda: str(uuid.uuid4()))
    theme_id = Column(String(36), ForeignKey("device_theme.id"), nullable=False)
    
    # Asset info
    asset_type = Column(String(50), nullable=False)  # idle, listening, speaking, thinking, error
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)  # bytes
    file_format = Column(String(20), default="png")  # png, jpg, gif
    
    # Dimensions
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Animation info
    is_animated = Column(Boolean, default=False)
    frame_count = Column(Integer, default=1)
    duration_ms = Column(Integer, nullable=True)  # Total animation duration
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class DeviceThemeInstallation(Base):
    """Track theme installations on devices"""
    
    __tablename__ = "device_theme_installation"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, init=False, default_factory=lambda: str(uuid.uuid4()))
    device_id = Column(String(36), ForeignKey("device.id"), nullable=False)
    theme_id = Column(String(36), ForeignKey("device_theme.id"), nullable=False)
    
    # Installation status
    installed_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)  # Currently active theme
    
    # Customizations
    custom_config = Column(JSON, nullable=True)  # Device-specific overrides
    
    # Widget settings
    widget_clock_enabled = Column(Boolean, default=True)
    widget_weather_enabled = Column(Boolean, default=True)
    widget_calendar_enabled = Column(Boolean, default=False)
    widget_lunar_enabled = Column(Boolean, default=True)

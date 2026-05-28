"""
Device model - represents an IoT device.

Tracks hardware devices (boards, speakers, microphones) that connect to the server
via WebSocket or MQTT for agent communication.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid6 import uuid7

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class Device(Base):
    """Device (IoT hardware) model."""

    __tablename__ = "device"
    __table_args__ = (
        UniqueConstraint("user_id", "mac_address", name="uq_device_user_mac_address"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    mac_address: Mapped[str] = mapped_column(String(50), index=True)

    agent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("agent.id"),
        nullable=True,
        default=None,
        index=True,
    )

    device_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )

    board: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)

    firmware_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None
    )

    status: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)

    # Intercom settings - if True, this device appears in friends' intercom contact lists
    intercom_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ============ License Management ============
    # License type: 'unlimited', 'days', 'months', 'years', 'date'
    license_type: Mapped[str] = mapped_column(
        String(20), default="unlimited", nullable=False, init=False
    )
    # License duration value (e.g., 30 days, 6 months, 1 year)
    license_value: Mapped[Optional[int]] = mapped_column(
        nullable=True, default=None, init=False
    )
    # Specific expiration date (for 'date' license type)
    license_expiration_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
    # When the device was activated (license starts counting from this date)
    license_activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )

    # ============ Feature Toggles ============
    # JSON dict of feature flags: {"music": true, "radio": true, "bluetooth": false, ...}
    # Keys: music, radio, weather, sdCardMusic, alarm, reminder, voiceRecording, bluetooth, homeAssistant
    features: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=None, init=False
    )

    # ============ Hardware capabilities reported by FW hello (multi-board) ============
    # Auto-populated whenever the device sends a hello message containing a
    # `capabilities` block. Server uses this to filter MCP tools, decide
    # image-proxy max_size, and gate admin features per device.
    # Shape mirrors BoardCapability::ToJson() — see firmware
    # main/board_capability.cc.
    # Example:
    #   {
    #     "soc": "esp32s3", "board_type": "xiaozhi-ai-iot-vietnam-1st",
    #     "fw_version": "2.0.4", "display_w": 284, "display_h": 240,
    #     "psram_mb": 8, "has_touch": false, "has_camera": false,
    #     "has_sd": false, "can_meeting": true, "can_sales": true,
    #     "enabled_features": ["meeting","sales","weather","alarm_clock"]
    #   }
    capabilities: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=None, init=False
    )
    capabilities_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )

    # ============ Custom Firmware ============
    # custom firmware variant slug (e.g., "vip", "demo"). If set, OTA uses this variant instead of common
    custom_firmware: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, default=None, init=False
    )

    # Custom background image URL for the device (used in display module)
    background_image_url: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, default=None, init=False
    )

    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        init=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        init=False,
    )

"""System Settings model for global configuration.

Stores key-value settings for the entire system.
Only SuperAdmin can read/write these settings.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class SystemSetting(Base):
    """Global system settings (key-value store).
    
    Categories:
    - auto_provision: Device auto-provisioning settings
    - oauth: OAuth provider settings (Google, Zalo)
    - general: General system settings
    """
    __tablename__ = "system_setting"

    key: Mapped[str] = mapped_column(
        String(100), primary_key=True,
        comment="Setting key (e.g., 'auto_provision.enabled')"
    )
    value: Mapped[dict] = mapped_column(
        JSON, nullable=False, default_factory=dict,
        comment="Setting value as JSON"
    )
    description: Mapped[str | None] = mapped_column(
        Text, default=None, nullable=True,
        comment="Human-readable description"
    )
    category: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False, index=True,
        comment="Setting category for grouping"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(36), default=None, nullable=True,
        comment="User ID who last updated"
    )

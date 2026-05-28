"""
UserTool model - User-defined tool configurations.

Stores custom tool configs với validated JSON schema.
Cho phép user tạo nhiều config khác nhau cho cùng một tool.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from ..core.db.database import Base


class UserTool(Base):
    """User-defined tool configuration."""

    __tablename__ = "user_tool"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id"), index=True
    )

    # Reference to system tool in registry
    tool_name: Mapped[str] = mapped_column(String(100), index=True)

    # User-friendly display name for this config instance
    name: Mapped[str] = mapped_column(String(255))

    # Optional description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tool configuration (validated against tool schema)
    config: Mapped[dict] = mapped_column(JSON, default_factory=dict)

    # Whether this tool config is active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

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

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

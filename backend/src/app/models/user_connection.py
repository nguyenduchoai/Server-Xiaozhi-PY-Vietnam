"""
UserConnection model — Centralized integration/channel configuration.

Each user configures their messaging channels ONCE here.
Agents, Meetings, Education modules reference connection IDs.

Supported types: telegram, zalo_oa, zalo, smtp, imap
"""

from datetime import datetime, timezone
from typing import Optional
from uuid6 import uuid7

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Boolean,
    JSON,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class UserConnection(Base):
    """User-level integration/connection configuration.
    
    Examples:
    - Telegram Bot: {bot_token, chat_ids}
    - Zalo OA: {oa_access_token, user_ids}
    - SMTP: {host, port, username, password, from_name, from_email}
    - IMAP: {host, port, username, password, folder, poll_interval}
    """

    __tablename__ = "user_connection"
    __table_args__ = (
        Index("ix_user_connection_user_type", "user_id", "type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id"), index=True
    )

    # Channel type: telegram, zalo_oa, zalo, smtp, imap
    type: Mapped[str] = mapped_column(String(50), index=True)

    # User-friendly label (e.g. "Bot Chính", "Gmail Công ty")
    name: Mapped[str] = mapped_column(String(255))

    # Channel-specific configuration (JSON)
    config: Mapped[dict] = mapped_column(JSON, default_factory=dict)

    # Whether this connection is active
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Connection status: connected, disconnected, error, pending
    status: Mapped[str] = mapped_column(String(50), default="disconnected")

    # Extra status info (error details, last check time, etc.)
    status_info: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=None
    )

    # Timestamps
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

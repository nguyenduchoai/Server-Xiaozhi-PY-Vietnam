"""
Voice model - represents a cloned voice profile for TTS.

A Voice is created by uploading an audio sample (3-30s) which is processed
by Valtec-TTS to generate voice embeddings. Each user can have max 10 voices.
"""

from datetime import datetime, timezone
from uuid6 import uuid7

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Float,
    Integer,
    Boolean,
    Text,
    LargeBinary,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class Voice(Base):
    """Voice cloning model for TTS customization."""

    __tablename__ = "voices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Audio file metadata (required fields first)
    audio_file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Path to original audio sample"
    )

    audio_duration: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Duration in seconds"
    )

    audio_size: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="File size in bytes"
    )

    # Optional fields with defaults
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    sample_rate: Mapped[int] = mapped_column(
        Integer, default=24000, comment="Audio sample rate (Hz)"
    )

    # Voice embeddings from Valtec-TTS /clone endpoint
    embeddings: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
        default=None,
        comment="Serialized voice embeddings (numpy array or base64)"
    )

    # Status flags
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="User's default voice"
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

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (
        # Index for faster queries
        Index(
            "idx_voices_user_id",
            "user_id",
            postgresql_where="is_deleted = FALSE"
        ),
        Index(
            "idx_voices_is_default",
            "user_id",
            "is_default",
            postgresql_where="is_deleted = FALSE"
        ),
        # Unique voice name per user (only active voices)
        # Note: UniqueConstraint with WHERE clause must be created via migration
        # We'll enforce uniqueness in application logic for now
    )

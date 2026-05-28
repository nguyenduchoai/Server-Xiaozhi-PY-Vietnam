"""
Emoji Pack Models

Stores custom emoji packs for ESP32 devices.
Users can create custom packs by replacing individual emotions.
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from ..core.db.database import Base


class ApprovalStatus(str, enum.Enum):
    """Approval status for public sharing"""
    PRIVATE = "private"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EmojiPack(Base):
    """
    Emoji Pack - A collection of 21 emotion emojis.
    
    Users can create packs, customize individual emotions,
    and optionally share with the community.
    """
    __tablename__ = "emoji_pack"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, init=True)
    
    # Owner
    user_id: Mapped[str] = mapped_column(
        String, 
        ForeignKey("user.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True,
        init=True
    )
    
    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False, init=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None, init=False)
    
    # Configuration
    target_size: Mapped[int] = mapped_column(Integer, default=64, nullable=False, init=False)
    base_pack: Mapped[str] = mapped_column(String(50), default="twemoji", nullable=False, init=False)
    
    # Sharing
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)
    approval_status: Mapped[str] = mapped_column(
        String(20), 
        default=ApprovalStatus.PRIVATE.value, 
        nullable=False,
        init=False
    )
    
    # Statistics
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)
    
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
    
    # Relationships
    assets: Mapped[list["EmojiPackAsset"]] = relationship(
        "EmojiPackAsset",
        back_populates="pack",
        cascade="all, delete-orphan",
        lazy="selectin",
        init=False
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_emoji_pack_public", "is_public", "approval_status"),
    )

    def __repr__(self) -> str:
        return f"<EmojiPack {self.name} (size={self.target_size})>"


class EmojiPackAsset(Base):
    """
    Individual emoji asset within a pack.
    
    Each asset represents one emotion (e.g., happy, sad, angry)
    with either a custom uploaded image or reference to library emoji.
    """
    __tablename__ = "emoji_pack_asset"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, init=True)
    
    # Parent pack
    pack_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("emoji_pack.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        init=True
    )
    
    # Emotion info
    emotion_name: Mapped[str] = mapped_column(String(50), nullable=False, init=True)
    
    # File info
    file_path: Mapped[str] = mapped_column(Text, nullable=False, init=True)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False, default="png", init=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)
    
    # Animation info (for GIFs)
    has_animation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)
    frame_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False, init=False)
    
    # Source tracking
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, init=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        init=False
    )
    
    # Relationships
    pack: Mapped["EmojiPack"] = relationship(
        "EmojiPack",
        back_populates="assets",
        init=False
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_emoji_asset_pack_emotion", "pack_id", "emotion_name", unique=True),
    )

    def __repr__(self) -> str:
        return f"<EmojiPackAsset {self.emotion_name} ({self.file_type})>"


class FlashJob(Base):
    """
    Flash job for OTA updates to devices.
    
    Tracks the status of flashing emoji packs or assets to devices.
    """
    __tablename__ = "flash_job"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, init=True)
    
    # Owner
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        init=True
    )
    
    # Target device
    device_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        init=True
    )
    
    # Content to flash
    pack_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("emoji_pack.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        init=False
    )
    asset_type: Mapped[str] = mapped_column(String(50), default="emoji_pack", nullable=False, init=False)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False, init=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None, init=False)
    
    # Binary info
    binary_size: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None, init=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        init=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        init=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        init=False
    )

    def __repr__(self) -> str:
        return f"<FlashJob {self.id[:8]} ({self.status})>"


# Emotion constants
EMOTION_NAMES = [
    "neutral", "happy", "laughing", "funny", "sad",
    "angry", "crying", "loving", "embarrassed", "surprised",
    "shocked", "thinking", "winking", "cool", "relaxed",
    "delicious", "kissy", "confident", "sleepy", "silly", "confused"
]

EMOTION_IDS = {name: idx for idx, name in enumerate(EMOTION_NAMES)}

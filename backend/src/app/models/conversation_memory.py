"""
Conversation Memory Model

Stores user preferences, conversation context, and learned information
to enable personalized AI interactions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid6 import uuid7

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class MemoryType(str, Enum):
    """Types of memory stored"""
    SHORT_TERM = "short_term"       # Recent conversation context (expires)
    LONG_TERM = "long_term"         # Permanent learned facts
    PREFERENCE = "preference"        # User preferences
    FACT = "fact"                   # Facts about user (name, birthday, etc.)
    HABIT = "habit"                 # User habits/patterns
    RELATIONSHIP = "relationship"   # Relationships (family, friends)


class MemorySource(str, Enum):
    """How the memory was acquired"""
    EXPLICIT = "explicit"           # User directly stated
    INFERRED = "inferred"          # AI inferred from conversation
    SYSTEM = "system"              # System-generated


class ConversationMemory(Base):
    """
    Stores memories and preferences for personalized AI interactions.
    
    Examples:
        - user_name: "Hoài" (explicit)
        - favorite_music: "nhạc trữ tình" (inferred)
        - wake_time: "06:30" (habit)
        - family_member: {"name": "Mẹ", "phone": "..."} (relationship)
    """
    __tablename__ = "conversation_memories"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False)
    
    # Required fields (no default)
    device_id: Mapped[str] = mapped_column(String(50), index=True)
    key: Mapped[str] = mapped_column(String(100), index=True)  # e.g., "user_name"
    
    # Content - required but has server default
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Optional ownership
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=True, default=None)
    agent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("agent.id", ondelete="SET NULL"), nullable=True, default=None)
    
    # Memory classification (with defaults)
    memory_type: Mapped[str] = mapped_column(String(20), default=MemoryType.LONG_TERM.value)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    
    # Confidence and source (with defaults)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(20), default=MemorySource.EXPLICIT.value)
    source_message_id: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    
    # Usage tracking (with defaults)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    
    # Expiration (with default)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default="now()",
        default=None,
        init=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=datetime.utcnow,
        nullable=True,
        default=None,
        init=False
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_memory_device_key", "device_id", "key"),
        Index("idx_memory_user_type", "user_id", "memory_type"),
        Index("idx_memory_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<ConversationMemory {self.key}={self.value}>"
    
    def is_expired(self) -> bool:
        """Check if this memory has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def increment_access(self) -> None:
        """Track that this memory was accessed"""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()


class EmotionLog(Base):
    """
    Logs detected emotions from user interactions.
    Used for emotional intelligence and adaptive responses.
    """
    __tablename__ = "emotion_logs"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False)
    
    # Required fields
    device_id: Mapped[str] = mapped_column(String(50), index=True)
    emotion: Mapped[str] = mapped_column(String(20))  # neutral, happy, sad, angry, etc.
    
    # Optional fields with defaults
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=True, default=None)
    message_id: Mapped[Optional[str]] = mapped_column(nullable=True, default=None)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    emotion_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    
    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default="now()",
        default=None,
        init=False
    )

    __table_args__ = (
        Index("idx_emotion_device_time", "device_id", "detected_at"),
    )

    def __repr__(self) -> str:
        return f"<EmotionLog {self.emotion} ({self.confidence:.2f})>"


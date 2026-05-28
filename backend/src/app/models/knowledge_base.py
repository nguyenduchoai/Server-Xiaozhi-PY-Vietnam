"""
Knowledge Base model - Independent knowledge storage entity.

A KnowledgeBase is a collection of knowledge entries owned by a user.
Multiple agents can share the same knowledge base (many-to-many relationship).
"""

from datetime import datetime, timezone
from typing import Optional
from uuid6 import uuid7

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Boolean,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class KnowledgeBase(Base):
    """Knowledge Base entity - independent knowledge storage.
    
    Each user can create multiple knowledge bases, and each knowledge base
    can be linked to multiple templates (many-to-many via TemplateKnowledgeBase).
    
    NOTE: As of 2026-01-30, KBs are now linked to Templates instead of Agents.
    See TemplateKnowledgeBase for the new junction table.
    """

    __tablename__ = "knowledge_base"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    # RAGFlow integration (optional)
    ragflow_dataset_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, default=None
    )

    # Embedding model configuration
    embedding_model: Mapped[str] = mapped_column(
        String(100), default="text-embedding-3-small"
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

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

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, name={self.name})>"

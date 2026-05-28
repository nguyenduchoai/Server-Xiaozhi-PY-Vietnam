"""
Template-KnowledgeBase junction table.

Many-to-many relationship between Template and KnowledgeBase.
Each Template can specify which Knowledge Bases it should search.
KB must belong to the same Agent's user as the Template.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    PrimaryKeyConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class TemplateKnowledgeBase(Base):
    """Junction table: Template <-> KnowledgeBase (many-to-many).
    
    Allows:
    - One Template to use multiple knowledge bases
    - One knowledge base to be used by multiple templates
    - Different templates under same Agent can have different KBs
    
    Constraint: Knowledge base should belong to same user as template.
    """

    __tablename__ = "template_knowledge_base"

    template_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("template.id", ondelete="CASCADE"),
        primary_key=True,
    )

    knowledge_base_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_base.id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        init=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint("template_id", "knowledge_base_id"),
        Index("ix_template_kb_template", "template_id"),
        Index("ix_template_kb_kb", "knowledge_base_id"),
    )

    def __repr__(self) -> str:
        return f"<TemplateKnowledgeBase(template={self.template_id}, kb={self.knowledge_base_id})>"

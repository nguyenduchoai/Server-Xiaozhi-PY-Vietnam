"""
Agent-KnowledgeBase junction table.

Many-to-many relationship between Agent and KnowledgeBase.
An agent can have multiple knowledge bases, and a knowledge base
can be shared by multiple agents.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class AgentKnowledgeBase(Base):
    """Junction table: Agent <-> KnowledgeBase (many-to-many).
    
    Allows:
    - One agent to use multiple knowledge bases
    - One knowledge base to be shared by multiple agents
    """

    __tablename__ = "agent_knowledge_base"

    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent.id", ondelete="CASCADE"),
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
        PrimaryKeyConstraint("agent_id", "knowledge_base_id"),
    )

    def __repr__(self) -> str:
        return f"<AgentKnowledgeBase(agent={self.agent_id}, kb={self.knowledge_base_id})>"

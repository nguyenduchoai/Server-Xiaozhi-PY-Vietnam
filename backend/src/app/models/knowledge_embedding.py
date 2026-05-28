"""
Knowledge Embeddings Model - pgvector based storage for Knowledge Base.

Replaces ChromaDB with native PostgreSQL vector storage using pgvector extension.
Benefits:
- Single database (no SQLite files)
- Better scalability
- Native PostgreSQL backups
- ACID compliance
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid

# Conditional import for pgvector
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None

from ..core.db.database import Base


class KnowledgeEmbedding(Base, init=False):
    """Vector embeddings storage for Knowledge Base.
    
    Stores document content with vector embeddings for semantic search.
    Each agent has its own knowledge base (isolated by agent_id).
    
    Note: init=False to avoid dataclass field ordering issues
    """
    
    __tablename__ = "knowledge_embeddings"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        init=False,
    )
    
    # Required field - must come first (no default)
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # Optional fields with defaults
    # DEPRECATED: agent_id is kept for backward compatibility during migration
    # New entries should use knowledge_base_id instead
    agent_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        default=None,
    )
    
    # NEW: Link to independent KnowledgeBase entity
    knowledge_base_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        default=None,
    )
    
    doc_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="text",
    )
    
    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="manual",
    )
    
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    
    # Timestamps with defaults
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        init=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        init=False,
    )
    
    # Vector embedding - defined as regular Column to avoid dataclass issues
    # 1536 dimensions for OpenAI text-embedding-3-small
    if HAS_PGVECTOR:
        embedding = Column(Vector(1536), nullable=True)
    else:
        embedding = Column(Text, nullable=True)  # Fallback if pgvector not installed
    
    # Indexes for performance
    __table_args__ = (
        Index("ix_knowledge_agent_created", "agent_id", "created_at"),
        Index("ix_knowledge_kb_created", "knowledge_base_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<KnowledgeEmbedding(id={self.id}, agent={self.agent_id}, type={self.doc_type})>"

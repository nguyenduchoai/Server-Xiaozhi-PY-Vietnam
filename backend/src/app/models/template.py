"""
Template model - shareable configuration template for agents.

Templates are now independent from agents and can be shared across multiple agents.
The relationship is managed through AgentTemplateAssignment junction table.

Provider fields (ASR, LLM, VLLM, TTS, Memory, Intent) store provider references:
- "config:{name}" - Provider from config.yml (e.g., "config:CopilotLLM")
- "db:{uuid}" - Provider from database (e.g., "db:019abc-def...")
- NULL - Fallback to selected_module in config.yml

Tools field stores tool references:
- List of strings: UserTool UUIDs or system tool names
- Empty list/NULL - Fallback to config["Intent"]["functions"]
"""

from datetime import datetime, timezone
from uuid6 import uuid7

from sqlalchemy import DateTime, ForeignKey, String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class Template(Base):
    """Shareable template configuration for agents."""

    __tablename__ = "template"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), index=True)

    # Template config
    name: Mapped[str] = mapped_column(String(255))
    prompt: Mapped[str] = mapped_column(String)

    # Avatar image URL for template (shown on device)
    avatar_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, default=None
    )

    # Provider references - format: "config:{name}" or "db:{uuid}" or NULL
    # NULL means fallback to selected_module in config.yml
    ASR: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        index=True,
    )

    LLM: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        index=True,
    )

    VLLM: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        index=True,
    )

    TTS: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        index=True,
    )

    # TTS Voice override - allows different voice per template using same TTS provider
    # Format depends on provider: "female"/"male" for Valtec, "vi-VN-HoaiMyNeural" for Edge, etc.
    tts_voice: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )

    Memory: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        index=True,
    )

    Intent: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        index=True,
    )

    # Tool references - list of UserTool UUIDs or system tool names
    tools: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        insert_default=list,
        default_factory=list,
    )

    summary_memory: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )

    # Sharing flag for future marketplace
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # ====== Knowledge & Memory Toggles ======
    # Enable personal memory (OpenMemory) - remembers user preferences
    enable_memory: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    
    # Enable knowledge base RAG (ChromaDB/RAGFlow)
    enable_knowledge_base: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Knowledge Base IDs - list of KB UUIDs linked to this template
    knowledge_base_ids: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        insert_default=list,
        default_factory=list,
    )

    # Memory scope for multi-device scenarios:
    # - "agent_shared": All devices using this agent share the same memory pool
    # - "device_isolated": Each device has its own memory, even with same agent
    # - "hybrid": Shared knowledge base + device-specific conversation context
    memory_scope: Mapped[str] = mapped_column(
        String(20), default="agent_shared", nullable=False
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

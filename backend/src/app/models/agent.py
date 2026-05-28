"""
Agent model - The CORE entity of Xiaozhi platform.

An Agent is a complete AI persona with its own prompt, providers (LLM, TTS, ASR...),
knowledge base, memory, and tools. Agents can be assigned to multiple Devices (N:N).

Architecture (Agent-Centric):
- Agent IS the AI brain: contains all config (prompt, LLM, TTS, KB, Memory...)
- Agent ↔ Device: N:N through device.agent_id (device can switch agents)
- Template: Marketplace blueprints that users CLONE into personal Agents
"""

import secrets
from datetime import datetime, timezone
from uuid6 import uuid7

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Boolean,
    Integer,
    JSON,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base
from ..core.enums import StatusEnum


def _generate_api_key() -> str:
    """Generate a cryptographically secure API key for webhook authentication."""
    return secrets.token_urlsafe(48)


class Agent(Base):
    """Agent (AI persona) model — the central entity of Xiaozhi platform.
    
    Contains ALL configuration needed to run an AI assistant:
    - Identity: name, description, avatar, prompt
    - Providers: LLM, TTS, ASR, VLLM, Memory, Intent
    - Knowledge: KB IDs, Notebook IDs, enable flags
    - Tools: MCP tools and system functions
    - Origin: source_template_id (if cloned from marketplace)
    """

    __tablename__ = "agent"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), index=True)

    agent_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String)

    # Avatar image URL for agent (shown on device)
    avatar_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, default=None
    )

    status: Mapped[StatusEnum] = mapped_column(
        ENUM(StatusEnum, name="status", native_enum=True), default=StatusEnum.disabled
    )

    # ============ AI Configuration (merged from agent_template) ============
    
    # System prompt — the AI's personality and instructions
    prompt: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )

    # Provider references — format: "config:{name}" or "db:{uuid}" or NULL
    # NULL means fallback to selected_module in config.yml
    ASR: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None, index=True,
    )
    LLM: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None, index=True,
    )
    VLLM: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None, index=True,
    )
    TTS: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None, index=True,
    )
    # TTS Voice override — allows different voice per agent using same provider
    tts_voice: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None,
    )
    Memory: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None, index=True,
    )
    Intent: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None, index=True,
    )

    # Tool references — list of UserTool UUIDs or system tool names
    tools: Mapped[list | None] = mapped_column(
        JSON, nullable=True, insert_default=list, default_factory=list,
    )

    # Conversation summary memory for context window management
    summary_memory: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )

    # ============ Knowledge & Memory Toggles ============
    
    # Enable personal memory (OpenMemory) — remembers user preferences
    enable_memory: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # Enable knowledge base RAG (ChromaDB/RAGFlow)
    enable_knowledge_base: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Knowledge Base IDs — list of KB UUIDs linked to this agent
    knowledge_base_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, insert_default=list, default_factory=list,
    )

    # ============ Feature Module Toggles ============
    
    # Enable Education module — assign courses to this agent
    enable_education: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    # Enable Sales module — assign sales programs to this agent  
    enable_sales: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    # Enable Meeting module — assign meeting rooms to this agent
    enable_meeting: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )

    # Feature-specific ID lists
    course_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, insert_default=list, default_factory=list,
        comment="Education course UUIDs assigned to this agent",
    )
    sales_program_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, insert_default=list, default_factory=list,
        comment="Sales program UUIDs assigned to this agent",
    )
    meeting_room_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, insert_default=list, default_factory=list,
        comment="Meeting room UUIDs assigned to this agent",
    )

    # Banner Images - Default ads/banners to show on Kiosk/devices when idle
    banner_images: Mapped[list | None] = mapped_column(
        JSON, nullable=True, insert_default=list, default_factory=list,
        comment="List of default banner/ad image URLs to display when idle",
    )

    # ============ Origin & Marketplace ============
    
    # If this agent was cloned from a marketplace template
    source_template_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("template.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # ============ Legacy fields (kept for backward compatibility) ============
    # TODO: Remove after full migration to N:N device_agent
    
    active_template_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("template.id", ondelete="SET NULL", name="fk_agent_active_template"),
        nullable=True,
        default=None,
    )

    device_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("device.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    device_mac_address: Mapped[str | None] = mapped_column(
        String(17), nullable=True, default=None, index=True
    )

    # ============ User & Chat Config ============

    user_profile: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )

    # Chat history config: 0=disabled, 1=text only, 2=text+audio
    chat_history_conf: Mapped[int] = mapped_column(Integer, default=1)

    api_key: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        index=True,
        default=None,
        nullable=True,
        comment="Unique API key for webhook authentication (generated on demand)",
    )

    # ============ Notification Channels ============
    # Multi-channel notification routing config (SaaS per-agent)
    # Format: {
    #   "telegram": {"enabled": true, "bot_token": "xxx", "chat_ids": ["123"]},
    #   "zalo_oa": {"enabled": true, "oa_access_token": "xxx", "user_ids": ["u1"]},
    #   "alert_escalation": {"enabled": true, "levels": {...}},
    #   "daily_report": {"enabled": true, "time": "21:00", "timezone": "Asia/Ho_Chi_Minh"}
    # }
    notification_channels: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None,
        comment="Multi-channel notification config: Telegram, Zalo, escalation, daily report",
    )

    # ============ Timestamps ============

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

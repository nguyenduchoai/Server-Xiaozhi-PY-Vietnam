"""
Skill Marketplace Models

Enables users to share and install skills, agents, and MCP configurations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid6 import uuid7

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class SkillType(str, Enum):
    """Types of skills that can be shared"""
    MCP_SERVER = "mcp_server"           # MCP server configuration
    PLUGIN = "plugin"                   # Server plugin
    AGENT_TEMPLATE = "agent_template"   # Complete agent template
    VOICE_PACK = "voice_pack"          # Voice/TTS configuration
    PROMPT_TEMPLATE = "prompt_template" # Prompt templates


class SkillCategory(str, Enum):
    """Skill categories for browsing"""
    HOME_AUTOMATION = "home_automation"
    ENTERTAINMENT = "entertainment"
    PRODUCTIVITY = "productivity"
    INFORMATION = "information"
    COMMUNICATION = "communication"
    EDUCATION = "education"
    HEALTH = "health"
    UTILITIES = "utilities"
    OTHER = "other"


class Skill(Base):
    """
    A skill that can be shared in the marketplace.
    
    Skills can be MCP servers, plugins, agent templates, or voice packs
    that users can install to extend their AI assistant's capabilities.
    """
    __tablename__ = "skills"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False)
    
    # Required fields (no default)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    author_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    author_name: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Optional fields with defaults
    short_description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default=None)
    skill_type: Mapped[str] = mapped_column(String(30), default=SkillType.MCP_SERVER.value)
    category: Mapped[str] = mapped_column(String(30), default=SkillCategory.UTILITIES.value)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=None)
    author_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    min_platform_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default=None)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    
    # Media (optional)
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    screenshots: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=None)
    demo_video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    
    # Documentation (optional)
    readme: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    documentation_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    support_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    
    # Stats (with defaults)
    install_count: Mapped[int] = mapped_column(Integer, default=0)
    active_installs: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status (with defaults)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    
    # Moderation (with defaults)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default=None)
    moderation_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    
    # Timestamps
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
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

    # Relationships
    installations = relationship("SkillInstallation", back_populates="skill", cascade="all, delete-orphan")
    reviews = relationship("SkillReview", back_populates="skill", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_skill_category", "category", "is_public"),
        Index("idx_skill_featured", "is_featured", "is_public"),
        Index("idx_skill_rating", "rating", "install_count"),
    )

    def __repr__(self) -> str:
        return f"<Skill {self.name} v{self.version}>"
    
    def update_rating(self, new_rating: int) -> None:
        """Update average rating with new review"""
        total = self.rating * self.rating_count + new_rating
        self.rating_count += 1
        self.rating = total / self.rating_count


class SkillInstallation(Base):
    """
    Tracks skill installations by users.
    """
    __tablename__ = "skill_installations"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False)
    
    # Required references
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    installed_version: Mapped[str] = mapped_column(String(20))
    
    # Optional fields with defaults
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    
    # Timestamps
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default="now()",
        default=None,
        init=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    uninstalled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    # Relationship
    skill = relationship("Skill", back_populates="installations")

    __table_args__ = (
        Index("idx_installation_user_skill", "user_id", "skill_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<SkillInstallation {self.skill_id} by {self.user_id}>"


class SkillReview(Base):
    """
    User reviews for skills.
    """
    __tablename__ = "skill_reviews"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False)
    
    # Required references
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(Integer)  # 1-5 stars
    version_reviewed: Mapped[str] = mapped_column(String(20))
    
    # Optional fields with defaults
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default=None)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    
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

    # Relationship
    skill = relationship("Skill", back_populates="reviews")

    __table_args__ = (
        Index("idx_review_skill_rating", "skill_id", "rating"),
    )

    def __repr__(self) -> str:
        return f"<SkillReview {self.rating}★ for {self.skill_id}>"


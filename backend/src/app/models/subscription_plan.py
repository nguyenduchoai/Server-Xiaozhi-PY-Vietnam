"""
Subscription Plan Model

Defines pricing tiers and quotas for the platform.
Plans: FREE, PRO, ENTERPRISE
"""

from sqlalchemy import Boolean, Integer, String, BigInteger, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Plan details
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    
    # Pricing
    price_monthly: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # VND
    price_yearly: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)  # VND (optional discount)
    
    # Quotas (-1 = unlimited)
    max_agents: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    max_devices: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_monthly_tokens: Mapped[int] = mapped_column(BigInteger, default=50000, nullable=False)
    max_knowledge_base_size_mb: Mapped[int] = mapped_column(Integer, default=10, nullable=False)  # MB
    max_tts_minutes_monthly: Mapped[int] = mapped_column(Integer, default=30, nullable=False)  # minutes
    max_mcps: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # Max MCP servers
    max_templates: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # Max templates
    max_tools: Mapped[int] = mapped_column(Integer, default=10, nullable=False)  # Max tools
    
    # Features
    enable_api_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_webhook: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_custom_branding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_priority_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Provider access control
    # List of provider types user can use from system providers (e.g., ["openai", "gemini", "edge"])
    # null or empty = no system providers allowed (user must add their own)
    allowed_provider_types: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
    
    # Allow user to add their own provider API keys
    allow_custom_providers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # List of provider categories user can use (e.g., ["LLM", "TTS", "ASR"])
    # null = all categories allowed
    allowed_provider_categories: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
    
    # Device feature toggles (per-plan device capability control)
    # JSONB dict: {"music": true, "reminder": false, "memory": false, "intercom": false, ...}
    # If null, all features are allowed (backwards compatible)
    allowed_device_features: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None,
        comment="Device feature toggles per plan"
    )
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # For display ordering
    
    def __repr__(self) -> str:
        return f"<SubscriptionPlan {self.name} - {self.price_monthly} VND/month>"

"""
Marketplace models - Models for the Marketplace ecosystem.

MarketplaceItem: Items available for browse/purchase (templates, themes, courses, etc.)
MarketplaceInstallation: Tracks user installations/purchases
MarketplaceReview: User ratings and reviews
"""

from datetime import datetime, timezone
from uuid6 import uuid7

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Boolean,
    Integer,
    Numeric,
    Text,
    JSON,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class MarketplaceItem(Base):
    """An item available in the Marketplace for browsing/installing."""

    __tablename__ = "marketplace_item"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    # Required fields (no defaults) must come first in dataclass order
    seller_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
        comment="template, theme, course, feature, emoji_pack"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional / defaulted fields
    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True, default=None,
        comment="education, business, entertainment, utility, smart_home"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    price: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0,
        comment="0 = FREE"
    )
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    source_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True, default=None,
        comment="template, emoji_pack, course, etc."
    )
    source_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None,
        comment="UUID of the source resource to clone"
    )
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    screenshots: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None,
        comment="Array of screenshot URLs"
    )
    install_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_avg: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True,
        comment="draft, pending, approved, rejected"
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    tags: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None,
        comment="Array of tag strings for search"
    )
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


class MarketplaceInstallation(Base):
    """Tracks a user's installation of a marketplace item."""

    __tablename__ = "marketplace_installation"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_user_marketplace_item"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    # Required
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("marketplace_item.id"), nullable=False, index=True
    )

    # Optional / defaulted
    cloned_resource_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True, default=None,
        comment="template, emoji_pack, etc."
    )
    cloned_resource_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None,
        comment="UUID of the cloned resource in user's account"
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), default="free",
        comment="free, paid, refunded"
    )
    payment_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    uninstalled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        init=False,
    )


class MarketplaceReview(Base):
    """User review/rating for a marketplace item."""

    __tablename__ = "marketplace_review"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_user_review_item"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    # Required
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("marketplace_item.id"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Optional
    comment: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

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

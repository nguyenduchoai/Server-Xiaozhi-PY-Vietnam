"""
Marketplace schemas - Pydantic models for marketplace operations.
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ========== Marketplace Item ==========

class MarketplaceItemBase(BaseModel):
    """Base schema for marketplace item."""
    type: str = Field(description="template, theme, course, feature, emoji_pack")
    category: str | None = Field(default=None, description="education, business, entertainment, utility")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    price: float = Field(default=0, ge=0, description="0 = FREE")
    currency: str = Field(default="VND", max_length=3)
    icon_url: str | None = None
    cover_image_url: str | None = None
    screenshots: list[str] | None = None
    version: str = "1.0.0"
    tags: list[str] | None = None


class MarketplaceItemCreate(MarketplaceItemBase):
    """Schema for creating a marketplace item."""
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(description="template, emoji_pack, etc.")
    source_id: str = Field(description="UUID of source resource to clone on install")


class MarketplaceItemRead(MarketplaceItemBase):
    """Schema for reading a marketplace item."""
    id: str
    seller_id: str
    source_type: str | None = None
    source_id: str | None = None
    install_count: int = 0
    rating_avg: float = 0
    rating_count: int = 0
    status: str = "draft"
    is_featured: bool = False
    is_public: bool = True
    created_at: datetime
    updated_at: datetime

    # Enriched fields (not in DB)
    seller_name: str | None = None
    seller_email: str | None = None
    is_installed: bool = False  # Whether current user has installed this


class MarketplaceItemUpdate(BaseModel):
    """Schema for updating a marketplace item."""
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    short_description: str | None = None
    price: float | None = Field(default=None, ge=0)
    category: str | None = None
    icon_url: str | None = None
    cover_image_url: str | None = None
    screenshots: list[str] | None = None
    version: str | None = None
    tags: list[str] | None = None
    is_public: bool | None = None


class MarketplaceItemAdminUpdate(MarketplaceItemUpdate):
    """Admin schema for updating item status."""
    status: str | None = Field(default=None, description="draft, pending, approved, rejected")
    is_featured: bool | None = None


# ========== Installation ==========

class MarketplaceInstallationRead(BaseModel):
    """Schema for reading an installation."""
    id: str
    user_id: str
    item_id: str
    cloned_resource_type: str | None = None
    cloned_resource_id: str | None = None
    payment_status: str = "free"
    payment_amount: float = 0
    installed_at: datetime
    uninstalled_at: datetime | None = None

    # Enriched
    item: MarketplaceItemRead | None = None


# ========== Review ==========

class MarketplaceReviewCreate(BaseModel):
    """Schema for creating a review."""
    model_config = ConfigDict(extra="forbid")

    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class MarketplaceReviewRead(BaseModel):
    """Schema for reading a review."""
    id: str
    user_id: str
    item_id: str
    rating: int
    comment: str | None = None
    created_at: datetime
    updated_at: datetime

    # Enriched
    user_name: str | None = None


class MarketplaceReviewUpdate(BaseModel):
    """Schema for updating a review."""
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None

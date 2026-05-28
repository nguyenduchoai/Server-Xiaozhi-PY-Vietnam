"""Subscription Plan Schemas"""

from pydantic import BaseModel, Field
from typing import Annotated


class SubscriptionPlanBase(BaseModel):
    """Base schema for Subscription Plan"""
    name: Annotated[str, Field(max_length=50, examples=["FREE", "PRO", "ENTERPRISE"])]
    display_name: Annotated[str, Field(max_length=100, examples=["Gói Miễn Phí"])]
    description: Annotated[str | None, Field(default=None, max_length=500)]
    price_monthly: Annotated[int, Field(ge=0, examples=[0, 299000])]
    price_yearly: Annotated[int | None, Field(default=None, ge=0)]
    max_agents: Annotated[int, Field(examples=[2, 10, -1])]  # -1 = unlimited
    max_devices: Annotated[int, Field(examples=[3, 20, -1])]
    max_monthly_tokens: Annotated[int, Field(examples=[50000, 500000, -1])]
    max_knowledge_base_size_mb: Annotated[int, Field(examples=[5, 50, -1])]
    max_tts_minutes_monthly: Annotated[int, Field(examples=[10, 120, -1])]
    max_mcps: Annotated[int, Field(default=3, examples=[3, 10, -1])]  # Max MCP servers
    max_templates: Annotated[int, Field(default=5, examples=[5, 20, -1])]  # Max templates
    max_tools: Annotated[int, Field(default=10, examples=[10, 50, -1])]  # Max tools
    enable_api_access: bool = False
    enable_webhook: bool = False
    enable_custom_branding: bool = False
    enable_priority_support: bool = False
    # Provider access control
    allowed_provider_types: list[str] | None = None  # ["openai", "gemini", "gemini_live", "edge"]
    allow_custom_providers: bool = True  # User can add own API keys
    allowed_provider_categories: list[str] | None = None  # ["LLM", "TTS", "ASR"]
    allowed_device_features: dict | None = None  # {"music": true, "reminder": false, ...}
    is_active: bool = True
    sort_order: int = 0


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Schema for creating a subscription plan"""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """Schema for updating a subscription plan"""
    display_name: str | None = None
    description: str | None = None
    price_monthly: int | None = None
    price_yearly: int | None = None
    max_agents: int | None = None
    max_devices: int | None = None
    max_monthly_tokens: int | None = None
    max_knowledge_base_size_mb: int | None = None
    max_tts_minutes_monthly: int | None = None
    max_mcps: int | None = None
    max_templates: int | None = None
    max_tools: int | None = None
    enable_api_access: bool | None = None
    enable_webhook: bool | None = None
    enable_custom_branding: bool | None = None
    enable_priority_support: bool | None = None
    allowed_provider_types: list[str] | None = None
    allow_custom_providers: bool | None = None
    allowed_provider_categories: list[str] | None = None
    allowed_device_features: dict | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class SubscriptionPlanRead(SubscriptionPlanBase):
    """Schema for reading a subscription plan"""
    id: int
    
    class Config:
        from_attributes = True


class SubscriptionPlanPublic(BaseModel):
    """Public schema for subscription plan (no sensitive data)"""
    id: int
    name: str
    display_name: str
    description: str | None
    price_monthly: int
    price_yearly: int | None
    max_agents: int
    max_devices: int
    max_monthly_tokens: int
    max_knowledge_base_size_mb: int
    max_tts_minutes_monthly: int
    max_mcps: int
    max_templates: int
    max_tools: int
    enable_api_access: bool
    enable_webhook: bool
    enable_custom_branding: bool
    enable_priority_support: bool
    allowed_provider_types: list[str] | None
    allow_custom_providers: bool
    allowed_provider_categories: list[str] | None
    allowed_device_features: dict | None = None
    sort_order: int  # Needed for sorting
    
    class Config:
        from_attributes = True

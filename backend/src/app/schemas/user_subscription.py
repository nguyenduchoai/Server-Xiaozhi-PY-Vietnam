"""User Subscription Schemas"""

from pydantic import BaseModel, Field
from datetime import datetime
from app.models.user_subscription import SubscriptionStatus, SubscriptionBillingCycle
from .subscription_plan import SubscriptionPlanPublic


class UserSubscriptionBase(BaseModel):
    """Base schema for User Subscription"""
    user_id: str
    plan_id: int
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    billing_cycle: SubscriptionBillingCycle = SubscriptionBillingCycle.MONTHLY


class UserSubscriptionCreate(UserSubscriptionBase):
    """Schema for creating a user subscription"""
    started_at: datetime | None = None
    expires_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


class UserSubscriptionUpdate(BaseModel):
    """Schema for updating a user subscription"""
    plan_id: int | None = None
    status: SubscriptionStatus | None = None
    billing_cycle: SubscriptionBillingCycle | None = None
    expires_at: datetime | None = None
    current_period_end: datetime | None = None
    monthly_tokens_used: int | None = None
    monthly_tts_minutes_used: int | None = None


class UserSubscriptionRead(UserSubscriptionBase):
    """Schema for reading a user subscription"""
    id: str
    started_at: datetime
    expires_at: datetime | None
    cancelled_at: datetime | None
    current_period_start: datetime
    current_period_end: datetime | None
    monthly_tokens_used: int
    monthly_tts_minutes_used: int
    created_at: datetime
    updated_at: datetime | None
    
    class Config:
        from_attributes = True


class UserSubscriptionWithPlan(UserSubscriptionRead):
    """User subscription with plan details"""
    plan: SubscriptionPlanPublic
    
    class Config:
        from_attributes = True


class UsagePercent(BaseModel):
    """Usage percentage for each resource"""
    agents: float = 0
    devices: float = 0
    tokens: float = 0
    tts_minutes: float = 0


class UserSubscriptionUsage(BaseModel):
    """Current usage statistics"""
    monthly_tokens_used: int
    monthly_tokens_limit: int
    monthly_tts_minutes_used: int
    monthly_tts_minutes_limit: int
    agents_count: int
    agents_limit: int
    devices_count: int
    devices_limit: int
    # Also expose with simpler names for frontend compatibility
    tokens_used: int = 0
    tokens_limit: int = 0
    usage_percentage: float  # Overall usage 0-100%
    usage_percent: UsagePercent = Field(default_factory=UsagePercent)
    
    class Config:
        from_attributes = True

"""
User Subscription Model

Tracks user's current subscription plan and status.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, BigInteger, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from ..core.db.database import Base


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enum"""
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"  # Waiting for payment approval
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class SubscriptionBillingCycle(str, enum.Enum):
    """Billing cycle enum"""
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"
    LIFETIME = "LIFETIME"


class UserSubscription(Base):
    __tablename__ = "user_subscription"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # Foreign keys
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_plan.id"), nullable=False)
    
    # Subscription details
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        index=True
    )
    billing_cycle: Mapped[SubscriptionBillingCycle] = mapped_column(
        SQLEnum(SubscriptionBillingCycle),
        default=SubscriptionBillingCycle.MONTHLY,
        nullable=False
    )
    
    # Dates
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=None  # Must be set explicitly
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )  # NULL = lifetime/never expires
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    
    # Usage tracking (reset monthly)
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=None  # Must be set explicitly
    )
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    
    # Usage counters
    monthly_tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    monthly_tts_minutes_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=None  # Must be set explicitly
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )
    
    # Relationships
    user = relationship("User", backref="subscriptions")
    plan = relationship("SubscriptionPlan", backref="subscriptions")
    
    def __repr__(self) -> str:
        return f"<UserSubscription user_id={self.user_id} status={self.status}>"

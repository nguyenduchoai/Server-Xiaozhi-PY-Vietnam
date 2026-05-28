"""
Subscription Payment Model

Tracks payment requests with proof of transfer image.
Admin approves/rejects based on payment proof.
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, BigInteger, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from ..core.db.database import Base


class PaymentStatus(str, enum.Enum):
    """Payment status enum"""
    PENDING = "pending"  # Waiting for admin approval
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"  # Request expired after 24h


class PaymentMethod(str, enum.Enum):
    """Payment method enum"""
    BANK_TRANSFER = "bank_transfer"
    MOMO = "momo"
    ZALOPAY = "zalopay"
    VNPAY = "vnpay"


class SubscriptionPayment(Base):
    __tablename__ = "subscription_payment"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # Foreign keys
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_plan.id"), nullable=False)
    
    # Payment details
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # VND
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod),
        default=PaymentMethod.BANK_TRANSFER,
        nullable=False
    )
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)  # monthly/yearly
    
    # Payment proof
    payment_proof_image_base64: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    transaction_note: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)  # User's note
    
    # Bank transfer details (optional)
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    account_number: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    account_holder: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    transfer_reference: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)  # Mã giao dịch
    
    # Status
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Admin approval
    reviewed_by_admin_id: Mapped[str | None] = mapped_column(String, ForeignKey("user.id"), nullable=True, default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    admin_note: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)  # Admin's rejection reason
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
        default=None
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )  # Auto-expire after 24h if not reviewed
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="payment_requests")
    plan = relationship("SubscriptionPlan", backref="payments")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_admin_id])
    
    def __repr__(self) -> str:
        return f"<SubscriptionPayment id={self.id} status={self.status} amount={self.amount}>"

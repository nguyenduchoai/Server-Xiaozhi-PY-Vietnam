"""Subscription Payment Schemas"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Annotated, Literal
from app.models.subscription_payment import PaymentStatus, PaymentMethod


# Supported billing cycles for a payment request. Keep narrow so arbitrary
# strings cannot be passed through to the approval flow (where they would be
# silently treated as "monthly" by the duration calculator).
BillingCycleLiteral = Literal["monthly", "yearly"]


class SubscriptionPaymentBase(BaseModel):
    """Base schema for Subscription Payment"""
    user_id: str
    plan_id: int
    amount: Annotated[int, Field(ge=0, examples=[299000])]
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    billing_cycle: Annotated[str, Field(examples=["monthly", "yearly"])] = "monthly"


class SubscriptionPaymentCreate(BaseModel):
    """Schema for creating a payment request"""
    plan_id: int
    billing_cycle: BillingCycleLiteral = "monthly"
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    payment_proof_image_base64: str  # Required
    transaction_note: str | None = None
    bank_name: str | None = None
    account_holder: str | None = None
    transfer_reference: str | None = None


class SubscriptionPaymentUpdate(BaseModel):
    """Schema for updating a payment (admin only)"""
    status: PaymentStatus | None = None
    admin_note: str | None = None


class SubscriptionPaymentRead(SubscriptionPaymentBase):
    """Schema for reading a payment"""
    id: str
    status: PaymentStatus
    payment_proof_image_base64: str | None
    transaction_note: str | None
    bank_name: str | None
    account_number: str | None
    account_holder: str | None
    transfer_reference: str | None
    reviewed_by_admin_id: str | None
    reviewed_at: datetime | None
    admin_note: str | None
    created_at: datetime
    updated_at: datetime | None
    expires_at: datetime | None
    
    class Config:
        from_attributes = True


class SubscriptionPaymentApprove(BaseModel):
    """Schema for approving/rejecting payment"""
    status: PaymentStatus  # APPROVED or REJECTED
    admin_note: str | None = None
    
    class Config:
        use_enum_values = False


class SubscriptionPaymentListItem(BaseModel):
    """Simplified payment list item"""
    id: str
    user_id: str
    plan_id: int
    amount: int
    payment_method: PaymentMethod
    billing_cycle: str
    status: PaymentStatus
    created_at: datetime
    reviewed_at: datetime | None
    
    class Config:
        from_attributes = True

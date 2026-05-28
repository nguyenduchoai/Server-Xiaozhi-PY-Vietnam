"""
Pay2s Pydantic Schemas

Request/Response models for Pay2s payment gateway integration.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Request Schemas
# =============================================================================

class Pay2sCreatePaymentRequest(BaseModel):
    """Request to create a new Pay2s payment"""
    plan_id: int = Field(..., description="Subscription plan ID")
    billing_cycle: Literal["monthly", "yearly"] = Field(
        default="monthly",
        description="Billing cycle"
    )


class Pay2sIPNCallback(BaseModel):
    """IPN callback from Pay2s"""
    partnerCode: str
    orderId: str
    requestId: str
    amount: int
    orderInfo: str
    orderType: Optional[str] = None
    transId: Optional[int] = None
    resultCode: int
    message: str
    payType: Optional[str] = None
    responseTime: Optional[int] = None
    signature: Optional[str] = Field(None, alias="m2signature")
    
    class Config:
        populate_by_name = True


class Pay2sWebhookTransaction(BaseModel):
    """Single transaction in webhook payload"""
    id: int
    gateway: str
    transactionDate: str
    transactionNumber: str
    vaNumber: Optional[str] = None
    accountNumber: str
    content: str
    transferType: str  # IN or OUT
    transferAmount: int
    checksum: str


class Pay2sWebhookPayload(BaseModel):
    """Webhook payload from Pay2s Partner API"""
    transactions: list[Pay2sWebhookTransaction]


# =============================================================================
# Response Schemas
# =============================================================================

class Pay2sPaymentResponse(BaseModel):
    """Response after creating a payment"""
    order_id: str
    payment_url: str
    amount: int
    plan_name: str
    expires_at: datetime
    status: str = "pending"


class Pay2sStatusResponse(BaseModel):
    """Payment status check response"""
    order_id: str
    status: str  # pending, processing, success, failed, expired
    amount: int
    trans_id: Optional[str] = None
    plan_name: str
    paid_at: Optional[datetime] = None
    message: Optional[str] = None


class Pay2sTransactionRead(BaseModel):
    """Full transaction details for admin/user view"""
    id: str
    order_id: str
    user_id: str
    plan_id: int
    plan_name: Optional[str] = None
    amount: int
    billing_cycle: str
    status: str
    trans_id: Optional[int] = None
    result_code: Optional[int] = None
    pay_type: Optional[str] = None
    message: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None
    email_sent: bool = False
    
    class Config:
        from_attributes = True


# =============================================================================
# Settings Schemas
# =============================================================================

class Pay2sSettingsRead(BaseModel):
    """Pay2s settings for admin view (masked secret)"""
    pay2s_enabled: bool = False
    pay2s_sandbox_mode: bool = True
    pay2s_partner_code: str = ""
    pay2s_access_key: str = ""
    pay2s_secret_key: str = "******"  # Always masked
    pay2s_payment_timeout_minutes: int = 15
    pay2s_bank_account_number: str = ""
    pay2s_bank_id: str = ""


class Pay2sSettingsUpdate(BaseModel):
    """Pay2s settings update request"""
    pay2s_enabled: Optional[bool] = None
    pay2s_sandbox_mode: Optional[bool] = None
    pay2s_partner_code: Optional[str] = None
    pay2s_access_key: Optional[str] = None
    pay2s_secret_key: Optional[str] = None  # Only update if not "******"
    pay2s_payment_timeout_minutes: Optional[int] = None
    pay2s_bank_account_number: Optional[str] = None
    pay2s_bank_id: Optional[str] = None


# =============================================================================
# Generic Responses
# =============================================================================

class Pay2sSuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str = "Success"
    data: Optional[dict] = None


class Pay2sErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: dict = Field(default_factory=lambda: {"code": "ERROR", "message": "Unknown error"})

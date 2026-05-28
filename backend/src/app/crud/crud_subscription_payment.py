"""CRUD operations for Subscription Payments"""

from fastcrud import FastCRUD
from app.models.subscription_payment import SubscriptionPayment
from app.schemas.subscription_payment import (
    SubscriptionPaymentCreate,
    SubscriptionPaymentUpdate,
    SubscriptionPaymentRead,
)
from pydantic import BaseModel


CRUDSubscriptionPayment = FastCRUD[
    SubscriptionPayment,
    SubscriptionPaymentCreate,
    SubscriptionPaymentUpdate,
    SubscriptionPaymentUpdate,
    BaseModel,
    SubscriptionPaymentRead,
]

crud_subscription_payment = CRUDSubscriptionPayment(SubscriptionPayment)

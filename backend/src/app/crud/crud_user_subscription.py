"""CRUD operations for User Subscriptions"""

from fastcrud import FastCRUD
from app.models.user_subscription import UserSubscription
from app.schemas.user_subscription import (
    UserSubscriptionCreate,
    UserSubscriptionUpdate,
    UserSubscriptionRead,
)
from pydantic import BaseModel


CRUDUserSubscription = FastCRUD[
    UserSubscription,
    UserSubscriptionCreate,
    UserSubscriptionUpdate,
    UserSubscriptionUpdate,
    BaseModel,
    UserSubscriptionRead,
]

crud_user_subscription = CRUDUserSubscription(UserSubscription)

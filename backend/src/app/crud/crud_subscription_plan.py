"""CRUD operations for Subscription Plans"""

from fastcrud import FastCRUD
from app.models.subscription_plan import SubscriptionPlan
from app.schemas.subscription_plan import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionPlanRead,
)
CRUDSubscriptionPlan = FastCRUD[
    SubscriptionPlan,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionPlanUpdate,
    None,  # Delete schema - None means delete by id
    SubscriptionPlanRead,
]

crud_subscription_plan = CRUDSubscriptionPlan(SubscriptionPlan)

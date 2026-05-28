from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.crud.crud_subscription_plan import crud_subscription_plan
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription
from app.schemas.subscription_plan import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionPlanRead,
)
from sqlalchemy import select, update

router = APIRouter(prefix="/admin/plans", tags=["admin-plans"])


def require_superuser(current_user: dict) -> dict:
    is_superuser = current_user.get("is_superuser")
    role = current_user.get("role")
    
    if is_superuser:
        return current_user
        
    if role in ["admin", "super_admin"]:
        return current_user
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Superuser access required"
    )


@router.post("", response_model=SubscriptionPlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: SubscriptionPlanCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new subscription plan (Admin only)"""
    require_superuser(current_user)
    try:
        plan = await crud_subscription_plan.create(db, plan_data)
        await db.commit()
        await db.refresh(plan)
        return plan
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create plan: {str(e)}"
        )


@router.put("/{plan_id}", response_model=SubscriptionPlanRead)
async def update_plan(
    plan_id: int,
    plan_data: SubscriptionPlanUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a subscription plan (Admin only)"""
    require_superuser(current_user)
    
    plan = await crud_subscription_plan.get(db=db, id=plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    try:
        await crud_subscription_plan.update(db=db, object=plan_data, id=plan_id)
        await db.commit()
        
        # Fetch updated plan
        updated_plan = await crud_subscription_plan.get(
            db=db, id=plan_id, schema_to_select=SubscriptionPlanRead
        )
        return updated_plan
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update plan: {str(e)}"
        )


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a subscription plan (Admin only)
    
    If the plan has active subscriptions, users will be migrated to FREE plan automatically.
    """
    require_superuser(current_user)
    
    plan = await crud_subscription_plan.get(db=db, id=plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Get plan name (handle both dict and object)
    plan_name = plan.get("name") if isinstance(plan, dict) else plan.name
    
    # Check if this is the FREE plan - cannot delete
    if plan_name == "FREE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete FREE plan - it's the default plan"
        )
    
    
    # Find FREE plan for migration
    free_plan_result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.name == "FREE")
    )
    free_plan = free_plan_result.scalar_one_or_none()
    
    if not free_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete plan: FREE plan not found for migration"
        )
    
    try:
        # Migrate all subscriptions to FREE plan
        await db.execute(
            update(UserSubscription)
            .where(UserSubscription.plan_id == plan_id)
            .values(plan_id=free_plan.id)
        )
        
        # Now delete the plan
        await crud_subscription_plan.delete(db=db, id=plan_id)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete plan: {str(e)}"
        )

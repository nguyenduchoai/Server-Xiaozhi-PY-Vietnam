"""
Subscription Quotas Middleware

Checks if user has exceeded their subscription limits before creating resources.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.models.user_subscription import UserSubscription
from app.models.agent import Agent
from app.models.device import Device
from app.core.logger import get_logger

logger = get_logger(__name__)


async def check_can_create_agent(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> bool:
    """
    Check if user can create a new agent based on subscription limits.
    
    Raises HTTPException if limit exceeded.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("id")
        
        # Get active subscription with plan
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == "active")
            .order_by(UserSubscription.created_at.desc())
        )
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active subscription found. Please subscribe to a plan."
            )
        
        await db.refresh(subscription, ["plan"])
        plan = subscription.plan
        
        # Check if unlimited
        if plan.max_agents == -1:
            return True
        
        # Count current agents
        count_stmt = select(func.count(Agent.id)).where(
            Agent.user_id == user_id,
            Agent.is_deleted == False
        )
        count_result = await db.execute(count_stmt)
        current_count = count_result.scalar_one()
        
        if current_count >= plan.max_agents:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent limit reached. Your {plan.name} plan allows {plan.max_agents} agents. Please upgrade your subscription."
            )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking agent quota: {e}")
        # Allow creation if check fails (graceful degradation)
        return True


async def check_can_create_device(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> bool:
    """
    Check if user can create a new device based on subscription limits.
    
    Raises HTTPException if limit exceeded.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("id")
        
        # Get active subscription with plan
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == "active")
            .order_by(UserSubscription.created_at.desc())
        )
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active subscription found. Please subscribe to a plan."
            )
        
        await db.refresh(subscription, ["plan"])
        plan = subscription.plan
        
        # Check if unlimited
        if plan.max_devices == -1:
            return True
        
        # Count current devices
        count_stmt = select(func.count(Device.id)).where(Device.user_id == user_id)
        count_result = await db.execute(count_stmt)
        current_count = count_result.scalar_one()
        
        if current_count >= plan.max_devices:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Device limit reached. Your {plan.name} plan allows {plan.max_devices} devices. Please upgrade your subscription."
            )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking device quota: {e}")
        # Allow creation if check fails (graceful degradation)
        return True


async def check_token_quota(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    tokens_to_use: int,
) -> bool:
    """
    Check if user has enough token quota remaining.
    
    Returns True if OK, raises HTTPException if limit exceeded.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("id")
        
        # Get active subscription with plan
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == "active")
            .order_by(UserSubscription.created_at.desc())
        )
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            # Graceful: allow if no subscription (will be blocked by other checks)
            return True
        
        await db.refresh(subscription, ["plan"])
        plan = subscription.plan
        
        # Check if unlimited
        if plan.max_monthly_tokens == -1:
            return True
        
        # Check quota
        if subscription.monthly_tokens_used + tokens_to_use > plan.max_monthly_tokens:
            remaining = plan.max_monthly_tokens - subscription.monthly_tokens_used
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly token quota exceeded. You have {remaining} tokens remaining. Your {plan.name} plan allows {plan.max_monthly_tokens} tokens/month. Please upgrade."
            )
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking token quota: {e}")
        return True


async def track_token_usage(
    db: AsyncSession,
    user_id: str,
    tokens_used: int,
) -> None:
    """
    Track token usage for a user's current subscription period.
    
    Call this after successful LLM request.
    """
    try:
        # Get active subscription
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == "active")
            .order_by(UserSubscription.created_at.desc())
        )
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.monthly_tokens_used += tokens_used
            await db.commit()
            logger.debug(f"Tracked {tokens_used} tokens for user {user_id}, total: {subscription.monthly_tokens_used}")
        
    except Exception as e:
        logger.error(f"Error tracking token usage: {e}")
        # Don't fail the request if tracking fails
        pass

"""
Subscription Usage Tracker Service

Tracks token usage, TTS minutes and enforces quotas.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from ..models.user_subscription import UserSubscription, SubscriptionStatus
from ..core.logger import get_logger

logger = get_logger(__name__)


async def track_token_usage(
    db: AsyncSession,
    user_id: str,
    tokens_used: int,
    check_quota: bool = True
) -> None:
    """
    Track token usage for user's subscription.
    
    Args:
        db: Database session
        user_id: User ID
        tokens_used: Number of tokens consumed
        check_quota: Whether to enforce quota (raise error if exceeded)
        
    Raises:
        HTTPException 403: If quota exceeded and check_quota=True
    """
    # Get active subscription
    stmt = (
        select(UserSubscription)
        .where(UserSubscription.user_id == user_id)
        .where(UserSubscription.status == SubscriptionStatus.ACTIVE)
        .order_by(UserSubscription.created_at.desc())
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        logger.warning(f"No active subscription for user {user_id}, skipping token tracking")
        return
    
    # Load plan
    await db.refresh(subscription, ["plan"])
    plan = subscription.plan
    
    # Check quota before adding (if requested)
    if check_quota and plan.max_monthly_tokens != -1:
        new_total = subscription.monthly_tokens_used + tokens_used
        if new_total > plan.max_monthly_tokens:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Monthly token quota exceeded. Limit: {plan.max_monthly_tokens}, Used: {subscription.monthly_tokens_used}, Requested: {tokens_used}"
            )
    
    # Add tokens to usage
    subscription.monthly_tokens_used += tokens_used
    await db.commit()
    
    logger.debug(f"Tracked {tokens_used} tokens for user {user_id}. Total: {subscription.monthly_tokens_used}/{plan.max_monthly_tokens}")


async def track_tts_usage(
    db: AsyncSession,
    user_id: str,
    minutes_used: int,
    check_quota: bool = True
) -> None:
    """
    Track TTS minutes usage for user's subscription.
    
    Args:
        db: Database session
        user_id: User ID
        minutes_used: Number of TTS minutes consumed
        check_quota: Whether to enforce quota
        
    Raises:
        HTTPException 403: If quota exceeded and check_quota=True
    """
    # Get active subscription
    stmt = (
        select(UserSubscription)
        .where(UserSubscription.user_id == user_id)
        .where(UserSubscription.status == SubscriptionStatus.ACTIVE)
        .order_by(UserSubscription.created_at.desc())
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        logger.warning(f"No active subscription for user {user_id}, skipping TTS tracking")
        return
    
    # Load plan
    await db.refresh(subscription, ["plan"])
    plan = subscription.plan
    
    # Check quota before adding (if requested)
    if check_quota and plan.max_tts_minutes_monthly != -1:
        new_total = subscription.monthly_tts_minutes_used + minutes_used
        if new_total > plan.max_tts_minutes_monthly:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Monthly TTS quota exceeded. Limit: {plan.max_tts_minutes_monthly} minutes"
            )
    
    # Add minutes to usage
    subscription.monthly_tts_minutes_used += minutes_used
    await db.commit()
    
    logger.debug(f"Tracked {minutes_used} TTS minutes for user {user_id}")


async def check_token_quota(
    db: AsyncSession,
    user_id: str,
    tokens_needed: int
) -> bool:
    """
    Check if user has enough token quota.
    
    Returns:
        bool: True if user has quota, False otherwise
    """
    try:
        await track_token_usage(db, user_id, 0, check_quota=True)
        
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == SubscriptionStatus.ACTIVE)
            .order_by(UserSubscription.created_at.desc())
        )
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return False
        
        await db.refresh(subscription, ["plan"])
        plan = subscription.plan
        
        if plan.max_monthly_tokens == -1:
            return True  # Unlimited
        
        return (subscription.monthly_tokens_used + tokens_needed) <= plan.max_monthly_tokens
    except Exception:
        return False

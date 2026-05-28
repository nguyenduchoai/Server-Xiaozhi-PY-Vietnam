"""
Auto-assign FREE subscription to users who don't have one.

Run this as a one-time migration or add to user registration flow.
"""

import asyncio
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_engine
from app.models.user import User
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription, SubscriptionStatus, SubscriptionBillingCycle


async def auto_assign_free_plan():
    """Assign FREE plan to all users without active subscription"""
    
    async with AsyncSession(async_engine) as session:
        # Get FREE plan
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.name == "FREE")
        result = await session.execute(stmt)
        free_plan = result.scalar_one_or_none()
        
        if not free_plan:
            print("❌ FREE plan not found! Please seed subscription plans first.")
            return
        
        print(f"✅ Found FREE plan (ID: {free_plan.id})")
        
        # Get all users
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        print(f"📊 Found {len(users)} users")
        
        assigned_count = 0
        skipped_count = 0
        
        for user in users:
            # Check if user already has active subscription
            stmt = (
                select(UserSubscription)
                .where(UserSubscription.user_id == user.id)
                .where(UserSubscription.status.in_(["active", "pending"]))
            )
            result = await session.execute(stmt)
            existing_sub = result.scalar_one_or_none()
            
            if existing_sub:
                print(f"⏭️  User {user.email} already has subscription, skipping")
                skipped_count += 1
                continue
            
            # Create FREE subscription
            subscription = UserSubscription(
                id=str(uuid4()),
                user_id=user.id,
                plan_id=free_plan.id,
                status=SubscriptionStatus.ACTIVE,
                billing_cycle=SubscriptionBillingCycle.LIFETIME,
                started_at=datetime.now(timezone.utc),
                current_period_start=datetime.now(timezone.utc),
                monthly_tokens_used=0,
                monthly_tts_minutes_used=0,
            )
            
            session.add(subscription)
            print(f"✅ Assigned FREE plan to {user.email}")
            assigned_count += 1
        
        await session.commit()
        
        print(f"\n🎉 Done!")
        print(f"   ✅ Assigned: {assigned_count}")
        print(f"   ⏭️  Skipped: {skipped_count}")


if __name__ == "__main__":
    asyncio.run(auto_assign_free_plan())

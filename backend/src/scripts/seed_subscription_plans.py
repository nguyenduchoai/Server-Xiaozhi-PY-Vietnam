"""
Seed Subscription Plans

Run this script to populate initial subscription plans.
"""

import asyncio
from sqlalchemy import select
from app.core.db.database import async_engine, AsyncSession
from app.models.subscription_plan import SubscriptionPlan


async def seed_subscription_plans():
    """Create default subscription plans"""
    
    plans_data = [
        {
            "name": "FREE",
            "display_name": "Gói Miễn Phí",
            "description": "Gói cơ bản để trải nghiệm nền tảng",
            "price_monthly": 0,
            "price_yearly": 0,
            "max_agents": 2,
            "max_devices": 3,
            "max_monthly_tokens": 50000,
            "max_knowledge_base_size_mb": 5,
            "max_tts_minutes_monthly": 10,
            "enable_api_access": False,
            "enable_webhook": False,
            "enable_custom_branding": False,
            "enable_priority_support": False,
            "is_active": True,
            "sort_order": 1
        },
        {
            "name": "PRO",
            "display_name": "Gói Chuyên Nghiệp",
            "description": "Dành cho cá nhân và doanh nghiệp nhỏ",
            "price_monthly": 299000,  # 299k VND/month
            "price_yearly": 2990000,  # ~249k/month if yearly (discount 17%)
            "max_agents": 10,
            "max_devices": 20,
            "max_monthly_tokens": 500000,
            "max_knowledge_base_size_mb": 50,
            "max_tts_minutes_monthly": 120,
            "enable_api_access": True,
            "enable_webhook": True,
            "enable_custom_branding": False,
            "enable_priority_support": True,
            "is_active": True,
            "sort_order": 2
        },
        {
            "name": "ENTERPRISE",
            "display_name": "Gói Doanh Nghiệp",
            "description": "Không giới hạn, hỗ trợ ưu tiên 24/7",
            "price_monthly": 0,  # Custom pricing - contact sales
            "price_yearly": None,
            "max_agents": -1,  # Unlimited
            "max_devices": -1,
            "max_monthly_tokens": -1,
            "max_knowledge_base_size_mb": -1,
            "max_tts_minutes_monthly": -1,
            "enable_api_access": True,
            "enable_webhook": True,
            "enable_custom_branding": True,
            "enable_priority_support": True,
            "is_active": True,
            "sort_order": 3
        }
    ]
    
    async with AsyncSession(async_engine) as session:
        for plan_data in plans_data:
            # Check if plan exists
            stmt = select(SubscriptionPlan).where(SubscriptionPlan.name == plan_data["name"])
            result = await session.execute(stmt)
            existing_plan = result.scalar_one_or_none()
            
            if existing_plan:
                print(f"✅ Plan {plan_data['name']} already exists, skipping...")
            else:
                plan = SubscriptionPlan(**plan_data)
                session.add(plan)
                print(f"✅ Created plan: {plan_data['name']}")
        
        await session.commit()
        print("✅ Subscription plans seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_subscription_plans())

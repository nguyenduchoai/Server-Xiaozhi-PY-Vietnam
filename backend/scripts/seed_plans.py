"""
Seed default subscription plans.

Run: docker exec xiaozhi-backend python scripts/seed_plans.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from uuid6 import uuid7
from sqlalchemy import select
from app.core.db.database import local_session
from app.models.subscription_plan import SubscriptionPlan


DEFAULT_PLANS = [
    {
        "name": "Free",
        "description": "Gói miễn phí cho người dùng cá nhân",
        "price_monthly": 0,
        "price_yearly": 0,
        "currency": "VND",
        "max_agents": 2,
        "max_devices": 2,
        "max_templates": 3,
        "max_mcp_configs": 2,
        "max_tools": 5,
        "max_monthly_tokens": 50000,
        "max_monthly_tts_minutes": 30,
        "allowed_providers": ["config"],
        "allowed_device_features": {
            "enable_memory": True,
            "enable_knowledge_base": True,
            "enable_notebooklm": False,
            "enable_intercom": False,
            "enable_education": False,
            "enable_meeting": False,

            "custom_provider": False,
        },
        "is_active": True,
        "sort_order": 0,
    },
    {
        "name": "Pro",
        "description": "Dành cho người dùng chuyên nghiệp và doanh nghiệp nhỏ",
        "price_monthly": 199000,
        "price_yearly": 1990000,
        "currency": "VND",
        "max_agents": 10,
        "max_devices": 10,
        "max_templates": 20,
        "max_mcp_configs": 10,
        "max_tools": 30,
        "max_monthly_tokens": 500000,
        "max_monthly_tts_minutes": 300,
        "allowed_providers": ["config", "db"],
        "allowed_device_features": {
            "enable_memory": True,
            "enable_knowledge_base": True,
            "enable_notebooklm": True,
            "enable_intercom": True,
            "enable_education": True,
            "enable_meeting": True,

            "custom_provider": True,
        },
        "is_active": True,
        "sort_order": 1,
    },
    {
        "name": "Enterprise",
        "description": "Giải pháp toàn diện cho doanh nghiệp và tổ chức lớn",
        "price_monthly": 999000,
        "price_yearly": 9990000,
        "currency": "VND",
        "max_agents": -1,
        "max_devices": -1,
        "max_templates": -1,
        "max_mcp_configs": -1,
        "max_tools": -1,
        "max_monthly_tokens": -1,
        "max_monthly_tts_minutes": -1,
        "allowed_providers": ["config", "db", "custom"],
        "allowed_device_features": {
            "enable_memory": True,
            "enable_knowledge_base": True,
            "enable_notebooklm": True,
            "enable_intercom": True,
            "enable_education": True,
            "enable_meeting": True,

            "custom_provider": True,
        },
        "is_active": True,
        "sort_order": 2,
    },
]


async def seed_plans():
    """Insert default plans if not present."""
    async with local_session() as db:
        result = await db.execute(select(SubscriptionPlan))
        existing = result.scalars().all()
        existing_names = {p.name for p in existing}

        inserted = 0
        for plan_data in DEFAULT_PLANS:
            if plan_data["name"] in existing_names:
                print(f"  ⏭  Skipped: {plan_data['name']} (already exists)")
                continue

            plan = SubscriptionPlan(
                id=str(uuid7()),
                **plan_data,
            )
            db.add(plan)
            inserted += 1
            print(f"  ✅ Created: {plan_data['name']} — {plan_data['price_monthly']:,}đ/tháng")

        await db.commit()
        print(f"\n💰 Plan seeding complete: {inserted} new plans, {len(existing_names)} already existed.")


if __name__ == "__main__":
    print("💰 Seeding default subscription plans...")
    asyncio.run(seed_plans())

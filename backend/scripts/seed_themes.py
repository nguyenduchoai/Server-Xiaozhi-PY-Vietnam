"""
Seed default system themes for Theme Gallery.

Run: docker exec xiaozhi-backend python scripts/seed_themes.py
"""

import asyncio
import sys
import os

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from uuid6 import uuid7
from sqlalchemy import select
from app.core.db.database import local_session
from app.models.device_theme import DeviceTheme


DEFAULT_THEMES = [
    {
        "name": "Midnight Ocean",
        "description": "Tông màu xanh đại dương sâu thẳm với gradient nhẹ nhàng. Phù hợp không gian phòng ngủ.",
        "preview_url": "/themes/midnight-ocean.webp",
        "config": {
            "background": "#0a1628",
            "primary": "#3b82f6",
            "secondary": "#1e3a5f",
            "text": "#e2e8f0",
            "accent": "#06b6d4",
            "font": "Inter",
            "border_radius": 16,
            "animation": "wave",
        },
        "category": "dark",
        "is_system": True,
        "is_public": True,
    },
    {
        "name": "Warm Sunset",
        "description": "Gam màu ấm áp hoàng hôn. Tạo cảm giác thư giãn, phù hợp phòng khách gia đình.",
        "preview_url": "/themes/warm-sunset.webp",
        "config": {
            "background": "#1a0f0a",
            "primary": "#f59e0b",
            "secondary": "#92400e",
            "text": "#fef3c7",
            "accent": "#ef4444",
            "font": "Outfit",
            "border_radius": 12,
            "animation": "fade",
        },
        "category": "warm",
        "is_system": True,
        "is_public": True,
    },
    {
        "name": "Forest Green",
        "description": "Thiên nhiên xanh mát với phong cách minimalist. Giảm mỏi mắt khi sử dụng lâu.",
        "preview_url": "/themes/forest-green.webp",
        "config": {
            "background": "#0f1f0f",
            "primary": "#22c55e",
            "secondary": "#14532d",
            "text": "#dcfce7",
            "accent": "#86efac",
            "font": "Inter",
            "border_radius": 20,
            "animation": "breathe",
        },
        "category": "nature",
        "is_system": True,
        "is_public": True,
    },
    {
        "name": "Pure White",
        "description": "Giao diện sáng sủa, tinh tế. Phù hợp văn phòng và không gian chuyên nghiệp.",
        "preview_url": "/themes/pure-white.webp",
        "config": {
            "background": "#ffffff",
            "primary": "#3b82f6",
            "secondary": "#f1f5f9",
            "text": "#1e293b",
            "accent": "#6366f1",
            "font": "Roboto",
            "border_radius": 12,
            "animation": "slide",
        },
        "category": "light",
        "is_system": True,
        "is_public": True,
    },
    {
        "name": "Cyberpunk Neon",
        "description": "Phong cách cyberpunk sống động với neon glow. Dành cho người yêu công nghệ.",
        "preview_url": "/themes/cyberpunk-neon.webp",
        "config": {
            "background": "#0d0d0d",
            "primary": "#ff00ff",
            "secondary": "#1a0033",
            "text": "#e0e0e0",
            "accent": "#00ffff",
            "font": "JetBrains Mono",
            "border_radius": 4,
            "animation": "glitch",
        },
        "category": "creative",
        "is_system": True,
        "is_public": True,
    },
    {
        "name": "Sakura Pink",
        "description": "Cảm hứng từ hoa anh đào Nhật Bản. Nhẹ nhàng, nữ tính và thanh lịch.",
        "preview_url": "/themes/sakura-pink.webp",
        "config": {
            "background": "#1a0a14",
            "primary": "#f472b6",
            "secondary": "#831843",
            "text": "#fce7f3",
            "accent": "#fb923c",
            "font": "Outfit",
            "border_radius": 24,
            "animation": "fall",
        },
        "category": "kawaii",
        "is_system": True,
        "is_public": True,
    },
    {
        "name": "Nordic Frost",
        "description": "Phong cách Bắc Âu tối giản. Màu trầm nhã nhặn, tập trung vào trải nghiệm.",
        "preview_url": "/themes/nordic-frost.webp",
        "config": {
            "background": "#0f172a",
            "primary": "#94a3b8",
            "secondary": "#1e293b",
            "text": "#f8fafc",
            "accent": "#38bdf8",
            "font": "Inter",
            "border_radius": 8,
            "animation": "none",
        },
        "category": "minimal",
        "is_system": True,
        "is_public": True,
    },
    {
        "name": "Vietnamese Heritage",
        "description": "Cảm hứng từ văn hóa Việt Nam. Sắc đỏ truyền thống kết hợp vàng son rực rỡ.",
        "preview_url": "/themes/vietnamese-heritage.webp",
        "config": {
            "background": "#1a0505",
            "primary": "#dc2626",
            "secondary": "#7f1d1d",
            "text": "#fef2f2",
            "accent": "#eab308",
            "font": "Be Vietnam Pro",
            "border_radius": 12,
            "animation": "fade",
        },
        "category": "cultural",
        "is_system": True,
        "is_public": True,
    },
]


async def seed_themes():
    """Insert default themes if not already present."""
    async with local_session() as db:
        # Check existing system themes
        result = await db.execute(
            select(DeviceTheme).where(DeviceTheme.is_system == True)
        )
        existing = result.scalars().all()
        existing_names = {t.name for t in existing}

        inserted = 0
        for theme_data in DEFAULT_THEMES:
            if theme_data["name"] in existing_names:
                print(f"  ⏭  Skipped: {theme_data['name']} (already exists)")
                continue

            theme = DeviceTheme(
                id=str(uuid7()),
                name=theme_data["name"],
                description=theme_data["description"],
                preview_url=theme_data.get("preview_url", ""),
                config=theme_data["config"],
                category=theme_data.get("category", "dark"),
                is_system=True,
                is_public=True,
                user_id=None,  # System themes have no owner
            )
            db.add(theme)
            inserted += 1
            print(f"  ✅ Created: {theme_data['name']}")

        await db.commit()
        print(f"\n🎨 Theme seeding complete: {inserted} new themes, {len(existing_names)} already existed.")


if __name__ == "__main__":
    print("🎨 Seeding default system themes...")
    asyncio.run(seed_themes())

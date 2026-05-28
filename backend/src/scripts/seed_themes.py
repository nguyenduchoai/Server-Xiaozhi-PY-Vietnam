"""
Seed default system themes
Run with: docker exec xiaozhi-backend python3 -m scripts.seed_themes
"""

import asyncio
import uuid
from datetime import datetime

# Add parent to path
import sys
sys.path.insert(0, '/app/src')

from app.core.db.database import local_session


DEFAULT_THEMES = [
    {
        "id": str(uuid.uuid4()),
        "name": "Lily Classic",
        "description": "Giao diện mặc định với màu tím sang trọng",
        "screen_type": "240x240",
        "category": "default",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#6366f1",
                "secondary": "#8b5cf6",
                "background": "#0f172a",
                "text": "#f8fafc"
            },
            "widgets": {
                "clock": {"enabled": True, "format": "24h"},
                "weather": {"enabled": True},
                "calendar": {"enabled": False}
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Dark Mode",
        "description": "Giao diện tối với màu đen sang trọng",
        "screen_type": "240x240",
        "category": "dark",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#ffffff",
                "secondary": "#9ca3af",
                "background": "#000000",
                "text": "#ffffff"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Sakura Pink",
        "description": "Giao diện màu hồng dễ thương phong cách Nhật Bản",
        "screen_type": "240x240",
        "category": "cute",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#f472b6",
                "secondary": "#ec4899",
                "background": "#fce7f3",
                "text": "#831843"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Ocean Blue",
        "description": "Giao diện xanh biển mát mẻ",
        "screen_type": "240x240",
        "category": "default",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#0ea5e9",
                "secondary": "#06b6d4",
                "background": "#0c4a6e",
                "text": "#f0f9ff"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Forest Green",
        "description": "Giao diện xanh lá tự nhiên",
        "screen_type": "240x240",
        "category": "default",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#22c55e",
                "secondary": "#16a34a",
                "background": "#052e16",
                "text": "#f0fdf4"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Minimal White",
        "description": "Giao diện trắng tối giản tinh tế",
        "screen_type": "240x240",  
        "category": "minimal",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#18181b",
                "secondary": "#71717a",
                "background": "#ffffff",
                "text": "#09090b"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Anime Neon",
        "description": "Giao diện neon rực rỡ phong cách anime",
        "screen_type": "240x240",
        "category": "anime",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#f0abfc",
                "secondary": "#a855f7",
                "background": "#1e1b4b",
                "text": "#fdf4ff"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Sunset Orange",
        "description": "Giao diện cam ấm áp như hoàng hôn",
        "screen_type": "240x240",
        "category": "colorful",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#f97316",
                "secondary": "#ea580c",
                "background": "#431407",
                "text": "#fff7ed"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Winter Snow",
        "description": "Giao diện mùa đông trắng lạnh",
        "screen_type": "240x240",
        "category": "seasonal",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#38bdf8",
                "secondary": "#7dd3fc",
                "background": "#f0f9ff",
                "text": "#0c4a6e"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Autumn Leaves",
        "description": "Giao diện mùa thu ấm áp",
        "screen_type": "240x240",
        "category": "seasonal",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#d97706",
                "secondary": "#b45309",
                "background": "#451a03",
                "text": "#fef3c7"
            }
        }
    },
    # OSTB themes (284x240)
    {
        "id": str(uuid.uuid4()),
        "name": "OSTB Classic",
        "description": "Giao diện mặc định cho OSTB 284x240",
        "screen_type": "284x240",
        "category": "default",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#6366f1",
                "secondary": "#8b5cf6",
                "background": "#0f172a",
                "text": "#f8fafc"
            }
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "OSTB Dark",
        "description": "Giao diện tối cho OSTB 284x240",
        "screen_type": "284x240",
        "category": "dark",
        "is_system": True,
        "theme_data": {
            "colors": {
                "primary": "#ffffff",
                "secondary": "#9ca3af", 
                "background": "#000000",
                "text": "#ffffff"
            }
        }
    },
]


async def seed_themes():
    """Insert default themes into database"""
    from app.models.device_theme import DeviceTheme
    from sqlalchemy import select
    
    async with local_session() as db:
        # Check if themes already exist
        result = await db.execute(
            select(DeviceTheme).where(DeviceTheme.is_system == True).limit(1)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("System themes already exist, skipping seed")
            return
        
        # Insert themes
        for theme_data in DEFAULT_THEMES:
            theme = DeviceTheme(
                id=theme_data["id"],
                name=theme_data["name"],
                description=theme_data["description"],
                screen_type=theme_data["screen_type"],
                category=theme_data["category"],
                is_system=theme_data["is_system"],
                theme_data=theme_data["theme_data"],
                is_public=True,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(theme)
        
        await db.commit()
        print(f"✅ Seeded {len(DEFAULT_THEMES)} system themes")


if __name__ == "__main__":
    asyncio.run(seed_themes())

"""
Seed Marketplace with Skills, Themes, and Device Features.

Run inside Docker:
  docker compose exec -T backend python3 -m app.seeds.seed_marketplace
"""

import asyncio
import sys
import os

# Ensure app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import select, text
from app.core.db.database import local_session as async_session


SKILLS_DATA = [
    # ===================== SKILLS (from original marketplace) =====================
    {
        "name": "Phát nhạc YouTube",
        "slug": "phat-nhac-youtube",
        "description": "Phát nhạc online từ YouTube qua lệnh giọng nói. Hỗ trợ tìm kiếm bài hát, video, nghệ sĩ và phát trực tiếp trên thiết bị IoT.",
        "short_description": "Nghe nhạc YouTube",
        "skill_type": "plugin",
        "category": "entertainment",
        "tags": ["music", "streaming"],
        "config": {"source": "youtube"},
        "is_public": True,
        "is_featured": True,
        "is_premium": False,
        "price": 0,
        "rating": 4.6,
        "rating_count": 48,
        "install_count": 312,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Nhắc thuốc & Sức khoẻ",
        "slug": "nhac-thuoc-suc-khoe",
        "description": "Đặt lịch nhắc uống thuốc, theo dõi sức khoẻ hàng ngày. Tích hợp AI phân tích tình trạng và nhắc nhở tự động qua giọng nói.",
        "short_description": "Nhắc thuốc & theo dõi sức khoẻ",
        "skill_type": "plugin",
        "category": "health",
        "tags": ["health", "reminder"],
        "config": {},
        "is_public": True,
        "is_featured": True,
        "is_premium": False,
        "price": 0,
        "rating": 4.9,
        "rating_count": 35,
        "install_count": 234,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Tin tức & Thời tiết",
        "slug": "tin-tuc-thoi-tiet",
        "description": "Cập nhật tin tức mới nhất và dự báo thời tiết theo vị trí. Hỗ trợ đọc tin bằng giọng nói, tóm tắt nhanh tin nóng trong ngày.",
        "short_description": "Tin tức và thời tiết",
        "skill_type": "plugin",
        "category": "information",
        "tags": ["news", "weather"],
        "config": {},
        "is_public": True,
        "is_featured": False,
        "is_premium": False,
        "price": 0,
        "rating": 4.3,
        "rating_count": 28,
        "install_count": 198,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Intercom (Bộ đàm)",
        "slug": "intercom-bo-dam",
        "description": "Giao tiếp giữa các thiết bị Xiaozhi như bộ đàm. Hỗ trợ gọi 1-1, nhóm, và relay audio full-duplex AES-256 mã hoá.",
        "short_description": "Bộ đàm Xiaozhi",
        "skill_type": "plugin",
        "category": "communication",
        "tags": ["intercom", "voice"],
        "config": {},
        "is_public": True,
        "is_featured": True,
        "is_premium": False,
        "price": 0,
        "rating": 4.6,
        "rating_count": 22,
        "install_count": 167,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Điều khiển nhà thông minh",
        "slug": "dieu-khien-nha-thong-minh",
        "description": "Điều khiển đèn, quạt, điều hoà, cửa… bằng giọng nói. Tương thích Home Assistant, Tuya, và các thiết bị IoT phổ biến.",
        "short_description": "Điều khiển nhà thông minh",
        "skill_type": "mcp_server",
        "category": "home_automation",
        "tags": ["iot", "home"],
        "config": {},
        "is_public": True,
        "is_featured": True,
        "is_premium": False,
        "price": 0,
        "rating": 4.7,
        "rating_count": 41,
        "install_count": 156,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Gia sư AI",
        "slug": "gia-su-ai",
        "description": "Gia sư AI cá nhân qua giọng nói. Hỗ trợ học từ vựng, ngữ pháp tiếng Anh, luyện phát âm, flashcard SRS và theo dõi tiến độ.",
        "short_description": "Gia sư AI qua giọng nói",
        "skill_type": "plugin",
        "category": "education",
        "tags": ["education", "tutor"],
        "config": {},
        "is_public": True,
        "is_featured": True,
        "is_premium": True,
        "price": 99000,
        "rating": 4.8,
        "rating_count": 32,
        "install_count": 145,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Ghi chú cuộc họp",
        "slug": "ghi-chu-cuoc-hop",
        "description": "Tự động ghi âm, chuyển văn bản, nhận diện người nói và trích xuất task từ cuộc họp. Gửi báo cáo qua Telegram/Zalo.",
        "short_description": "Ghi chú cuộc họp AI",
        "skill_type": "plugin",
        "category": "productivity",
        "tags": ["meeting", "asr"],
        "config": {},
        "is_public": True,
        "is_featured": False,
        "is_premium": True,
        "price": 149000,
        "rating": 4.4,
        "rating_count": 18,
        "install_count": 89,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Trợ lý bán hàng AI",
        "slug": "tro-ly-ban-hang-ai",
        "description": "AI Sales Assistant thông minh. Tự động tư vấn sản phẩm, tra cứu kho, hiển thị sản phẩm trên màn LCD thiết bị và chốt đơn.",
        "short_description": "Trợ lý bán hàng AI",
        "skill_type": "plugin",
        "category": "productivity",
        "tags": ["sales", "retail"],
        "config": {},
        "is_public": True,
        "is_featured": True,
        "is_premium": True,
        "price": 199000,
        "rating": 4.5,
        "rating_count": 15,
        "install_count": 78,
        "icon_url": None,
        "banner_url": None,
    },

    # ===================== THEMES =====================
    {
        "name": "Theme Mặc Định",
        "slug": "theme-mac-dinh",
        "description": "Giao diện mặc định cho thiết bị Xiaozhi. Bao gồm 21 emoji cảm xúc cơ bản, màu xanh dương chủ đạo.",
        "short_description": "Theme gốc của Xiaozhi",
        "skill_type": "voice_pack",
        "category": "other",
        "tags": ["theme", "default", "free"],
        "config": {"type": "theme", "emoji_count": 21},
        "is_public": True,
        "is_featured": False,
        "is_premium": False,
        "price": 0,
        "rating": 4.2,
        "rating_count": 56,
        "install_count": 890,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Theme Doraemon",
        "slug": "theme-doraemon",
        "description": "Bộ emoji và giao diện Doraemon dễ thương cho thiết bị. 21 emoji phong cách hoạt hình Nhật Bản, phù hợp cho trẻ em.",
        "short_description": "🐱 Theme Doraemon dễ thương",
        "skill_type": "voice_pack",
        "category": "entertainment",
        "tags": ["theme", "doraemon", "cute"],
        "config": {"type": "theme", "emoji_count": 21},
        "is_public": True,
        "is_featured": True,
        "is_premium": True,
        "price": 49000,
        "rating": 4.8,
        "rating_count": 24,
        "install_count": 156,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Theme Robot Chibi",
        "slug": "theme-robot-chibi",
        "description": "Giao diện robot chibi siêu dễ thương. Emoji phong cách pixel art retro, phù hợp cho fan công nghệ.",
        "short_description": "🤖 Robot Chibi pixel art",
        "skill_type": "voice_pack",
        "category": "entertainment",
        "tags": ["theme", "robot", "pixel"],
        "config": {"type": "theme", "emoji_count": 21},
        "is_public": True,
        "is_featured": True,
        "is_premium": True,
        "price": 39000,
        "rating": 4.6,
        "rating_count": 19,
        "install_count": 98,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Theme Dark Mode OLED",
        "slug": "theme-dark-mode-oled",
        "description": "Giao diện tối cho màn hình OLED. Tiết kiệm pin, bảo vệ mắt, emoji neon rực rỡ trên nền đen.",
        "short_description": "🌙 Dark Mode cho OLED",
        "skill_type": "voice_pack",
        "category": "utilities",
        "tags": ["theme", "dark", "oled"],
        "config": {"type": "theme", "emoji_count": 21},
        "is_public": True,
        "is_featured": False,
        "is_premium": False,
        "price": 0,
        "rating": 4.5,
        "rating_count": 33,
        "install_count": 245,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Theme Tết Nguyên Đán",
        "slug": "theme-tet-nguyen-dan",
        "description": "Theme mừng Tết Nguyên Đán. Hoa mai, bánh chưng, lì xì, pháo hoa — emoji Tết đậm chất Việt Nam.",
        "short_description": "🧧 Theme Tết Việt Nam",
        "skill_type": "voice_pack",
        "category": "entertainment",
        "tags": ["theme", "tet", "vietnam", "holiday"],
        "config": {"type": "theme", "emoji_count": 21},
        "is_public": True,
        "is_featured": True,
        "is_premium": True,
        "price": 29000,
        "rating": 4.9,
        "rating_count": 42,
        "install_count": 310,
        "icon_url": None,
        "banner_url": None,
    },

    # ===================== DEVICE FEATURES (mua để active) =====================
    {
        "name": "Multi-Language (Đa ngôn ngữ)",
        "slug": "feature-multi-language",
        "description": "Mở khoá hỗ trợ đa ngôn ngữ cho thiết bị. AI có thể nói/nghe Tiếng Việt, Tiếng Anh, Tiếng Trung, Tiếng Nhật, Tiếng Hàn.",
        "short_description": "🌐 Hỗ trợ 5+ ngôn ngữ",
        "skill_type": "prompt_template",
        "category": "utilities",
        "tags": ["feature", "language", "premium"],
        "config": {"type": "device_feature", "feature_key": "multi_language"},
        "is_public": True,
        "is_featured": True,
        "is_premium": True,
        "price": 79000,
        "rating": 4.7,
        "rating_count": 28,
        "install_count": 134,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Bộ nhớ dài hạn (Long Memory)",
        "slug": "feature-long-memory",
        "description": "AI ghi nhớ mọi cuộc trò chuyện, sở thích, thói quen của bạn. Trả lời cá nhân hoá dựa trên lịch sử tương tác.",
        "short_description": "🧠 AI ghi nhớ vĩnh viễn",
        "skill_type": "prompt_template",
        "category": "productivity",
        "tags": ["feature", "memory", "premium"],
        "config": {"type": "device_feature", "feature_key": "long_memory"},
        "is_public": True,
        "is_featured": True,
        "is_premium": True,
        "price": 99000,
        "rating": 4.8,
        "rating_count": 35,
        "install_count": 189,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Nhận diện giọng nói (Voiceprint)",
        "slug": "feature-voiceprint",
        "description": "Thiết bị nhận diện ai đang nói dựa trên giọng nói. Tự động chuyển profile, cá nhân hoá phản hồi cho từng thành viên.",
        "short_description": "🎤 Nhận biết ai đang nói",
        "skill_type": "prompt_template",
        "category": "utilities",
        "tags": ["feature", "voiceprint", "premium"],
        "config": {"type": "device_feature", "feature_key": "voiceprint"},
        "is_public": True,
        "is_featured": False,
        "is_premium": True,
        "price": 129000,
        "rating": 4.5,
        "rating_count": 16,
        "install_count": 67,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Full Duplex Intercom (Đàm thoại song công)",
        "slug": "feature-full-duplex",
        "description": "Nâng cấp intercom lên Full Duplex — nói và nghe đồng thời, không cần chờ. Mã hoá AES-256 bảo mật tuyệt đối.",
        "short_description": "📞 Đàm thoại 2 chiều đồng thời",
        "skill_type": "prompt_template",
        "category": "communication",
        "tags": ["feature", "intercom", "duplex"],
        "config": {"type": "device_feature", "feature_key": "full_duplex_intercom"},
        "is_public": True,
        "is_featured": False,
        "is_premium": True,
        "price": 149000,
        "rating": 4.4,
        "rating_count": 12,
        "install_count": 43,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "Thông báo đa kênh (Multi-channel Notify)",
        "slug": "feature-multi-notify",
        "description": "Gửi thông báo qua Telegram, Zalo OA, Email đồng thời. Phân cấp cảnh báo Info → Warning → Critical → SOS.",
        "short_description": "📢 Telegram + Zalo + Email",
        "skill_type": "prompt_template",
        "category": "communication",
        "tags": ["feature", "notification", "multi-channel"],
        "config": {"type": "device_feature", "feature_key": "multi_channel_notify"},
        "is_public": True,
        "is_featured": False,
        "is_premium": True,
        "price": 69000,
        "rating": 4.3,
        "rating_count": 19,
        "install_count": 87,
        "icon_url": None,
        "banner_url": None,
    },
    {
        "name": "OTA tự động & Quản lý Firmware",
        "slug": "feature-ota-management",
        "description": "Cập nhật firmware thiết bị từ xa qua OTA. Quản lý phiên bản, rollback, và lên lịch update cho nhóm thiết bị.",
        "short_description": "⬆️ Cập nhật firmware từ xa",
        "skill_type": "prompt_template",
        "category": "utilities",
        "tags": ["feature", "ota", "firmware"],
        "config": {"type": "device_feature", "feature_key": "ota_management"},
        "is_public": True,
        "is_featured": False,
        "is_premium": False,
        "price": 0,
        "rating": 4.6,
        "rating_count": 39,
        "install_count": 445,
        "icon_url": None,
        "banner_url": None,
    },
]


async def seed_marketplace():
    """Insert seed marketplace skills if not already present."""
    from app.models.skill import Skill

    async with async_session() as session:
        # Get admin user ID for author_id
        result = await session.execute(text("SELECT id FROM \"user\" WHERE is_superuser = true LIMIT 1"))
        admin_id = result.scalar_one_or_none()
        if not admin_id:
            print("❌ No admin user found! Create a superuser first.")
            return
        print(f"👤 Using admin user: {admin_id}")

        # Check current count
        result = await session.execute(text("SELECT COUNT(*) FROM skills"))
        count = result.scalar()
        print(f"📊 Current skills count: {count}")

        inserted = 0
        skipped = 0

        for skill_data in SKILLS_DATA:
            # Check if slug already exists
            result = await session.execute(
                select(Skill).where(Skill.slug == skill_data["slug"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  ⏭️  Skip (exists): {skill_data['name']}")
                skipped += 1
                continue

            # Create ORM object
            skill = Skill(
                name=skill_data["name"],
                slug=skill_data["slug"],
                description=skill_data["description"],
                short_description=skill_data.get("short_description"),
                skill_type=skill_data.get("skill_type", "plugin"),
                category=skill_data.get("category", "utilities"),
                tags=skill_data.get("tags", []),
                config=skill_data.get("config", {}),
                author_id=str(admin_id),
                author_name="Xiaozhi Official",
                author_verified=True,
                version="1.0.0",
                icon_url=skill_data.get("icon_url"),
                banner_url=skill_data.get("banner_url"),
                is_public=skill_data.get("is_public", True),
                is_featured=skill_data.get("is_featured", False),
                is_premium=skill_data.get("is_premium", False),
                price=skill_data.get("price", 0),
                is_approved=True,
                is_verified=True,
            )
            # Set stats directly (they have init=False or default)
            skill.rating = skill_data.get("rating", 0.0)
            skill.rating_count = skill_data.get("rating_count", 0)
            skill.install_count = skill_data.get("install_count", 0)

            session.add(skill)
            price_str = f"💎 {skill_data['price']:,}đ" if skill_data.get('is_premium') else "🆓 Free"
            print(f"  ✅ Inserted: {skill_data['name']} ({skill_data['category']}) {price_str}")
            inserted += 1

        await session.commit()
        print(f"\n🎉 Done! Inserted: {inserted}, Skipped: {skipped}")
        print(f"📊 Total skills now: {count + inserted}")


if __name__ == "__main__":
    asyncio.run(seed_marketplace())

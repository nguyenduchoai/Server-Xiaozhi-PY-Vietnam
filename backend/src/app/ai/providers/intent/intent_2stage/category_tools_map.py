"""
Category → Tools Mapping for 2-Stage Intent Detection

This module defines the intent categories and their associated tools.
Stage 1 classifies the user's intent into one of these categories.
Stage 2 only loads tools from the detected category.
"""

from typing import Dict, List, Optional

# Intent categories with metadata
INTENT_CATEGORIES: Dict[str, Dict] = {
    # ============================================
    # FAST-PATH CATEGORIES (Skip Stage 2)
    # ============================================
    "greeting": {
        "description": "Chào hỏi, xin chào",
        "keywords": ["xin chào", "hello", "hi", "chào", "alo", "hey", "chào bạn"],
        "action": "continue_chat",
        "skip_stage2": True,
        "tools": []
    },
    "goodbye": {
        "description": "Tạm biệt, kết thúc trò chuyện",
        "keywords": ["tạm biệt", "bye", "goodbye", "thoát", "kết thúc", "không nói nữa", 
                     "đi ngủ", "chào nhé", "gặp lại sau"],
        "action": "handle_exit_intent",
        "skip_stage2": True,
        "tools": ["handle_exit_intent"]
    },
    "context_query": {
        "description": "Hỏi thông tin cơ bản từ ngữ cảnh",
        "keywords": ["mấy giờ", "thứ mấy", "ngày bao nhiêu", "âm lịch", "hôm nay là", 
                     "bây giờ là", "hiện tại", "thời gian"],
        "action": "result_for_context",
        "skip_stage2": True,
        "tools": []
    },
    "general_chat": {
        "description": "Hội thoại thông thường, fallback",
        "keywords": [],  # Fallback category
        "action": "continue_chat",
        "skip_stage2": True,
        "tools": []
    },
    
    # ============================================
    # STANDARD CATEGORIES (Stage 2 Required)
    # ============================================
    "music": {
        "description": "Nghe nhạc, tìm bài hát, điều khiển nhạc",
        "keywords": ["nhạc", "bài hát", "phát", "nghe", "mở nhạc", "tìm nhạc", "bật nhạc",
                     "hát", "ca sĩ", "album", "playlist", "youtube",
                     "bài số", "bài tiếp", "bài trước", "dừng nhạc", "tắt nhạc", "radio"],
        "skip_stage2": False,
        "tools": [
            "stop_music",
            "search_youtube", "play_youtube", "play_music",
            "self_music_play_song", "self_music_stop", "self_music_next",
            "self_music_previous", "self_radio_play", "self_radio_stop"
        ]
    },
    "weather": {
        "description": "Thời tiết, nhiệt độ, dự báo",
        "keywords": ["thời tiết", "trời", "nhiệt độ", "mưa", "nắng", "độ ẩm", "gió",
                     "dự báo", "weather", "trời hôm nay", "nóng", "lạnh"],
        "skip_stage2": False,
        "tools": ["get_weather", "get_weather_openmeteo"]
    },
    "news": {
        "description": "Tin tức, tin mới",
        "keywords": ["tin tức", "tin mới", "đọc tin", "tin gì", "news", "báo",
                     "thời sự", "thể thao", "kinh tế", "giải trí"],
        "skip_stage2": False,
        "tools": ["get_news_by_topic", "get_news_detail"]
    },
    "reminder": {
        "description": "Nhắc nhở, đặt hẹn, báo thức",
        "keywords": ["nhắc nhở", "nhắc tôi", "đặt hẹn", "báo thức", "reminder",
                     "nhắc lúc", "nhắc sau", "hẹn giờ", "phút nữa", "tiếng nữa",
                     "lịch nhắc", "xóa nhắc", "danh sách nhắc"],
        "skip_stage2": False,
        "tools": [
            "create_reminder", "get_list_reminder", 
            "delete_reminder", "update_status_reminder"
        ]
    },
    "device_control": {
        "description": "Điều khiển thiết bị (âm lượng, độ sáng, pin...)",
        "keywords": ["âm lượng", "volume", "độ sáng", "brightness", "tắt màn", "bật màn",
                     "pin", "battery", "đèn", "lamp", "sáng lên", "tối đi",
                     "to lên", "nhỏ lại", "mute", "tắt tiếng"],
        "skip_stage2": False,
        "tools": [
            "self_audio_speaker_set_volume", "self_audio_speaker_get_volume",
            "self_screen_set_brightness", "self_screen_get_brightness",
            "self_get_device_status", "self_lamp_turn_on", "self_lamp_turn_off",
            "self_lamp_get_state", "get_battery_level"
        ]
    },
    "home_assistant": {
        "description": "Điều khiển nhà thông minh",
        "keywords": ["nhà thông minh", "điều hòa", "quạt", "đèn phòng", "home assistant",
                     "smart home", "curtain", "rèm", "tv", "máy lạnh"],
        "skip_stage2": False,
        "tools": ["hass_get_state", "hass_set_state", "hass_play_music"]
    },
    "knowledge": {
        "description": "Tra cứu kiến thức, RAG, tìm tài liệu",
        "keywords": ["kiến thức", "tìm kiếm", "tra cứu", "knowledge base",
                     "tài liệu", "document", "hỏi về", "tìm hiểu"],
        "skip_stage2": False,
        "tools": ["search_knowledge_base", "add_knowledge", "search_from_ragflow"]
    },
    "education": {
        "description": "Học ngoại ngữ, bài học, từ vựng, flashcard",
        "keywords": [
            # Learning keywords
            "học tiếng anh", "học tiếng", "bài học", "từ vựng", "vocabulary", "flashcard",
            "ôn tập", "kiểm tra", "quiz", "test", "dạy tôi", "học english",
            "luyện nói", "luyện nghe", "học hội thoại", "tiến độ học",
            "bắt đầu học", "start lesson", "review", "ôn bài",
            # Course listing keywords (for get_my_courses)
            "khóa học nào", "course nào", "bạn dạy gì", "có khóa học gì",
            "danh sách khóa học", "list course", "học được gì", "dạy được gì"
        ],
        "skip_stage2": False,
        "tools": [
            "start_lesson", "take_quiz", "review_flashcards",
            "get_learning_stats", "quick_vocabulary", "get_my_courses"
        ]
    },
    "agent": {
        "description": "Quản lý agent, chuyển agent",
        "keywords": ["chuyển agent", "đổi agent", "danh sách agent", "agent nào",
                     "thay đổi trợ lý", "list agent"],
        "skip_stage2": False,
        "tools": ["get_list_agent", "change_agent"]
    },
    "economic": {
        "description": "Lịch kinh tế, tài chính",
        "keywords": ["lịch kinh tế", "economic calendar", "forex", "chứng khoán",
                     "tỷ giá", "gold", "vàng"],
        "skip_stage2": False,
        "tools": ["get_economic_calendar"]
    }
}

# Category names for prompt
CATEGORY_NAMES: List[str] = list(INTENT_CATEGORIES.keys())


def get_category_tools(category: str) -> List[str]:
    """Get tools for a specific category."""
    cat_info = INTENT_CATEGORIES.get(category, INTENT_CATEGORIES["general_chat"])
    return cat_info.get("tools", [])


def is_fast_path_category(category: str) -> bool:
    """Check if category can skip Stage 2."""
    cat_info = INTENT_CATEGORIES.get(category, {})
    return cat_info.get("skip_stage2", False)


def get_fast_path_action(category: str) -> Optional[str]:
    """Get the action for fast-path categories."""
    cat_info = INTENT_CATEGORIES.get(category, {})
    if cat_info.get("skip_stage2", False):
        return cat_info.get("action", "continue_chat")
    return None


def get_category_description() -> str:
    """Generate category descriptions for Stage 1 prompt."""
    lines = []
    for name, info in INTENT_CATEGORIES.items():
        if name == "general_chat":
            continue  # Fallback, don't list in prompt
        desc = info.get("description", name)
        keywords = info.get("keywords", [])
        keyword_str = ", ".join(keywords[:3]) if keywords else ""
        lines.append(f"- {name}: {desc} ({keyword_str})")
    return "\n".join(lines)


def keyword_match_category(text: str) -> Optional[str]:
    """Fast keyword-based category detection (pre-LLM optimization)."""
    text_lower = text.lower().strip()
    
    # Check each category's keywords
    for cat_name, cat_info in INTENT_CATEGORIES.items():
        if cat_name == "general_chat":
            continue
        keywords = cat_info.get("keywords", [])
        for kw in keywords:
            if kw in text_lower:
                return cat_name
    
    return None  # No keyword match, need LLM

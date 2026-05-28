"""
Tool Schema Registry - Định nghĩa metadata và config schema cho mỗi tool.

Registry này cho phép:
1. UI render dynamic forms từ schema
2. Validation tự động config từ schema
3. Single source of truth cho tool metadata

Sử dụng:
    from app.ai.providers.tools.tool_schema_registry import (
        get_tool_schema,
        get_all_tool_schemas,
        ToolCategory,
    )

    # Lấy schema của một tool
    schema = get_tool_schema("get_weather")

    # Lấy tất cả schemas
    all_schemas = get_all_tool_schemas()
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolFieldType(Enum):
    """Các loại field config cho tool."""

    STRING = "string"
    SECRET = "secret"  # Masked trong response (API keys, passwords)
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"  # Dropdown với options
    ARRAY = "array"  # List of items
    PATH = "path"  # File/directory path
    URL = "url"  # URL string


class ToolCategory(Enum):
    """Phân loại tools theo chức năng."""

    WEATHER = "weather"
    MUSIC = "music"
    REMINDER = "reminder"
    NEWS = "news"
    AGENT = "agent"
    IOT = "iot"
    CALENDAR = "calendar"
    KNOWLEDGE = "knowledge"
    OTHER = "other"


@dataclass
class ToolFieldSchema:
    """Schema cho một field config của tool."""

    name: str
    display_name: str
    field_type: ToolFieldType
    description: str = ""
    required: bool = False
    default: Any = None
    options: list[str] | None = None  # Cho SELECT type
    validation: dict[str, Any] | None = None  # min, max, pattern, etc.


@dataclass
class ToolSchema:
    """Schema đầy đủ cho một tool."""

    name: str  # Key trong all_function_registry
    display_name: str
    description: str
    category: ToolCategory
    requires_config: bool = True  # Tool có cần config không
    fields: list[ToolFieldSchema] = field(default_factory=list)
    function_schema: dict[str, Any] | None = None  # OpenAI function schema

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API response."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "requires_config": self.requires_config,
            "fields": [
                {
                    "name": f.name,
                    "display_name": f.display_name,
                    "field_type": f.field_type.value,
                    "description": f.description,
                    "required": f.required,
                    "default": f.default,
                    "options": f.options,
                    "validation": f.validation,
                }
                for f in self.fields
            ],
            "function_schema": self.function_schema,
        }


# =============================================================================
# TOOL SCHEMAS REGISTRY
# =============================================================================

TOOL_SCHEMAS: dict[str, ToolSchema] = {}


def register_tool_schema(schema: ToolSchema) -> ToolSchema:
    """Đăng ký tool schema vào registry."""
    TOOL_SCHEMAS[schema.name] = schema
    return schema


def get_tool_schema(tool_name: str) -> ToolSchema | None:
    """Lấy schema của một tool theo name."""
    return TOOL_SCHEMAS.get(tool_name)


def get_all_tool_schemas() -> dict[str, ToolSchema]:
    """Lấy tất cả tool schemas."""
    return TOOL_SCHEMAS.copy()


def get_tool_schemas_by_category(category: ToolCategory) -> list[ToolSchema]:
    """Lấy danh sách schemas theo category."""
    return [s for s in TOOL_SCHEMAS.values() if s.category == category]


def get_all_categories() -> list[str]:
    """Lấy danh sách tất cả categories có tool."""
    categories = set(s.category.value for s in TOOL_SCHEMAS.values())
    return sorted(categories)


def validate_tool_config(
    tool_name: str, config: dict[str, Any]
) -> tuple[bool, dict[str, Any], list[str]]:
    """
    Validate tool config against schema.
    
    Args:
        tool_name: Name of the tool
        config: Config dict to validate
        
    Returns:
        Tuple of (is_valid, normalized_config, errors)
    """
    schema = get_tool_schema(tool_name)
    if not schema:
        return False, config, [f"Tool '{tool_name}' not found in registry"]
    
    errors: list[str] = []
    normalized = dict(config)
    
    # Check required fields
    for field in schema.fields:
        if field.required and field.name not in config:
            if field.default is not None:
                normalized[field.name] = field.default
            else:
                errors.append(f"Missing required field: {field.display_name}")
        
        # Type validation
        if field.name in config:
            value = config[field.name]
            
            if field.field_type == ToolFieldType.STRING:
                if not isinstance(value, str):
                    errors.append(f"{field.display_name} must be a string")
            
            elif field.field_type == ToolFieldType.SECRET:
                if not isinstance(value, str):
                    errors.append(f"{field.display_name} must be a string")
            
            elif field.field_type == ToolFieldType.NUMBER:
                if not isinstance(value, (int, float)):
                    errors.append(f"{field.display_name} must be a number")
                # Check min/max
                if field.validation:
                    if "min" in field.validation and value < field.validation["min"]:
                        errors.append(f"{field.display_name} must be >= {field.validation['min']}")
                    if "max" in field.validation and value > field.validation["max"]:
                        errors.append(f"{field.display_name} must be <= {field.validation['max']}")
            
            elif field.field_type == ToolFieldType.BOOLEAN:
                if not isinstance(value, bool):
                    errors.append(f"{field.display_name} must be a boolean")
            
            elif field.field_type == ToolFieldType.SELECT:
                if field.options and value not in field.options:
                    errors.append(f"{field.display_name} must be one of: {', '.join(field.options)}")
            
            elif field.field_type == ToolFieldType.ARRAY:
                if not isinstance(value, list):
                    errors.append(f"{field.display_name} must be an array")
            
            elif field.field_type == ToolFieldType.URL:
                if not isinstance(value, str) or not (value.startswith("http://") or value.startswith("https://")):
                    errors.append(f"{field.display_name} must be a valid URL")
    
    return len(errors) == 0, normalized, errors


# =============================================================================
# REGISTER SCHEMAS FOR EXISTING TOOLS
# =============================================================================

# Weather Tool
register_tool_schema(
    ToolSchema(
        name="get_weather",
        display_name="Thời tiết",
        description="Lấy thông tin thời tiết theo địa điểm",
        category=ToolCategory.WEATHER,
        requires_config=True,
        fields=[
            ToolFieldSchema(
                name="api_host",
                display_name="API Host",
                field_type=ToolFieldType.STRING,
                description="Host của Weather API",
                required=False,
                default="mj7p3y7naa.re.qweatherapi.com",
            ),
            ToolFieldSchema(
                name="api_key",
                display_name="API Key",
                field_type=ToolFieldType.SECRET,
                description="API key cho dịch vụ thời tiết",
                required=True,
            ),
            ToolFieldSchema(
                name="default_location",
                display_name="Địa điểm mặc định",
                field_type=ToolFieldType.STRING,
                description="Địa điểm mặc định khi không chỉ định",
                required=True,
                default="Hanoi",
            ),
        ],
    )
)

# Weather Tool using Open-Meteo (FREE, no API key required)
register_tool_schema(
    ToolSchema(
        name="get_weather_openmeteo",
        display_name="Thời tiết (Open-Meteo)",
        description="Lấy thông tin thời tiết miễn phí từ Open-Meteo API - không cần API key",
        category=ToolCategory.WEATHER,
        requires_config=False,  # No config needed!
        function_schema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Tên thành phố, ví dụ 'Hanoi', 'Ho Chi Minh City', 'Tokyo'",
                },
            },
            "required": ["location"],
        },
    )
)

# Play Music Tool
register_tool_schema(
    ToolSchema(
        name="play_music",
        display_name="Phát nhạc",
        description="Phát file nhạc từ thư mục local",
        category=ToolCategory.MUSIC,
        requires_config=True,
        fields=[
            ToolFieldSchema(
                name="music_dir",
                display_name="Thư mục nhạc",
                field_type=ToolFieldType.PATH,
                description="Đường dẫn thư mục chứa file nhạc (để trống = mặc định)",
                required=False,
                default="",
            ),
            ToolFieldSchema(
                name="music_ext",
                display_name="Định dạng file",
                field_type=ToolFieldType.ARRAY,
                description="Các định dạng file nhạc được hỗ trợ",
                required=False,
                default=[".mp3", ".wav", ".p3"],
            ),
            ToolFieldSchema(
                name="refresh_time",
                display_name="Thời gian refresh (giây)",
                field_type=ToolFieldType.NUMBER,
                description="Thời gian làm mới danh sách nhạc",
                required=False,
                default=300,
                validation={"min": 60, "max": 3600},
            ),
        ],
    )
)

# Economic Calendar Tool
register_tool_schema(
    ToolSchema(
        name="get_economic_calendar",
        display_name="Lịch kinh tế",
        description="Lấy sự kiện kinh tế quan trọng trong tuần",
        category=ToolCategory.CALENDAR,
        requires_config=True,
        fields=[
            ToolFieldSchema(
                name="api_timezone",
                display_name="Múi giờ API",
                field_type=ToolFieldType.STRING,
                description="Múi giờ của dữ liệu API",
                required=False,
                default="Asia/Ho_Chi_Minh",
            ),
            ToolFieldSchema(
                name="api_url",
                display_name="API URL",
                field_type=ToolFieldType.URL,
                description="URL endpoint của API lịch kinh tế",
                required=False,
                default="https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            ),
        ],
    )
)

# News Tools
register_tool_schema(
    ToolSchema(
        name="get_news_by_topic",
        display_name="Tin tức theo chủ đề",
        description="Lấy danh sách tin tức theo chủ đề từ nguồn tin",
        category=ToolCategory.NEWS,
        requires_config=True,
        fields=[
            ToolFieldSchema(
                name="default_source",
                display_name="Nguồn tin mặc định",
                field_type=ToolFieldType.SELECT,
                description="Nguồn tin tức mặc định",
                required=False,
                default="vnexpress",
                options=["vnexpress"],
            ),
            ToolFieldSchema(
                name="max_articles",
                display_name="Số bài tối đa",
                field_type=ToolFieldType.NUMBER,
                description="Số lượng bài viết tối đa lấy về",
                required=False,
                default=10,
                validation={"min": 1, "max": 50},
            ),
            ToolFieldSchema(
                name="timeout",
                display_name="Timeout (giây)",
                field_type=ToolFieldType.NUMBER,
                description="Thời gian chờ tối đa cho request",
                required=False,
                default=10,
                validation={"min": 5, "max": 60},
            ),
        ],
    )
)

register_tool_schema(
    ToolSchema(
        name="get_news_detail",
        display_name="Chi tiết tin tức",
        description="Lấy nội dung chi tiết của một bài viết từ URL",
        category=ToolCategory.NEWS,
        requires_config=True,
        fields=[
            ToolFieldSchema(
                name="max_content_length",
                display_name="Độ dài nội dung tối đa",
                field_type=ToolFieldType.NUMBER,
                description="Số ký tự tối đa của nội dung",
                required=False,
                default=4000,
                validation={"min": 500, "max": 10000},
            ),
        ],
    )
)

# Reminder Tools (không cần config)
register_tool_schema(
    ToolSchema(
        name="create_reminder",
        display_name="Tạo lời nhắc",
        description="Tạo một lời nhắc cho người dùng tại thời điểm chỉ định",
        category=ToolCategory.REMINDER,
        requires_config=False,
    )
)

register_tool_schema(
    ToolSchema(
        name="get_list_reminder",
        display_name="Danh sách lời nhắc",
        description="Lấy danh sách lời nhắc của thiết bị",
        category=ToolCategory.REMINDER,
        requires_config=False,
    )
)

register_tool_schema(
    ToolSchema(
        name="delete_reminder",
        display_name="Xóa lời nhắc",
        description="Xóa một hoặc nhiều lời nhắc",
        category=ToolCategory.REMINDER,
        requires_config=False,
    )
)

register_tool_schema(
    ToolSchema(
        name="update_status_reminder",
        display_name="Cập nhật trạng thái lời nhắc",
        description="Cập nhật trạng thái của một lời nhắc",
        category=ToolCategory.REMINDER,
        requires_config=False,
    )
)

# Music Tools (Additional)
register_tool_schema(
    ToolSchema(
        name="stop_music",
        display_name="Dừng nhạc",
        description="Dừng phát nhạc hoặc video đang chạy",
        category=ToolCategory.MUSIC,
        requires_config=False,
    )
)

register_tool_schema(
    ToolSchema(
        name="search_from_ragflow",
        display_name="Tìm kiếm RAGFlow",
        description="Tìm kiếm thông tin từ cơ sở tri thức RAGFlow",
        category=ToolCategory.KNOWLEDGE,
        requires_config=False,
        function_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi hoặc từ khóa tìm kiếm",
                },
            },
            "required": ["query"],
        },
    )
)

# Home Assistant Tools
register_tool_schema(
    ToolSchema(
        name="hass_play_music",
        display_name="Phát nhạc HASS",
        description="Phát nhạc thông qua thực thể Media Player của Home Assistant",
        category=ToolCategory.IOT,
        requires_config=False,
        function_schema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID của media player trong HASS",
                },
                "media_content_id": {
                    "type": "string",
                    "description": "URL hoặc ID nội dung cần phát",
                },
            },
            "required": ["entity_id", "media_content_id"],
        },
    )
)

register_tool_schema(
    ToolSchema(
        name="hass_get_state",
        display_name="Trạng thái HASS",
        description="Lấy trạng thái của một thực thể trong Home Assistant",
        category=ToolCategory.IOT,
        requires_config=False,
        function_schema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID của thực thể (ví dụ: light.living_room)",
                },
            },
            "required": ["entity_id"],
        },
    )
)

register_tool_schema(
    ToolSchema(
        name="hass_set_state",
        display_name="Điều khiển HASS",
        description="Điều khiển thực thể trong Home Assistant (bật/tắt/đổi màu...)",
        category=ToolCategory.IOT,
        requires_config=False,
        function_schema={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID của thực thể",
                },
                "state": {
                    "type": "string",
                    "description": "Trạng thái mới hoặc lệnh (on, off, toggle)",
                },
                "attributes": {
                    "type": "object",
                    "description": "Các thuộc tính bổ sung (ví dụ: brightness)",
                },
            },
            "required": ["entity_id", "state"],
        },
    )
)

# Agent Tools (không cần config)
register_tool_schema(
    ToolSchema(
        name="get_list_agent",
        display_name="Danh sách vai trò",
        description="Lấy danh sách các vai trò/agent có thể chuyển đổi",
        category=ToolCategory.AGENT,
        requires_config=False,
    )
)

register_tool_schema(
    ToolSchema(
        name="change_agent",
        display_name="Đổi vai trò",
        description="Chuyển đổi sang vai trò/agent khác",
        category=ToolCategory.AGENT,
        requires_config=False,
    )
)

# Knowledge Base Tool
register_tool_schema(
    ToolSchema(
        name="search_knowledge_base",
        display_name="Tìm kiếm cơ sở tri thức",
        description="Tìm kiếm thông tin trong cơ sở tri thức của agent. "
        "Sử dụng khi cần tra cứu thông tin đã lưu trước đó như: "
        "tài liệu, ghi chú, kiến thức cá nhân, sự kiện, quy trình.",
        category=ToolCategory.KNOWLEDGE,
        requires_config=False,
        function_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi hoặc từ khóa cần tìm kiếm",
                },
                "k": {
                    "type": "integer",
                    "description": "Số lượng kết quả trả về (1-10)",
                    "default": 5,
                },
                "sector": {
                    "type": "string",
                    "description": "Lọc theo loại tri thức: episodic (sự kiện), semantic (kiến thức), "
                    "procedural (quy trình), emotional (cảm xúc), reflective (suy nghĩ)",
                    "enum": [
                        "episodic",
                        "semantic",
                        "procedural",
                        "emotional",
                        "reflective",
                    ],
                },
            },
            "required": ["query"],
        },
    )
)

# Add Knowledge Tool
register_tool_schema(
    ToolSchema(
        name="add_knowledge",
        display_name="Thêm tri thức",
        description="Thêm thông tin mới vào cơ sở tri thức của agent. "
        "Sử dụng khi người dùng yêu cầu ghi nhớ, lưu trữ hoặc thêm thông tin mới.",
        category=ToolCategory.KNOWLEDGE,
        requires_config=False,
        function_schema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Nội dung cần lưu vào cơ sở tri thức",
                },
                "sector": {
                    "type": "string",
                    "description": "Loại tri thức: episodic (sự kiện), semantic (kiến thức), "
                    "procedural (quy trình), emotional (cảm xúc), reflective (suy nghĩ)",
                    "enum": [
                        "episodic",
                        "semantic",
                        "procedural",
                        "emotional",
                        "reflective",
                    ],
                    "default": "semantic",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Các thẻ tag để phân loại",
                },
                "salience": {
                    "type": "number",
                    "description": "Mức độ quan trọng (0.0-1.0)",
                    "default": 0.5,
                },
            },
            "required": ["content"],
        },
    )
)

# YouTube Search Tool (không cần config)
register_tool_schema(
    ToolSchema(
        name="search_youtube",
        display_name="Tìm kiếm YouTube",
        description="Tìm kiếm video trên YouTube. Trả về danh sách video với tên, tác giả, thời lượng.",
        category=ToolCategory.MUSIC,
        requires_config=False,
        function_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa tìm kiếm (tên bài hát, nghệ sĩ, hoặc nội dung)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Số lượng kết quả tối đa (mặc định: 5, tối đa: 10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    )
)

# YouTube Play Tool (không cần config)
register_tool_schema(
    ToolSchema(
        name="play_youtube",
        display_name="Phát YouTube",
        description="Phát audio từ video YouTube. Sử dụng sau khi tìm kiếm với search_youtube.",
        category=ToolCategory.MUSIC,
        requires_config=False,
        function_schema={
            "type": "object",
            "properties": {
                "video_id": {
                    "type": "string",
                    "description": "Video ID của YouTube (từ kết quả search_youtube)",
                },
                "title": {
                    "type": "string",
                    "description": "Tên video để hiển thị (optional)",
                    "default": "",
                },
            },
            "required": ["video_id"],
        },
    )
)

# ZingMP3 Search and Play tools removed for copyright safety

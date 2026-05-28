"""
Prompt templates for 2-Stage Intent Detection.

Stage 1: Lightweight category classification (~200 tokens)
Stage 2: Category-specific function call detection (~500 tokens)
"""

from typing import List, Dict

# ==============================================
# STAGE 1: CATEGORY CLASSIFIER PROMPT
# ==============================================
# This prompt is designed to be as short as possible
# to minimize latency while maintaining accuracy.

CATEGORY_CLASSIFIER_SYSTEM_PROMPT = """Phân loại ý định người dùng vào 1 category duy nhất.

Categories:
- greeting: chào hỏi (xin chào, hi, alo)
- goodbye: tạm biệt, kết thúc (bye, thoát)
- context_query: hỏi thời gian, ngày tháng, âm lịch
- music: nghe nhạc, tìm bài, phát nhạc
- weather: thời tiết, nhiệt độ
- news: tin tức, đọc tin
- reminder: nhắc nhở, hẹn giờ
- device_control: âm lượng, độ sáng, pin, đèn
- home_assistant: điều khiển nhà thông minh
- knowledge: tra cứu kiến thức
- agent: quản lý/chuyển agent
- economic: lịch kinh tế, tài chính
- general_chat: hội thoại thông thường

CHỈ TRẢ VỀ TÊN CATEGORY, không giải thích."""

CATEGORY_CLASSIFIER_USER_TEMPLATE = """User: {text}
Category:"""


# ==============================================
# STAGE 2: FUNCTION CALL PROMPT
# ==============================================
# This prompt includes only category-specific tools

FUNCTION_CALL_SYSTEM_TEMPLATE = """Bạn là trợ lý nhận diện ý định. Phân tích câu của người dùng và chọn hàm phù hợp.

【QUAN TRỌNG】Chỉ trả về JSON, không thêm văn bản khác!

Các hàm có thể dùng:
{tools_description}

Yêu cầu output:
1. Phải là JSON thuần túy
2. Format: {{"function_call": {{"name": "function_name", "arguments": {{...}}}}}}
3. Nếu không cần gọi hàm: {{"function_call": {{"name": "continue_chat"}}}}

【QUY TẮC ĐẶC BIỆT】
- Với câu hỏi kiến thức/học tập/tra cứu tài liệu: LUÔN gọi search_knowledge_base trước
- Với yêu cầu "tóm tắt", "tìm hiểu", "giải thích": LUÔN gọi search_knowledge_base"""

FUNCTION_CALL_USER_TEMPLATE = """User: {text}
Response:"""


# ==============================================
# FAST-PATH RESPONSES
# ==============================================
# Pre-built responses for categories that skip Stage 2

FAST_PATH_RESPONSES = {
    "greeting": '{"function_call": {"name": "continue_chat"}}',
    "goodbye": '{"function_call": {"name": "handle_exit_intent", "arguments": {"say_goodbye": "goodbye"}}}',
    "context_query": '{"function_call": {"name": "result_for_context"}}',
    "general_chat": '{"function_call": {"name": "continue_chat"}}'
}


def format_tools_for_prompt(tools: List[Dict]) -> str:
    """
    Format tools into a concise description for Stage 2 prompt.
    
    Args:
        tools: List of tool definitions in OpenAI function format
        
    Returns:
        Formatted string describing available tools
    """
    if not tools:
        return "Không có hàm nào - trả về continue_chat"
    
    lines = []
    for tool in tools:
        func_info = tool.get("function", {})
        name = func_info.get("name", "")
        desc = func_info.get("description", "")
        params = func_info.get("parameters", {})
        
        # Only show first 80 chars of description
        short_desc = desc[:80] + "..." if len(desc) > 80 else desc
        
        param_list = []
        for param_name, param_info in params.get("properties", {}).items():
            param_type = param_info.get("type", "string")
            param_list.append(f"{param_name}:{param_type}")
        
        params_str = ", ".join(param_list) if param_list else "none"
        lines.append(f"• {name}({params_str}): {short_desc}")
    
    return "\n".join(lines)


def build_category_prompt(text: str) -> tuple:
    """
    Build Stage 1 category classification prompt.
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    return (
        CATEGORY_CLASSIFIER_SYSTEM_PROMPT,
        CATEGORY_CLASSIFIER_USER_TEMPLATE.format(text=text)
    )


def build_function_call_prompt(text: str, tools: List[Dict]) -> tuple:
    """
    Build Stage 2 function call detection prompt.
    
    Args:
        text: User input
        tools: Category-specific tools
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    tools_desc = format_tools_for_prompt(tools)
    
    system_prompt = FUNCTION_CALL_SYSTEM_TEMPLATE.format(
        tools_description=tools_desc
    )
    user_prompt = FUNCTION_CALL_USER_TEMPLATE.format(text=text)
    
    return (system_prompt, user_prompt)


def get_fast_path_response(category: str) -> str:
    """Get pre-built response for fast-path categories."""
    return FAST_PATH_RESPONSES.get(category, FAST_PATH_RESPONSES["general_chat"])

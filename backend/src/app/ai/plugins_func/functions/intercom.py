"""
Intercom MCP Tools - Voice relay between devices.

Provides AI-callable functions for walkie-talkie functionality.

Created: 2026-02-03
Feature: Walkie-Talkie / Intercom

Tools:
- intercom_send: Send voice message to another device
- intercom_reply: Reply to an intercom message (internal)
"""

from app.ai.plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)
from app.core.logger import setup_logging

TAG = __name__
logger = setup_logging()


# ========================
# Tool: intercom.send
# ========================

intercom_send_function_desc = {
    "type": "function",
    "function": {
        "name": "intercom_send",
        "description": """Gửi tin nhắn giọng nói đến thiết bị khác trong cùng tài khoản.
        
Sử dụng khi người dùng muốn:
- Gọi điện/nhắn tin đến phòng khác
- Thông báo cho người ở thiết bị khác
- Liên lạc kiểu bộ đàm

Ví dụ:
- "Gọi phòng ngủ - con ơi ăn cơm đi" → intercom_send("phòng ngủ", "con ơi ăn cơm đi")
- "Nhắn phòng làm việc là có khách" → intercom_send("phòng làm việc", "có khách tới")
- "Gọi bếp nói chuẩn bị xong chưa" → intercom_send("bếp", "chuẩn bị xong chưa")
""",
        "parameters": {
            "type": "object",
            "properties": {
                "target_device": {
                    "type": "string",
                    "description": "Tên thiết bị đích (ví dụ: 'phòng ngủ', 'phòng khách', 'bếp')"
                },
                "message": {
                    "type": "string",
                    "description": "Nội dung tin nhắn cần gửi"
                }
            },
            "required": ["target_device", "message"]
        }
    }
}


@register_function(
    "intercom_send", intercom_send_function_desc, ToolType.SYSTEM_CTL
)
async def intercom_send(conn, target_device: str, message: str) -> ActionResponse:
    """
    Send voice message to another device.
    
    Args:
        conn: Connection handler with device context
        target_device: Target device name (e.g., "phòng ngủ")
        message: Message content to send
        
    Returns:
        Result message for TTS
    """
    from app.services.intercom_service import get_intercom_service
    
    logger.bind(tag=TAG).info(
        f"[Intercom Tool] Send to '{target_device}': {message[:50]}..."
    )
    
    try:
        # Get device info from connection
        device_id = getattr(conn, 'device_id', None)
        device_name = getattr(conn, 'device_name', None) or "thiết bị của bạn"
        mac_address = getattr(conn, 'mac_address', None) or ""
        user_id = getattr(conn, 'user_id', None)
        
        if not device_id or not user_id:
            logger.bind(tag=TAG).warning("[Intercom Tool] Missing device/user context")
            return "Không thể gửi tin nhắn: thiếu thông tin thiết bị"
        
        # Get intercom service
        service = get_intercom_service()
        
        # Send intercom message
        result = await service.send_intercom(
            from_device_id=str(device_id),
            from_device_name=device_name,
            from_mac=mac_address,
            target_device_name=target_device,
            message=message,
            user_id=str(user_id),
        )
        
        if result.success:
            return ActionResponse(
                action=Action.REQLLM,
                result=f"Đã gửi tin nhắn đến {result.target_device_name}: {message}",
                response=None,
            )
        else:
            return ActionResponse(
                action=Action.RESPONSE,
                result=result.error,
                response=f"Không thể gửi tin nhắn: {result.error}",
            )
            
    except Exception as e:
        logger.bind(tag=TAG).exception(f"[Intercom Tool] Error: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result=str(e),
            response=f"Lỗi gửi tin nhắn: {str(e)}",
        )


# ========================
# Tool: intercom.reply (Internal)
# ========================

intercom_reply_function_desc = {
    "type": "function",
    "function": {
        "name": "intercom_reply",
        "description": """Trả lời tin nhắn intercom đang hoạt động.
        
Được sử dụng nội bộ khi thiết bị nhận được tin nhắn intercom và người dùng phản hồi.
Không nên được gọi trực tiếp bởi người dùng.
""",
        "parameters": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "ID cuộc hội thoại intercom"
                },
                "message": {
                    "type": "string",
                    "description": "Nội dung phản hồi"
                }
            },
            "required": ["conversation_id", "message"]
        }
    }
}


@register_function(
    "intercom_reply", intercom_reply_function_desc, ToolType.SYSTEM_CTL
)
async def intercom_reply(conn, conversation_id: str, message: str) -> ActionResponse:
    """
    Reply to an active intercom conversation.
    
    Args:
        conn: Connection handler with device context
        conversation_id: Active conversation ID
        message: Reply message content
        
    Returns:
        Result message for TTS
    """
    from app.services.intercom_service import get_intercom_service
    
    logger.bind(tag=TAG).info(
        f"[Intercom Tool] Reply to conv {conversation_id}: {message[:50]}..."
    )
    
    try:
        device_id = getattr(conn, 'device_id', None)
        device_name = getattr(conn, 'device_name', None) or "thiết bị"
        mac_address = getattr(conn, 'mac_address', None) or ""
        
        if not device_id:
            return "Không thể phản hồi: thiếu thông tin thiết bị"
        
        service = get_intercom_service()
        
        result = await service.handle_reply(
            from_device_id=str(device_id),
            from_device_name=device_name,
            from_mac=mac_address,
            conversation_id=conversation_id,
            message=message,
        )
        
        if result.success:
            return ActionResponse(
                action=Action.REQLLM,
                result="Đã gửi phản hồi",
                response=None,
            )
        else:
            return ActionResponse(
                action=Action.RESPONSE,
                result=result.error,
                response=f"Không thể phản hồi: {result.error}",
            )
            
    except Exception as e:
        logger.bind(tag=TAG).exception(f"[Intercom Tool] Reply error: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result=str(e),
            response=f"Lỗi gửi phản hồi: {str(e)}",
        )


# ========================
# Tool: intercom.end
# ========================

intercom_end_function_desc = {
    "type": "function",
    "function": {
        "name": "intercom_end",
        "description": """Kết thúc cuộc hội thoại intercom hiện tại.
        
Sử dụng khi người dùng muốn ngừng liên lạc với thiết bị khác.

Ví dụ:
- "Kết thúc cuộc gọi" → intercom_end()
- "Ngừng liên lạc" → intercom_end()
""",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


@register_function(
    "intercom_end", intercom_end_function_desc, ToolType.SYSTEM_CTL
)
async def intercom_end(conn) -> ActionResponse:
    """
    End the current intercom conversation.
    
    Args:
        conn: Connection handler with device context
        
    Returns:
        Result message for TTS
    """
    from app.services.intercom_service import get_intercom_service
    
    logger.bind(tag=TAG).info("[Intercom Tool] Ending conversation")
    
    try:
        device_id = getattr(conn, 'device_id', None)
        
        if not device_id:
            return "Không có cuộc hội thoại nào đang hoạt động"
        
        service = get_intercom_service()
        conversation = service.get_active_conversation(str(device_id))
        
        if not conversation:
            return ActionResponse(
                action=Action.RESPONSE,
                result="no_active_conversation",
                response="Không có cuộc hội thoại nào đang hoạt động",
            )
        
        await service.end_conversation(
            conversation.conversation_id,
            reason="user_ended"
        )
        
        return ActionResponse(
            action=Action.RESPONSE,
            result="conversation_ended",
            response="Đã kết thúc cuộc hội thoại",
        )
        
    except Exception as e:
        logger.bind(tag=TAG).exception(f"[Intercom Tool] End error: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result=str(e),
            response=f"Lỗi kết thúc: {str(e)}",
        )

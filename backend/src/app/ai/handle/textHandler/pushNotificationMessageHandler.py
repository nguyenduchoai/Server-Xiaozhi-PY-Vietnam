from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict

from app.ai.handle.intentHandler import speak_txt
from app.ai.handle.textMessageHandler import TextMessageHandler
from app.ai.handle.textMessageType import TextMessageType
from app.core.logger import setup_logging

if TYPE_CHECKING:
    from app.ai.connection import (
        ConnectionHandler,
    )  # chỉ dùng cho hint, không chạy lúc runtime


TAG = __name__


class PushNotificationMessageHandler(TextMessageHandler):
    """
    Handler for push_notification messages from firmware.
    
    When device receives MQTT TTS message, it opens WebSocket and sends:
    {"type": "push_notification", "content": "...", "session_id": "...", "need_tts": true}
    
    This handler speaks the content via TTS.
    """

    def __init__(self):
        self.logger = setup_logging()

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.PUSH_NOTIFICATION

    async def handle(self, conn: ConnectionHandler, msg_json: Dict[str, Any]) -> None:
        """
        Handle push notification by speaking content via TTS.
        """
        # Extract content - firmware sends "content" or "text" field
        content = msg_json.get("content") or msg_json.get("text") or ""
        title = msg_json.get("title", "")
        need_tts = msg_json.get("need_tts", True)
        
        # Combine title and content for speaking
        speak_text = content
        if title and content:
            speak_text = f"{title}. {content}"
        elif title:
            speak_text = title
        
        if not speak_text or not speak_text.strip():
            conn.logger.bind(tag=TAG).warning(
                f"Push notification with empty content: {msg_json}"
            )
            return
        
        conn.logger.bind(tag=TAG).info(
            f"Processing push notification: {speak_text[:50]}..."
        )
        
        if not need_tts:
            conn.logger.bind(tag=TAG).debug("TTS disabled for this notification")
            return
        
        try:
            # Wait for TTS pipeline ready
            pipeline_ready = await conn.wait_for_pipeline_ready(timeout=5)
            if not pipeline_ready or not getattr(conn, "tts", None):
                conn.logger.bind(tag=TAG).error("TTS pipeline not ready")
                return
            
            # Generate sentence_id
            sentence_id = msg_json.get("session_id") or str(uuid.uuid4().hex)
            conn.sentence_id = sentence_id
            conn.client_abort = False
            
            # Speak via TTS
            speak_txt(conn, speak_text)
            
            conn.logger.bind(tag=TAG).info(
                f"Push notification sent to TTS: {speak_text[:30]}..."
            )
            
        except Exception as e:
            conn.logger.bind(tag=TAG).error(
                f"Failed to process push notification: {e}"
            )

"""Chat Message Handler — Handles direct text chat messages.

Compatible with Go server pattern (AnimeAIChat/xiaozhi-server-go).
Firmware or web clients can send: {"type":"chat","text":"Hello world"}
This triggers the LLM pipeline directly with text input (no ASR).
"""

from __future__ import annotations
from typing import Dict, Any, TYPE_CHECKING
from app.ai.handle.receiveAudioHandle import startToChat
from app.ai.handle.textMessageHandler import TextMessageHandler
from app.ai.handle.textMessageType import TextMessageType

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler

TAG = __name__


class ChatTextMessageHandler(TextMessageHandler):
    """Handler for 'chat' type messages — direct text-to-LLM."""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.CHAT

    async def handle(self, conn: ConnectionHandler, msg_json: Dict[str, Any]) -> None:
        text = msg_json.get("text", "").strip()
        if not text:
            conn.logger.bind(tag=TAG).warning("Received empty chat message, ignoring")
            return

        conn.logger.bind(tag=TAG).info(f"Chat message received: {text[:60]}...")
        # Route directly to LLM pipeline (same as listen detect)
        await startToChat(conn, text)

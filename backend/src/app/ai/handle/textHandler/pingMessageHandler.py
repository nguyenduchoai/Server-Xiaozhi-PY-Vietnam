"""Ping Message Handler — Standard WebSocket Keepalive

Matches original project: core/handle/textHandler/pingMessageHandler.py
Client sends {"type": "ping"}, server responds with {"type": "pong"}
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Dict, Any

from app.ai.handle.textMessageHandler import TextMessageHandler
from app.ai.handle.textMessageType import TextMessageType

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler

TAG = __name__


class PingMessageHandler(TextMessageHandler):
    """Ping message handler — WebSocket keepalive heartbeat"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.PING

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        """
        Handle PING message, send PONG response.
        
        Message format: {"type": "ping"}
        Response: {"type": "pong", "timestamp": "..."}
        """
        # Check if WebSocket heartbeat is enabled (default: enabled for compatibility)
        enable_websocket_ping = conn.config.get("enable_websocket_ping", True)
        if not enable_websocket_ping:
            conn.logger.bind(tag=TAG).debug("WebSocket heartbeat disabled, ignoring PING")
            return

        try:
            conn.logger.bind(tag=TAG).debug("Received PING, sending PONG")
            conn.last_activity_time = time.time() * 1000

            pong_message = {
                "type": "pong",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            }

            await conn.send_raw(pong_message)
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Error handling PING: {e}")

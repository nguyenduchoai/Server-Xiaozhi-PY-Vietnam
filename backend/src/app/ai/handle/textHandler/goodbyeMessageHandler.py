"""Goodbye Message Handler — Standard disconnect signal

Client sends {"type": "goodbye"} to signal graceful disconnect.
Server should close the connection cleanly.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Dict, Any

from app.ai.handle.textMessageHandler import TextMessageHandler
from app.ai.handle.textMessageType import TextMessageType

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler

TAG = __name__


class GoodbyeMessageHandler(TextMessageHandler):
    """Goodbye message handler — graceful disconnect"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.GOODBYE

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        """
        Handle GOODBYE message — client wants to disconnect.
        
        Message format: {"type": "goodbye"}
        """
        try:
            conn.logger.bind(tag=TAG).info(
                f"Received goodbye from device {conn.device_id}, closing connection"
            )
            
            # Send goodbye acknowledgement
            goodbye_response = {
                "type": "goodbye",
                "session_id": conn.session_id,
            }
            await conn.send_raw(goodbye_response)
            
            # Close the connection cleanly
            if conn.websocket:
                await conn.close(conn.websocket)
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"Error handling goodbye: {e}")

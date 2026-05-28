from enum import Enum


class TextMessageType(Enum):
    """Enum các loại thông điệp"""

    HELLO = "hello"
    ABORT = "abort"
    LISTEN = "listen"
    IOT = "iot"
    MCP = "mcp"
    CHAT = "chat"          # Standard: Text-only chat (Go server pattern)
    SERVER = "server"
    REMINDER = "reminder"
    NOTIFICATION = "notification"
    PUSH_NOTIFICATION = "push_notification"
    SPEAK = "speak"
    PING = "ping"       # Standard: WebSocket keepalive heartbeat
    GOODBYE = "goodbye"  # Standard: Client disconnect signal



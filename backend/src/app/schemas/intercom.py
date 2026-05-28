"""
Intercom Schemas - Data models for voice relay between devices.

Created: 2026-02-03
Feature: Walkie-Talkie / Intercom
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel


class ConversationState(str, Enum):
    """Conversation lifecycle states."""
    ACTIVE = "active"
    WAITING_REPLY = "waiting_reply"
    ENDED = "ended"
    TIMEOUT = "timeout"


class MessageDirection(str, Enum):
    """Message direction in conversation."""
    OUTGOING = "outgoing"
    INCOMING = "incoming"


@dataclass
class IntercomMessage:
    """Single message in an intercom conversation."""
    sender_device_id: str
    sender_name: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    direction: MessageDirection = MessageDirection.OUTGOING


@dataclass
class IntercomConversation:
    """Active intercom conversation between two devices."""
    conversation_id: str
    
    # Initiator (device that started the call)
    initiator_device_id: str
    initiator_mac: str
    initiator_name: str
    
    # Target (device receiving the call)
    target_device_id: str
    target_mac: str
    target_name: str
    
    # Account owner
    user_id: str
    
    # State
    state: ConversationState = ConversationState.ACTIVE
    
    # Message history
    messages: List[IntercomMessage] = field(default_factory=list)
    
    # Timestamps
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Configuration
    timeout_seconds: int = 30  # Auto-end after 30s inactivity
    
    def is_timed_out(self) -> bool:
        """Check if conversation has timed out."""
        elapsed = (datetime.now(timezone.utc) - self.last_activity).total_seconds()
        return elapsed > self.timeout_seconds
    
    def add_message(self, sender_id: str, sender_name: str, content: str, direction: MessageDirection):
        """Add message and update activity timestamp."""
        self.messages.append(IntercomMessage(
            sender_device_id=sender_id,
            sender_name=sender_name,
            content=content,
            direction=direction,
        ))
        self.last_activity = datetime.now(timezone.utc)
    
    def get_other_device(self, device_id: str) -> tuple:
        """Get the other device in conversation (name, mac, id)."""
        if device_id == self.initiator_device_id:
            return (self.target_name, self.target_mac, self.target_device_id)
        else:
            return (self.initiator_name, self.initiator_mac, self.initiator_device_id)


# Pydantic models for API/MQTT
class IntercomSendRequest(BaseModel):
    """Request to send intercom message."""
    target_device: str  # Device name
    message: str


class IntercomReplyRequest(BaseModel):
    """Request to reply to intercom message."""
    conversation_id: str
    message: str


class IntercomResult(BaseModel):
    """Result of intercom operation."""
    success: bool
    conversation_id: Optional[str] = None
    target_device_name: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


class IntercomMqttPayload(BaseModel):
    """MQTT payload for intercom message."""
    type: str = "intercom"
    from_device_name: str
    from_device_id: str
    message: str
    conversation_id: str
    reply_to_mac: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IntercomReplyMqttPayload(BaseModel):
    """MQTT payload for intercom reply."""
    type: str = "intercom_reply"
    from_device_name: str
    from_device_id: str
    message: str
    conversation_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

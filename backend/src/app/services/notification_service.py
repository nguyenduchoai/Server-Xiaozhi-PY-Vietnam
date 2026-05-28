"""
Notification Service - Push notifications to connected devices.

Enables proactive communication from server to devices via WebSocket.
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from app.core.logger import get_logger

logger = get_logger(__name__)

TAG = __name__


class NotificationService:
    """
    Service to send notifications to connected devices.
    
    Notifications are sent via WebSocket to active device connections.
    """
    
    def __init__(self):
        # Track active connections by device_id
        self._connections: Dict[str, Any] = {}
    
    def register_connection(self, device_id: str, connection):
        """Register a device connection for notifications."""
        self._connections[device_id] = connection
        logger.bind(tag=TAG).debug(f"Registered notification connection: {device_id}")
    
    def unregister_connection(self, device_id: str):
        """Unregister a device connection."""
        if device_id in self._connections:
            del self._connections[device_id]
            logger.bind(tag=TAG).debug(f"Unregistered notification connection: {device_id}")
    
    def get_active_devices(self) -> List[str]:
        """Get list of device IDs with active connections."""
        return list(self._connections.keys())
    
    async def send_notification(
        self,
        device_id: str,
        message: str,
        notification_type: str = "info",
        speak: bool = True,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send notification to a specific device.
        
        Args:
            device_id: Target device ID
            message: Notification message
            notification_type: Type (info, warning, alert, reminder)
            speak: Whether device should speak the message via TTS
            data: Additional data payload
            
        Returns:
            True if sent successfully, False otherwise
        """
        conn = self._connections.get(device_id)
        if not conn:
            logger.bind(tag=TAG).warning(f"Device {device_id} not connected for notification")
            return False
        
        try:
            notification = {
                "type": "notification",
                "notification_type": notification_type,
                "message": message,
                "speak": speak,
                "data": data or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            await conn.send_raw(notification)
            logger.bind(tag=TAG).info(f"Notification sent to {device_id}: {message[:50]}...")
            
            # If speak is True, also trigger TTS
            if speak and hasattr(conn, 'tts') and conn.tts:
                await self._speak_notification(conn, message)
            
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to send notification to {device_id}: {e}")
            return False
    
    async def _speak_notification(self, conn, message: str):
        """Speak the notification via TTS."""
        try:
            from app.ai.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
            import uuid
            
            conn.sentence_id = str(uuid.uuid4().hex)
            conn.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=conn.sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )
            conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=message)
            conn.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=conn.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to speak notification: {e}")
    
    async def broadcast_notification(
        self,
        message: str,
        notification_type: str = "info",
        speak: bool = True,
        device_ids: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        Broadcast notification to multiple devices.
        
        Args:
            message: Notification message
            notification_type: Type (info, warning, alert)
            speak: Whether to speak via TTS
            device_ids: List of device IDs (None = all connected devices)
            
        Returns:
            Dict mapping device_id to success status
        """
        targets = device_ids or list(self._connections.keys())
        results = {}
        
        for device_id in targets:
            results[device_id] = await self.send_notification(
                device_id=device_id,
                message=message,
                notification_type=notification_type,
                speak=speak,
            )
        
        return results
    
    async def send_reminder(
        self,
        device_id: str,
        title: str,
        description: Optional[str] = None,
    ) -> bool:
        """Send a reminder notification."""
        message = title
        if description:
            message = f"{title}. {description}"
        
        return await self.send_notification(
            device_id=device_id,
            message=f"Nhắc nhở: {message}",
            notification_type="reminder",
            speak=True,
            data={"title": title, "description": description},
        )

    async def send_friend_request_notification(
        self,
        target_user_id: str,
        sender_name: str,
        sender_id: str,
        db = None,
    ) -> bool:
        """
        Send friend request notification to all devices of a user.
        
        Args:
            target_user_id: User ID to notify
            sender_name: Name of person sending friend request
            sender_id: ID of sender
            db: Database session (optional, for looking up devices)
            
        Returns:
            True if at least one device received the notification
        """
        try:
            message = f"{sender_name} muốn kết bạn với bạn"
            
            # Find all online devices for target user
            online_devices = []
            for device_id, conn in self._connections.items():
                # Check if this connection belongs to target user
                if hasattr(conn, 'user_id') and conn.user_id == target_user_id:
                    online_devices.append(device_id)
            
            if not online_devices:
                logger.bind(tag=TAG).debug(
                    f"No online devices for user {target_user_id} to send friend request notification"
                )
                return False
            
            # Send to all online devices
            success = False
            for device_id in online_devices:
                result = await self.send_notification(
                    device_id=device_id,
                    message=message,
                    notification_type="friend_request",
                    speak=True,
                    data={
                        "type": "friend_request",
                        "sender_id": sender_id,
                        "sender_name": sender_name,
                    },
                )
                if result:
                    success = True
            
            return success
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error sending friend request notification: {e}")
            return False


# Global singleton instance
notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get the global notification service instance."""
    return notification_service

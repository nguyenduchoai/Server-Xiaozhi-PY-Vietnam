"""
Telegram Bot Service - Send notifications via Telegram Bot API.

SaaS multi-tenant: Each agent can have its own Telegram bot configuration.
Supports personal chats and group chats.
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.core.logger import get_logger

logger = get_logger(__name__)
TAG = "TelegramBot"

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramBotService:
    """Send notifications to Telegram chats via Bot API.
    
    Each instance is configured per-agent with its own bot token and chat IDs.
    """

    def __init__(self, bot_token: str, chat_ids: Optional[List[str]] = None):
        """
        Args:
            bot_token: Telegram Bot API token from @BotFather
            chat_ids: Default list of chat IDs to send to
        """
        self.bot_token = bot_token
        self.chat_ids = chat_ids or []
        self.api_url = TELEGRAM_API_BASE.format(token=bot_token)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ========== Core Send Methods ==========

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        disable_notification: bool = False,
    ) -> bool:
        """Send a text message to a Telegram chat.
        
        Args:
            chat_id: Telegram chat ID (user or group)
            text: Message text (supports Markdown)
            parse_mode: "Markdown" or "HTML"
            disable_notification: If True, send silently
            
        Returns:
            True if sent successfully
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_notification": disable_notification,
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    logger.bind(tag=TAG).info(
                        f"Telegram message sent to {chat_id}: {text[:50]}..."
                    )
                    return True
                else:
                    logger.bind(tag=TAG).error(
                        f"Telegram API error: {data.get('description')}"
                    )
            else:
                logger.bind(tag=TAG).error(
                    f"Telegram HTTP error {response.status_code}: {response.text[:200]}"
                )
            return False
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to send Telegram message: {e}")
            return False

    async def broadcast(
        self,
        text: str,
        chat_ids: Optional[List[str]] = None,
        parse_mode: str = "Markdown",
    ) -> Dict[str, bool]:
        """Send message to multiple chats.
        
        Args:
            text: Message text
            chat_ids: Target chat IDs (defaults to configured chat_ids)
            parse_mode: Message format
            
        Returns:
            Dict mapping chat_id to success status
        """
        targets = chat_ids or self.chat_ids
        results = {}
        
        for chat_id in targets:
            results[chat_id] = await self.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
            )
        
        return results

    # ========== Notification Templates ==========

    LEVEL_EMOJI = {
        "info": "ℹ️",
        "warning": "⚠️",
        "critical": "🚨",
        "sos": "🆘",
        "reminder": "⏰",
        "report": "📋",
        "medication": "💊",
        "exercise": "🏃",
        "safety": "🛡️",
    }

    async def send_alert(
        self,
        message: str,
        level: str = "info",
        agent_name: Optional[str] = None,
        chat_ids: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """Send a formatted alert notification.
        
        Args:
            message: Alert message content
            level: Alert level (info/warning/critical/sos)
            agent_name: Optional agent name for identification
            chat_ids: Override default chat IDs
        """
        emoji = self.LEVEL_EMOJI.get(level, "ℹ️")
        
        header = f"{emoji} *{level.upper()}*"
        if agent_name:
            header += f" — {agent_name}"
        
        text = f"{header}\n\n{message}\n\n_{datetime.now().strftime('%H:%M %d/%m/%Y')}_"
        
        return await self.broadcast(text=text, chat_ids=chat_ids)

    async def send_daily_report(
        self,
        report_data: Dict[str, Any],
        chat_ids: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """Send a formatted daily summary report.
        
        Args:
            report_data: Dict with report fields:
                - name: Person/agent name
                - date: Report date string
                - summary: Text summary
                - alerts_count: Number of alerts today
                - reminders_completed: e.g. "3/5"
                - custom_fields: Optional extra data
        """
        name = report_data.get("name", "Agent")
        date = report_data.get("date", datetime.now().strftime("%d/%m/%Y"))
        summary = report_data.get("summary", "Không có sự kiện đặc biệt.")
        alerts = report_data.get("alerts_count", 0)
        reminders = report_data.get("reminders_completed", "N/A")
        
        text = (
            f"📋 *Báo cáo ngày {date}*\n\n"
            f"👤 {name}\n"
            f"📝 {summary}\n"
            f"⚠️ Cảnh báo: {alerts}\n"
            f"⏰ Nhắc nhở: {reminders}\n"
        )
        
        # Add custom fields
        for key, value in report_data.get("custom_fields", {}).items():
            text += f"• {key}: {value}\n"
        
        text += f"\n_{datetime.now().strftime('%H:%M %d/%m/%Y')}_"
        
        return await self.broadcast(text=text, chat_ids=chat_ids)

    async def send_medication_reminder(
        self,
        medication_name: str,
        person_name: str,
        status: str = "pending",
        chat_ids: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """Send medication reminder status to family.
        
        Args:
            medication_name: Name of medication
            person_name: Name of person
            status: "pending" | "taken" | "missed"
        """
        status_emoji = {
            "pending": "⏳ Đang chờ",
            "taken": "✅ Đã uống",
            "missed": "❌ Bỏ lỡ",
        }
        
        text = (
            f"💊 *Nhắc thuốc*\n\n"
            f"👤 {person_name}\n"
            f"💊 {medication_name}\n"
            f"📊 Trạng thái: {status_emoji.get(status, status)}\n"
            f"\n_{datetime.now().strftime('%H:%M %d/%m/%Y')}_"
        )
        
        return await self.broadcast(text=text, chat_ids=chat_ids)

    async def verify_bot(self) -> Optional[Dict[str, Any]]:
        """Verify bot token is valid and return bot info.
        
        Returns:
            Bot info dict or None if invalid
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.api_url}/getMe")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data["result"]
                    logger.bind(tag=TAG).info(
                        f"Telegram bot verified: @{bot_info.get('username')}"
                    )
                    return bot_info
            
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to verify Telegram bot: {e}")
            return None

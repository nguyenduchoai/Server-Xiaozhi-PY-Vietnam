"""
Notification Channel Router - Multi-channel notification delivery for SaaS platform.

Routes notifications to the appropriate channels based on agent configuration:
- Device (WebSocket/MQTT) — always available
- Telegram Bot — requires bot_token + chat_ids
- Zalo OA (Official Account Bot) — requires oa_access_token + user_ids

Also provides Alert Escalation: graduated alert levels that automatically
route to more channels as severity increases.

SaaS Multi-Tenant: Each agent has its own notification_channels config.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.core.logger import get_logger
from app.services.telegram_bot_service import TelegramBotService

logger = get_logger(__name__)
TAG = "NotificationRouter"


class NotificationChannelRouter:
    """Routes notifications to configured channels per-agent.

    Supports:
    - Device notifications (WebSocket/MQTT)
    - Telegram Bot messages
    - Zalo OA messages (via Official Account API)
    - Alert escalation with graduated severity
    """

    def __init__(self):
        self._telegram_cache: Dict[str, TelegramBotService] = {}
        self._zalo_oa_cache: Dict[str, "ZaloOABotService"] = {}    # Zalo OA

    def _get_telegram(self, channel_config: Dict[str, Any]) -> Optional[TelegramBotService]:
        """Get or create Telegram service for this config."""
        bot_token = channel_config.get("bot_token")
        if not bot_token:
            return None
        
        if bot_token not in self._telegram_cache:
            chat_ids = channel_config.get("chat_ids", [])
            self._telegram_cache[bot_token] = TelegramBotService(
                bot_token=bot_token,
                chat_ids=chat_ids,
            )
        return self._telegram_cache[bot_token]

    def _get_zalo_oa(self, channel_config: Dict[str, Any]) -> Optional[Any]:
        """Get or create Zalo OA (Official Account) Bot service.
        
        Uses Zalo OA API with oa_access_token (separate from personal Zalo).
        """
        oa_access_token = channel_config.get("oa_access_token")
        if not oa_access_token:
            return None
        
        # Cache by token
        if oa_access_token not in self._zalo_oa_cache:
            # Zalo OA uses HTTP API with access token
            # For now, create a lightweight wrapper
            self._zalo_oa_cache[oa_access_token] = ZaloOABotService(
                oa_access_token=oa_access_token,
                user_ids=channel_config.get("user_ids", []),
            )
        return self._zalo_oa_cache[oa_access_token]

    async def send_notification(
        self,
        notification_channels: Dict[str, Any],
        message: str,
        level: str = "info",
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        notification_type: str = "alert",
        device_callback=None,
        report_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Route notification to all configured and applicable channels.
        
        Args:
            notification_channels: Agent's notification_channels JSON config
            message: Notification message text
            level: Alert level (info/warning/critical/sos)
            agent_name: Agent name for identification
            agent_id: Agent UUID (for Zalo personal account routing)
            notification_type: "alert", "reminder", "report", "medication"
            device_callback: Async callable to send device notification
            report_data: Data for daily report format
            
        Returns:
            Dict with delivery results per channel
        """
        results = {
            "channels_attempted": [],
            "channels_delivered": [],
            "details": {},
        }
        
        # Enrich config with DB UserConnections if agent_id is provided
        if agent_id:
            try:
                from app.core.db.database import async_session_maker
                from app.models.user_connection import UserConnection
                from app.models.agent import Agent
                from sqlalchemy import select
                async with async_session_maker() as db:
                    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
                    ag = agent_res.scalar_one_or_none()
                    if ag:
                        conn_res = await db.execute(select(UserConnection).where(UserConnection.user_id == ag.user_id))
                        cmap = {c.type: c for c in conn_res.scalars().all()}
                        
                        if notification_channels.get("telegram", {}).get("enabled") and "telegram" in cmap:
                            notification_channels["telegram"]["bot_token"] = cmap["telegram"].config.get("bot_token")
                        if notification_channels.get("zalo_oa", {}).get("enabled") and "zalo_oa" in cmap:
                            notification_channels["zalo_oa"]["oa_access_token"] = cmap["zalo_oa"].config.get("oa_access_token")
            except Exception as e:
                logger.error(f"Router DB Enrich error: {e}")

        target_channels = self._resolve_channels(
            notification_channels, level, notification_type
        )

        tasks = []

        # Device notification
        if "device" in target_channels and device_callback:
            tasks.append(("device", self._send_device(device_callback, message)))

        # Telegram
        if "telegram" in target_channels:
            telegram_config = notification_channels.get("telegram", {})
            if telegram_config.get("enabled"):
                telegram = self._get_telegram(telegram_config)
                if telegram:
                    if notification_type == "report" and report_data:
                        tasks.append(("telegram", telegram.send_daily_report(report_data)))
                    else:
                        tasks.append(("telegram", telegram.send_alert(
                            message=message,
                            level=level,
                            agent_name=agent_name,
                        )))

        # Zalo OA Bot (Official Account)
        if "zalo_oa" in target_channels:
            zalo_oa_config = notification_channels.get("zalo_oa", {})
            if zalo_oa_config.get("enabled"):
                zalo_oa = self._get_zalo_oa(zalo_oa_config)
                if zalo_oa:
                    if notification_type == "report" and report_data:
                        tasks.append(("zalo_oa", zalo_oa.send_daily_report(report_data)))
                    else:
                        tasks.append(("zalo_oa", zalo_oa.send_alert(
                            message=message,
                            level=level,
                            agent_name=agent_name,
                        )))

        # Execute all channel deliveries in parallel
        if tasks:
            channel_names = [t[0] for t in tasks]
            coroutines = [t[1] for t in tasks]
            
            results["channels_attempted"] = channel_names
            
            task_results = await asyncio.gather(*coroutines, return_exceptions=True)
            
            for channel_name, result in zip(channel_names, task_results):
                if isinstance(result, Exception):
                    logger.bind(tag=TAG).error(
                        f"Channel {channel_name} failed: {result}"
                    )
                    results["details"][channel_name] = {"success": False, "error": str(result)}
                elif isinstance(result, bool):
                    if result:
                        results["channels_delivered"].append(channel_name)
                    results["details"][channel_name] = {"success": result}
                elif isinstance(result, dict):
                    any_success = any(result.values())
                    if any_success:
                        results["channels_delivered"].append(channel_name)
                    results["details"][channel_name] = {"success": any_success, "recipients": result}
                else:
                    results["details"][channel_name] = {"success": bool(result)}
                    if result:
                        results["channels_delivered"].append(channel_name)

        logger.bind(tag=TAG).info(
            f"Notification routed: level={level}, "
            f"attempted={results['channels_attempted']}, "
            f"delivered={results['channels_delivered']}"
        )

        return results

    def _resolve_channels(
        self,
        notification_channels: Dict[str, Any],
        level: str,
        notification_type: str,
    ) -> List[str]:
        """Determine which channels to use based on escalation rules.
        
        Default escalation:
        - info: device only
        - warning: device + telegram
        - critical: device + telegram + zalo_oa
        - sos: device + telegram + zalo_oa (with repeat)
        """
        escalation = notification_channels.get("alert_escalation", {})
        
        if escalation.get("enabled"):
            levels_config = escalation.get("levels", {})
            level_config = levels_config.get(level, {})
            
            if level_config:
                return level_config.get("channels", ["device"])

        # Default escalation rules
        default_channels = {
            "info": ["device"],
            "warning": ["device", "telegram"],
            "critical": ["device", "telegram", "zalo_oa"],
            "sos": ["device", "telegram", "zalo_oa"],
            "reminder": ["device"],
            "report": ["telegram", "zalo_oa"],
            "medication": ["device", "telegram"],
        }

        # For reports, use daily_report channels if configured
        if notification_type == "report":
            daily_config = notification_channels.get("daily_report", {})
            if daily_config.get("enabled"):
                return daily_config.get("channels", ["telegram"])

        return default_channels.get(level, ["device"])

    async def _send_device(self, callback, message: str) -> bool:
        """Send notification via device callback."""
        try:
            result = await callback(message)
            return bool(result)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Device notification failed: {e}")
            return False

    async def close(self):
        """Cleanup all cached service instances."""
        for service in self._telegram_cache.values():
            await service.close()
        self._telegram_cache.clear()
        self._zalo_oa_cache.clear()


# ============ Zalo OA Bot Service (lightweight) ============

class ZaloOABotService:
    """Zalo Official Account Bot — sends via Zalo OA API.

    - Uses OA Access Token (from oa.zalo.me)
    - Sends to followers of the OA
    - API: https://developers.zalo.me/docs/official-account
    """

    LEVEL_EMOJI = {
        "info": "ℹ️", "warning": "⚠️", "critical": "🚨",
        "sos": "🆘", "reminder": "⏰", "report": "📋", "medication": "💊",
    }

    def __init__(self, oa_access_token: str, user_ids: Optional[List[str]] = None):
        self.oa_access_token = oa_access_token
        self.user_ids = user_ids or []
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def send_message(self, user_id: str, text: str) -> bool:
        """Send a text message via Zalo OA API."""
        try:
            client = await self._get_client()
            response = await client.post(
                "https://openapi.zalo.me/v3.0/oa/message/cs",
                headers={
                    "Content-Type": "application/json",
                    "access_token": self.oa_access_token,
                },
                json={
                    "recipient": {"user_id": user_id},
                    "message": {"text": text},
                },
            )
            data = response.json()
            if data.get("error") == 0:
                logger.bind(tag=TAG).info(f"Zalo OA sent to {user_id}: {text[:50]}...")
                return True
            else:
                logger.bind(tag=TAG).error(f"Zalo OA error: {data}")
                return False
        except Exception as e:
            logger.bind(tag=TAG).error(f"Zalo OA send failed: {e}")
            return False

    async def send_alert(
        self,
        message: str,
        level: str = "info",
        agent_name: Optional[str] = None,
        user_ids: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """Send formatted alert to all configured OA followers."""
        emoji = self.LEVEL_EMOJI.get(level, "ℹ️")
        text = f"{emoji} [{level.upper()}]"
        if agent_name:
            text += f" - {agent_name}"
        text += f"\n\n{message}"
        text += f"\n\n{datetime.now().strftime('%H:%M %d/%m/%Y')}"

        targets = user_ids or self.user_ids
        results = {}
        for uid in targets:
            results[uid] = await self.send_message(uid, text)
        return results

    async def send_daily_report(
        self,
        report_data: Dict[str, Any],
        user_ids: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """Send daily report via Zalo OA."""
        name = report_data.get("name", "Agent")
        date = report_data.get("date", datetime.now().strftime("%d/%m/%Y"))
        summary = report_data.get("summary", "Không có sự kiện đặc biệt.")

        text = (
            f"📋 Báo cáo ngày {date}\n\n"
            f"👤 {name}\n"
            f"📝 {summary}\n"
        )

        for key, value in report_data.get("custom_fields", {}).items():
            text += f"• {key}: {value}\n"

        targets = user_ids or self.user_ids
        results = {}
        for uid in targets:
            results[uid] = await self.send_message(uid, text)
        return results

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global singleton
_router_instance: Optional[NotificationChannelRouter] = None


def get_notification_router() -> NotificationChannelRouter:
    """Get the global notification channel router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = NotificationChannelRouter()
    return _router_instance

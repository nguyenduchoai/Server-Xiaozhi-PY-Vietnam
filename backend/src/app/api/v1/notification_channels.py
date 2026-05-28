"""
Notification Channels API - Manage multi-channel notification config per agent.

Endpoints:
  GET    /agents/{agent_id}/notification-channels     → Get current config
  PUT    /agents/{agent_id}/notification-channels     → Update full config
  PATCH  /agents/{agent_id}/notification-channels/{channel} → Update single channel
  POST   /agents/{agent_id}/notification-channels/test     → Test notification delivery
  DELETE /agents/{agent_id}/notification-channels/{channel} → Disable a channel
"""

from typing import Annotated, Any, Optional, Dict
from datetime import datetime, timezone as dt_timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_get_db
from app.core.logger import get_logger
from app.api.dependencies import get_current_user
from app.models.agent import Agent
from app.schemas.base import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["notification-channels"])


# ========== Schemas ==========

class TelegramChannelConfig(BaseModel):
    """Telegram Bot channel configuration."""
    enabled: bool = False
    bot_token: Optional[str] = Field(None, description="Telegram Bot API token")
    chat_ids: list[str] = Field(default_factory=list, description="Telegram chat IDs")


class EscalationLevelConfig(BaseModel):
    """Alert escalation level configuration."""
    channels: list[str] = Field(default_factory=lambda: ["device"])


class AlertEscalationConfig(BaseModel):
    """Alert escalation configuration."""
    enabled: bool = False
    levels: Dict[str, EscalationLevelConfig] = Field(
        default_factory=lambda: {
            "info": EscalationLevelConfig(channels=["device"]),
            "warning": EscalationLevelConfig(channels=["device", "telegram"]),
            "critical": EscalationLevelConfig(channels=["device", "telegram", "zalo_oa"]),
            "sos": EscalationLevelConfig(channels=["device", "telegram", "zalo_oa"]),
        }
    )


class DailyReportConfig(BaseModel):
    """Daily report schedule configuration."""
    enabled: bool = False
    time: str = Field("21:00", description="Report time in HH:MM format")
    timezone: str = Field("Asia/Ho_Chi_Minh", description="Timezone for scheduling")
    channels: list[str] = Field(
        default_factory=lambda: ["telegram"],
        description="Channels to send report to"
    )


class AgentChannelConfig(BaseModel):
    """Per-connection channel selection with recipient list.
    
    This is the NEW format: Agent stores which connections to use + who to send to.
    Credentials live in UserConnection (Settings → Tích hợp).
    """
    connection_id: str = Field(..., description="UserConnection ID from Integrations")
    recipients: list[str] = Field(default_factory=list, description="Recipient IDs/emails/phones")
    enabled: bool = True


class NotificationChannelsConfig(BaseModel):
    """Full notification channels configuration for an agent.
    
    Supports BOTH formats:
    - Legacy: telegram, alert_escalation, daily_report (inline config)
    - New: channels[] referencing UserConnection + recipients
    """
    # Legacy per-agent config
    telegram: Optional[TelegramChannelConfig] = None
    alert_escalation: Optional[AlertEscalationConfig] = None
    daily_report: Optional[DailyReportConfig] = None
    # New: connection references + recipients
    channels: Optional[list[AgentChannelConfig]] = Field(
        None, description="List of connection channels with recipient selection"
    )


class TestNotificationRequest(BaseModel):
    """Request to test notification delivery."""
    message: str = Field("Đây là tin nhắn thử nghiệm từ Xiaozhi AI", description="Test message")
    level: str = Field("info", description="Alert level to test")
    channels: Optional[list[str]] = Field(None, description="Specific channels to test (null = all)")


# ========== Helper ==========

async def _get_agent(db: AsyncSession, agent_id: str, user_id: str) -> Agent:
    """Get agent and verify ownership."""
    stmt = select(Agent).where(
        Agent.id == agent_id,
        Agent.user_id == user_id,
        Agent.is_deleted == False,
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ========== Endpoints ==========

@router.get("/{agent_id}/notification-channels", response_model=SuccessResponse)
async def get_notification_channels(
    agent_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get notification channels config for an agent."""
    agent = await _get_agent(db, agent_id, current_user["id"])
    
    config = agent.notification_channels or {}
    
    return SuccessResponse(
        success=True,
        message="Notification channels retrieved",
        data=config,
    ).model_dump()


@router.put("/{agent_id}/notification-channels", response_model=SuccessResponse)
async def update_notification_channels(
    agent_id: str,
    config: NotificationChannelsConfig,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Update full notification channels config for an agent.
    
    This replaces the entire notification_channels configuration.
    """
    agent = await _get_agent(db, agent_id, current_user["id"])
    
    # Convert to dict, excluding None values
    config_dict = config.model_dump(exclude_none=True)
    
    agent.notification_channels = config_dict
    agent.updated_at = datetime.now(dt_timezone.utc)
    db.add(agent)
    await db.commit()
    
    # Update daily report scheduler if config changed
    daily_config = config_dict.get("daily_report", {})
    if daily_config.get("enabled"):
        from app.services.daily_report_service import get_daily_report_scheduler
        scheduler = get_daily_report_scheduler()
        time_str = daily_config.get("time", "21:00")
        tz = daily_config.get("timezone", "Asia/Ho_Chi_Minh")
        try:
            hour, minute = map(int, time_str.split(":"))
        except (ValueError, AttributeError):
            hour, minute = 21, 0
        scheduler.schedule_report(agent_id, hour, minute, tz)
    
    logger.info(f"Updated notification channels for agent {agent_id}")
    
    return SuccessResponse(
        success=True,
        message="Notification channels updated",
        data=config_dict,
    ).model_dump()


@router.patch("/{agent_id}/notification-channels/{channel}", response_model=SuccessResponse)
async def update_single_channel(
    agent_id: str,
    channel: str,
    config: dict[str, Any],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Update a single notification channel config.
    
    Channel must be one of: telegram, alert_escalation, daily_report
    """
    valid_channels = ["telegram", "alert_escalation", "daily_report"]
    if channel not in valid_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel: {channel}. Must be one of: {valid_channels}"
        )
    
    agent = await _get_agent(db, agent_id, current_user["id"])
    
    current_config = agent.notification_channels or {}
    current_config[channel] = config
    
    agent.notification_channels = current_config
    agent.updated_at = datetime.now(dt_timezone.utc)
    db.add(agent)
    await db.commit()
    
    logger.info(f"Updated {channel} channel for agent {agent_id}")
    
    return SuccessResponse(
        success=True,
        message=f"Channel {channel} updated",
        data=current_config,
    ).model_dump()


@router.delete("/{agent_id}/notification-channels/{channel}", response_model=SuccessResponse)
async def disable_channel(
    agent_id: str,
    channel: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Disable (remove) a notification channel."""
    agent = await _get_agent(db, agent_id, current_user["id"])
    
    current_config = agent.notification_channels or {}
    
    if channel in current_config:
        del current_config[channel]
        agent.notification_channels = current_config if current_config else None
        agent.updated_at = datetime.now(dt_timezone.utc)
        db.add(agent)
        await db.commit()
        
        # Cancel daily report if it was the daily_report channel
        if channel == "daily_report":
            from app.services.daily_report_service import get_daily_report_scheduler
            get_daily_report_scheduler().cancel_report(agent_id)
    
    return SuccessResponse(
        success=True,
        message=f"Channel {channel} disabled",
        data=current_config,
    ).model_dump()


@router.post("/{agent_id}/notification-channels/test", response_model=SuccessResponse)
async def test_notification(
    agent_id: str,
    test_request: TestNotificationRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Test notification delivery across configured channels.
    
    Sends a test message to verify each channel is working correctly.
    """
    agent = await _get_agent(db, agent_id, current_user["id"])
    
    notification_channels = agent.notification_channels or {}
    
    if not notification_channels:
        raise HTTPException(
            status_code=400,
            detail="No notification channels configured for this agent"
        )
    
    results = {}
    
    # Enrich with global UserConnection tokens
    try:
        from app.models.user_connection import UserConnection
        conn_res = await db.execute(select(UserConnection).where(UserConnection.user_id == current_user["id"]))
        conns = conn_res.scalars().all()
        cmap = {c.type: c for c in conns}
        
        if "telegram" in notification_channels and "telegram" in cmap:
            notification_channels["telegram"]["bot_token"] = cmap["telegram"].config.get("bot_token")
        if "zalo_oa" in notification_channels and "zalo_oa" in cmap:
            notification_channels["zalo_oa"]["oa_access_token"] = cmap["zalo_oa"].config.get("oa_access_token")
    except Exception as e:
        logger.error(f"Error enriching connection tokens: {e}")
    
    
    # Test Telegram
    if "telegram" in notification_channels and (
        test_request.channels is None or "telegram" in test_request.channels
    ):
        telegram_config = notification_channels["telegram"]
        if telegram_config.get("enabled") and telegram_config.get("bot_token"):
            try:
                from app.services.telegram_bot_service import TelegramBotService
                telegram = TelegramBotService(
                    bot_token=telegram_config["bot_token"],
                    chat_ids=telegram_config.get("chat_ids", []),
                )
                
                # Verify bot first
                bot_info = await telegram.verify_bot()
                if bot_info:
                    send_results = await telegram.send_alert(
                        message=test_request.message,
                        level=test_request.level,
                        agent_name=agent.agent_name,
                    )
                    results["telegram"] = {
                        "bot_name": f"@{bot_info.get('username', 'unknown')}",
                        "delivery": send_results,
                        "success": any(send_results.values()) if send_results else False,
                    }
                else:
                    results["telegram"] = {"success": False, "error": "Invalid bot token"}
                
                await telegram.close()
            except Exception as e:
                results["telegram"] = {"success": False, "error": str(e)}
    
    # Test Zalo OA Bot (Official Account API)
    if "zalo_oa" in notification_channels and (
        test_request.channels is None or "zalo_oa" in test_request.channels
    ):
        zalo_oa_config = notification_channels["zalo_oa"]
        if zalo_oa_config.get("enabled"):
            try:
                from app.services.notification_channel_router import NotificationChannelRouter
                router = NotificationChannelRouter()
                zalo_oa = router._get_zalo_oa(zalo_oa_config)
                if zalo_oa:
                    send_results = await zalo_oa.send_alert(
                        message=test_request.message,
                        level=test_request.level,
                        agent_name=agent.agent_name,
                    )
                    results["zalo_oa"] = {
                        "delivery": send_results,
                        "success": any(send_results.values()) if send_results else False,
                    }
                    await zalo_oa.close()
                else:
                    results["zalo_oa"] = {"success": False, "error": "Missing OA Access Token"}
            except Exception as e:
                results["zalo_oa"] = {"success": False, "error": str(e)}

    overall_success = any(
        r.get("success", False) for r in results.values()
    ) if results else False
    
    return SuccessResponse(
        success=overall_success,
        message="Test notification complete" if overall_success else "No channels delivered successfully",
        data=results,
    ).model_dump()

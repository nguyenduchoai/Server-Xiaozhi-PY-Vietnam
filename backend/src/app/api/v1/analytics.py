"""
Analytics API - Real-time usage metrics and statistics.
"""

from typing import Annotated
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user, async_get_db
from ...core.logger import get_logger
from ...models.agent import Agent
from ...models.agent_message import AgentMessage
from ...models.device import Device
from ...services.latency_tracker import latency_tracker
from ...services.mqtt_presence_tracker import get_presence_tracker

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/latency")
async def get_latency_stats(
    current_user: Annotated[dict, Depends(get_current_user)],
    last_n: Annotated[int, Query(ge=1, le=500)] = 50,
):
    """
    Get real-time AI pipeline latency for the current user's conversations.

    Data is collected in-memory from active device WebSocket/MQTT-gateway
    sessions and resets when the backend process restarts.
    """
    return latency_tracker.get_stats(last_n=last_n, user_id=current_user["id"])


@router.get("/dashboard")
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
):
    """
    Get dashboard statistics for the current user.
    
    Returns:
        - total_devices: Total devices owned
        - active_devices: Devices connected in last 24h
        - total_agents: Total agents owned
        - total_messages: Total voice interactions
        - messages_today: Messages in last 24h
        - daily_usage: Array of daily message counts
    """
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    now - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Total devices
    devices_result = await db.execute(
        Device.__table__.select().where(
            and_(
                Device.user_id == user_id
            )
        )
    )
    devices = devices_result.fetchall()
    total_devices = len(devices)
    
    # Active devices (connected in last 5 minutes or explicitly active)
    active_devices = sum(
        1 for d in devices 
        if (d.last_connected_at and d.last_connected_at > now - timedelta(minutes=5)) or d.status in ("online", "active")
    )
    
    # Total agents
    agents_result = await db.execute(
        Agent.__table__.select().where(
            and_(
                Agent.user_id == user_id,
                Agent.is_deleted == False
            )
        )
    )
    total_agents = len(agents_result.fetchall())
    
    # Total messages (all time)
    total_messages_result = await db.execute(
        func.count(AgentMessage.id).select().where(
            AgentMessage.agent_id.in_(
                Agent.__table__.select().where(Agent.user_id == user_id).with_only_columns(Agent.id)
            )
        )
    )
    total_messages = total_messages_result.scalar() or 0
    
    # Messages today
    messages_today_result = await db.execute(
        func.count(AgentMessage.id).select().where(
            and_(
                AgentMessage.agent_id.in_(
                    Agent.__table__.select().where(Agent.user_id == user_id).with_only_columns(Agent.id)
                ),
                AgentMessage.created_at >= today_start
            )
        )
    )
    messages_today = messages_today_result.scalar() or 0
    
    return {
        "total_devices": total_devices,
        "active_devices": active_devices,
        "total_agents": total_agents,
        "total_messages": total_messages,
        "messages_today": messages_today,
        "period_days": days,
        "generated_at": now.isoformat(),
    }


@router.get("/usage/daily")
async def get_daily_usage(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
):
    """
    Get daily usage breakdown for charts.
    
    Returns array of {date, messages, sessions} for each day.
    """
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    now - timedelta(days=days)
    
    # Get user's agent IDs
    agents_result = await db.execute(
        Agent.__table__.select().where(
            and_(
                Agent.user_id == user_id,
                Agent.is_deleted == False
            )
        ).with_only_columns(Agent.id)
    )
    agent_ids = [a.id for a in agents_result.fetchall()]
    
    if not agent_ids:
        return {"daily": [], "period_days": days}
    
    # Generate empty days
    daily_data = {}
    for i in range(days):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_data[date] = {"date": date, "messages": 0, "sessions": 0}
    
    # Query messages per day
    # Note: This would need a proper GROUP BY with date functions
    # For now, return structure with placeholder
    
    return {
        "daily": list(reversed(daily_data.values())),
        "period_days": days,
    }


@router.get("/devices/status")
async def get_devices_status(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Get status of all devices with last activity.
    
    Status priority:
    - online: WebSocket active (last_connected_at < 5 min)
    - available: MQTT connected (idle but can receive notifications)
    - offline: Not connected
    """
    
    user_id = current_user["id"]
    now = datetime.now(timezone.utc)
    
    # Get MQTT connected devices
    mqtt_tracker = get_presence_tracker()
    mqtt_online_macs = set()
    try:
        # Synchronous check (fast, uses in-memory cache)
        mqtt_online_macs = set(mqtt_tracker._online_devices.keys())
        logger.debug(f"MQTT online MACs from tracker: {mqtt_online_macs}")
    except Exception as e:
        logger.error(f"Failed to get MQTT online devices: {e}")
    
    devices_result = await db.execute(
        Device.__table__.select().where(
            and_(
                Device.user_id == user_id
            )
        )
    )
    devices = devices_result.fetchall()
    
    device_statuses = []
    online_count = 0
    available_count = 0
    
    for device in devices:
        last_seen = device.last_connected_at
        is_online = (last_seen and last_seen > now - timedelta(minutes=5)) or device.status in ("online", "active")
        mac_address = device.mac_address or ""
        is_mqtt_connected = mac_address.lower() in mqtt_online_macs
        
        # Determine status
        if is_online:
            status = "online"
            online_count += 1
        elif is_mqtt_connected:
            status = "available"
            available_count += 1
        else:
            status = "offline"
        
        device_statuses.append({
            "id": str(device.id),
            "name": device.device_name or device.mac_address,
            "mac_address": device.mac_address,
            "is_online": is_online,
            "is_mqtt_connected": is_mqtt_connected,
            "last_seen": last_seen.isoformat() if last_seen else None,
            "status": status,
        })
    
    return {
        "devices": device_statuses,
        "total": len(device_statuses),
        "online": online_count,
        "available": available_count,
        "offline": len(device_statuses) - online_count - available_count,
    }

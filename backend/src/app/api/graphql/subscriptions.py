"""
GraphQL Subscriptions for Real-Time Features

Provides GraphQL subscriptions for:
- WebSocket connection events
- Device status updates
- Agent activity
- System metrics streaming
"""

import asyncio
import strawberry
from typing import AsyncGenerator, List, Optional
from datetime import datetime
from uuid import UUID

from .types import (
    ConnectionInfoType,
    ConnectionMetricsType,
    SystemMetricsType,
    DeviceType,
    AgentType,
)
from app.core.logger import get_logger


logger = get_logger(__name__)


@strawberry.type
class Subscription:
    """GraphQL Subscription resolvers."""
    
    @strawberry.subscription
    async def connection_updates(
        self,
        user_id: Optional[UUID] = None,
        device_id: Optional[UUID] = None,
    ) -> AsyncGenerator[ConnectionInfoType, None]:
        """
        Subscribe to WebSocket connection updates.
        
        Yields connection state changes for specified filters.
        """
        from app.monitoring.websocket_monitor import monitor
        
        last_seen_states = {}
        
        while True:
            try:
                await asyncio.sleep(1)
                
                connections = monitor.get_all_connections()
                
                for conn in connections:
                    if user_id and str(conn.user_id) != str(user_id):
                        continue
                    if device_id and str(conn.device_id) != str(device_id):
                        continue
                    
                    state_key = conn.connection_id
                    if state_key not in last_seen_states:
                        last_seen_states[state_key] = conn.state
                    
                    if last_seen_states[state_key] != conn.state:
                        last_seen_states[state_key] = conn.state
                        
                        metrics = conn.metrics.get_metrics()
                        
                        yield ConnectionInfoType(
                            connection_id=conn.connection_id,
                            device_id=conn.device_id,
                            agent_id=str(conn.agent_id) if conn.agent_id else None,
                            user_id=str(conn.user_id) if conn.user_id else None,
                            client_ip=conn.client_ip,
                            state=conn.state.value,
                            metrics=ConnectionMetricsType(
                                connection_id=conn.connection_id,
                                uptime_seconds=metrics.get("uptime_seconds", 0),
                                message_count=metrics.get("message_count", 0),
                                bytes_received=metrics.get("bytes_received", 0),
                                bytes_sent=metrics.get("bytes_sent", 0),
                                errors=metrics.get("errors", 0),
                                reconnects=metrics.get("reconnects", 0),
                                avg_latency_ms=metrics.get("avg_latency_ms", 0),
                                p95_latency_ms=metrics.get("p95_latency_ms", 0),
                                p99_latency_ms=metrics.get("p99_latency_ms", 0),
                            ),
                            started_at=conn.started_at,
                            last_activity=metrics.get("last_activity"),
                        )
                            
            except asyncio.CancelledError:
                logger.info("Connection subscription cancelled")
                break
            except Exception as e:
                logger.error(f"Connection subscription error: {e}")
                await asyncio.sleep(5)
    
    @strawberry.subscription
    async def system_metrics_stream(
        self,
        interval: int = 5,
    ) -> AsyncGenerator[SystemMetricsType, None]:
        """
        Stream system metrics at specified intervals.
        
        Args:
            interval: Update interval in seconds (default: 5)
        """
        max_interval = 60
        interval = min(interval, max_interval)
        
        while True:
            try:
                await asyncio.sleep(interval)
                
                from app.monitoring.websocket_monitor import monitor
                metrics = monitor.get_system_metrics()
                
                yield SystemMetricsType(
                    timestamp=metrics.get("timestamp"),
                    total_connections=metrics.get("total_connections", 0),
                    active_connections=metrics.get("active_connections", 0),
                    idle_connections=metrics.get("idle_connections", 0),
                    error_connections=metrics.get("error_connections", 0),
                    total_errors=metrics.get("total_errors", 0),
                    total_messages=metrics.get("total_messages", 0),
                    unique_devices=metrics.get("unique_devices", 0),
                    unique_users=metrics.get("unique_users", 0),
                    cpu_percent=metrics.get("system", {}).get("cpu_percent", 0),
                    memory_percent=metrics.get("system", {}).get("memory_percent", 0),
                    memory_rss_mb=metrics.get("system", {}).get("memory_rss_mb", 0),
                )
                
            except asyncio.CancelledError:
                logger.info("Metrics subscription cancelled")
                break
            except Exception as e:
                logger.error(f"Metrics subscription error: {e}")
                await asyncio.sleep(5)
    
    @strawberry.subscription
    async def device_status_updates(
        self,
        agent_id: Optional[UUID] = None,
    ) -> AsyncGenerator[DeviceType, None]:
        """
        Subscribe to device status updates.
        
        Yields device status changes for specified agent.
        """
        last_seen_status = {}
        
        while True:
            try:
                await asyncio.sleep(2)
                
                from app.monitoring.websocket_monitor import monitor
                
                if agent_id:
                    connections = []
                    for conn in monitor.get_all_connections():
                        if conn.agent_id and str(conn.agent_id) == str(agent_id):
                            connections.append(conn)
                else:
                    connections = monitor.get_all_connections()
                
                for conn in connections:
                    device_status_key = conn.device_id
                    
                    current_online = conn.state.value in ("active", "processing")
                    
                    if device_status_key not in last_seen_status:
                        last_seen_status[device_status_key] = current_online
                    
                    if last_seen_status[device_status_key] != current_online:
                        last_seen_status[device_status_key] = current_online
                        
                        yield DeviceType(
                            id=UUID(conn.device_id) if conn.device_id else UUID("00000000-0000-0000-0000-000000000000"),
                            name=f"Device {conn.device_id[:8]}",
                            mac_address=conn.device_id or "",
                            board="Unknown",
                            firmware_version=None,
                            status="online" if current_online else "offline",
                            last_seen=conn.metrics.get_metrics().get("last_activity"),
                            agent_id=UUID(str(conn.agent_id)) if conn.agent_id else None,
                            user_id=UUID(str(conn.user_id)) if conn.user_id else UUID("00000000-0000-0000-0000-000000000000"),
                            created_at=conn.started_at,
                            is_online=current_online,
                        )
                            
            except asyncio.CancelledError:
                logger.info("Device status subscription cancelled")
                break
            except Exception as e:
                logger.error(f"Device status subscription error: {e}")
                await asyncio.sleep(5)
    
    @strawberry.subscription
    async def alert_stream(
        self,
        levels: Optional[List[str]] = None,
    ) -> AsyncGenerator[strawberry.scalars.JSON, None]:
        """
        Stream system alerts.
        
        Args:
            levels: Filter by alert levels (error, warning, info)
        """
        if levels is None:
            levels = ["error", "warning", "info"]
        
        from app.monitoring.websocket_monitor import monitor
        
        last_alert_count = 0
        
        while True:
            try:
                await asyncio.sleep(1)
                
                all_metrics = monitor.get_all_metrics()
                alerts = all_metrics.get("recent_alerts", [])
                
                if len(alerts) > last_alert_count:
                    new_alerts = alerts[last_alert_count:]
                    last_alert_count = len(alerts)
                    
                    for alert in new_alerts:
                        if alert["level"] in levels:
                            yield alert
            
            except asyncio.CancelledError:
                logger.info("Alert subscription cancelled")
                break
            except Exception as e:
                logger.error(f"Alert subscription error: {e}")
                await asyncio.sleep(5)

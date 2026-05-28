"""
WebSocket Connection Monitor

Provides comprehensive monitoring for WebSocket connections including:
- Connection state tracking
- Performance metrics
- Resource usage
- Connection pooling
- Real-time alerts
"""

import time
import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from collections import defaultdict
import psutil

from app.core.logger import get_logger


logger = get_logger(__name__)


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    IDLE = "idle"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectionMetrics:
    """Metrics for a single connection."""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.started_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.message_count = 0
        self.bytes_received = 0
        self.bytes_sent = 0
        self.errors = 0
        self.reconnects = 0
        self.state_changes = []
        self.latencies = []
        self._lock = threading.Lock()
    
    def record_message(self, direction: str, size: int):
        """Record a message."""
        with self._lock:
            self.message_count += 1
            if direction == "in":
                self.bytes_received += size
            else:
                self.bytes_sent += size
            self.last_activity = datetime.utcnow()
    
    def record_state_change(self, from_state: str, to_state: str):
        """Record a state change."""
        with self._lock:
            self.state_changes.append({
                "from": from_state,
                "to": to_state,
                "timestamp": datetime.utcnow().isoformat(),
            })
    
    def record_error(self):
        """Record an error."""
        with self._lock:
            self.errors += 1
    
    def record_reconnect(self):
        """Record a reconnection."""
        with self._lock:
            self.reconnects += 1
    
    def record_latency(self, latency_ms: float):
        """Record latency measurement."""
        with self._lock:
            self.latencies.append(latency_ms)
            if len(self.latencies) > 1000:
                self.latencies = self.latencies[-1000:]
    
    def get_metrics(self) -> dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            uptime = (datetime.utcnow() - self.started_at).total_seconds()
            avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
            p95_latency = self._percentile(self.latencies, 95) if self.latencies else 0
            p99_latency = self._percentile(self.latencies, 99) if self.latencies else 0
            
            return {
                "connection_id": self.connection_id,
                "uptime_seconds": uptime,
                "last_activity": self.last_activity.isoformat(),
                "message_count": self.message_count,
                "bytes_received": self.bytes_received,
                "bytes_sent": self.bytes_sent,
                "errors": self.errors,
                "reconnects": self.reconnects,
                "state_changes_count": len(self.state_changes),
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "p99_latency_ms": round(p99_latency, 2),
            }
    
    @staticmethod
    def _percentile(data: list[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


@dataclass
class ConnectionInfo:
    """Information about a connection."""
    connection_id: str
    device_id: str
    agent_id: str | None
    user_id: str | None
    client_ip: str
    state: ConnectionState
    metrics: ConnectionMetrics
    started_at: datetime
    agent_info: dict[str, Any] = field(default_factory=dict)


class WebSocketMonitor:
    """
    Centralized WebSocket connection monitoring.
    
    Provides:
    - Connection tracking
    - Performance metrics
    - Resource monitoring
    - Alerting
    """
    
    def __init__(self):
        self._connections: dict[str, ConnectionInfo] = {}
        self._device_connections: dict[str, set[str]] = defaultdict(set)
        self._user_connections: dict[str, set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._metrics_history = []
        self._max_history = 1000
        self._alerts: list[dict[str, Any]] = []
        self._alert_callbacks: list[callable] = []
        self._system_metrics = SystemMetrics()
        
        logger.info("[WebSocketMonitor] Initialized", tag=__name__)
    
    def register_connection(
        self,
        connection_id: str,
        device_id: str,
        client_ip: str,
        agent_id: str | None = None,
        user_id: str | None = None,
    ) -> ConnectionInfo:
        """Register a new connection."""
        with self._lock:
            metrics = ConnectionMetrics(connection_id)
            
            info = ConnectionInfo(
                connection_id=connection_id,
                device_id=device_id,
                agent_id=agent_id,
                user_id=user_id,
                client_ip=client_ip,
                state=ConnectionState.CONNECTING,
                metrics=metrics,
                started_at=datetime.utcnow(),
            )
            
            self._connections[connection_id] = info
            self._device_connections[device_id].add(connection_id)
            
            if user_id:
                self._user_connections[user_id].add(connection_id)
            
            self._log_connection_event("registered", connection_id, device_id)
            
            return info
    
    def update_connection_state(
        self,
        connection_id: str,
        new_state: ConnectionState,
        agent_info: dict[str, Any] | None = None,
    ):
        """Update connection state."""
        with self._lock:
            if connection_id not in self._connections:
                logger.warning(f"Connection {connection_id} not found")
                return
            
            info = self._connections[connection_id]
            old_state = info.state
            
            info.state = new_state
            info.metrics.record_state_change(old_state.value, new_state.value)
            
            if agent_info:
                info.agent_info = agent_info
            
            self._check_state_transitions(connection_id, old_state, new_state)
            
            self._log_connection_event(
                "state_changed",
                connection_id,
                info.device_id,
                {"from": old_state.value, "to": new_state.value},
            )
    
    def record_message(
        self,
        connection_id: str,
        direction: str,
        size: int,
    ):
        """Record message for a connection."""
        with self._lock:
            if connection_id not in self._connections:
                return
            
            self._connections[connection_id].metrics.record_message(direction, size)
    
    def record_error(self, connection_id: str):
        """Record error for a connection."""
        with self._lock:
            if connection_id not in self._connections:
                return
            
            info = self._connections[connection_id]
            info.metrics.record_error()
            info.state = ConnectionState.ERROR
            
            self._trigger_alert(
                "error",
                f"Connection {connection_id} recorded an error",
                {"connection_id": connection_id, "device_id": info.device_id},
            )
    
    def unregister_connection(self, connection_id: str, reason: str = "normal"):
        """Unregister a connection."""
        with self._lock:
            if connection_id not in self._connections:
                return
            
            info = self._connections[connection_id]
            
            self._log_connection_event(
                "unregistered",
                connection_id,
                info.device_id,
                {"reason": reason, "uptime": info.metrics.get_metrics()["uptime_seconds"]},
            )
            
            self._device_connections[info.device_id].discard(connection_id)
            if info.user_id:
                self._user_connections[info.user_id].discard(connection_id)
            
            del self._connections[connection_id]
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get information about a connection."""
        with self._lock:
            return self._connections.get(connection_id)
    
    def get_all_connections(self) -> list[ConnectionInfo]:
        """Get all active connections."""
        with self._lock:
            return list(self._connections.values())
    
    def get_connections_by_state(self, state: ConnectionState) -> list[ConnectionInfo]:
        """Get connections by state."""
        with self._lock:
            return [
                info
                for info in self._connections.values()
                if info.state == state
            ]
    
    def get_device_connections(self, device_id: str) -> list[ConnectionInfo]:
        """Get all connections for a device."""
        with self._lock:
            connection_ids = self._device_connections.get(device_id, set())
            return [
                self._connections[cid]
                for cid in connection_ids
                if cid in self._connections
            ]
    
    def get_user_connections(self, user_id: str) -> list[ConnectionInfo]:
        """Get all connections for a user."""
        with self._lock:
            connection_ids = self._user_connections.get(user_id, set())
            return [
                self._connections[cid]
                for cid in connection_ids
                if cid in self._connections
            ]
    
    def get_system_metrics(self) -> dict[str, Any]:
        """Get system-wide metrics."""
        with self._lock:
            total_connections = len(self._connections)
            state_distribution = defaultdict(int)
            
            for info in self._connections.values():
                state_distribution[info.state.value] += 1
            
            active_connections = sum(
                1 for info in self._connections.values()
                if info.state in (ConnectionState.ACTIVE, ConnectionState.PROCESSING)
            )
            
            total_errors = sum(
                info.metrics.errors for info in self._connections.values()
            )
            
            total_messages = sum(
                info.metrics.message_count for info in self._connections.values()
            )
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "total_connections": total_connections,
                "active_connections": active_connections,
                "idle_connections": state_distribution.get("idle", 0),
                "error_connections": state_distribution.get("error", 0),
                "state_distribution": dict(state_distribution),
                "total_errors": total_errors,
                "total_messages": total_messages,
                "unique_devices": len(self._device_connections),
                "unique_users": len(self._user_connections),
                "system": self._system_metrics.get_metrics(),
                "alerts_count": len(self._alerts),
            }
    
    def get_all_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics."""
        system = self.get_system_metrics()
        connections = [
            info.metrics.get_metrics()
            for info in self._connections.values()
        ]
        
        return {
            "system": system,
            "connections": connections,
            "recent_alerts": self._alerts[-10:],
        }
    
    def register_alert_callback(self, callback: callable):
        """Register an alert callback."""
        self._alert_callbacks.append(callback)
    
    def _trigger_alert(
        self,
        level: str,
        message: str,
        data: dict[str, Any],
    ):
        """Trigger an alert."""
        alert = {
            "level": level,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._alerts.append(alert)
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]
        
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        logger.warning(f"[ALERT] {level}: {message}", **data)
    
    def _check_state_transitions(
        self,
        connection_id: str,
        old_state: ConnectionState,
        new_state: ConnectionState,
    ):
        """Check for concerning state transitions."""
        if new_state == ConnectionState.ERROR:
            self._trigger_alert(
                "error",
                f"Connection {connection_id} entered ERROR state",
                {"connection_id": connection_id},
            )
        
        if (
            old_state == ConnectionState.ACTIVE
            and new_state == ConnectionState.DISCONNECTING
        ):
            info = self._connections.get(connection_id)
            if info and info.metrics.errors > 10:
                self._trigger_alert(
                    "warning",
                    f"Connection {connection_id} disconnected with high error count",
                    {
                        "connection_id": connection_id,
                        "errors": info.metrics.errors,
                    },
                )
    
    def _log_connection_event(
        self,
        event: str,
        connection_id: str,
        device_id: str,
        extra: dict[str, Any] | None = None,
    ):
        """Log a connection event."""
        log_data = {
            "tag": "websocket_monitor",
            "event": event,
            "connection_id": connection_id,
            "device_id": device_id,
        }
        if extra:
            log_data.update(extra)
        
        logger.debug(f"[WS Event] {event}", **log_data)


class SystemMetrics:
    """System-level metrics."""
    
    def __init__(self):
        self._process = psutil.Process()
        self._last_cpu_times = None
        self._last_measure_time = None
    
    def get_metrics(self) -> dict[str, Any]:
        """Get current system metrics."""
        try:
            cpu_percent = self._process.cpu_percent(interval=0.1)
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            
            io_counters = self._process.io_counters()
            
            threads = self._process.num_threads()
            open_files = len(self._process.open_files())
            
            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "memory_vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "memory_percent": round(memory_percent, 2),
                "io_read_bytes": io_counters.read_bytes,
                "io_write_bytes": io_counters.write_bytes,
                "threads": threads,
                "open_files": open_files,
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}


monitor = WebSocketMonitor()

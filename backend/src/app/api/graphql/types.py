"""
GraphQL Types for Xiaozhi Platform

Defines GraphQL types using Strawberry for the Xiaozhi AI IoT platform.
"""

import strawberry
from typing import Optional, List
from datetime import datetime
from uuid import UUID


@strawberry.enum
class ConnectionState:
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    ACTIVE = "active"
    PROCESSING = "processing"
    IDLE = "idle"
    DISCONNECTED = "disconnected"


@strawberry.enum
class DeviceStatus:
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


@strawberry.type
class UserType:
    id: UUID
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]


@strawberry.type
class AgentType:
    id: UUID
    name: str
    description: Optional[str]
    prompt: str
    voice_id: Optional[str]
    tts_type: str
    asr_type: str
    llm_type: str
    vad_type: str
    is_active: bool
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    device_count: int
    knowledge_base_count: int


@strawberry.type
class DeviceType:
    id: UUID
    name: str
    mac_address: str
    board: str
    firmware_version: Optional[str]
    status: DeviceStatus
    last_seen: Optional[datetime]
    agent_id: Optional[UUID]
    user_id: UUID
    created_at: datetime
    is_online: bool


@strawberry.type
class KnowledgeBaseType:
    id: UUID
    name: str
    description: Optional[str]
    source_type: str
    document_count: int
    user_id: UUID
    agent_id: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool


@strawberry.type
class SubscriptionType:
    id: UUID
    user_id: UUID
    plan: str
    status: str
    started_at: datetime
    expires_at: datetime
    features: List[str]


@strawberry.type
class ConnectionMetricsType:
    connection_id: str
    uptime_seconds: float
    message_count: int
    bytes_received: int
    bytes_sent: int
    errors: int
    reconnects: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


@strawberry.type
class ConnectionInfoType:
    connection_id: str
    device_id: str
    agent_id: Optional[str]
    user_id: Optional[str]
    client_ip: str
    state: ConnectionState
    metrics: ConnectionMetricsType
    started_at: datetime
    last_activity: datetime


@strawberry.type
class SystemMetricsType:
    timestamp: datetime
    total_connections: int
    active_connections: int
    idle_connections: int
    error_connections: int
    total_errors: int
    total_messages: int
    unique_devices: int
    unique_users: int
    cpu_percent: float
    memory_percent: float
    memory_rss_mb: float


@strawberry.type
class WebSocketMonitorType:
    system: SystemMetricsType
    connections: List[ConnectionInfoType]
    alert_count: int


@strawberry.type
class RateLimitTierType:
    name: str
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int
    concurrent_connections: int


@strawberry.type
class RateLimitStatusType:
    allowed: bool
    limit: int
    remaining: int
    reset_time: int
    retry_after: Optional[int]
    tier: str
    limit_type: str


@strawberry.type
class HealthCheckType:
    status: str
    version: str
    environment: str
    timestamp: datetime
    database: str
    redis: str
    mqtt: str


@strawberry.type
class APIResponseType:
    success: bool
    message: Optional[str]
    data: Optional[strawberry.scalars.JSON]


@strawberry.type
class PaginatedAgentsType:
    items: List[AgentType]
    total: int
    page: int
    per_page: int
    total_pages: int


@strawberry.type
class PaginatedDevicesType:
    items: List[DeviceType]
    total: int
    page: int
    per_page: int
    total_pages: int

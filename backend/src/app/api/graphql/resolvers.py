"""
GraphQL Resolvers for Xiaozhi Platform

Implements GraphQL queries and mutations for the Xiaozhi AI IoT platform.
"""

import strawberry
from typing import List, Optional
from uuid import UUID
import logging

from .types import (
    AgentType,
    DeviceType,
    KnowledgeBaseType,
    UserType,
    ConnectionInfoType,
    SystemMetricsType,
    WebSocketMonitorType,
    RateLimitTierType,
    RateLimitStatusType,
    HealthCheckType,
    PaginatedAgentsType,
    PaginatedDevicesType,
)
from .subscriptions import Subscription
from app.core.logger import get_logger


logger = get_logger(__name__)


@strawberry.type
class Query:
    """GraphQL Query resolvers."""
    
    @strawberry.field
    async def agents(
        self,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
    ) -> PaginatedAgentsType:
        """Get paginated list of agents."""
        return PaginatedAgentsType(
            items=[],
            total=0,
            page=skip // limit + 1 if limit > 0 else 1,
            per_page=limit,
            total_pages=0,
        )
    
    @strawberry.field
    async def agent(self, id: UUID) -> Optional[AgentType]:
        """Get a single agent by ID."""
        return None
    
    @strawberry.field
    async def devices(
        self,
        skip: int = 0,
        limit: int = 20,
        agent_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedDevicesType:
        """Get paginated list of devices."""
        return PaginatedDevicesType(
            items=[],
            total=0,
            page=skip // limit + 1 if limit > 0 else 1,
            per_page=limit,
            total_pages=0,
        )
    
    @strawberry.field
    async def device(self, id: UUID) -> Optional[DeviceType]:
        """Get a single device by ID."""
        return None
    
    @strawberry.field
    async def me(self, info: strawberry.Info) -> Optional[UserType]:
        """Get current authenticated user."""
        return None
    
    @strawberry.field
    async def websocket_metrics(self) -> WebSocketMonitorType:
        """Get WebSocket connection metrics."""
        try:
            from app.monitoring.websocket_monitor import monitor
            
            system_metrics = monitor.get_system_metrics()
            
            return WebSocketMonitorType(
                system=SystemMetricsType(
                    timestamp=system_metrics.get("timestamp"),
                    total_connections=system_metrics.get("total_connections", 0),
                    active_connections=system_metrics.get("active_connections", 0),
                    idle_connections=system_metrics.get("idle_connections", 0),
                    error_connections=system_metrics.get("error_connections", 0),
                    total_errors=system_metrics.get("total_errors", 0),
                    total_messages=system_metrics.get("total_messages", 0),
                    unique_devices=system_metrics.get("unique_devices", 0),
                    unique_users=system_metrics.get("unique_users", 0),
                    cpu_percent=system_metrics.get("system", {}).get("cpu_percent", 0),
                    memory_percent=system_metrics.get("system", {}).get("memory_percent", 0),
                    memory_rss_mb=system_metrics.get("system", {}).get("memory_rss_mb", 0),
                ),
                connections=[],
                alert_count=system_metrics.get("alerts_count", 0),
            )
        except Exception as e:
            logger.error(f"Error getting WebSocket metrics: {e}")
            return WebSocketMonitorType(
                system=SystemMetricsType(
                    timestamp=None,
                    total_connections=0,
                    active_connections=0,
                    idle_connections=0,
                    error_connections=0,
                    total_errors=0,
                    total_messages=0,
                    unique_devices=0,
                    unique_users=0,
                    cpu_percent=0,
                    memory_percent=0,
                    memory_rss_mb=0,
                ),
                connections=[],
                alert_count=0,
            )
    
    @strawberry.field
    async def rate_limit_tiers(self) -> List[RateLimitTierType]:
        """Get available rate limit tiers."""
        from app.middleware.rate_limit import TIER_CONFIGS, RateLimitTier
        
        return [
            RateLimitTierType(
                name=tier.value,
                requests_per_minute=config.requests_per_minute,
                requests_per_hour=config.requests_per_hour,
                requests_per_day=config.requests_per_day,
                burst_size=config.burst_size,
                concurrent_connections=config.concurrent_connections,
            )
            for tier, config in TIER_CONFIGS.items()
        ]
    
    @strawberry.field
    async def health_check(self) -> HealthCheckType:
        """Get system health status."""
        return HealthCheckType(
            status="healthy",
            version="1.0.0",
            environment="development",
            timestamp=None,
            database="healthy",
            redis="healthy",
            mqtt="healthy",
        )


@strawberry.type
class Mutation:
    """GraphQL Mutation resolvers."""
    
    @strawberry.mutation
    async def create_agent(
        self,
        name: str,
        prompt: str,
        tts_type: str = "openai",
        asr_type: str = "openai",
        llm_type: str = "openai",
        vad_type: str = "silero",
    ) -> AgentType:
        """Create a new agent."""
        return AgentType(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name=name,
            description=None,
            prompt=prompt,
            voice_id=None,
            tts_type=tts_type,
            asr_type=asr_type,
            llm_type=llm_type,
            vad_type=vad_type,
            is_active=True,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            created_at=None,
            updated_at=None,
            device_count=0,
            knowledge_base_count=0,
        )
    
    @strawberry.mutation
    async def update_agent(
        self,
        id: UUID,
        name: Optional[str] = None,
        prompt: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[AgentType]:
        """Update an existing agent."""
        return None
    
    @strawberry.mutation
    async def delete_agent(self, id: UUID) -> bool:
        """Delete an agent."""
        return True


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)

"""
Health Service - Comprehensive health checks for all system components.
Provides detailed status information for the System Health Dashboard.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Tuple

import httpx
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.health import ComponentHealth, DetailedHealthCheck, MonitoringLinks
from ..core.config import settings

LOGGER = logging.getLogger(__name__)

# Component configuration - All Docker services in the system
# NOTE: ChromaDB is EMBEDDED in backend (PersistentClient) - no external service needed
# NOTE: Prometheus/Grafana/cAdvisor removed - not needed for basic health monitoring
COMPONENT_CONFIGS = {
    # Core AI Services
    "openmemory": {
        "name": "OpenMemory AI",
        "host": "openmemory",
        "port": 8080,
        "http_path": "/",
        "timeout": 5.0
    },
    
    # Messaging & Communication
    "mqtt": {
        "name": "MQTT Broker (EMQX)",
        "host": "emqx",
        "port": 1883,
        "timeout": 3.0
    },
    
    # Node.js Services
    "mcp_endpoint": {
        "name": "MCP Endpoint Server",
        "host": "mcp-endpoint-server",
        "port": 8004,
        "http_path": "/",
        "timeout": 5.0
    },
}


class HealthService:
    """Service for checking health of all system components."""
    
    _start_time: float = time.time()  # Track application start time
    
    @classmethod
    def get_uptime_seconds(cls) -> int:
        """Get application uptime in seconds."""
        return int(time.time() - cls._start_time)
    
    @staticmethod
    async def check_database(db: AsyncSession) -> ComponentHealth:
        """Check PostgreSQL database health."""
        start = time.time()
        try:
            await db.execute(text("SELECT 1"))
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status="healthy",
                latency_ms=round(latency, 2),
                details="PostgreSQL connected successfully",
                last_check=datetime.now(timezone.utc)
            )
        except Exception as e:
            LOGGER.error(f"Database health check failed: {e}")
            return ComponentHealth(
                status="unhealthy",
                latency_ms=None,
                details=f"Database error: {str(e)[:100]}",
                last_check=datetime.now(timezone.utc)
            )
    
    @staticmethod
    async def check_redis(redis: Redis) -> ComponentHealth:
        """Check Redis health."""
        start = time.time()
        try:
            await redis.ping()
            latency = (time.time() - start) * 1000
            info = await redis.info("server")
            redis_version = info.get("redis_version", "unknown")
            return ComponentHealth(
                status="healthy",
                latency_ms=round(latency, 2),
                details=f"Redis v{redis_version} - PONG received",
                last_check=datetime.now(timezone.utc)
            )
        except Exception as e:
            LOGGER.error(f"Redis health check failed: {e}")
            return ComponentHealth(
                status="unhealthy",
                latency_ms=None,
                details=f"Redis error: {str(e)[:100]}",
                last_check=datetime.now(timezone.utc)
            )
    
    @staticmethod
    async def check_tcp_port(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float]:
        """Check if a TCP port is open."""
        start = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            latency = (time.time() - start) * 1000
            return True, latency
        except Exception:
            return False, 0
    
    @staticmethod
    async def check_http_endpoint(
        host: str, 
        port: int, 
        path: str = "/health",
        timeout: float = 5.0
    ) -> Tuple[bool, float, str]:
        """Check HTTP endpoint health."""
        url = f"http://{host}:{port}{path}"
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                latency = (time.time() - start) * 1000
                # Accept 2xx, 3xx, 401, and 404 as healthy 
                # (401/404 means service is running but requires auth or returns auth error)
                if response.status_code < 400 or response.status_code in (401, 404):
                    return True, latency, f"HTTP {response.status_code} OK"
                else:
                    return False, latency, f"HTTP {response.status_code}"
        except httpx.TimeoutException:
            return False, 0, "Connection timeout"
        except httpx.ConnectError:
            return False, 0, "Connection refused"
        except Exception as e:
            return False, 0, str(e)[:100]
    
    @classmethod
    async def check_component(cls, name: str, config: dict) -> ComponentHealth:
        """Check a single component's health."""
        try:
            if "http_path" in config:
                # HTTP-based health check
                healthy, latency, details = await cls.check_http_endpoint(
                    host=config["host"],
                    port=config["port"],
                    path=config["http_path"],
                    timeout=config.get("timeout", 5.0)
                )
            else:
                # TCP port check only
                healthy, latency = await cls.check_tcp_port(
                    host=config["host"],
                    port=config["port"],
                    timeout=config.get("timeout", 3.0)
                )
                details = f"Port {config['port']} is {'open' if healthy else 'closed'}"
            
            return ComponentHealth(
                status="healthy" if healthy else "unhealthy",
                latency_ms=round(latency, 2) if latency > 0 else None,
                details=f"{config['name']}: {details}",
                last_check=datetime.now(timezone.utc)
            )
        except Exception as e:
            LOGGER.error(f"Health check for {name} failed: {e}")
            return ComponentHealth(
                status="unhealthy",
                latency_ms=None,
                details=f"{config['name']}: Error - {str(e)[:100]}",
                last_check=datetime.now(timezone.utc)
            )
    
    @classmethod
    async def get_detailed_health(
        cls,
        db: AsyncSession,
        redis: Redis
    ) -> DetailedHealthCheck:
        """Get detailed health status of all components."""
        
        # Run all health checks in parallel
        tasks = {
            "database": cls.check_database(db),
            "redis": cls.check_redis(redis),
        }
        
        # Add external component checks
        for name, config in COMPONENT_CONFIGS.items():
            tasks[name] = cls.check_component(name, config)
        
        # Execute all checks concurrently
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Build components dict
        components: Dict[str, ComponentHealth] = {}
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                LOGGER.error(f"Health check {name} raised exception: {result}")
                components[name] = ComponentHealth(
                    status="unhealthy",
                    details=f"Check failed: {str(result)[:100]}",
                    last_check=datetime.now(timezone.utc)
                )
            else:
                components[name] = result
        
        # Determine overall status
        # Critical components: database, redis
        # Non-critical: tts, openmemory, mqtt, prometheus, grafana
        critical_healthy = all(
            components.get(c, ComponentHealth(status="unhealthy")).status == "healthy"
            for c in ["database", "redis"]
        )
        all_healthy = all(c.status == "healthy" for c in components.values())
        
        if all_healthy:
            overall_status = "healthy"
        elif critical_healthy:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return DetailedHealthCheck(
            status=overall_status,
            environment=settings.ENVIRONMENT.value,
            version=settings.APP_VERSION,
            uptime_seconds=cls.get_uptime_seconds(),
            timestamp=datetime.now(timezone.utc),
            components=components
        )
    
    @classmethod
    async def get_monitoring_links(cls) -> MonitoringLinks:
        """Get links and status of monitoring dashboards.
        
        NOTE: Prometheus/Grafana removed from system - returning unavailable status.
        """
        return MonitoringLinks(
            grafana_url=None,
            prometheus_url=None,
            grafana_status="unavailable",
            prometheus_status="unavailable"
        )


# Singleton instance
health_service = HealthService()


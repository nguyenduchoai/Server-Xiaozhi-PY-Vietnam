import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.db.database import async_get_db
from ...core.health import check_database_health, check_redis_health
from ...core.schemas import HealthCheck, ReadyCheck
from ...core.utils.cache import async_get_redis
from ...schemas.health import DetailedHealthCheck, MonitoringLinks
from ...services.health_service import health_service
from ..dependencies import get_current_superuser

router = APIRouter(tags=["health"])

STATUS_HEALTHY = "healthy"
STATUS_UNHEALTHY = "unhealthy"

LOGGER = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheck)
async def health():
    """Basic health check - no authentication required."""
    http_status = status.HTTP_200_OK
    response = {
        "status": STATUS_HEALTHY,
        "environment": settings.ENVIRONMENT.value,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    return JSONResponse(status_code=http_status, content=response)


@router.get("/ready", response_model=ReadyCheck)
async def ready(
    redis: Annotated[Redis, Depends(async_get_redis)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Readiness check for load balancers - checks database and redis."""
    database_status = await check_database_health(db=db)
    LOGGER.debug(f"Database health check status: {database_status}")
    redis_status = await check_redis_health(redis=redis)
    LOGGER.debug(f"Redis health check status: {redis_status}")

    overall_status = (
        STATUS_HEALTHY if database_status and redis_status else STATUS_UNHEALTHY
    )
    http_status = (
        status.HTTP_200_OK
        if overall_status == STATUS_HEALTHY
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    response = {
        "status": overall_status,
        "environment": settings.ENVIRONMENT.value,
        "version": settings.APP_VERSION,
        "app": STATUS_HEALTHY,
        "database": STATUS_HEALTHY if database_status else STATUS_UNHEALTHY,
        "redis": STATUS_HEALTHY if redis_status else STATUS_UNHEALTHY,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    return JSONResponse(status_code=http_status, content=response)


@router.get("/health/detailed", response_model=DetailedHealthCheck)
async def detailed_health(
    redis: Annotated[Redis, Depends(async_get_redis)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    _current_user=Depends(get_current_superuser),
):
    """
    Detailed health check for all system components.
    
    Requires admin authentication.
    
    Returns status of:
    - Database (PostgreSQL)
    - Redis
    - MQTT Broker
    - OpenMemory
    - Prometheus
    - Grafana
    """
    detailed = await health_service.get_detailed_health(db=db, redis=redis)
    
    http_status = (
        status.HTTP_200_OK
        if detailed.status in ["healthy", "degraded"]
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    return JSONResponse(
        status_code=http_status,
        content=detailed.model_dump(mode="json")
    )


@router.get("/health/monitoring-links", response_model=MonitoringLinks)
async def monitoring_links(
    _current_user=Depends(get_current_superuser),
):
    """
    Get links to external monitoring dashboards (Grafana, Prometheus).
    
    Requires admin authentication.
    """
    links = await health_service.get_monitoring_links()
    return links

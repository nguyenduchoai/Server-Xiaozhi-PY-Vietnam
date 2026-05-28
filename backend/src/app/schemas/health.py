"""
Health check response schemas for detailed system monitoring.
"""
from datetime import datetime
from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    """Health status of a single system component."""
    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        description="Component health status"
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Response latency in milliseconds"
    )
    details: Optional[str] = Field(
        default=None,
        description="Additional details about the component status"
    )
    last_check: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the last health check"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "latency_ms": 5.2,
                "details": "PostgreSQL connected successfully",
                "last_check": "2026-01-14T02:00:00Z"
            }
        }


class DetailedHealthCheck(BaseModel):
    """Detailed health check response with all component statuses."""
    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        description="Overall system health status"
    )
    environment: str = Field(
        description="Current environment (development, staging, production)"
    )
    version: str = Field(
        description="Application version"
    )
    uptime_seconds: int = Field(
        description="Application uptime in seconds"
    )
    timestamp: datetime = Field(
        description="Current timestamp"
    )
    components: Dict[str, ComponentHealth] = Field(
        description="Health status of individual components"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "environment": "production",
                "version": "1.0.0",
                "uptime_seconds": 86400,
                "timestamp": "2026-01-14T02:00:00Z",
                "components": {
                    "database": {
                        "status": "healthy",
                        "latency_ms": 5.2,
                        "details": "PostgreSQL connected"
                    },
                    "redis": {
                        "status": "healthy",
                        "latency_ms": 2.1,
                        "details": "Redis PONG received"
                    }
                }
            }
        }


class MonitoringLinks(BaseModel):
    """Links to external monitoring dashboards."""
    grafana_url: Optional[str] = Field(
        default=None,
        description="URL to Grafana dashboard"
    )
    prometheus_url: Optional[str] = Field(
        default=None,
        description="URL to Prometheus dashboard"
    )
    grafana_status: Literal["available", "unavailable"] = Field(
        default="unavailable",
        description="Grafana availability status"
    )
    prometheus_status: Literal["available", "unavailable"] = Field(
        default="unavailable",
        description="Prometheus availability status"
    )

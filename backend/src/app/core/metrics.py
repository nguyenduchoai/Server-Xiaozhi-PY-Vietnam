"""
Prometheus Metrics Configuration

Provides comprehensive metrics collection for:
- HTTP request duration and count
- Database query metrics
- WebSocket connection metrics
- Cache hit/miss rates
- Business metrics (agents, devices, users)
- System resource metrics

Usage:
    from app.core.metrics import (
        http_request_duration,
        db_query_duration,
        ws_connections_active,
        cache_hits_total,
    )
"""

from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
from typing import Callable, Optional
import time
from functools import wraps


REGISTRY = CollectorRegistry(auto_describe=True)

# ===== HTTP Metrics =====

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method", "endpoint"],
)

# ===== Database Metrics =====

DB_QUERIES_TOTAL = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "table", "status"],
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

DB_POOL_SIZE = Gauge(
    "db_pool_size",
    "Database connection pool size",
    ["state"],  # total, checked_out, overflow
)

DB_POOL_WAIT_TIME = Histogram(
    "db_pool_wait_seconds",
    "Time spent waiting for connection from pool",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

# ===== WebSocket Metrics =====

WS_CONNECTIONS_ACTIVE = Gauge(
    "ws_connections_active",
    "Number of active WebSocket connections",
    ["device_type"],
)

WS_CONNECTIONS_TOTAL = Counter(
    "ws_connections_total",
    "Total WebSocket connections established",
    ["device_type", "status"],
)

WS_MESSAGES_TOTAL = Counter(
    "ws_messages_total",
    "Total WebSocket messages",
    ["direction", "message_type"],  # direction: sent/received, type: audio/control/data
)

WS_MESSAGE_DURATION = Histogram(
    "ws_message_duration_seconds",
    "WebSocket message processing duration",
    ["message_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

WS_AUDIO_BUFFER_SIZE = Gauge(
    "ws_audio_buffer_size",
    "Size of WebSocket audio buffer",
    ["connection_id"],
)

# ===== Cache Metrics =====

CACHE_OPERATIONS_TOTAL = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["operation", "cache_key", "status"],  # operation: get/set/delete, status: hit/miss/error
)

CACHE_HIT_RATIO = Gauge(
    "cache_hit_ratio",
    "Cache hit ratio (rolling)",
    ["cache_key"],
)

CACHE_LATENCY = Histogram(
    "cache_latency_seconds",
    "Cache operation latency",
    ["operation"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05),
)

# ===== Business Metrics =====

AGENTS_TOTAL = Gauge(
    "agents_total",
    "Total number of agents",
    ["status"],  # active, inactive, error
)

DEVICES_TOTAL = Gauge(
    "devices_total",
    "Total number of devices",
    ["status", "type"],  # status: online/offline/error, type: esp32/mobile/web
)

USERS_TOTAL = Gauge(
    "users_total",
    "Total number of users",
    ["subscription_tier"],  # free, pro, enterprise
)

MCP_SERVERS_TOTAL = Gauge(
    "mcp_servers_total",
    "Total number of MCP servers",
    ["status"],
)

# ===== AI Module Metrics =====

AI_MODULE_CALLS_TOTAL = Counter(
    "ai_module_calls_total",
    "Total AI module calls",
    ["module", "provider", "status"],  # module: tts/asr/vad/llm/intent
)

AI_MODULE_LATENCY = Histogram(
    "ai_module_latency_seconds",
    "AI module call latency",
    ["module", "provider"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

AI_MODULE_ERRORS = Counter(
    "ai_module_errors_total",
    "Total AI module errors",
    ["module", "error_type"],
)

LLM_TOKEN_USAGE = Counter(
    "llm_token_usage_total",
    "Total LLM token usage",
    ["model", "token_type"],  # token_type: input/output
)

TTS_CHARACTERS_USED = Counter(
    "tts_characters_used_total",
    "Total TTS characters converted",
    ["provider"],
)

ASR_AUDIO_MINUTES = Counter(
    "asr_audio_minutes_total",
    "Total ASR audio minutes processed",
    ["provider"],
)

# ===== Rate Limiting Metrics =====

RATE_LIMIT_HITS_TOTAL = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits",
    ["tier", "limit_type"],  # tier: free/pro/enterprise, limit_type: rpm/hour/day
)

RATE_LIMIT_REJECTED_TOTAL = Counter(
    "rate_limit_rejected_total",
    "Total requests rejected due to rate limiting",
    ["tier", "endpoint"],
)

# ===== Error Metrics =====

ERRORS_TOTAL = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "severity"],  # severity: warning/error/critical
)

EXCEPTION_TOTAL = Counter(
    "exceptions_total",
    "Total exceptions by type",
    ["exception_type", "module"],
)

# ===== System Metrics =====

SYSTEM_UPTIME = Gauge(
    "system_uptime_seconds",
    "System uptime in seconds",
)

PROCESS_MEMORY_BYTES = Gauge(
    "process_memory_bytes",
    "Process memory usage in bytes",
    ["metric_type"],  # rss, vms, heap
)

PROCESS_CPU_PERCENT = Gauge(
    "process_cpu_percent",
    "Process CPU usage percentage",
)

# ===== Health Metrics =====

HEALTH_CHECK_TOTAL = Counter(
    "health_check_total",
    "Total health check calls",
    ["check_type", "status"],  # check_type: liveness/readiness, status: healthy/unhealthy
)

HEALTH_CHECK_DURATION = Histogram(
    "health_check_duration_seconds",
    "Health check duration",
    ["check_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
)

# ===== Queue Metrics =====

QUEUE_SIZE = Gauge(
    "queue_size",
    "Queue size",
    ["queue_name"],
)

QUEUE_PUBLISHED_TOTAL = Counter(
    "queue_published_total",
    "Total messages published to queue",
    ["queue_name"],
)

QUEUE_CONSUMED_TOTAL = Counter(
    "queue_consumed_total",
    "Total messages consumed from queue",
    ["queue_name", "status"],  # status: success/error
)

# ===== Helper Functions =====

def track_request_duration(method: str, endpoint: str):
    """Decorator to track HTTP request duration."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            endpoint_clean = endpoint.replace("{", "{").replace("}", "}")  # Normalize path params
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint_clean).inc()
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint_clean).observe(duration)
                HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint_clean, status_code="500").inc()
                raise
            finally:
                HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint_clean).dec()
        return wrapper
    return decorator


def track_db_query(operation: str, table: str):
    """Decorator to track database query metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                DB_QUERY_DURATION.labels(operation=operation, table=table).observe(duration)
                DB_QUERIES_TOTAL.labels(operation=operation, table=table, status="success").inc()
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                DB_QUERY_DURATION.labels(operation=operation, table=table).observe(duration)
                DB_QUERIES_TOTAL.labels(operation=operation, table=table, status="error").inc()
                raise
        return wrapper
    return decorator


def track_cache_operation(operation: str, cache_key: str):
    """Track cache operation hit/miss."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                CACHE_LATENCY.labels(operation=operation).observe(duration)
                is_hit = result is not None
                CACHE_OPERATIONS_TOTAL.labels(
                    operation=operation,
                    cache_key=cache_key,
                    status="hit" if is_hit else "miss"
                ).inc()
                return result
            except Exception as e:
                CACHE_OPERATIONS_TOTAL.labels(
                    operation=operation,
                    cache_key=cache_key,
                    status="error"
                ).inc()
                raise
        return wrapper
    return decorator


class MetricsMiddleware:
    """Middleware to automatically track HTTP request metrics."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]
        
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        start_time = time.perf_counter()

        status_code = "500"

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start_time
            HTTP_REQUEST_DURATION.labels(method=method, endpoint=path).observe(duration)
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status_code=status_code).inc()
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).dec()


async def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get Prometheus metrics content type."""
    return CONTENT_TYPE_LATEST
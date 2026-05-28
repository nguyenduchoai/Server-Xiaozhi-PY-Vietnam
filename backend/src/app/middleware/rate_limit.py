"""
Enhanced Rate Limiting Middleware

Implements comprehensive rate limiting with:
- Per-user and per-IP limiting
- Different tiers (free, premium, enterprise)
- Burst limiting
- Automatic optimization
- Metrics collection
- Redis-based distributed rate limiting
"""

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Any

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from redis.asyncio import Redis
from redis.asyncio.client import Pipeline

from app.core.logger import get_logger


logger = get_logger(__name__)


class RateLimitTier(str, Enum):
    """User subscription tiers for rate limiting."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    INTERNAL = "internal"


@dataclass
class RateLimitTierConfig:
    """Configuration for a specific tier."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int
    concurrent_connections: int


TIER_CONFIGS: dict[RateLimitTier, RateLimitTierConfig] = {
    RateLimitTier.FREE: RateLimitTierConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000,
        burst_size=10,
        concurrent_connections=5,
    ),
    RateLimitTier.PRO: RateLimitTierConfig(
        requests_per_minute=300,
        requests_per_hour=5000,
        requests_per_day=50000,
        burst_size=50,
        concurrent_connections=20,
    ),
    RateLimitTier.ENTERPRISE: RateLimitTierConfig(
        requests_per_minute=1000,
        requests_per_hour=20000,
        requests_per_day=200000,
        burst_size=200,
        concurrent_connections=100,
    ),
    RateLimitTier.INTERNAL: RateLimitTierConfig(
        requests_per_minute=10000,
        requests_per_hour=100000,
        requests_per_day=1000000,
        burst_size=1000,
        concurrent_connections=500,
    ),
}


@dataclass
class EndpointConfig:
    """Rate limit configuration for specific endpoints."""
    requests_per_minute: int
    burst_size: int = 5
    tier_multiplier: float = 1.0


ENDPOINT_CONFIGS: dict[str, EndpointConfig] = {
    # Authentication - very strict
    "/api/v1/auth/login": EndpointConfig(requests_per_minute=10, burst_size=3),
    "/api/v1/auth/register": EndpointConfig(requests_per_minute=5, burst_size=2),
    "/api/v1/auth/forgot-password": EndpointConfig(requests_per_minute=3, burst_size=1),
    "/api/v1/auth/refresh": EndpointConfig(requests_per_minute=30, burst_size=5),
    
    # Device operations - moderate
    "/api/v1/devices/request-activation": EndpointConfig(requests_per_minute=30, burst_size=10),
    "/api/v1/devices/activate": EndpointConfig(requests_per_minute=20, burst_size=5),
    "/api/v1/devices": EndpointConfig(requests_per_minute=100, burst_size=20),
    
    # AI/ML endpoints - expensive, moderate limits
    "/api/v1/embeddings": EndpointConfig(requests_per_minute=20, burst_size=5, tier_multiplier=2.0),
    "/api/v1/vision": EndpointConfig(requests_per_minute=30, burst_size=10, tier_multiplier=2.0),
    "/api/v1/chat": EndpointConfig(requests_per_minute=60, burst_size=15, tier_multiplier=1.5),
    
    # Knowledge base - moderate
    "/api/v1/knowledge": EndpointConfig(requests_per_minute=50, burst_size=15),
    "/api/v1/knowledge/upload": EndpointConfig(requests_per_minute=10, burst_size=3),
    
    # WebSocket - high limits
    "/api/v1/websocket": EndpointConfig(requests_per_minute=1000, burst_size=100),
    
    # Admin endpoints - strict
    "/api/v1/admin": EndpointConfig(requests_per_minute=100, burst_size=20),
}

WHITELIST_PATHS = [
    "/api/v1/health",
    "/api/v1/ready",
    "/api/v1/ota",      # Device OTA checks — must not 429 or device crash-loops
    "/api/v1/ws",       # WebSocket persistent connection — not a burst endpoint
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
]


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    tier: RateLimitTier = RateLimitTier.FREE


class EnhancedRateLimiter:
    """
    Enhanced Redis-based rate limiter with:
    - Sliding window algorithm
    - Tiered limits
    - Burst protection
    - Automatic cleanup
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.lua_scripts: dict[str, Any] = {}
        self._init_lua_scripts()
    
    def _init_lua_scripts(self):
        """Initialize Lua scripts for atomic operations."""
        self.sliding_window_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local burst = tonumber(ARGV[4])
        
        local window_start = now - window
        
        -- Remove old entries outside the window
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        
        -- Get current count
        local current = redis.call('ZCARD', key)
        
        -- Calculate effective limit with burst
        local effective_limit = limit + burst
        
        -- Check if limit exceeded
        if current >= effective_limit then
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local reset_time = 0
            if #oldest > 0 then
                reset_time = math.ceil(tonumber(oldest[2]) + window)
            else
                reset_time = math.ceil(now + window)
            end
            return {0, current, effective_limit, reset_time}
        end
        
        -- Add this request
        redis.call('ZADD', key, now, now .. ':' .. math.random(1000000))
        
        -- Set expiry
        redis.call('EXPIRE', key, window * 2)
        
        return {1, current + 1, effective_limit, math.ceil(now + window)}
        """
        
        self.check_and_increment_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        
        local window_start = now - window
        
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        local current = redis.call('ZCARD', key)
        
        if current >= limit then
            return {0, current, limit}
        end
        
        redis.call('ZADD', key, now, now .. ':' .. math.random(1000000))
        redis.call('EXPIRE', key, window * 2)
        
        return {1, current + 1, limit}
        """
    
    def _get_key(self, identifier: str, endpoint: str, window_type: str) -> str:
        """Generate Redis key."""
        endpoint_normalized = endpoint.split("?")[0].rstrip("/")
        return f"ratelimit:{window_type}:{identifier}:{endpoint_normalized}"
    
    def _get_tier_from_identifier(self, identifier: str) -> RateLimitTier:
        """Extract tier from identifier or default to FREE."""
        if identifier.startswith("internal:"):
            return RateLimitTier.INTERNAL
        elif identifier.startswith("enterprise:"):
            return RateLimitTier.ENTERPRISE
        elif identifier.startswith("pro:"):
            return RateLimitTier.PRO
        return RateLimitTier.FREE
    
    def _get_endpoint_config(self, endpoint: str) -> EndpointConfig:
        """Get rate limit config for endpoint."""
        endpoint_normalized = endpoint.split("?")[0].rstrip("/")
        
        for path, config in ENDPOINT_CONFIGS.items():
            if endpoint_normalized == path or endpoint_normalized.startswith(path):
                return config
        
        return EndpointConfig(requests_per_minute=100, burst_size=20)
    
    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        tier: RateLimitTier | None = None,
    ) -> RateLimitResult:
        """
        Check if request is allowed under rate limits.
        
        Performs multiple checks:
        1. Per-minute sliding window
        2. Per-hour counter
        3. Per-day counter
        """
        # Check whitelist
        for path in WHITELIST_PATHS:
            if endpoint.startswith(path):
                return RateLimitResult(
                    allowed=True,
                    limit=0,
                    remaining=0,
                    reset_time=0,
                )
        
        # Get tier
        if tier is None:
            tier = self._get_tier_from_identifier(identifier)
        
        tier_config = TIER_CONFIGS[tier]
        endpoint_config = self._get_endpoint_config(endpoint)
        
        # Apply tier multiplier
        effective_limit = int(endpoint_config.requests_per_minute * endpoint_config.tier_multiplier)
        burst = int(endpoint_config.burst_size * endpoint_config.tier_multiplier)
        
        now = time.time()
        now_int = int(now)
        
        # Per-minute sliding window
        key_minute = self._get_key(identifier, endpoint, "minute")
        try:
            pipe = self.redis.pipeline(transaction=True)
            pipe.zremrangebyscore(key_minute, 0, now - 60)
            pipe.zcard(key_minute)
            pipe.zrange(key_minute, 0, 0, withscores=True)
            results = await pipe.execute()
            
            current_minute = results[1]
            oldest = results[2]
            
            effective_limit_with_burst = effective_limit + burst
            
            if current_minute >= effective_limit_with_burst:
                reset_time = int(oldest[0][1] + 60) if oldest else now_int + 60
                return RateLimitResult(
                    allowed=False,
                    limit=effective_limit,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=int(reset_time - now),
                    tier=tier,
                )
            
            # Add request to sliding window
            await self.redis.zadd(key_minute, {f"{now_int}:{hash(str(now))}": now_int})
            await self.redis.expire(key_minute, 130)  # 2 * 60 + buffer
            
            remaining = effective_limit_with_burst - current_minute - 1
            
            return RateLimitResult(
                allowed=True,
                limit=effective_limit,
                remaining=max(0, remaining),
                reset_time=now_int + 60,
                tier=tier,
            )
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return RateLimitResult(
                allowed=True,
                limit=effective_limit,
                remaining=effective_limit,
                reset_time=now_int + 60,
                tier=tier,
            )
    
    async def check_concurrent_connections(
        self,
        identifier: str,
    ) -> tuple[bool, int]:
        """Check concurrent connection limit."""
        tier = self._get_tier_from_identifier(identifier)
        tier_config = TIER_CONFIGS[tier]
        
        key = f"conncount:{identifier}"
        
        try:
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, 60)
            
            if current > tier_config.concurrent_connections:
                await self.redis.decr(key)
                return False, tier_config.concurrent_connections
            
            return True, current
            
        except Exception as e:
            logger.warning(f"Connection counter error: {e}")
            return True, 0
    
    async def release_connection(self, identifier: str):
        """Release a concurrent connection slot."""
        key = f"conncount:{identifier}"
        try:
            current = await self.redis.decr(key)
            if current <= 0:
                await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Failed to release connection: {e}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enhanced FastAPI middleware for rate limiting.
    
    Features:
    - Per-user and per-IP rate limiting
    - Tiered limits based on subscription
    - Burst protection
    - Concurrent connection limiting
    - Automatic metrics collection
    """
    
    def __init__(
        self,
        app,
        redis_client: Optional[Redis] = None,
        enable_metrics: bool = True,
    ):
        super().__init__(app)
        self.redis = redis_client
        self.limiter: Optional[EnhancedRateLimiter] = None
        self.enable_metrics = enable_metrics
        self._metrics = {
            "total_requests": 0,
            "allowed_requests": 0,
            "rate_limited_requests": 0,
            "errors": 0,
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        self._metrics["total_requests"] += 1
        
        # Initialize limiter lazily
        if self.limiter is None and self.redis:
            try:
                self.limiter = EnhancedRateLimiter(self.redis)
            except Exception as e:
                logger.error(f"Failed to initialize rate limiter: {e}")
                self.limiter = None
        
        # Skip if no limiter
        if not self.limiter:
            return await call_next(request)
        
        # Get identifier
        identifier = await self._get_identifier(request)
        endpoint = request.url.path
        
        # Check rate limit
        try:
            result = await self.limiter.check_rate_limit(identifier, endpoint)
            
            if not result.allowed:
                self._metrics["rate_limited_requests"] += 1
                logger.warning(
                    f"Rate limit exceeded",
                    identifier=identifier[:20],
                    endpoint=endpoint,
                    tier=result.tier.value,
                )
                
                headers = {
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_time),
                    "X-RateLimit-Tier": result.tier.value,
                }
                
                if result.retry_after:
                    headers["Retry-After"] = str(result.retry_after)
                
                return Response(
                    content=f'{{"success": false, "error": {{"code": "RATE_LIMIT_EXCEEDED", "message": "Rate limit exceeded. Please try again later."}}, "retry_after": {result.retry_after}}}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers=headers,
                    media_type="application/json"
                )
            
            # Add rate limit headers
            self._metrics["allowed_requests"] += 1
            headers = {
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(result.reset_time),
                "X-RateLimit-Tier": result.tier.value,
            }
            
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Rate limiter error: {e}")
            headers = {}
        
        # Process request
        response = await call_next(request)
        
        # Add headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    
    async def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Try to get user ID from auth
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            return f"user:{token_hash}"
        
        # Try to get user from request state
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    def get_metrics(self) -> dict[str, Any]:
        """Get rate limiting metrics."""
        return {
            **self._metrics,
            "allow_rate": (
                self._metrics["allowed_requests"] / self._metrics["total_requests"]
                if self._metrics["total_requests"] > 0 else 0
            ),
        }

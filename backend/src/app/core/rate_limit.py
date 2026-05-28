"""
Rate Limiting Module using Redis.

Provides IP-based rate limiting for API endpoints to prevent abuse.
Uses Redis for distributed rate limiting across multiple workers/instances.

Usage:
    from ..core.rate_limit import RateLimiter, rate_limit_dependency
    
    @router.post("/endpoint")
    async def my_endpoint(
        rate_check: None = Depends(rate_limit_dependency(calls=10, period=60))
    ):
        ...
"""

import time
from typing import Optional, Callable

from fastapi import HTTPException, Request, Depends
from redis.asyncio import Redis

from .logger import get_logger
from ..api.dependencies import get_redis_client

logger = get_logger(__name__)


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(
        self,
        redis: Redis,
        key_prefix: str = "rate_limit",
        calls: int = 10,
        period: int = 60,  # seconds
    ):
        """
        Initialize rate limiter.
        
        Args:
            redis: Redis client instance
            key_prefix: Prefix for Redis keys
            calls: Maximum number of calls allowed
            period: Time window in seconds
        """
        self.redis = redis
        self.key_prefix = key_prefix
        self.calls = calls
        self.period = period
    
    def _get_key(self, identifier: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"{self.key_prefix}:{identifier}"
    
    async def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            identifier: Unique identifier (IP, user_id, etc.)
            
        Returns:
            tuple: (is_allowed: bool, info: dict with limit details)
        """
        key = self._get_key(identifier)
        now = time.time()
        window_start = now - self.period
        
        pipe = self.redis.pipeline()
        
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current entries in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiry on key
        pipe.expire(key, self.period)
        
        results = await pipe.execute()
        current_count = results[1]
        
        info = {
            "limit": self.calls,
            "remaining": max(0, self.calls - current_count - 1),
            "reset": int(now + self.period),
            "retry_after": self.period if current_count >= self.calls else 0,
        }
        
        if current_count >= self.calls:
            # Remove the request we just added since it's rate limited
            await self.redis.zrem(key, str(now))
            logger.warning(f"Rate limit exceeded for {identifier}: {current_count}/{self.calls}")
            return False, info
        
        return True, info
    
    async def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        key = self._get_key(identifier)
        await self.redis.delete(key)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for X-Forwarded-For (behind proxy/load balancer)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()
    
    # Check for X-Real-IP (nginx)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection IP
    if request.client:
        return request.client.host
    
    return "unknown"


def rate_limit_dependency(
    calls: int = 10,
    period: int = 60,
    key_prefix: str = "rate_limit",
    identifier_func: Optional[Callable[[Request], str]] = None,
):
    """
    Create a FastAPI dependency for rate limiting.
    
    Args:
        calls: Maximum calls allowed in period
        period: Time window in seconds
        key_prefix: Redis key prefix
        identifier_func: Function to extract identifier from request
                         (defaults to client IP)
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(
            rate_check: None = Depends(rate_limit_dependency(calls=10, period=60))
        ):
            ...
    """
    async def dependency(
        request: Request,
        redis: Redis = Depends(get_redis_client),
    ) -> None:
        # Get identifier
        if identifier_func:
            identifier = identifier_func(request)
        else:
            identifier = get_client_ip(request)
        
        # Add endpoint to identifier for per-endpoint limiting
        endpoint = request.url.path
        full_identifier = f"{endpoint}:{identifier}"
        
        limiter = RateLimiter(
            redis=redis,
            key_prefix=key_prefix,
            calls=calls,
            period=period,
        )
        
        allowed, info = await limiter.is_allowed(full_identifier)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {info['retry_after']} seconds.",
                    "retry_after": info["retry_after"],
                },
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset"]),
                },
            )
        
        # Add rate limit headers to response (optional, could use middleware)
        # request.state.rate_limit_info = info
    
    return dependency


# Pre-configured rate limiters for common use cases
rate_limit_api = rate_limit_dependency(calls=100, period=60)  # 100 calls/min
rate_limit_auth = rate_limit_dependency(calls=10, period=60)  # 10 calls/min for auth
rate_limit_activation = rate_limit_dependency(calls=5, period=60)  # 5 calls/min for device activation
rate_limit_strict = rate_limit_dependency(calls=3, period=60)  # 3 calls/min for sensitive ops


def _ota_identifier(request) -> str:
    """Identify OTA caller by Device-Id header (fallback to IP)."""
    dev = request.headers.get("device-id") or request.headers.get("Device-Id")
    if dev:
        return f"dev:{dev.upper()}"
    return f"ip:{get_client_ip(request)}"


# BE-H6: dedicated rate limit for OTA endpoints — keyed by Device-Id (or IP).
# 30 calls / hour per device is generous for legitimate boot+update polling
# but blocks brute-force probing for valid MACs.
rate_limit_ota = rate_limit_dependency(
    calls=3000,
    period=3600,
    key_prefix="rate_limit_ota",
    identifier_func=_ota_identifier,
)

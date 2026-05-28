"""
Connection Retry Utilities
Cung cấp retry logic cho các kết nối external services.
"""
import asyncio
import functools
from typing import TypeVar, Callable, Optional
from app.core.logger import setup_logging

TAG = __name__
logger = setup_logging()

T = TypeVar('T')


class RetryConfig:
    """Configuration cho retry logic"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


# Default configs cho các services khác nhau
REDIS_RETRY_CONFIG = RetryConfig(max_retries=5, initial_delay=0.5, max_delay=10.0)
DATABASE_RETRY_CONFIG = RetryConfig(max_retries=5, initial_delay=1.0, max_delay=30.0)
MCP_RETRY_CONFIG = RetryConfig(max_retries=3, initial_delay=1.0, max_delay=15.0)
HTTP_RETRY_CONFIG = RetryConfig(max_retries=3, initial_delay=0.5, max_delay=10.0)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Tính delay cho lần retry tiếp theo với exponential backoff.
    
    Args:
        attempt: Số lần retry hiện tại (0-indexed)
        config: RetryConfig
        
    Returns:
        Delay time in seconds
    """
    import random
    
    delay = min(
        config.initial_delay * (config.exponential_base ** attempt),
        config.max_delay
    )
    
    if config.jitter:
        # Add random jitter ±25%
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0.1, delay)  # Minimum 100ms


async def retry_async(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    retryable_exceptions: tuple = (Exception,),
    *args,
    **kwargs
) -> T:
    """
    Execute async function với retry logic.
    
    Args:
        func: Async function to execute
        config: RetryConfig, default sử dụng HTTP_RETRY_CONFIG
        on_retry: Callback khi retry (attempt, exception)
        retryable_exceptions: Tuple các exception types được retry
        *args, **kwargs: Arguments cho func
        
    Returns:
        Result từ func
        
    Raises:
        Exception cuối cùng nếu vượt quá max_retries
    """
    config = config or HTTP_RETRY_CONFIG
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt < config.max_retries:
                delay = calculate_delay(attempt, config)
                
                if on_retry:
                    on_retry(attempt + 1, e)
                else:
                    logger.bind(tag=TAG).warning(
                        f"Retry {attempt + 1}/{config.max_retries} sau {delay:.2f}s: {type(e).__name__}: {e}"
                    )
                
                await asyncio.sleep(delay)
            else:
                logger.bind(tag=TAG).error(
                    f"Đã retry {config.max_retries} lần, vẫn thất bại: {type(e).__name__}: {e}"
                )
    
    raise last_exception


def retry_sync(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    retryable_exceptions: tuple = (Exception,),
    *args,
    **kwargs
) -> T:
    """
    Execute sync function với retry logic.
    
    Args:
        func: Sync function to execute
        config: RetryConfig
        on_retry: Callback khi retry
        retryable_exceptions: Tuple các exception types được retry
        *args, **kwargs: Arguments cho func
        
    Returns:
        Result từ func
    """
    import time
    
    config = config or HTTP_RETRY_CONFIG
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt < config.max_retries:
                delay = calculate_delay(attempt, config)
                
                if on_retry:
                    on_retry(attempt + 1, e)
                else:
                    logger.bind(tag=TAG).warning(
                        f"Retry {attempt + 1}/{config.max_retries} sau {delay:.2f}s: {type(e).__name__}: {e}"
                    )
                
                time.sleep(delay)
            else:
                logger.bind(tag=TAG).error(
                    f"Đã retry {config.max_retries} lần, vẫn thất bại: {type(e).__name__}: {e}"
                )
    
    raise last_exception


def with_retry(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Decorator để thêm retry logic vào function.
    
    Args:
        config: RetryConfig
        retryable_exceptions: Tuple các exception types được retry
        
    Example:
        @with_retry(config=REDIS_RETRY_CONFIG)
        async def get_from_redis(key: str):
            return await redis.get(key)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await retry_async(
                    func, config, None, retryable_exceptions, *args, **kwargs
                )
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return retry_sync(
                    func, config, None, retryable_exceptions, *args, **kwargs
                )
            return sync_wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit Breaker pattern để ngăn chặn cascading failures.
    
    States:
    - CLOSED: Normal operation, requests được forward
    - OPEN: Quá nhiều failures, requests bị reject ngay
    - HALF_OPEN: Đang test để xem service đã recover chưa
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> str:
        return self._state
    
    async def _check_state(self) -> bool:
        """Check và update state. Return True nếu request được phép."""
        import time
        
        async with self._lock:
            if self._state == self.CLOSED:
                return True
            
            if self._state == self.OPEN:
                if self._last_failure_time and \
                   (time.time() - self._last_failure_time) >= self.recovery_timeout:
                    self._state = self.HALF_OPEN
                    self._half_open_calls = 0
                    logger.bind(tag=TAG).info("Circuit breaker chuyển sang HALF_OPEN")
                    return True
                return False
            
            if self._state == self.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            return True
    
    async def record_success(self) -> None:
        """Ghi nhận request thành công."""
        async with self._lock:
            if self._state == self.HALF_OPEN:
                self._state = self.CLOSED
                self._failure_count = 0
                logger.bind(tag=TAG).info("Circuit breaker đã CLOSED (recovered)")
            elif self._state == self.CLOSED:
                self._failure_count = 0
    
    async def record_failure(self) -> None:
        """Ghi nhận request thất bại."""
        import time
        
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == self.HALF_OPEN:
                self._state = self.OPEN
                logger.bind(tag=TAG).warning("Circuit breaker OPEN (half_open failed)")
            elif self._state == self.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = self.OPEN
                    logger.bind(tag=TAG).warning(
                        f"Circuit breaker OPEN sau {self._failure_count} failures"
                    )
    
    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function với circuit breaker protection.
        
        Raises:
            CircuitBreakerOpenError: Khi circuit đang OPEN
        """
        if not await self._check_state():
            raise CircuitBreakerOpenError(f"Circuit breaker đang {self._state}")
        
        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception:
            await self.record_failure()
            raise


class CircuitBreakerOpenError(Exception):
    """Raised khi circuit breaker đang OPEN và reject request."""
    pass


# Pre-configured circuit breakers cho các services
redis_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
mcp_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
database_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

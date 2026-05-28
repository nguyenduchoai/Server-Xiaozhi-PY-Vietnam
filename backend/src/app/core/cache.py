"""
Cache module for Redis connection pooling.

Provides a global cache object for rate limiting and caching operations.
"""

from redis.asyncio import ConnectionPool, Redis
from typing import Optional

from .logger import get_logger

logger = get_logger(__name__)


class Cache:
    """Redis cache wrapper with connection pooling."""
    
    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        
    async def init(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 10,
    ) -> None:
        """Initialize Redis connection pool."""
        try:
            self.pool = ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                decode_responses=True,
            )
            self._client = Redis(connection_pool=self.pool)
            
            # Test connection
            await self._client.ping()
            logger.info(f"Redis cache connected to {host}:{port}/{db}")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis cache: {e}")
            self.pool = None
            self._client = None
    
    @property
    def client(self) -> Optional[Redis]:
        """Get Redis client."""
        return self._client
    
    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.close()
        if self.pool:
            await self.pool.disconnect()
        logger.info("Redis cache connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self._client:
            return None
        return await self._client.get(key)
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if not self._client:
            return False
        await self._client.set(key, value, ex=expire)
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._client:
            return False
        await self._client.delete(key)
        return True


# Global cache instance
cache = Cache()

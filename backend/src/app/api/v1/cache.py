"""
Cache Stats API - Monitor Redis cache performance
"""

from fastapi import APIRouter, Depends, HTTPException
from redis import asyncio as aioredis
from app.core.utils.cache_manager import get_cache_manager, CacheManager
from app.core.utils import cache as cache_utils

router = APIRouter(prefix="/cache", tags=["Cache Management"])


async def get_cache_mgr() -> CacheManager:
    """Dependency: Get cache manager instance"""
    if cache_utils.pool is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    redis_client = aioredis.Redis(connection_pool=cache_utils.pool)
    return await get_cache_manager(redis_client)


@router.get("/stats")
async def get_cache_statistics(
    cache_mgr: CacheManager = Depends(get_cache_mgr)
):
    """
    Get Redis cache statistics
    
    Returns:
        - keyspace_hits: Number of cache hits
        - keyspace_misses: Number of cache misses
        - hit_rate: Cache hit rate percentage
        - total_keys: Total number of keys in cache
        - memory_usage: Current memory usage
    """
    stats = await cache_mgr.get_cache_stats()
    
    hits = stats.get('keyspace_hits', 0)
    misses = stats.get('keyspace_misses', 0)
    total = hits + misses
    
    hit_rate = (hits / total * 100) if total > 0 else 0
    
    return {
        "cache_hits": hits,
        "cache_misses": misses,
        "hit_rate_percent": round(hit_rate, 2),
        "total_keys": stats.get('total_keys', 0),
        "memory_used": stats.get('used_memory_human', 'N/A'),
        "memory_peak": stats.get('used_memory_peak_human', 'N/A'),
    }


@router.delete("/clear")
async def clear_all_cache(
    cache_mgr: CacheManager = Depends(get_cache_mgr)
):
    """
    Clear all cache (use with caution!)
    
    Requires admin authentication in production
    """
    success = await cache_mgr.clear_all_cache()
    
    if success:
        return {"message": "All cache cleared successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.delete("/agent/{agent_id}/config")
async def invalidate_agent_config_cache(
    agent_id: int,
    cache_mgr: CacheManager = Depends(get_cache_mgr)
):
    """
    Invalidate agent config cache
    
    Use this when agent configuration is updated
    """
    success = await cache_mgr.invalidate_agent_config(agent_id)
    
    if success:
        return {"message": f"Agent {agent_id} config cache invalidated"}
    else:
        raise HTTPException(status_code=500, detail="Failed to invalidate cache")

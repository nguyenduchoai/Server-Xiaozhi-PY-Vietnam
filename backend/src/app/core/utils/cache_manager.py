"""
Cache Manager - Redis caching layer cho LLM responses và TTS audio

Sử dụng:
- FAQ cache: TTL 1 hour (3600s)
- TTS cache: TTL 24 hours (86400s)
- Agent config cache: Invalidate on update
"""

import hashlib
import json
import base64
from typing import Optional
from redis import asyncio as aioredis
from app.core.logger import setup_logging

logger = setup_logging()
TAG = __name__


class CacheManager:
    """Redis cache manager cho FAQ, TTS, và agent configs"""
    
    # Cache TTL constants (seconds)
    FAQ_TTL = 3600  # 1 hour
    TTS_TTL = 86400  # 24 hours
    AGENT_CONFIG_TTL = 7200  # 2 hours
    
    def __init__(self, redis_client: aioredis.Redis):
        """
        Initialize cache manager
        
        Args:
            redis_client: Redis async client instance
        """
        self.redis = redis_client
        logger.bind(tag=TAG).info("CacheManager initialized")
    
    @staticmethod
    def _generate_hash(content: str) -> str:
        """Generate SHA256 hash for cache key"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    # ==================== FAQ CACHE ====================
    
    def get_faq_cache_key(self, agent_id: int, question: str) -> str:
        """
        Generate cache key for FAQ
        
        Args:
            agent_id: Agent ID
            question: User question (normalized)
            
        Returns:
            Redis cache key
        """
        question_hash = self._generate_hash(question.lower().strip())
        return f"agent:{agent_id}:faq:{question_hash}"
    
    async def get_faq_response(self, agent_id: int, question: str) -> Optional[str]:
        """
        Get cached FAQ response
        
        Args:
            agent_id: Agent ID
            question: User question
            
        Returns:
            Cached response or None if not found
        """
        try:
            key = self.get_faq_cache_key(agent_id, question)
            cached = await self.redis.get(key)
            
            if cached:
                logger.bind(tag=TAG).debug(f"FAQ cache HIT: {key}")
                return cached.decode('utf-8')
            
            logger.bind(tag=TAG).debug(f"FAQ cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).warning(f"FAQ cache read error: {e}")
            return None
    
    async def set_faq_response(self, agent_id: int, question: str, response: str) -> bool:
        """
        Cache FAQ response
        
        Args:
            agent_id: Agent ID
            question: User question
            response: LLM response
            
        Returns:
            True if cached successfully
        """
        try:
            key = self.get_faq_cache_key(agent_id, question)
            await self.redis.setex(key, self.FAQ_TTL, response)
            logger.bind(tag=TAG).debug(f"FAQ cached: {key} (TTL: {self.FAQ_TTL}s)")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"FAQ cache write error: {e}")
            return False
    
    # ==================== TTS CACHE ====================
    
    def get_tts_cache_key(self, voice: str, text: str, model: str = "edge") -> str:
        """
        Generate cache key for TTS audio
        
        Args:
            voice: Voice ID/name
            text: Text to synthesize
            model: TTS model name (edge, valtec)
            
        Returns:
            Redis cache key
        """
        text_hash = self._generate_hash(text)
        return f"tts:{model}:{voice}:{text_hash}"
    
    async def get_tts_audio(self, voice: str, text: str, model: str = "edge") -> Optional[bytes]:
        """
        Get cached TTS audio
        
        Args:
            voice: Voice ID
            text: Text content
            model: TTS model
            
        Returns:
            Audio bytes or None if not found
        """
        try:
            key = self.get_tts_cache_key(voice, text, model)
            cached = await self.redis.get(key)
            
            if cached:
                logger.bind(tag=TAG).debug(f"TTS cache HIT: {key}")
                # Decode base64 back to bytes
                return base64.b64decode(cached)
            
            logger.bind(tag=TAG).debug(f"TTS cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).warning(f"TTS cache read error: {e}")
            return None
    
    async def set_tts_audio(self, voice: str, text: str, audio_data: bytes, model: str = "edge") -> bool:
        """
        Cache TTS audio
        
        Args:
            voice: Voice ID
            text: Text content
            audio_data: Audio bytes
            model: TTS model
            
        Returns:
            True if cached successfully
        """
        try:
            key = self.get_tts_cache_key(voice, text, model)
            # Encode audio to base64 for Redis storage
            encoded_audio = base64.b64encode(audio_data)
            await self.redis.setex(key, self.TTS_TTL, encoded_audio)
            
            size_kb = len(audio_data) / 1024
            logger.bind(tag=TAG).debug(f"TTS cached: {key} ({size_kb:.1f}KB, TTL: {self.TTS_TTL}s)")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS cache write error: {e}")
            return False
    
    # ==================== AGENT CONFIG CACHE ====================
    
    def get_agent_config_key(self, agent_id: int, version: Optional[int] = None) -> str:
        """
        Generate cache key for agent config
        
        Args:
            agent_id: Agent ID
            version: Config version (for cache invalidation)
            
        Returns:
            Redis cache key
        """
        if version:
            return f"agent:{agent_id}:config:v{version}"
        return f"agent:{agent_id}:config"
    
    async def get_agent_config(self, agent_id: int, version: Optional[int] = None) -> Optional[dict]:
        """
        Get cached agent config
        
        Args:
            agent_id: Agent ID
            version: Config version
            
        Returns:
            Agent config dict or None
        """
        try:
            key = self.get_agent_config_key(agent_id, version)
            cached = await self.redis.get(key)
            
            if cached:
                logger.bind(tag=TAG).debug(f"Agent config cache HIT: {key}")
                return json.loads(cached.decode('utf-8'))
            
            logger.bind(tag=TAG).debug(f"Agent config cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).warning(f"Agent config cache read error: {e}")
            return None
    
    async def set_agent_config(self, agent_id: int, config: dict, version: Optional[int] = None) -> bool:
        """
        Cache agent config
        
        Args:
            agent_id: Agent ID
            config: Agent configuration dict
            version: Config version
            
        Returns:
            True if cached successfully
        """
        try:
            key = self.get_agent_config_key(agent_id, version)
            config_json = json.dumps(config)
            await self.redis.setex(key, self.AGENT_CONFIG_TTL, config_json)
            logger.bind(tag=TAG).debug(f"Agent config cached: {key} (TTL: {self.AGENT_CONFIG_TTL}s)")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Agent config cache write error: {e}")
            return False
    
    async def invalidate_agent_config(self, agent_id: int) -> bool:
        """
        Invalidate all agent config cache (when agent updated)
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if invalidated
        """
        try:
            pattern = f"agent:{agent_id}:config*"
            keys = await self.redis.keys(pattern)
            
            if keys:
                await self.redis.delete(*keys)
                logger.bind(tag=TAG).info(f"Invalidated {len(keys)} agent config cache keys")
            
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Agent config cache invalidation error: {e}")
            return False
    
    # ==================== CACHE STATS ====================
    
    async def get_cache_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            Dict with cache stats (hits, misses, memory usage)
        """
        try:
            info = await self.redis.info('stats')
            memory = await self.redis.info('memory')
            
            return {
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'used_memory_human': memory.get('used_memory_human', 'N/A'),
                'used_memory_peak_human': memory.get('used_memory_peak_human', 'N/A'),
                'total_keys': await self.redis.dbsize(),
            }
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Cache stats error: {e}")
            return {}
    
    async def clear_all_cache(self) -> bool:
        """
        Clear all cache (use with caution!)
        
        Returns:
            True if cleared
        """
        try:
            await self.redis.flushdb()
            logger.bind(tag=TAG).warning("All cache cleared!")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Cache clear error: {e}")
            return False


# Singleton instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager(redis_client: aioredis.Redis) -> CacheManager:
    """Get or create cache manager instance"""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager(redis_client)
    
    return _cache_manager

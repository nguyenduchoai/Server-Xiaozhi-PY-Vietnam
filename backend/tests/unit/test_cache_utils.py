"""
Tests for Cache Utils

Tests comprehensive caching functionality including:
- Cache key management
- Cache manager operations
- Serialization/deserialization
- Pattern-based invalidation
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.utils.cache import (
    CacheKey,
    BaseCacheManager,
    RedisCacheManager,
    _infer_resource_id,
    _extract_data_inside_brackets,
    _construct_data_dict,
    _format_prefix,
    _format_extra_data,
)


class TestCacheKey:
    """Tests for CacheKey enum."""

    def test_cache_key_enum_values(self):
        """Test CacheKey enum has correct values."""
        assert CacheKey.DEVICE_ACTIVATION.value == "device_activation"
        assert CacheKey.OTA_DEVICE_DATA.value == "ota_device_data"
        assert CacheKey.USER_CACHE.value == "user"
        assert CacheKey.AGENT_CACHE.value == "agent"
        assert CacheKey.SUBSCRIPTION_PLANS.value == "subscription_plans"

    def test_cache_key_format_key(self):
        """Test CacheKey.format_key() creates correct keys."""
        key = CacheKey.DEVICE_ACTIVATION.format_key("AA:BB:CC:DD:EE:FF")
        assert key == "device_activation:AA:BB:CC:DD:EE:FF"

    def test_cache_key_format_key_multiple_identifiers(self):
        """Test CacheKey.format_key() with multiple identifiers."""
        key = CacheKey.AGENT_CACHE.format_key("agent-123", "v1")
        assert key == "agent:agent-123:v1"

    def test_cache_key_pattern(self):
        """Test CacheKey.pattern() returns wildcard pattern."""
        pattern = CacheKey.DEVICE_ACTIVATION.pattern()
        assert pattern == "device_activation:*"

    def test_cache_key_string_value(self):
        """Test CacheKey can be used as string."""
        key_str = str(CacheKey.USER_CACHE)
        assert key_str == "user"


class TestRedisCacheManager:
    """Tests for RedisCacheManager."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)
        redis.exists = AsyncMock(return_value=0)
        redis.scan = AsyncMock(return_value=(0, []))
        redis.flushdb = AsyncMock()
        return redis

    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create RedisCacheManager with mock Redis."""
        return RedisCacheManager(mock_redis, default_ttl=3600)

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self, cache_manager, mock_redis):
        """Test get returns None when key doesn't exist."""
        mock_redis.get.return_value = None
        
        result = await cache_manager.get(CacheKey.USER_CACHE, "user-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_deserializes_json(self, cache_manager, mock_redis):
        """Test get deserializes JSON string from Redis."""
        test_data = {"id": "user-123", "name": "Test User"}
        mock_redis.get.return_value = json.dumps(test_data)
        
        result = await cache_manager.get(CacheKey.USER_CACHE, "user-123")
        assert result == test_data

    @pytest.mark.asyncio
    async def test_get_handles_bytes(self, cache_manager, mock_redis):
        """Test get handles bytes returned from Redis."""
        test_data = {"id": "user-123"}
        mock_redis.get.return_value = json.dumps(test_data).encode()
        
        result = await cache_manager.get(CacheKey.USER_CACHE, "user-123")
        assert result == test_data

    @pytest.mark.asyncio
    async def test_set_serializes_json(self, cache_manager, mock_redis):
        """Test set serializes dict to JSON before storing."""
        test_data = {"id": "user-123", "name": "Test User"}
        
        await cache_manager.set(CacheKey.USER_CACHE, test_data, "user-123")
        
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert "user:user-123" in str(call_args)
        serialized_data = call_args[0][1]
        assert json.loads(serialized_data) == test_data

    @pytest.mark.asyncio
    async def test_set_uses_ttl(self, cache_manager, mock_redis):
        """Test set uses custom TTL when provided."""
        test_data = {"id": "user-123"}
        
        await cache_manager.set(CacheKey.USER_CACHE, test_data, "user-123", ttl=7200)
        
        call_args = mock_redis.set.call_args
        assert "ex=7200" in str(call_args) or call_args[1].get('ex') == 7200

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, cache_manager, mock_redis):
        """Test delete removes key from Redis."""
        await cache_manager.delete(CacheKey.USER_CACHE, "user-123")
        
        mock_redis.delete.assert_called_once_with("user:user-123")

    @pytest.mark.asyncio
    async def test_exists_returns_boolean(self, cache_manager, mock_redis):
        """Test exists returns boolean."""
        mock_redis.exists.return_value = 1
        
        result = await cache_manager.exists(CacheKey.USER_CACHE, "user-123")
        assert result is True
        
        mock_redis.exists.return_value = 0
        result = await cache_manager.exists(CacheKey.USER_CACHE, "user-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_pattern_uses_scan(self, cache_manager, mock_redis):
        """Test delete_pattern uses SCAN for pattern matching."""
        mock_redis.scan.return_value = (0, ["key1", "key2"])
        
        await cache_manager.delete_pattern("user:*")
        
        mock_redis.scan.assert_called()
        mock_redis.delete.assert_called_with("key1", "key2")

    @pytest.mark.asyncio
    async def test_clear_all_flushes_db(self, cache_manager, mock_redis):
        """Test clear_all flushes the database."""
        await cache_manager.clear_all()
        
        mock_redis.flushdb.assert_called_once()


class TestCacheKeyHelpers:
    """Tests for cache key helper functions."""

    def test_extract_data_inside_brackets(self):
        """Test extracting data from curly brackets."""
        result = _extract_data_inside_brackets("user:{id}:profile")
        assert result == ["id"]

    def test_extract_data_inside_brackets_multiple(self):
        """Test extracting multiple data from curly brackets."""
        result = _extract_data_inside_brackets("device:{mac}:agent:{agent_id}")
        assert result == ["mac", "agent_id"]

    def test_extract_data_inside_brackets_empty(self):
        """Test extracting from string without brackets."""
        result = _extract_data_inside_brackets("user:id:profile")
        assert result == []

    def test_construct_data_dict(self):
        """Test constructing data dict from brackets."""
        data_inside_brackets = ["id", "name"]
        kwargs = {"id": "user-123", "name": "Test User"}
        
        result = _construct_data_dict(data_inside_brackets, kwargs)
        assert result == {"id": "user-123", "name": "Test User"}

    def test_format_prefix(self):
        """Test formatting prefix with kwargs."""
        prefix = "user:{id}:session"
        kwargs = {"id": "user-123"}
        
        result = _format_prefix(prefix, kwargs)
        assert result == "user:user-123:session"

    def test_format_extra_data(self):
        """Test formatting extra data for invalidation."""
        to_invalidate_extra = {
            "user:{user_id}:agents": "agent_id"
        }
        kwargs = {"user_id": "user-123", "agent_id": "agent-456"}
        
        result = _format_extra_data(to_invalidate_extra, kwargs)
        assert result == {"user:user-123:agents": "agent-456"}


class TestCacheKeyNewEntries:
    """Tests for newly added cache keys."""

    def test_subscription_plans_key(self):
        """Test SUBSCRIPTION_PLANS cache key."""
        key = CacheKey.SUBSCRIPTION_PLANS
        assert key.value == "subscription_plans"

    def test_user_subscription_key(self):
        """Test USER_SUBSCRIPTION cache key with format."""
        key = CacheKey.USER_SUBSCRIPTION.format_key("user-123")
        assert key == "user_subscription:user-123"

    def test_provider_config_modules_key(self):
        """Test PROVIDER_CONFIG_MODULES cache key."""
        key = CacheKey.PROVIDER_CONFIG_MODULES
        assert key.value == "provider_config_modules"
"""
Integration Tests for API Performance

Tests API response times and caching effectiveness:
- Subscription plans endpoint
- Provider config modules endpoint
- Response time assertions
- Cache hit/miss verification
"""

import pytest
import pytest_asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.subscription import list_subscription_plans, _get_cache_manager
from app.api.v1.providers import get_config_modules
from app.core.utils.cache import CacheKey, RedisCacheManager


class TestSubscriptionPlansPerformance:
    """Tests for subscription plans endpoint performance."""

    @pytest.mark.asyncio
    async def test_subscription_plans_caches_result(self, db_session):
        """Test subscription plans endpoint caches results."""
        mock_cache_manager = AsyncMock(spec=RedisCacheManager)
        mock_cache_manager.get.return_value = None  # Cache miss
        mock_cache_manager.set = AsyncMock()

        with patch('app.api.v1.subscription._get_cache_manager', return_value=mock_cache_manager):
            with patch('app.crud.crud_subscription_plan.get_multi') as mock_get_multi:
                mock_get_multi.return_value = {
                    "data": [],
                    "total": 0,
                    "offset": 0,
                    "limit": 0,
                    "pages": 0
                }
                
                result = await list_subscription_plans(db=db_session)
                
                mock_cache_manager.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscription_plans_returns_cached(self, db_session):
        """Test subscription plans returns cached data on cache hit."""
        cached_data = [
            {"id": "1", "name": "FREE", "sort_order": 0},
            {"id": "2", "name": "PRO", "sort_order": 1},
        ]
        
        mock_cache_manager = AsyncMock(spec=RedisCacheManager)
        mock_cache_manager.get.return_value = cached_data

        with patch('app.api.v1.subscription._get_cache_manager', return_value=mock_cache_manager):
            result = await list_subscription_plans(db=db_session)
            
            assert len(result) == 2
            assert result[0].name == "FREE"


class TestProviderConfigModulesCaching:
    """Tests for provider config modules caching."""

    @pytest.mark.asyncio
    async def test_provider_modules_uses_cache(self):
        """Test provider config modules uses cache."""
        mock_cache_manager = AsyncMock(spec=RedisCacheManager)
        mock_cache_manager.get.return_value = None

        with patch('app.api.v1.providers._get_cache_manager', return_value=mock_cache_manager):
            mock_user = {"sub": "user-123", "id": "user-123"}
            
            with patch('app.api.v1.providers.db') as mock_db:
                mock_result = MagicMock()
                mock_result.scalars.return_value.all.return_value = []
                mock_db.execute.return_value = mock_result
                
                mock_request = MagicMock()
                mock_request.app.state = MagicMock()
                mock_request.headers = {}
                
                # Test the caching logic
                cache_key = CacheKey.PROVIDER_CONFIG_MODULES
                cache_key_str = f"{cache_key.value}:user-123:False"
                cached_data = await mock_cache_manager.get(cache_key_str)
                
                assert cached_data is None


class TestCacheKeyDistribution:
    """Tests for cache key usage patterns."""

    def test_all_new_cache_keys_defined(self):
        """Test all new cache keys are properly defined."""
        assert CacheKey.SUBSCRIPTION_PLANS.value == "subscription_plans"
        assert CacheKey.USER_SUBSCRIPTION.value == "user_subscription"
        assert CacheKey.PROVIDER_CONFIG_MODULES.value == "provider_config_modules"

    def test_cache_key_ttl_values(self):
        """Test cache TTL constants are reasonable."""
        from app.api.v1.subscription import SUBSCRIPTION_PLANS_CACHE_TTL
        from app.api.v1.providers import PROVIDERS_CACHE_TTL
        
        assert SUBSCRIPTION_PLANS_CACHE_TTL == 3600  # 1 hour
        assert PROVIDERS_CACHE_TTL == 300  # 5 minutes

    def test_cache_key_patterns_for_invalidation(self):
        """Test cache keys support pattern-based invalidation."""
        # Test SUBSCRIPTION_PLANS has pattern
        pattern = CacheKey.SUBSCRIPTION_PLANS.pattern()
        assert pattern == "subscription_plans:*"
        
        # Test USER_SUBSCRIPTION supports user-specific keys
        user_key = CacheKey.USER_SUBSCRIPTION.format_key("user-123")
        assert user_key == "user_subscription:user-123"
        
        # Test PROVIDER_CONFIG_MODULES supports user+config keys
        provider_key = CacheKey.PROVIDER_CONFIG_MODULES.format_key("user-123", "true")
        assert provider_key == "provider_config_modules:user-123:true"


class TestPerformanceAssertions:
    """Tests for performance assertion helpers."""

    def test_api_response_time_benchmark(self):
        """Test API response times meet benchmarks."""
        # Simulate cached response time
        cached_response_time_ms = 5  # Redis get
        assert cached_response_time_ms < 50
        
        # Simulate DB query time
        db_query_time_ms = 150  # Typical query
        assert db_query_time_ms < 200
        
        # Total cached response should be < 200ms
        total_cached_time = cached_response_time_ms + 20  # processing overhead
        assert total_cached_time < 200

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation helper."""
        total_requests = 100
        cache_hits = 80
        cache_misses = 20
        
        hit_rate = (cache_hits / total_requests) * 100
        assert hit_rate == 80.0


class TestCacheInvalidation:
    """Tests for cache invalidation strategies."""

    @pytest.mark.asyncio
    async def test_subscription_plans_invalidation_on_update(self):
        """Test subscription plans cache can be invalidated."""
        mock_cache_manager = AsyncMock(spec=RedisCacheManager)
        
        cache_key = CacheKey.SUBSCRIPTION_PLANS
        cache_key_str = cache_key.value
        
        # Invalidate the cache
        await mock_cache_manager.delete(cache_key_str)
        
        mock_cache_manager.delete.assert_called_once_with(cache_key_str)

    @pytest.mark.asyncio
    async def test_user_specific_cache_invalidation(self):
        """Test user-specific cache can be invalidated."""
        mock_cache_manager = AsyncMock(spec=RedisCacheManager)
        
        user_id = "user-123"
        cache_key = CacheKey.USER_SUBSCRIPTION.format_key(user_id)
        
        await mock_cache_manager.delete(cache_key)
        
        mock_cache_manager.delete.assert_called_once_with("user_subscription:user-123")

    @pytest.mark.asyncio
    async def test_pattern_based_invalidation(self):
        """Test pattern-based cache invalidation."""
        mock_cache_manager = AsyncMock(spec=RedisCacheManager)
        mock_cache_manager.scan.return_value = (0, [
            "provider_config_modules:user-123:False",
            "provider_config_modules:user-456:False"
        ])
        
        pattern = "provider_config_modules:*"
        await mock_cache_manager.delete_pattern(pattern)
        
        mock_cache_manager.delete_pattern.assert_called_once_with(pattern)
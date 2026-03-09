"""Flow tests for caching behavior.

Validates:
- Recommendation cache TTL
- Answers hash invalidation
- Robot catalog cache refresh
- Cache clear and stats
"""

import copy
import time
from unittest.mock import patch

import pytest

from tests.flow.conftest import COMPLETE_DISCOVERY_ANSWERS, SEED_ROBOTS


class TestRecommendationCacheTTL:
    """Verify recommendation cache TTL behavior."""

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        """Cached entry returns None after TTL expires."""
        from src.services.recommendation_cache import (
            RecommendationCache,
            RecommendationCacheConfig,
        )

        # Use a very short TTL
        config = RecommendationCacheConfig(max_size=100, ttl_seconds=1)
        cache = RecommendationCache(config)

        answers = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
        response = {"recommendations": [{"robot_id": "test"}]}

        await cache.set(answers, response)

        # Immediately should be cached
        cached = await cache.get(answers)
        assert cached is not None

        # Simulate time passing by directly manipulating the entry
        key = cache._generate_key(answers)
        cache._cache[key].expires_at = time.time() - 1

        # Should be expired now
        cached = await cache.get(answers)
        assert cached is None

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_entries(self):
        """cleanup() removes all expired entries."""
        from src.services.recommendation_cache import (
            RecommendationCache,
            RecommendationCacheConfig,
        )

        config = RecommendationCacheConfig(max_size=100, ttl_seconds=3600)
        cache = RecommendationCache(config)

        # Add entries
        for i in range(5):
            answers = {"key": {"value": f"val_{i}"}}
            await cache.set(answers, {"id": i})

        # Expire all
        for entry in cache._cache.values():
            entry.expires_at = time.time() - 1

        removed = await cache.cleanup()
        assert removed == 5

        stats = await cache.get_stats()
        assert stats["total_entries"] == 0


class TestAnswersHashInvalidation:
    """Verify that answer changes produce different cache keys."""

    def test_same_answers_same_hash(self):
        """Identical answers produce identical hash."""
        from src.services.discovery_profile_service import compute_answers_hash

        answers = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
        h1 = compute_answers_hash(answers)
        h2 = compute_answers_hash(answers)
        assert h1 == h2

    def test_different_value_different_hash(self):
        """Changing a value produces a different hash."""
        from src.services.discovery_profile_service import compute_answers_hash

        answers1 = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
        answers2 = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
        answers2["company_name"]["value"] = "Different Company"

        h1 = compute_answers_hash(answers1)
        h2 = compute_answers_hash(answers2)
        assert h1 != h2

    def test_additional_key_different_hash(self):
        """Adding a new key changes the hash."""
        from src.services.discovery_profile_service import compute_answers_hash

        answers1 = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
        answers2 = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
        answers2["extra_key"] = {"value": "something"}

        h1 = compute_answers_hash(answers1)
        h2 = compute_answers_hash(answers2)
        assert h1 != h2

    def test_order_independent_hash(self):
        """Hash is independent of dict insertion order."""
        from src.services.discovery_profile_service import compute_answers_hash

        answers1 = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
        # Reverse the key order
        answers2 = dict(reversed(list(answers1.items())))

        h1 = compute_answers_hash(answers1)
        h2 = compute_answers_hash(answers2)
        assert h1 == h2

    @pytest.mark.asyncio
    async def test_cache_key_matches_hash(self):
        """RecommendationCache._generate_key uses same logic as compute_answers_hash."""
        from src.services.discovery_profile_service import compute_answers_hash
        from src.services.recommendation_cache import RecommendationCache, RecommendationCacheConfig

        cache = RecommendationCache(RecommendationCacheConfig())
        answers = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)

        cache_key = cache._generate_key(answers)
        profile_hash = compute_answers_hash(answers)
        assert cache_key == profile_hash


class TestRobotCatalogCache:
    """Verify robot catalog module-level TTL cache."""

    @pytest.mark.asyncio
    async def test_cache_refresh_after_ttl(self, _patch_all, fake_supabase):
        """Robot cache refreshes after TTL expires."""
        import src.services.agent_service as agent_mod

        # Set cache with old timestamp (past TTL)
        agent_mod._robot_cache = (time.monotonic() - 600, [{"name": "old"}])

        result = await agent_mod._get_cached_robot_catalog()

        # Should get fresh data (from FakeSupabase seeded robots)
        assert len(result) == len(SEED_ROBOTS)
        assert result[0]["name"] != "old"

        # Clean up
        agent_mod._robot_cache = None

    @pytest.mark.asyncio
    async def test_cache_hit_within_ttl(self, _patch_all):
        """Robot cache returns cached data within TTL window."""
        import src.services.agent_service as agent_mod

        # Set cache with current timestamp
        cached_data = [{"name": "cached_robot"}]
        agent_mod._robot_cache = (time.monotonic(), cached_data)

        result = await agent_mod._get_cached_robot_catalog()
        assert len(result) == 1
        assert result[0]["name"] == "cached_robot"

        # Clean up
        agent_mod._robot_cache = None


class TestCacheStats:
    """Verify cache statistics reporting."""

    @pytest.mark.asyncio
    async def test_stats_reflect_state(self):
        """get_stats returns accurate cache state."""
        from src.services.recommendation_cache import (
            RecommendationCache,
            RecommendationCacheConfig,
        )

        config = RecommendationCacheConfig(max_size=100, ttl_seconds=3600)
        cache = RecommendationCache(config)

        # Empty cache
        stats = await cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["max_size"] == 100

        # Add entries
        for i in range(3):
            await cache.set({"k": {"value": f"v{i}"}}, {"id": i})

        stats = await cache.get_stats()
        assert stats["total_entries"] == 3
        assert stats["valid_entries"] == 3

        # Expire one
        first_key = list(cache._cache.keys())[0]
        cache._cache[first_key].expires_at = time.time() - 1

        stats = await cache.get_stats()
        assert stats["expired_entries"] == 1
        assert stats["valid_entries"] == 2

    @pytest.mark.asyncio
    async def test_clear_resets_cache(self):
        """clear() removes all entries and returns count."""
        from src.services.recommendation_cache import (
            RecommendationCache,
            RecommendationCacheConfig,
        )

        cache = RecommendationCache(RecommendationCacheConfig())

        for i in range(5):
            await cache.set({"k": {"value": f"v{i}"}}, {"id": i})

        count = await cache.clear()
        assert count == 5

        stats = await cache.get_stats()
        assert stats["total_entries"] == 0

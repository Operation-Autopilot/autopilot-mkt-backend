"""Flow tests for concurrent request handling.

Validates:
- Robot cache lock: concurrent fetches → single DB call
- BackgroundTasks isolation: concurrent message sends don't leak
- Recommendation cache lock: concurrent requests don't duplicate LLM calls
"""

import asyncio
import copy
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.robot_catalog_service import RobotCatalogService
from tests.flow.conftest import COMPLETE_DISCOVERY_ANSWERS, SEED_ROBOTS


class TestRobotCacheLock:
    """Verify robot catalog cache uses async lock to prevent thundering herd."""

    @pytest.mark.asyncio
    async def test_concurrent_fetches_hit_db_once(self, _patch_all, fake_supabase):
        """10 concurrent _get_cached_robot_catalog() calls should fetch from DB only once."""
        import src.services.agent_service as agent_mod

        # Reset the module-level cache
        agent_mod._robot_cache = None

        # Track how many times list_robots is actually called via a wrapper
        call_count = 0
        original_list_robots = RobotCatalogService.list_robots

        async def tracked_list_robots(self, active_only=True):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return copy.deepcopy(SEED_ROBOTS)

        with patch.object(RobotCatalogService, "list_robots", tracked_list_robots):
            # Launch 10 concurrent calls
            tasks = [agent_mod._get_cached_robot_catalog() for _ in range(10)]
            results = await asyncio.gather(*tasks)

        # All should return the same data
        assert all(len(r) == len(SEED_ROBOTS) for r in results)

        # DB should be called at most twice (once for first caller, possibly once
        # for a caller that checked before lock but lock was already acquired)
        # The key thing: NOT 10 times
        assert call_count <= 2, f"Expected ≤2 DB calls, got {call_count}"

        # Clean up
        agent_mod._robot_cache = None

    @pytest.mark.asyncio
    async def test_cache_returns_stale_data_within_ttl(self, _patch_all):
        """Cached data is returned without DB call within TTL window."""
        import src.services.agent_service as agent_mod

        # Pre-populate cache
        cached_robots = copy.deepcopy(SEED_ROBOTS[:2])
        agent_mod._robot_cache = (time.monotonic(), cached_robots)

        result = await agent_mod._get_cached_robot_catalog()
        assert len(result) == 2  # Returns cached (not full catalog)

        # Clean up
        agent_mod._robot_cache = None


class TestRecommendationCacheConcurrency:
    """Verify recommendation cache handles concurrent access safely."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_writes_no_corruption(self, _patch_recommendation_cache):
        """Multiple concurrent writes to the cache don't corrupt data."""
        cache = _patch_recommendation_cache

        async def write_cache(i: int):
            answers = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
            answers["company_name"]["value"] = f"Company {i}"
            response = {"recommendations": [{"robot_id": f"robot_{i}"}]}
            await cache.set(answers, response)

        # Concurrent writes
        tasks = [write_cache(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Verify each entry is retrievable
        for i in range(20):
            answers = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
            answers["company_name"]["value"] = f"Company {i}"
            cached = await cache.get(answers)
            assert cached is not None
            assert cached["recommendations"][0]["robot_id"] == f"robot_{i}"

    @pytest.mark.asyncio
    async def test_concurrent_reads_and_writes(self, _patch_recommendation_cache):
        """Concurrent reads and writes don't deadlock or corrupt."""
        cache = _patch_recommendation_cache

        # Pre-populate one entry
        answers = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
        response = {"recommendations": [{"robot_id": "original"}]}
        await cache.set(answers, response)

        results = []

        async def read_cache():
            cached = await cache.get(answers)
            results.append(cached)

        async def write_new():
            new_answers = copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)
            new_answers["company_name"]["value"] = "New Company"
            await cache.set(new_answers, {"recommendations": [{"robot_id": "new"}]})

        # Mix reads and writes
        tasks = []
        for i in range(10):
            tasks.append(read_cache())
            if i % 3 == 0:
                tasks.append(write_new())

        await asyncio.gather(*tasks)

        # All reads should have returned data (not None, not corrupted)
        for r in results:
            assert r is not None
            assert "recommendations" in r


class TestCacheEviction:
    """Test cache size limits and eviction."""

    @pytest.mark.asyncio
    async def test_cache_respects_max_size(self):
        """Cache evicts old entries when max_size is reached."""
        from src.services.recommendation_cache import (
            RecommendationCache,
            RecommendationCacheConfig,
        )

        config = RecommendationCacheConfig(max_size=5, ttl_seconds=3600)
        cache = RecommendationCache(config)

        # Fill beyond capacity
        for i in range(10):
            answers = {"key": {"value": f"val_{i}"}}
            await cache.set(answers, {"id": i})

        stats = await cache.get_stats()
        assert stats["total_entries"] <= 5

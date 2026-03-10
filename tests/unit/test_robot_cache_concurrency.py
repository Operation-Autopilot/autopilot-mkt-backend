"""Tests for robot catalog cache concurrency (thundering herd prevention)."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRobotCacheConcurrency:
    """Tests for _get_cached_robot_catalog with asyncio.Lock."""

    @pytest.mark.asyncio
    async def test_cache_returns_data_without_refetch_within_ttl(self) -> None:
        """Cached data should be returned without hitting the DB within TTL."""
        from src.services import agent_service

        # Reset cache state
        agent_service._robot_cache = None

        mock_catalog = [{"id": "robot-1", "name": "TestBot", "active": True}]

        with patch.object(
            agent_service.RobotCatalogService,
            "list_robots",
            new_callable=AsyncMock,
            return_value=mock_catalog,
        ) as mock_list:
            # First call — populates cache
            result1 = await agent_service._get_cached_robot_catalog()
            assert result1 == mock_catalog
            assert mock_list.call_count == 1

            # Second call — should use cache, not call list_robots again
            result2 = await agent_service._get_cached_robot_catalog()
            assert result2 == mock_catalog
            assert mock_list.call_count == 1

        # Cleanup
        agent_service._robot_cache = None

    @pytest.mark.asyncio
    async def test_cache_refetches_after_ttl_expiry(self) -> None:
        """Cache should refetch after TTL expires."""
        from src.services import agent_service

        old_ttl = agent_service._ROBOT_CACHE_TTL
        agent_service._ROBOT_CACHE_TTL = 0  # Expire immediately

        mock_catalog = [{"id": "robot-1", "name": "TestBot", "active": True}]

        try:
            agent_service._robot_cache = None

            with patch.object(
                agent_service.RobotCatalogService,
                "list_robots",
                new_callable=AsyncMock,
                return_value=mock_catalog,
            ) as mock_list:
                # First call
                await agent_service._get_cached_robot_catalog()
                assert mock_list.call_count == 1

                # Second call — TTL=0 so cache should be expired
                await agent_service._get_cached_robot_catalog()
                assert mock_list.call_count == 2
        finally:
            agent_service._ROBOT_CACHE_TTL = old_ttl
            agent_service._robot_cache = None

    @pytest.mark.asyncio
    async def test_concurrent_requests_only_fetch_once(self) -> None:
        """Multiple concurrent requests on expired cache should only trigger one DB fetch."""
        from src.services import agent_service

        agent_service._robot_cache = None
        call_count = 0

        async def slow_list_robots(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Simulate DB latency
            return [{"id": "robot-1", "name": "TestBot", "active": True}]

        with patch.object(
            agent_service.RobotCatalogService,
            "list_robots",
            side_effect=slow_list_robots,
        ):
            # Launch 10 concurrent requests
            results = await asyncio.gather(
                *[agent_service._get_cached_robot_catalog() for _ in range(10)]
            )

            # All should get the same data
            for result in results:
                assert len(result) == 1
                assert result[0]["name"] == "TestBot"

            # DB should have been called only once (lock prevents thundering herd)
            assert call_count == 1

        # Cleanup
        agent_service._robot_cache = None

    @pytest.mark.asyncio
    async def test_lock_exists_on_module(self) -> None:
        """Verify the lock is defined at module level."""
        from src.services import agent_service

        assert hasattr(agent_service, "_robot_cache_lock")
        assert isinstance(agent_service._robot_cache_lock, asyncio.Lock)

"""Unit tests for RecommendationService — UUID parsing safety."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest


class TestUUIDParsingSafety:
    """Tests for safe UUID parsing in recommendation service."""

    @pytest.mark.asyncio
    async def test_invalid_uuid_in_search_results_skipped(self) -> None:
        """Test that invalid UUID in search results is skipped, not crash."""
        from src.services.recommendation_service import RecommendationService

        with (
            patch("src.services.recommendation_service.get_settings") as mock_settings,
            patch("src.services.recommendation_service.get_openai_client"),
            patch("src.services.recommendation_service.get_rag_service") as mock_rag_fn,
            patch("src.services.recommendation_service.RobotCatalogService") as MockCatalog,
        ):
            mock_settings.return_value = MagicMock()

            mock_rag_instance = MagicMock()
            mock_rag_fn.return_value = mock_rag_instance

            mock_catalog_instance = MagicMock()
            MockCatalog.return_value = mock_catalog_instance

            # RAG returns results with one invalid UUID
            mock_rag_instance.search_robots_for_discovery = AsyncMock(
                return_value=[
                    {"robot_id": "not-a-uuid", "semantic_score": 0.9},
                    {"robot_id": "550e8400-e29b-41d4-a716-446655440000", "semantic_score": 0.8},
                ]
            )

            # get_robots_by_ids returns empty (fine for this test)
            mock_catalog_instance.get_robots_by_ids = AsyncMock(return_value=[])
            mock_catalog_instance.list_robots = AsyncMock(return_value=[])

            service = RecommendationService()
            robots = await service._get_semantic_candidates("test context")

            # The invalid UUID should be skipped, only valid one passed
            call_args = mock_catalog_instance.get_robots_by_ids.call_args[0][0]
            assert len(call_args) == 1
            assert call_args[0] == UUID("550e8400-e29b-41d4-a716-446655440000")

"""Tests for the refactored deterministic recommendation service (v3.0).

Verifies that:
1. Scoring is fully deterministic (no LLM needed for ranking)
2. UUIDs never pass through an LLM
3. Semantic scores boost the base rule-based score
4. LLM summaries are optional and non-blocking
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.schemas.roi import RecommendationReason, RecommendationsRequest
from src.services.recommendation_service import RecommendationService


def _make_robot(name: str, **overrides) -> dict:
    """Create a minimal robot dict for testing."""
    robot_id = overrides.pop("id", str(uuid4()))
    return {
        "id": robot_id,
        "name": name,
        "category": "Cleaning Robot",
        "vendor": "TestVendor",
        "best_for": overrides.pop("best_for", "general use"),
        "modes": overrides.pop("modes", ["vacuum", "mop"]),
        "surfaces": overrides.pop("surfaces", ["hard floor"]),
        "monthly_lease": overrides.pop("monthly_lease", 500),
        "time_efficiency": overrides.pop("time_efficiency", 0.85),
        "image_url": "",
        "key_reasons": [],
        "specs": [],
        "_semantic_score": overrides.pop("_semantic_score", 0.8),
        **overrides,
    }


def _make_answers(**overrides) -> dict:
    """Create minimal discovery answers."""
    base = {
        "company_type": {"value": "Warehouse", "questionId": 1, "key": "company_type", "label": "Type", "group": "Company"},
        "method": {"value": "Vacuum", "questionId": 2, "key": "method", "label": "Method", "group": "Operations"},
        "monthly_spend": {"value": "$3,001 - $5,000", "questionId": 3, "key": "monthly_spend", "label": "Budget", "group": "Economics"},
    }
    base.update(overrides)
    return base


class TestDeterministicScoring:
    """Tests for _score_candidates_deterministic."""

    def test_scores_robots_without_llm(self):
        """Core test: scoring works with zero LLM calls."""
        service = RecommendationService(
            rag_service=MagicMock(),
            robot_catalog_service=MagicMock(),
        )
        candidates = [
            _make_robot("WarehouseBot", best_for="industrial", modes=["vacuum", "sweep"], _semantic_score=0.9),
            _make_robot("CompactBot", best_for="restaurant", modes=["mop"], _semantic_score=0.5),
        ]

        scored = service._score_candidates_deterministic(candidates, _make_answers())

        assert len(scored) == 2
        # WarehouseBot should score higher (warehouse facility + vacuum mode + industrial best_for)
        assert scored[0]["_robot_name"] == "WarehouseBot"
        assert scored[0]["match_score"] > scored[1]["match_score"]
        # Both should have reasons
        assert len(scored[0]["reasons"]) > 0
        assert len(scored[1]["reasons"]) > 0

    def test_semantic_boost_affects_ranking(self):
        """Semantic similarity score should boost the total score."""
        service = RecommendationService(
            rag_service=MagicMock(),
            robot_catalog_service=MagicMock(),
        )
        # Two identical robots except for semantic score
        robot_a = _make_robot("RobotA", _semantic_score=1.0)
        robot_b = _make_robot("RobotB", _semantic_score=0.0)

        scored = service._score_candidates_deterministic([robot_a, robot_b], _make_answers())

        score_a = next(s for s in scored if s["_robot_name"] == "RobotA")
        score_b = next(s for s in scored if s["_robot_name"] == "RobotB")
        # RobotA should have ~15 points more from semantic boost
        assert score_a["match_score"] > score_b["match_score"]

    def test_uuids_preserved_exactly(self):
        """Robot IDs in output must exactly match input — no LLM truncation possible."""
        service = RecommendationService(
            rag_service=MagicMock(),
            robot_catalog_service=MagicMock(),
        )
        robot_id = str(uuid4())
        candidates = [_make_robot("TestBot", id=robot_id)]

        scored = service._score_candidates_deterministic(candidates, _make_answers())

        assert scored[0]["robot_id"] == robot_id  # Exact match, not truncated

    def test_label_assignment(self):
        """Labels should be assigned deterministically based on rank and price."""
        service = RecommendationService(
            rag_service=MagicMock(),
            robot_catalog_service=MagicMock(),
        )
        candidates = [
            _make_robot("BestBot", monthly_lease=800, _semantic_score=1.0, best_for="industrial", modes=["vacuum"]),
            _make_robot("ValueBot", monthly_lease=400, _semantic_score=0.8, best_for="industrial", modes=["vacuum"]),
            _make_robot("PremiumBot", monthly_lease=1500, _semantic_score=0.7, best_for="industrial", modes=["vacuum"]),
        ]

        scored = service._score_candidates_deterministic(candidates, _make_answers())

        assert scored[0]["label"] == "RECOMMENDED"  # Rank 1 always RECOMMENDED

    def test_reasons_include_semantic_relevance(self):
        """Every scored robot should have a 'Semantic Relevance' reason."""
        service = RecommendationService(
            rag_service=MagicMock(),
            robot_catalog_service=MagicMock(),
        )
        candidates = [_make_robot("TestBot")]

        scored = service._score_candidates_deterministic(candidates, _make_answers())

        reason_factors = [r.factor for r in scored[0]["reasons"]]
        assert "Semantic Relevance" in reason_factors


class TestLLMSummaryEnrichment:
    """Tests for _enrich_with_llm_summaries."""

    @pytest.mark.asyncio
    async def test_skips_llm_when_disabled(self):
        """When use_llm_recommendations is False, summaries should not call LLM."""
        settings = MagicMock()
        settings.use_llm_recommendations = False

        with patch("src.services.recommendation_service.get_settings", return_value=settings):
            service = RecommendationService(
                rag_service=MagicMock(),
                robot_catalog_service=MagicMock(),
            )
            service.settings = settings

            scored = [{"robot_id": str(uuid4()), "_robot_name": "Bot", "match_score": 80, "reasons": [], "summary": "Template summary"}]
            result = await service._enrich_with_llm_summaries(scored, "test context", top_k=1)

            assert result[0]["summary"] == "Template summary"  # Unchanged

    @pytest.mark.asyncio
    async def test_keeps_template_on_llm_failure(self):
        """If LLM fails, template summaries should be preserved."""
        settings = MagicMock()
        settings.use_llm_recommendations = True
        settings.openai_model_scoring = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_client.chat.create = AsyncMock(side_effect=Exception("API down"))

        with patch("src.services.recommendation_service.get_settings", return_value=settings):
            service = RecommendationService(
                rag_service=MagicMock(),
                robot_catalog_service=MagicMock(),
            )
            service.settings = settings
            service.client = mock_client

            scored = [{"robot_id": str(uuid4()), "_robot_name": "Bot", "match_score": 80, "reasons": [], "summary": "Template summary"}]
            result = await service._enrich_with_llm_summaries(scored, "test context", top_k=1)

            assert result[0]["summary"] == "Template summary"  # Preserved on failure


class TestBuildResponse:
    """Tests for _build_response."""

    def test_builds_valid_response(self):
        """Response should have correct structure with deterministic data."""
        service = RecommendationService(
            rag_service=MagicMock(),
            robot_catalog_service=MagicMock(),
        )
        robot_id = str(uuid4())
        candidates = [_make_robot("TestBot", id=robot_id)]
        scored = [{
            "robot_id": robot_id,
            "_robot_name": "TestBot",
            "match_score": 75.0,
            "label": "RECOMMENDED",
            "reasons": [
                RecommendationReason(factor="Test", explanation="Test reason", score_impact=10.0),
            ],
            "summary": "Great robot.",
        }]

        request = RecommendationsRequest(
            answers=_make_answers(),
            top_k=3,
        )

        response = service._build_response(scored, candidates, request)

        assert len(response.recommendations) == 1
        assert response.recommendations[0].robot_name == "TestBot"
        assert response.recommendations[0].match_score == 75.0
        assert response.algorithm_version == "3.0.0"
        assert response.recommendations[0].robot_id.hex  # Valid UUID

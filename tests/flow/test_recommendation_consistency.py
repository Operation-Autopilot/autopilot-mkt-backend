"""Flow tests for recommendation consistency.

Validates:
- Same answers → same #1 robot (chat and ROI endpoints return identical top pick)
- No mid-discovery cache pollution
- Cache invalidation on answer change
- Deterministic scoring idempotency
"""

import copy
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.flow.conftest import (
    COMPLETE_DISCOVERY_ANSWERS,
    SEED_ROBOTS,
    TEST_PROFILE_ID,
    TEST_USER_ID,
    FakeSupabase,
)


class TestRecommendationConsistency:
    """Ensure chat-derived and ROI-endpoint recommendations rank identically."""

    @pytest.mark.asyncio
    async def test_same_answers_same_top_robot_via_roi_endpoint(
        self, async_client: AsyncClient, complete_answers
    ):
        """POST /roi/recommendations with identical answers returns identical top robot."""
        # First request
        resp1 = await async_client.post(
            "/api/v1/roi/recommendations",
            json={"answers": complete_answers, "top_k": 3},
            headers={"X-Session-Token": "dummy"},
        )
        assert resp1.status_code == 200
        recs1 = resp1.json()["recommendations"]
        assert len(recs1) > 0

        # Second request with same answers
        resp2 = await async_client.post(
            "/api/v1/roi/recommendations",
            json={"answers": complete_answers, "top_k": 3},
            headers={"X-Session-Token": "dummy"},
        )
        assert resp2.status_code == 200
        recs2 = resp2.json()["recommendations"]

        # Top robot must be the same
        assert recs1[0]["robot_id"] == recs2[0]["robot_id"]
        assert recs1[0]["robot_name"] == recs2[0]["robot_name"]

    @pytest.mark.asyncio
    async def test_session_recommendations_match_direct_recommendations(
        self, async_client: AsyncClient, complete_answers
    ):
        """GET /roi/recommendations/session produces same top robot as POST /roi/recommendations."""
        # Create a session with all answers
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]

        await async_client.put(
            "/api/v1/sessions/me",
            headers={"X-Session-Token": token},
            json={"answers": complete_answers},
        )

        # Get recommendations via session endpoint
        session_recs_resp = await async_client.post(
            "/api/v1/roi/recommendations/session",
            headers={"X-Session-Token": token},
        )
        assert session_recs_resp.status_code == 200
        session_recs = session_recs_resp.json()["recommendations"]

        # Get recommendations via direct endpoint with same answers
        direct_recs_resp = await async_client.post(
            "/api/v1/roi/recommendations",
            json={"answers": complete_answers, "top_k": 3},
            headers={"X-Session-Token": token},
        )
        assert direct_recs_resp.status_code == 200
        direct_recs = direct_recs_resp.json()["recommendations"]

        # Top robot must match
        assert len(session_recs) > 0
        assert len(direct_recs) > 0
        assert session_recs[0]["robot_id"] == direct_recs[0]["robot_id"]

    @pytest.mark.asyncio
    async def test_no_recommendations_with_incomplete_answers(
        self, async_client: AsyncClient
    ):
        """Session endpoint returns 400 when no answers exist."""
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]

        resp = await async_client.post(
            "/api/v1/roi/recommendations/session",
            headers={"X-Session-Token": token},
        )
        assert resp.status_code == 400
        assert "No discovery answers" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_recommendations_response_has_required_fields(
        self, async_client: AsyncClient, complete_answers
    ):
        """Recommendations response includes all required fields per schema."""
        resp = await async_client.post(
            "/api/v1/roi/recommendations",
            json={"answers": complete_answers, "top_k": 3},
            headers={"X-Session-Token": "dummy"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "recommendations" in data
        assert "other_options" in data
        assert "total_robots_evaluated" in data
        assert "algorithm_version" in data
        assert data["total_robots_evaluated"] > 0

        for rec in data["recommendations"]:
            assert "robot_id" in rec
            assert "robot_name" in rec
            assert "match_score" in rec
            assert "rank" in rec
            assert "label" in rec
            assert rec["label"] in ["RECOMMENDED", "BEST VALUE", "UPGRADE", "ALTERNATIVE"]
            assert "projected_roi" in rec
            assert "reasons" in rec

    @pytest.mark.asyncio
    async def test_top_robot_labeled_recommended(
        self, async_client: AsyncClient, complete_answers
    ):
        """The #1 ranked robot always has label RECOMMENDED."""
        resp = await async_client.post(
            "/api/v1/roi/recommendations",
            json={"answers": complete_answers, "top_k": 3},
            headers={"X-Session-Token": "dummy"},
        )
        assert resp.status_code == 200
        recs = resp.json()["recommendations"]
        assert recs[0]["rank"] == 1
        assert recs[0]["label"] == "RECOMMENDED"


class TestDeterministicScoring:
    """Verify that the scoring algorithm is fully deterministic."""

    def test_score_candidates_idempotent(self, _patch_all, complete_answers):
        """Calling _score_candidates_deterministic N times yields identical output."""
        from src.services.recommendation_service import RecommendationService

        service = RecommendationService()

        # Prepare candidates with semantic scores
        candidates = copy.deepcopy(SEED_ROBOTS)
        for i, c in enumerate(candidates):
            c["_semantic_score"] = 0.8 - i * 0.05

        results = []
        for _ in range(50):
            scored = service._score_candidates_deterministic(candidates, complete_answers)
            results.append([(s["robot_id"], s["match_score"]) for s in scored])

        # All iterations must be identical
        for i in range(1, len(results)):
            assert results[i] == results[0], f"Iteration {i} differs from iteration 0"

    def test_different_answers_different_scores(self, _patch_all, complete_answers):
        """Different answers produce different top robot or scores."""
        from src.services.recommendation_service import RecommendationService

        service = RecommendationService()

        candidates = copy.deepcopy(SEED_ROBOTS)
        for i, c in enumerate(candidates):
            c["_semantic_score"] = 0.8 - i * 0.05

        scored1 = service._score_candidates_deterministic(candidates, complete_answers)

        # Change company_type to Restaurant
        alt_answers = copy.deepcopy(complete_answers)
        alt_answers["company_type"]["value"] = "Restaurant"
        scored2 = service._score_candidates_deterministic(candidates, alt_answers)

        # Scores or ordering should differ
        ids1 = [s["robot_id"] for s in scored1]
        ids2 = [s["robot_id"] for s in scored2]
        scores1 = [s["match_score"] for s in scored1]
        scores2 = [s["match_score"] for s in scored2]
        assert ids1 != ids2 or scores1 != scores2, "Different answers should produce different scoring"


class TestCacheInvalidation:
    """Verify recommendation cache invalidates when answers change."""

    @pytest.mark.asyncio
    async def test_cache_hit_with_same_answers(self, _patch_recommendation_cache, complete_answers):
        """Same answers → cache hit (no re-scoring)."""
        from src.services.recommendation_cache import RecommendationCache

        cache: RecommendationCache = _patch_recommendation_cache
        mock_response = {"recommendations": [{"robot_id": "test"}]}

        await cache.set(complete_answers, mock_response)
        cached = await cache.get(complete_answers)
        assert cached is not None
        assert cached["recommendations"][0]["robot_id"] == "test"

    @pytest.mark.asyncio
    async def test_cache_miss_after_answer_change(self, _patch_recommendation_cache, complete_answers):
        """Changed answers → cache miss (different hash)."""
        from src.services.recommendation_cache import RecommendationCache

        cache: RecommendationCache = _patch_recommendation_cache
        mock_response = {"recommendations": [{"robot_id": "test"}]}

        await cache.set(complete_answers, mock_response)

        # Modify an answer
        modified = copy.deepcopy(complete_answers)
        modified["company_type"]["value"] = "Restaurant"

        cached = await cache.get(modified)
        assert cached is None, "Cache should miss after answer change"

    @pytest.mark.asyncio
    async def test_answers_hash_deterministic(self, complete_answers):
        """compute_answers_hash produces same hash for same answers."""
        from src.services.discovery_profile_service import compute_answers_hash

        hash1 = compute_answers_hash(complete_answers)
        hash2 = compute_answers_hash(complete_answers)
        assert hash1 == hash2

        # Different answers → different hash
        modified = copy.deepcopy(complete_answers)
        modified["company_name"]["value"] = "Different Name"
        hash3 = compute_answers_hash(modified)
        assert hash3 != hash1

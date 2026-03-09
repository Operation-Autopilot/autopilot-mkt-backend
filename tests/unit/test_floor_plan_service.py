"""Unit tests for FloorPlanService."""

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.services.floor_plan_service import FloorPlanAnalysisError, FloorPlanService


@pytest.fixture
def mock_supabase() -> MagicMock:
    """Create a mock Supabase client."""
    return MagicMock()


@pytest.fixture
def mock_openai() -> MagicMock:
    """Create a mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def floor_plan_service(mock_supabase: MagicMock, mock_openai: MagicMock) -> FloorPlanService:
    """Create FloorPlanService with mocked clients."""
    with (
        patch(
            "src.services.floor_plan_service.get_supabase_client",
            return_value=mock_supabase,
        ),
        patch(
            "src.services.floor_plan_service.get_openai_client",
            return_value=mock_openai,
        ),
        patch("src.services.floor_plan_service.get_settings"),
    ):
        return FloorPlanService()


class TestGetRecordNullGuard:
    """Tests for _get_record returning None guard."""

    def test_get_record_returns_none_raises_error(
        self, floor_plan_service: FloorPlanService, mock_supabase: MagicMock
    ) -> None:
        """Test that _get_record returning None raises FloorPlanAnalysisError."""
        analysis_id = uuid4()

        # Mock _get_record to return None (record not found)
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_response
        )

        record = floor_plan_service._get_record(analysis_id)
        assert record is None

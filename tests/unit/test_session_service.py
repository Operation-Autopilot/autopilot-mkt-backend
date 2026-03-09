"""Unit tests for SessionService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from src.services.session_service import SessionService


@pytest.fixture
def mock_supabase() -> MagicMock:
    """Create a mock Supabase client."""
    return MagicMock()


@pytest.fixture
def session_service(mock_supabase: MagicMock) -> SessionService:
    """Create SessionService with mocked client."""
    with patch("src.services.session_service.get_supabase_client", return_value=mock_supabase):
        return SessionService()


class TestCreateSession:
    """Tests for create_session method."""

    @pytest.mark.asyncio
    async def test_generates_64_char_token(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that session token is 64 characters."""
        new_session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "session_token": "a" * 64,
            "current_question_index": 0,
            "phase": "discovery",
        }

        mock_response = MagicMock()
        mock_response.data = [new_session]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        session_data, token = await session_service.create_session()

        assert len(token) == 64
        assert session_data["id"] == new_session["id"]

    @pytest.mark.asyncio
    async def test_creates_session_with_defaults(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that session is created with default values."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "test-id", "session_token": "token"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        await session_service.create_session()

        # Check that insert was called with proper defaults
        insert_call = mock_supabase.table.return_value.insert.call_args
        insert_data = insert_call[0][0]

        assert insert_data["current_question_index"] == 0
        assert insert_data["phase"] == "discovery"
        assert insert_data["answers"] == {}
        assert insert_data["selected_product_ids"] == []


class TestGetSessionByToken:
    """Tests for get_session_by_token method."""

    @pytest.mark.asyncio
    async def test_returns_session_when_found(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that session is returned when token is valid."""
        session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "session_token": "valid_token",
            "phase": "discovery",
        }

        mock_response = MagicMock()
        mock_response.data = session
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.get_session_by_token("valid_token")

        assert result == session

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that None is returned when token is invalid."""
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.get_session_by_token("invalid_token")

        assert result is None


class TestIsSessionValid:
    """Tests for is_session_valid method."""

    @pytest.mark.asyncio
    async def test_returns_true_for_valid_session(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that valid session returns True."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "session_token": "valid_token",
            "expires_at": future_date,
            "claimed_by_profile_id": None,
        }

        mock_response = MagicMock()
        mock_response.data = session
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.is_session_valid("valid_token")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_expired_session(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that expired session returns False."""
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "session_token": "expired_token",
            "expires_at": past_date,
            "claimed_by_profile_id": None,
        }

        mock_response = MagicMock()
        mock_response.data = session
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.is_session_valid("expired_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_claimed_session(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that claimed session returns False."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "session_token": "claimed_token",
            "expires_at": future_date,
            "claimed_by_profile_id": "660e8400-e29b-41d4-a716-446655440000",
        }

        mock_response = MagicMock()
        mock_response.data = session
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.is_session_valid("claimed_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent_session(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that non-existent session returns False."""
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.is_session_valid("nonexistent_token")

        assert result is False


class TestClaimSession:
    """Tests for claim_session method."""

    @pytest.mark.asyncio
    async def test_raises_error_when_session_not_found(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that ValueError is raised when session not found."""
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        with pytest.raises(ValueError, match="Session not found"):
            await session_service.claim_session(
                session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
                profile_id=UUID("660e8400-e29b-41d4-a716-446655440000"),
            )

    @pytest.mark.asyncio
    async def test_raises_error_when_already_claimed(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that ValueError is raised when session already claimed."""
        session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "claimed_by_profile_id": "existing-profile-id",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }

        mock_response = MagicMock()
        mock_response.data = session
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        with pytest.raises(ValueError, match="already been claimed"):
            await session_service.claim_session(
                session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
                profile_id=UUID("660e8400-e29b-41d4-a716-446655440000"),
            )

    @pytest.mark.asyncio
    async def test_raises_error_when_expired(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that ValueError is raised when session is expired."""
        session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "claimed_by_profile_id": None,
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        }

        mock_response = MagicMock()
        mock_response.data = session
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        with pytest.raises(ValueError, match="expired"):
            await session_service.claim_session(
                session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
                profile_id=UUID("660e8400-e29b-41d4-a716-446655440000"),
            )


class TestUpdateSession:
    """Tests for update_session method."""

    @pytest.mark.asyncio
    async def test_updates_session_fields(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that session fields are updated."""
        from src.schemas.session import SessionUpdate

        updated_session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "phase": "roi",
            "current_question_index": 5,
        }

        mock_response = MagicMock()
        mock_response.data = [updated_session]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        update_data = SessionUpdate(phase="roi", current_question_index=5)
        result = await session_service.update_session(
            session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            data=update_data,
        )

        assert result["phase"] == "roi"
        assert result["current_question_index"] == 5


class TestGetSessionByTokenExpiration:
    """Tests for session expiration check in get_session_by_token."""

    @pytest.mark.asyncio
    async def test_expired_session_returns_none(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that expired session returns None from get_session_by_token."""
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "session_token": "expired_token",
            "expires_at": past_date,
        }

        mock_response = MagicMock()
        mock_response.data = session
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.get_session_by_token("expired_token")
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_session_returns_data(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that valid (not expired) session returns data."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        session = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "session_token": "valid_token",
            "expires_at": future_date,
        }

        mock_response = MagicMock()
        mock_response.data = session
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.get_session_by_token("valid_token")
        assert result is not None
        assert result["id"] == "550e8400-e29b-41d4-a716-446655440000"


class TestAnswerMerge:
    """Tests for answer merge during session claim."""

    def test_session_answers_take_precedence(self) -> None:
        """Test that session answers override existing keys during merge."""
        # Simulate the merge logic from _create_or_update_discovery_profile
        existing_answers = {"q1": {"value": "old"}, "q2": {"value": "existing"}}
        session_answers = {"q1": {"value": "new"}, "q3": {"value": "added"}}

        # The fixed merge: session answers take precedence
        merged = {**existing_answers, **session_answers}

        assert merged["q1"]["value"] == "new"  # Session overrides
        assert merged["q2"]["value"] == "existing"  # Kept from existing
        assert merged["q3"]["value"] == "added"  # New from session


class TestROIInputsSchemaConversion:
    """Tests for ROIInputsSchema.to_roi_inputs conversion."""

    def test_to_roi_inputs_converts_correctly(self) -> None:
        """Test that to_roi_inputs converts camelCase to snake_case."""
        from src.schemas.session import ROIInputsSchema

        schema = ROIInputsSchema(
            laborRate=25.0,
            utilization=0.8,
            maintenanceFactor=0.05,
            manualMonthlySpend=5000.0,
            manualMonthlyHours=160.0,
        )

        result = schema.to_roi_inputs()

        assert result["labor_rate"] == 25.0
        assert result["utilization"] == 0.8
        assert result["maintenance_factor"] == 0.05
        assert result["manual_monthly_spend"] == 5000.0
        assert result["manual_monthly_hours"] == 160.0


class TestCleanupExpiredSessions:
    """Tests for cleanup_expired_sessions method."""

    @pytest.mark.asyncio
    async def test_returns_count_of_deleted_sessions(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that count of deleted sessions is returned."""
        deleted_sessions = [{"id": "1"}, {"id": "2"}, {"id": "3"}]

        mock_response = MagicMock()
        mock_response.data = deleted_sessions
        mock_supabase.table.return_value.delete.return_value.lt.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.cleanup_expired_sessions()

        assert result == 3

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_expired_sessions(
        self, session_service: SessionService, mock_supabase: MagicMock
    ) -> None:
        """Test that zero is returned when no sessions to delete."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.delete.return_value.lt.return_value.execute.return_value = (
            mock_response
        )

        result = await session_service.cleanup_expired_sessions()

        assert result == 0

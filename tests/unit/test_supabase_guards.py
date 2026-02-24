"""Tests for Supabase data[0] guards.

Ensures that services raise ValueError (not IndexError) when Supabase
returns empty data arrays from .execute().
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import UUID


# ---------------------------------------------------------------------------
# 1. checkout_service - empty data on insert
# ---------------------------------------------------------------------------

class TestCheckoutServiceGuard:
    """checkout_service.create_checkout_session should raise ValueError on empty data."""

    @pytest.fixture
    def mock_supabase(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_create_checkout_session_empty_data_raises_valueerror(self, mock_supabase):
        """Insert into orders returns data=[] -> ValueError, not IndexError."""
        with patch("src.services.checkout_service.get_supabase_client", return_value=mock_supabase), \
             patch("src.services.checkout_service.get_stripe") as mock_get_stripe, \
             patch("src.services.checkout_service.get_stripe_api_key", return_value="sk_test_key"), \
             patch("src.services.checkout_service.RobotCatalogService") as MockRobotCatalog:

            mock_stripe = MagicMock()
            mock_get_stripe.return_value = mock_stripe

            mock_robot_service = MagicMock()
            MockRobotCatalog.return_value = mock_robot_service
            mock_robot_service.get_robot_with_stripe_ids = AsyncMock(return_value={
                "name": "Test Robot",
                "monthly_lease": 100,
                "active": True,
                "stripe_lease_price_id": "price_test_123",
            })

            # The critical mock: insert into orders returns empty data
            mock_execute = MagicMock()
            mock_execute.data = []
            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

            from src.services.checkout_service import CheckoutService
            service = CheckoutService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_checkout_session(
                    product_id=UUID("11111111-1111-1111-1111-111111111111"),
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                    profile_id=UUID("22222222-2222-2222-2222-222222222222"),
                )


# ---------------------------------------------------------------------------
# 2. invitation_service - empty data on insert
# ---------------------------------------------------------------------------

class TestInvitationServiceGuard:
    """invitation_service should raise ValueError on empty data."""

    @pytest.fixture
    def mock_supabase(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_create_invitation_empty_data_raises_valueerror(self, mock_supabase):
        """Insert into invitations returns data=[] -> ValueError, not IndexError."""
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

        with patch("src.services.invitation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.invitation_service import InvitationService
            from src.schemas.company import InvitationCreate

            service = InvitationService()
            data = InvitationCreate(email="test@example.com")

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_invitation(
                    company_id=UUID("11111111-1111-1111-1111-111111111111"),
                    data=data,
                    invited_by=UUID("22222222-2222-2222-2222-222222222222"),
                )

    @pytest.mark.asyncio
    async def test_accept_invitation_empty_update_raises_valueerror(self, mock_supabase):
        """Update in accept_invitation returns data=[] -> ValueError."""
        with patch("src.services.invitation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.invitation_service import InvitationService
            service = InvitationService()

            # Mock get_invitation to return a valid invitation
            mock_get_response = MagicMock()
            mock_get_response.data = {
                "id": "33333333-3333-3333-3333-333333333333",
                "company_id": "11111111-1111-1111-1111-111111111111",
                "email": "test@example.com",
                "status": "pending",
                "expires_at": "2099-12-31T23:59:59+00:00",
            }
            mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_get_response

            # Mock existing member check (not already a member)
            mock_member_response = MagicMock()
            mock_member_response.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_member_response

            # Mock the member insert (succeeds)
            mock_insert_response = MagicMock()
            mock_insert_response.data = [{"id": "member-1"}]
            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_response

            # Mock the invitation update to return empty data
            mock_update_response = MagicMock()
            mock_update_response.data = []
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_response

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.accept_invitation(
                    invitation_id=UUID("33333333-3333-3333-3333-333333333333"),
                    profile_id=UUID("22222222-2222-2222-2222-222222222222"),
                    user_email="test@example.com",
                )

    @pytest.mark.asyncio
    async def test_decline_invitation_empty_update_raises_valueerror(self, mock_supabase):
        """Update in decline_invitation returns data=[] -> ValueError."""
        with patch("src.services.invitation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.invitation_service import InvitationService
            service = InvitationService()

            # Mock get_invitation to return a valid invitation
            mock_get_response = MagicMock()
            mock_get_response.data = {
                "id": "33333333-3333-3333-3333-333333333333",
                "company_id": "11111111-1111-1111-1111-111111111111",
                "email": "test@example.com",
                "status": "pending",
                "expires_at": "2099-12-31T23:59:59+00:00",
            }
            mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_get_response

            # Mock the update to return empty data
            mock_update_response = MagicMock()
            mock_update_response.data = []
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_response

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.decline_invitation(
                    invitation_id=UUID("33333333-3333-3333-3333-333333333333"),
                    user_email="test@example.com",
                )


# ---------------------------------------------------------------------------
# 3. company_service - empty data on insert
# ---------------------------------------------------------------------------

class TestCompanyServiceGuard:
    """company_service.create_company should raise ValueError on empty data."""

    @pytest.fixture
    def mock_supabase(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_create_company_empty_data_raises_valueerror(self, mock_supabase):
        """Insert into companies returns data=[] -> ValueError, not IndexError."""
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

        with patch("src.services.company_service.get_supabase_client", return_value=mock_supabase):
            from src.services.company_service import CompanyService
            from src.schemas.company import CompanyCreate

            service = CompanyService()
            data = CompanyCreate(name="Test Company")

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_company(
                    data=data,
                    owner_profile_id=UUID("22222222-2222-2222-2222-222222222222"),
                )


# ---------------------------------------------------------------------------
# 4. profile_service - empty data on insert (get_or_create path)
# ---------------------------------------------------------------------------

class TestProfileServiceGuard:
    """profile_service.get_or_create_profile should raise ValueError on empty insert data."""

    @pytest.fixture
    def mock_supabase(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_or_create_profile_empty_data_raises_valueerror(self, mock_supabase):
        """When profile doesn't exist and insert returns data=[] -> ValueError."""
        # First call: select returns empty (no existing profile)
        mock_select_response = MagicMock()
        mock_select_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_select_response

        # Second call: insert returns empty data
        mock_insert_response = MagicMock()
        mock_insert_response.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_response

        with patch("src.services.profile_service.get_supabase_client", return_value=mock_supabase):
            from src.services.profile_service import ProfileService
            service = ProfileService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.get_or_create_profile(
                    user_id=UUID("11111111-1111-1111-1111-111111111111"),
                    email="test@example.com",
                )


# ---------------------------------------------------------------------------
# 5. session_service - empty data on insert
# ---------------------------------------------------------------------------

class TestSessionServiceGuard:
    """session_service.create_session should raise ValueError on empty data."""

    @pytest.fixture
    def mock_supabase(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_create_session_empty_data_raises_valueerror(self, mock_supabase):
        """Insert into sessions returns data=[] -> ValueError, not IndexError."""
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

        with patch("src.services.session_service.get_supabase_client", return_value=mock_supabase):
            from src.services.session_service import SessionService
            service = SessionService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_session()


# ---------------------------------------------------------------------------
# 6. conversation_service - empty data on insert / create operations
# ---------------------------------------------------------------------------

class TestConversationServiceGuard:
    """conversation_service operations should raise ValueError on empty data."""

    @pytest.fixture
    def mock_supabase(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_create_conversation_empty_data_raises_valueerror(self, mock_supabase):
        """Insert into conversations returns data=[] -> ValueError."""
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

        with patch("src.services.conversation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.conversation_service import ConversationService
            service = ConversationService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_conversation(
                    user_profile_id=UUID("11111111-1111-1111-1111-111111111111"),
                )

    @pytest.mark.asyncio
    async def test_add_message_empty_data_raises_valueerror(self, mock_supabase):
        """Insert into messages returns data=[] -> ValueError."""
        with patch("src.services.conversation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.conversation_service import ConversationService
            from src.models.message import MessageRole

            # Mock asyncio.to_thread to just call the function
            mock_execute = MagicMock()
            mock_execute.data = []

            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

            service = ConversationService()

            with patch("asyncio.to_thread", new_callable=AsyncMock, side_effect=lambda fn, *a, **kw: fn(*a, **kw) if callable(fn) else mock_execute) as mock_thread:
                mock_thread.return_value = mock_execute

                with pytest.raises(ValueError, match="Database operation returned no data"):
                    await service.add_message(
                        conversation_id=UUID("11111111-1111-1111-1111-111111111111"),
                        role=MessageRole.USER,
                        content="Hello",
                    )

    @pytest.mark.asyncio
    async def test_create_conversation_for_session_empty_data_raises_valueerror(self, mock_supabase):
        """Insert into conversations (session) returns data=[] -> ValueError."""
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

        with patch("src.services.conversation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.conversation_service import ConversationService
            service = ConversationService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_conversation_for_session(
                    session_id=UUID("11111111-1111-1111-1111-111111111111"),
                )

    @pytest.mark.asyncio
    async def test_create_fresh_for_profile_empty_data_raises_valueerror(self, mock_supabase):
        """Insert for fresh profile conversation returns data=[] -> ValueError."""
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

        with patch("src.services.conversation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.conversation_service import ConversationService
            service = ConversationService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_fresh_for_profile(
                    profile_id=UUID("11111111-1111-1111-1111-111111111111"),
                )

    @pytest.mark.asyncio
    async def test_create_fresh_for_session_empty_data_raises_valueerror(self, mock_supabase):
        """Insert for fresh session conversation returns data=[] -> ValueError."""
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_execute

        with patch("src.services.conversation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.conversation_service import ConversationService
            service = ConversationService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_fresh_for_session(
                    session_id=UUID("11111111-1111-1111-1111-111111111111"),
                )

    @pytest.mark.asyncio
    async def test_get_or_create_current_for_profile_empty_insert_raises_valueerror(self, mock_supabase):
        """When no existing conversation, insert returns data=[] -> ValueError."""
        # Select returns empty (no existing conversation)
        mock_select_response = MagicMock()
        mock_select_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_select_response

        # Insert returns empty data
        mock_insert_response = MagicMock()
        mock_insert_response.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_response

        with patch("src.services.conversation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.conversation_service import ConversationService
            service = ConversationService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.get_or_create_current_for_profile(
                    profile_id=UUID("11111111-1111-1111-1111-111111111111"),
                )

    @pytest.mark.asyncio
    async def test_get_or_create_current_for_session_empty_insert_raises_valueerror(self, mock_supabase):
        """When no existing session conversation, insert returns data=[] -> ValueError."""
        # Select returns empty (no existing conversation)
        mock_select_response = MagicMock()
        mock_select_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_select_response

        # Insert returns empty data
        mock_insert_response = MagicMock()
        mock_insert_response.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_response

        with patch("src.services.conversation_service.get_supabase_client", return_value=mock_supabase):
            from src.services.conversation_service import ConversationService
            service = ConversationService()

            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.get_or_create_current_for_session(
                    session_id=UUID("11111111-1111-1111-1111-111111111111"),
                )

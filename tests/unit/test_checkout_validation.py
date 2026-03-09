"""Tests for checkout validation and schema fixes."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4


@pytest.fixture
def mock_supabase():
    mock_client = MagicMock()
    with patch("src.services.checkout_service.get_supabase_client", return_value=mock_client):
        yield mock_client


class TestCheckoutValidation:
    """Tests for checkout input validation."""

    @pytest.mark.asyncio
    async def test_robot_without_stripe_price_raises_error(self, mock_supabase):
        """Robot without stripe_lease_price_id should raise ValueError."""
        with patch("src.core.stripe.get_stripe") as mock_stripe_fn, \
             patch("src.services.robot_catalog_service.RobotCatalogService.get_robot_with_stripe_ids", new_callable=AsyncMock) as mock_robot, \
             patch("src.core.stripe.get_stripe_api_key", return_value="sk_test_key"):

            mock_stripe_fn.return_value = MagicMock()
            mock_robot.return_value = {
                "name": "TestBot",
                "active": True,
                "monthly_lease": 500,
                "stripe_lease_price_id": None,  # Missing!
            }

            from src.services.checkout_service import CheckoutService
            service = CheckoutService()

            with pytest.raises(ValueError, match="missing price configuration"):
                await service.create_checkout_session(
                    product_id=uuid4(),
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )

    @pytest.mark.asyncio
    async def test_robot_with_valid_price_passes_validation(self, mock_supabase):
        """Robot with valid stripe_lease_price_id should pass validation (not raise missing price error).

        We let the flow proceed past validation and fail at order insert — proving
        the price validation check passed.
        """
        with patch("src.core.stripe.get_stripe") as mock_stripe_fn, \
             patch("src.services.robot_catalog_service.RobotCatalogService.get_robot_with_stripe_ids", new_callable=AsyncMock) as mock_robot, \
             patch("src.core.stripe.get_stripe_api_key", return_value="sk_test_key"):

            mock_stripe_fn.return_value = MagicMock()
            mock_robot.return_value = {
                "name": "TestBot",
                "active": True,
                "monthly_lease": 500,
                "stripe_lease_price_id": "price_test123",  # Valid price ID
            }

            # Make order insert return empty data to trigger our guard
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])

            from src.services.checkout_service import CheckoutService
            service = CheckoutService()

            # Should NOT raise "missing price configuration" — should fail later at order insert
            with pytest.raises(ValueError, match="Database operation returned no data"):
                await service.create_checkout_session(
                    product_id=uuid4(),
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )


class TestOrderStatusSchema:
    """Tests for order status schema completeness."""

    def test_payment_pending_is_valid_status(self):
        """payment_pending should be a valid OrderStatus."""
        from src.schemas.checkout import OrderStatus
        # Check that "payment_pending" is in the Literal values
        import typing
        args = typing.get_args(OrderStatus)
        assert "payment_pending" in args, f"payment_pending not in OrderStatus: {args}"

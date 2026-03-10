"""Tests for webhook security fixes."""

import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestWebhookReplayPrevention:
    """Tests for webhook replay attack prevention."""

    def test_first_event_processed_successfully(self, client, mock_supabase_client):
        """First webhook event should be processed normally."""
        from src.api.routes import webhooks
        webhooks._processed_events.clear()

        mock_event = {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"order_id": "order-123"},
                    "customer_details": {},
                    "payment_status": "paid",
                    "customer": "cus_123",
                    "subscription": "sub_123",
                }
            },
        }

        mock_update_response = MagicMock()
        mock_update_response.data = [{"id": "order-123", "status": "completed"}]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_response

        with patch("src.services.checkout_service.CheckoutService.verify_webhook_signature") as mock_verify, \
             patch("src.services.checkout_service.CheckoutService.handle_checkout_completed", new_callable=AsyncMock):
            mock_verify.return_value = (mock_event, False)

            response = client.post(
                "/api/v1/webhooks/stripe",
                content=b"test-payload",
                headers={"stripe-signature": "test-sig"},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "received"

    def test_duplicate_event_rejected(self, client, mock_supabase_client):
        """Same event ID sent twice should be deduplicated."""
        from src.api.routes import webhooks
        webhooks._processed_events.clear()

        mock_event = {
            "id": "evt_duplicate_456",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"order_id": "order-456"},
                    "customer_details": {},
                    "payment_status": "paid",
                    "customer": "cus_456",
                    "subscription": "sub_456",
                }
            },
        }

        with patch("src.services.checkout_service.CheckoutService.verify_webhook_signature") as mock_verify, \
             patch("src.services.checkout_service.CheckoutService.handle_checkout_completed", new_callable=AsyncMock):
            mock_verify.return_value = (mock_event, False)

            mock_update_response = MagicMock()
            mock_update_response.data = [{"id": "order-456", "status": "completed"}]
            mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_response

            # First call
            response1 = client.post(
                "/api/v1/webhooks/stripe",
                content=b"test-payload",
                headers={"stripe-signature": "test-sig"},
            )
            assert response1.status_code == 200

            # Second call with same event ID
            response2 = client.post(
                "/api/v1/webhooks/stripe",
                content=b"test-payload",
                headers={"stripe-signature": "test-sig"},
            )
            assert response2.status_code == 200
            assert response2.json()["status"] == "already_processed"

    def test_event_without_id_still_processed(self, client, mock_supabase_client):
        """Events without an ID should still be processed (backward compat)."""
        from src.api.routes import webhooks
        webhooks._processed_events.clear()

        mock_event = {
            "type": "checkout.session.expired",
            "data": {"object": {"metadata": {"order_id": "order-789"}}},
        }

        with patch("src.services.checkout_service.CheckoutService.verify_webhook_signature") as mock_verify, \
             patch("src.services.checkout_service.CheckoutService.handle_checkout_expired", new_callable=AsyncMock):
            mock_verify.return_value = (mock_event, False)

            response = client.post(
                "/api/v1/webhooks/stripe",
                content=b"test-payload",
                headers={"stripe-signature": "test-sig"},
            )
            assert response.status_code == 200


class TestWebhookSecretLogging:
    """Tests for webhook secret not being logged."""

    def test_verify_webhook_does_not_log_secrets(self, mock_supabase_client):
        """verify_webhook_signature should not log secret substrings."""
        with patch("src.services.checkout_service.get_stripe") as mock_stripe_fn, \
             patch("src.services.checkout_service.get_stripe_api_key", return_value="sk_test_key"):
            mock_stripe = MagicMock()
            mock_stripe_fn.return_value = mock_stripe
            mock_stripe.Webhook.construct_event.side_effect = Exception("test")

            from src.services.checkout_service import CheckoutService

            # Capture log output
            log_records = []
            handler = logging.Handler()
            handler.emit = lambda record: log_records.append(record)

            logger = logging.getLogger("src.services.checkout_service")
            logger.addHandler(handler)
            old_level = logger.level
            logger.setLevel(logging.DEBUG)

            try:
                service = CheckoutService()
                try:
                    service.verify_webhook_signature(b"payload", "sig")
                except (ValueError, Exception):
                    pass

                # Check that no log message contains webhook secret substrings
                for record in log_records:
                    msg = record.getMessage()
                    assert "whsec_" not in msg, f"Webhook secret leaked in log: {msg}"
            finally:
                logger.removeHandler(handler)
                logger.setLevel(old_level)

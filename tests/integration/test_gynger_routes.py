"""Integration tests for Gynger financing API routes."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gynger_sig(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# POST /checkout/gynger-session
# ---------------------------------------------------------------------------


class TestCreateGyngerSession:
    """Tests for POST /api/v1/checkout/gynger-session."""

    @pytest.fixture
    def mock_robot(self):
        return {
            "id": "robot-uuid-123",
            "name": "TestBot",
            "category": "Test",
            "monthly_lease": 500.00,
            "purchase_price": 5000.00,
            "active": True,
            "stripe_product_id": "placeholder",
            "stripe_lease_price_id": "placeholder",
        }

    @pytest.fixture
    def mock_order(self):
        return {
            "id": "order-uuid-456",
            "status": "pending",
            "total_cents": 500000,
            "payment_provider": "gynger",
        }

    def test_create_gynger_session_success(self, mock_robot, mock_order):
        """Happy path: returns application_url and order_id."""
        with (
            patch("src.api.routes.checkout.RobotCatalogService") as mock_catalog_cls,
            patch("src.api.routes.checkout.GyngerService") as mock_gynger_cls,
            patch("src.api.routes.checkout.CheckoutService") as mock_checkout_cls,
            patch("src.api.routes.checkout._get_profile_for_auth", new=AsyncMock(return_value=(None, None))),
        ):
            # Setup robot catalog mock
            mock_catalog = MagicMock()
            mock_catalog.get_robot = AsyncMock(return_value=mock_robot)
            mock_catalog_cls.return_value = mock_catalog

            # Setup checkout service mock (for order creation)
            mock_checkout = MagicMock()
            mock_checkout._validate_redirect_url = MagicMock(side_effect=lambda x: x)
            mock_order_result = MagicMock()
            mock_order_result.data = [mock_order]
            mock_checkout._execute_sync = AsyncMock(return_value=mock_order_result)
            mock_checkout.client = MagicMock()
            mock_checkout_cls.return_value = mock_checkout

            # Setup Gynger service mock
            mock_gynger = MagicMock()
            mock_gynger.create_financing_application = AsyncMock(
                return_value={
                    "application_id": "gynger-app-abc123",
                    "application_url": "https://app.gynger.io/apply/abc123",
                }
            )
            mock_gynger_cls.return_value = mock_gynger

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/checkout/gynger-session",
                    json={
                        "product_id": "robot-uuid-123",
                        "success_url": "http://localhost:3000/success",
                        "cancel_url": "http://localhost:3000/cancel",
                    },
                )

        assert resp.status_code == 201
        data = resp.json()
        assert data["application_url"] == "https://app.gynger.io/apply/abc123"
        assert data["gynger_application_id"] == "gynger-app-abc123"
        assert "order_id" in data

    def test_create_gynger_session_invalid_redirect_url(self):
        """Disallowed redirect domain returns 400."""
        with (
            patch("src.api.routes.checkout.CheckoutService") as mock_checkout_cls,
            patch("src.api.routes.checkout._get_profile_for_auth", new=AsyncMock(return_value=(None, None))),
        ):
            from src.services.checkout_service import CheckoutService as RealCheckoutService

            mock_checkout = MagicMock()
            mock_checkout._validate_redirect_url = RealCheckoutService._validate_redirect_url.__func__.__get__(
                mock_checkout, type(mock_checkout)
            )
            mock_checkout_cls.return_value = mock_checkout

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/checkout/gynger-session",
                    json={
                        "product_id": "robot-uuid-123",
                        "success_url": "https://evil.attacker.com/steal",
                        "cancel_url": "http://localhost:3000/cancel",
                    },
                )

        assert resp.status_code == 400

    def test_create_gynger_session_product_not_found(self):
        """Robot not found returns 400."""
        with (
            patch("src.api.routes.checkout.RobotCatalogService") as mock_catalog_cls,
            patch("src.api.routes.checkout.GyngerService"),
            patch("src.api.routes.checkout.CheckoutService") as mock_checkout_cls,
            patch("src.api.routes.checkout._get_profile_for_auth", new=AsyncMock(return_value=(None, None))),
        ):
            mock_checkout = MagicMock()
            mock_checkout._validate_redirect_url = MagicMock(side_effect=lambda x: x)
            mock_checkout_cls.return_value = mock_checkout

            mock_catalog = MagicMock()
            mock_catalog.get_robot = AsyncMock(return_value=None)
            mock_catalog_cls.return_value = mock_catalog

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/checkout/gynger-session",
                    json={
                        "product_id": "nonexistent-uuid",
                        "success_url": "http://localhost:3000/success",
                        "cancel_url": "http://localhost:3000/cancel",
                    },
                )

        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /webhooks/gynger
# ---------------------------------------------------------------------------


class TestGyngerWebhook:
    """Tests for POST /api/v1/webhooks/gynger."""

    WEBHOOK_SECRET = "test-gynger-webhook-secret"

    def _build_event(self, event_type: str, order_id: str = "order-uuid-456") -> tuple[bytes, str]:
        event = {
            "id": f"evt_{event_type.replace('.', '_')}_123",
            "type": event_type,
            "data": {
                "application_id": "gynger-app-abc123",
                "metadata": {"order_id": order_id},
            },
        }
        payload = json.dumps(event).encode()
        sig = _make_gynger_sig(self.WEBHOOK_SECRET, payload)
        return payload, sig

    def test_gynger_webhook_application_approved(self):
        """application.approved event triggers handle_application_approved."""
        payload, sig = self._build_event("application.approved")

        with patch("src.api.routes.webhooks.GyngerService") as mock_gynger_cls:
            mock_gynger = MagicMock()
            mock_gynger.verify_webhook_signature = MagicMock(
                return_value=json.loads(payload)
            )
            mock_gynger.handle_application_approved = AsyncMock(
                return_value={"id": "order-uuid-456", "status": "completed"}
            )
            mock_gynger_cls.return_value = mock_gynger

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/webhooks/gynger",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-gynger-signature": sig,
                    },
                )

        assert resp.status_code == 200
        assert resp.json()["status"] == "received"
        mock_gynger.handle_application_approved.assert_called_once()

    def test_gynger_webhook_application_rejected(self):
        """application.rejected event triggers handle_application_rejected."""
        payload, sig = self._build_event("application.rejected")

        with patch("src.api.routes.webhooks.GyngerService") as mock_gynger_cls:
            mock_gynger = MagicMock()
            mock_gynger.verify_webhook_signature = MagicMock(
                return_value=json.loads(payload)
            )
            mock_gynger.handle_application_rejected = AsyncMock(
                return_value={"id": "order-uuid-456", "status": "cancelled"}
            )
            mock_gynger_cls.return_value = mock_gynger

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/webhooks/gynger",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-gynger-signature": sig,
                    },
                )

        assert resp.status_code == 200
        mock_gynger.handle_application_rejected.assert_called_once()

    def test_gynger_webhook_invalid_signature(self):
        """Invalid signature returns 400."""
        payload = json.dumps({"type": "application.approved"}).encode()

        with patch("src.api.routes.webhooks.GyngerService") as mock_gynger_cls:
            mock_gynger = MagicMock()
            mock_gynger.verify_webhook_signature = MagicMock(
                side_effect=ValueError("Invalid Gynger webhook signature")
            )
            mock_gynger_cls.return_value = mock_gynger

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/webhooks/gynger",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-gynger-signature": "badsignature",
                    },
                )

        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    def test_gynger_webhook_missing_signature_header(self):
        """Missing signature header returns 400."""
        payload = json.dumps({"type": "application.approved"}).encode()

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/webhooks/gynger",
                content=payload,
                headers={"Content-Type": "application/json"},
                # No x-gynger-signature header
            )

        assert resp.status_code == 400

    def test_gynger_webhook_pending_event_no_action(self):
        """application.pending event is logged but returns 200 with no DB changes."""
        payload, sig = self._build_event("application.pending")

        with patch("src.api.routes.webhooks.GyngerService") as mock_gynger_cls:
            mock_gynger = MagicMock()
            mock_gynger.verify_webhook_signature = MagicMock(
                return_value=json.loads(payload)
            )
            mock_gynger_cls.return_value = mock_gynger

            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/webhooks/gynger",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-gynger-signature": sig,
                    },
                )

        assert resp.status_code == 200
        # Neither approved nor rejected handlers should have been called
        assert not hasattr(mock_gynger, "handle_application_approved") or \
               not mock_gynger.handle_application_approved.called

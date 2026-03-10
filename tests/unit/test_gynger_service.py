"""Unit tests for GyngerService."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.gynger_service import GyngerService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.gynger_api_key = "test-gynger-api-key"
    settings.gynger_api_url = "https://api.gynger.io/v1"
    settings.gynger_webhook_secret = "test-webhook-secret"
    return settings


@pytest.fixture
def mock_supabase():
    return MagicMock()


@pytest.fixture
def service(mock_settings, mock_supabase):
    with (
        patch("src.services.gynger_service.get_settings", return_value=mock_settings),
        patch("src.services.gynger_service.get_supabase_client", return_value=mock_supabase),
    ):
        return GyngerService()


@pytest.fixture
def sample_robot():
    return {
        "id": "robot-uuid-123",
        "name": "TestBot",
        "category": "Test",
        "monthly_lease": 500.00,
    }


# ---------------------------------------------------------------------------
# create_financing_application
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_financing_application_success(service, sample_robot):
    """Happy path: Gynger API returns application_id and application_url."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "application_id": "gynger-app-abc123",
        "application_url": "https://app.gynger.io/apply/abc123",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_http

        result = await service.create_financing_application(
            robot=sample_robot,
            amount_cents=50000,
            customer_email="buyer@example.com",
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
            order_id="order-uuid-456",
        )

    assert result["application_id"] == "gynger-app-abc123"
    assert result["application_url"] == "https://app.gynger.io/apply/abc123"

    # Verify request was made correctly
    call_kwargs = mock_http.post.call_args
    assert "applications" in call_kwargs[0][0]
    body = call_kwargs[1]["json"]
    assert body["amount_cents"] == 50000
    assert body["customer_email"] == "buyer@example.com"
    assert body["metadata"]["order_id"] == "order-uuid-456"


@pytest.mark.asyncio
async def test_create_financing_application_api_error(service, sample_robot):
    """Gynger API returns HTTP error — should propagate."""
    import httpx

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        error_response = MagicMock()
        error_response.status_code = 422
        error_response.text = "Unprocessable Entity"
        mock_http.post.return_value = error_response
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "422", request=MagicMock(), response=error_response
        )
        mock_client_cls.return_value.__aenter__.return_value = mock_http

        with pytest.raises(httpx.HTTPStatusError):
            await service.create_financing_application(
                robot=sample_robot,
                amount_cents=50000,
                customer_email=None,
                success_url="http://localhost:3000/success",
                cancel_url="http://localhost:3000/cancel",
                order_id="order-uuid-456",
            )


@pytest.mark.asyncio
async def test_create_financing_application_missing_api_key(mock_settings, mock_supabase, sample_robot):
    """Missing API key raises ValueError before making any HTTP calls."""
    mock_settings.gynger_api_key = ""

    with (
        patch("src.services.gynger_service.get_settings", return_value=mock_settings),
        patch("src.services.gynger_service.get_supabase_client", return_value=mock_supabase),
    ):
        svc = GyngerService()

    with pytest.raises(ValueError, match="GYNGER_API_KEY"):
        await svc.create_financing_application(
            robot=sample_robot,
            amount_cents=50000,
            customer_email=None,
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
            order_id="order-uuid-456",
        )


# ---------------------------------------------------------------------------
# verify_webhook_signature
# ---------------------------------------------------------------------------


def _make_signature(secret: str, payload: bytes) -> str:
    """Helper: compute expected HMAC-SHA256 hex digest."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_verify_webhook_signature_valid(service):
    """Valid signature passes and returns parsed event."""
    event = {"type": "application.approved", "data": {"application_id": "app-123"}}
    payload = json.dumps(event).encode()
    sig = _make_signature("test-webhook-secret", payload)

    result = service.verify_webhook_signature(payload, sig)
    assert result["type"] == "application.approved"


def test_verify_webhook_signature_valid_with_prefix(service):
    """Signature with 'sha256=' prefix is also accepted."""
    event = {"type": "application.rejected"}
    payload = json.dumps(event).encode()
    sig = "sha256=" + _make_signature("test-webhook-secret", payload)

    result = service.verify_webhook_signature(payload, sig)
    assert result["type"] == "application.rejected"


def test_verify_webhook_signature_invalid(service):
    """Tampered payload fails signature check."""
    event = {"type": "application.approved"}
    payload = json.dumps(event).encode()
    bad_sig = "deadbeef" * 8  # Wrong signature

    with pytest.raises(ValueError, match="Invalid Gynger webhook signature"):
        service.verify_webhook_signature(payload, bad_sig)


def test_verify_webhook_signature_missing_secret(mock_settings, mock_supabase):
    """Missing webhook secret raises ValueError."""
    mock_settings.gynger_webhook_secret = ""

    with (
        patch("src.services.gynger_service.get_settings", return_value=mock_settings),
        patch("src.services.gynger_service.get_supabase_client", return_value=mock_supabase),
    ):
        svc = GyngerService()

    with pytest.raises(ValueError, match="GYNGER_WEBHOOK_SECRET"):
        svc.verify_webhook_signature(b'{"type":"application.approved"}', "sig")


# ---------------------------------------------------------------------------
# handle_application_approved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_application_approved(service, mock_supabase):
    """Approved event sets order status to 'completed'."""
    mock_result = MagicMock()
    mock_result.data = [{"id": "order-uuid-456", "status": "completed"}]

    mock_supabase.table.return_value.update.return_value.eq.return_value = MagicMock()
    with patch.object(service, "_execute_sync", AsyncMock(return_value=mock_result)):
        event = {
            "type": "application.approved",
            "data": {
                "application_id": "gynger-app-abc123",
                "metadata": {"order_id": "order-uuid-456"},
            },
        }
        result = await service.handle_application_approved(event)

    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_handle_application_approved_missing_order_id(service):
    """Approved event without order_id in metadata raises ValueError."""
    event = {
        "type": "application.approved",
        "data": {
            "application_id": "gynger-app-abc123",
            "metadata": {},  # Missing order_id
        },
    }

    with pytest.raises(ValueError, match="missing order_id"):
        await service.handle_application_approved(event)


# ---------------------------------------------------------------------------
# handle_application_rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_application_rejected(service, mock_supabase):
    """Rejected event sets order status to 'cancelled'."""
    mock_result = MagicMock()
    mock_result.data = [{"id": "order-uuid-456", "status": "cancelled"}]

    with patch.object(service, "_execute_sync", AsyncMock(return_value=mock_result)):
        event = {
            "type": "application.rejected",
            "data": {
                "application_id": "gynger-app-abc123",
                "metadata": {"order_id": "order-uuid-456"},
            },
        }
        result = await service.handle_application_rejected(event)

    assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_handle_application_rejected_missing_order_id(service):
    """Rejected event without order_id in metadata raises ValueError."""
    event = {
        "type": "application.rejected",
        "data": {"application_id": "gynger-app-abc123", "metadata": {}},
    }

    with pytest.raises(ValueError, match="missing order_id"):
        await service.handle_application_rejected(event)

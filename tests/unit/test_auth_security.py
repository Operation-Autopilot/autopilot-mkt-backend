"""Tests for authentication security fixes."""

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import UUID


class TestEmailValidation:
    """Tests for EmailStr validation on auth schemas."""

    def test_signup_rejects_invalid_email(self) -> None:
        """Test that SignupRequest rejects invalid email."""
        from src.schemas.auth import SignupRequest
        with pytest.raises(ValidationError):
            SignupRequest(email="not-an-email", password="password123")

    def test_login_rejects_invalid_email(self) -> None:
        """Test that LoginRequest rejects invalid email."""
        from src.schemas.auth import LoginRequest
        with pytest.raises(ValidationError):
            LoginRequest(email="just-text", password="password123")

    def test_forgot_password_rejects_invalid_email(self) -> None:
        """Test that ForgotPasswordRequest rejects invalid email."""
        from src.schemas.auth import ForgotPasswordRequest
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="@nodomain")

    def test_resend_verification_rejects_invalid_email(self) -> None:
        """Test that ResendVerificationRequest rejects invalid email."""
        from src.schemas.auth import ResendVerificationRequest
        with pytest.raises(ValidationError):
            ResendVerificationRequest(email="bad-email")


class TestResetPasswordSecurity:
    """Tests for password reset security."""

    def test_get_reset_password_returns_405(self, client):
        """GET /reset-password should be removed (405 Method Not Allowed)."""
        response = client.get("/api/v1/auth/reset-password", params={
            "token": "test-token",
            "new_password": "new-password-123"
        })
        assert response.status_code == 405

    def test_post_reset_password_still_works(self, client):
        """POST /reset-password should still work."""
        with patch("src.services.auth_service.AuthService.reset_password", new_callable=AsyncMock) as mock_reset:
            mock_reset.return_value = {
                "message": "Password reset successfully",
                "redirect_url": "https://example.com",
            }
            response = client.post("/api/v1/auth/reset-password", json={
                "token": "test-token",
                "new_password": "new-password-123"
            })
            assert response.status_code == 200


class TestOrderEnumeration:
    """Tests for order enumeration prevention.

    Verifies that the checkout route always returns 404 for both
    'not found' and 'not authorized', preventing order ID enumeration.
    """

    @pytest.mark.asyncio
    async def test_unauthorized_order_returns_404_not_403(self):
        """Accessing another user's order should return 404, not 403."""
        from fastapi import HTTPException
        from src.api.routes.checkout import get_order
        from src.api.deps import AuthContext

        # Mock auth context with no valid credentials
        mock_auth = AuthContext()

        # Mock CheckoutService to return False for can_access
        with patch("src.api.routes.checkout.CheckoutService") as MockService, \
             patch("src.api.routes.checkout._get_profile_for_auth", new_callable=AsyncMock) as mock_auth_fn:
            mock_auth_fn.return_value = (None, None)

            mock_svc = MagicMock()
            MockService.return_value = mock_svc
            mock_svc.can_access_order = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await get_order(
                    order_id=UUID("11111111-1111-1111-1111-111111111111"),
                    auth=mock_auth,
                )
            # Must be 404, not 403
            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_order_returns_404(self):
        """Non-existent order should return 404."""
        from fastapi import HTTPException
        from src.api.routes.checkout import get_order
        from src.api.deps import AuthContext

        mock_auth = AuthContext()

        with patch("src.api.routes.checkout.CheckoutService") as MockService, \
             patch("src.api.routes.checkout._get_profile_for_auth", new_callable=AsyncMock) as mock_auth_fn:
            mock_auth_fn.return_value = (None, None)

            mock_svc = MagicMock()
            MockService.return_value = mock_svc
            mock_svc.can_access_order = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await get_order(
                    order_id=UUID("99999999-9999-9999-9999-999999999999"),
                    auth=mock_auth,
                )
            assert exc_info.value.status_code == 404

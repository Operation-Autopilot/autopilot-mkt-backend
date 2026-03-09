"""Unit tests for JWT decoding and authentication utilities."""

import time
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jose import jwt as jose_jwt

from src.api.middleware.auth import AuthError, AuthErrorCode, decode_jwt


# Generate a test EC key pair for ES256
_test_private_key = ec.generate_private_key(ec.SECP256R1())
_test_public_key = _test_private_key.public_key()


def create_test_token(
    sub: str = "550e8400-e29b-41d4-a716-446655440000",
    email: str | None = "test@example.com",
    role: str | None = "user",
    exp_offset: int = 3600,
    private_key=_test_private_key,
    algorithm: str = "ES256",
) -> str:
    """Create a test JWT token signed with ES256."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "exp": now + exp_offset,
        "iat": now,
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
    }
    # Remove None values to test optional fields
    payload = {k: v for k, v in payload.items() if v is not None}
    return jose_jwt.encode(payload, private_key, algorithm=algorithm)


class TestDecodeJWT:
    """Tests for decode_jwt function."""

    @patch("src.api.middleware.auth.get_signing_key", return_value=_test_public_key)
    def test_decode_jwt_with_valid_token(self, mock_key) -> None:
        """Test decode_jwt successfully decodes a valid token."""
        token = create_test_token()
        payload = decode_jwt(token)

        assert payload.sub == "550e8400-e29b-41d4-a716-446655440000"
        assert payload.email == "test@example.com"
        assert payload.role == "user"

    @patch("src.api.middleware.auth.get_signing_key", return_value=_test_public_key)
    def test_decode_jwt_with_expired_token(self, mock_key) -> None:
        """Test decode_jwt raises AuthError for expired token."""
        token = create_test_token(exp_offset=-3600)

        with pytest.raises(AuthError) as exc_info:
            decode_jwt(token)

        assert exc_info.value.code == AuthErrorCode.TOKEN_EXPIRED
        assert "expired" in exc_info.value.message.lower()

    @patch("src.api.middleware.auth.get_signing_key", return_value=_test_public_key)
    def test_decode_jwt_with_invalid_signature(self, mock_key) -> None:
        """Test decode_jwt raises AuthError for invalid signature."""
        # Create token with a different key
        other_key = ec.generate_private_key(ec.SECP256R1())
        token = create_test_token(private_key=other_key)

        with pytest.raises(AuthError) as exc_info:
            decode_jwt(token)

        assert exc_info.value.code in [AuthErrorCode.INVALID_SIGNATURE, AuthErrorCode.INVALID_TOKEN]

    @patch("src.api.middleware.auth.get_signing_key", return_value=_test_public_key)
    def test_decode_jwt_with_malformed_token(self, mock_key) -> None:
        """Test decode_jwt raises AuthError for malformed token."""
        with pytest.raises(AuthError) as exc_info:
            decode_jwt("not-a-valid-jwt-token")

        assert exc_info.value.code == AuthErrorCode.INVALID_TOKEN

    @patch("src.api.middleware.auth.get_signing_key", return_value=_test_public_key)
    def test_decode_jwt_with_empty_token(self, mock_key) -> None:
        """Test decode_jwt raises AuthError for empty token."""
        with pytest.raises(AuthError) as exc_info:
            decode_jwt("")

        assert exc_info.value.code == AuthErrorCode.INVALID_TOKEN

    @patch("src.api.middleware.auth.get_signing_key", return_value=_test_public_key)
    def test_decode_jwt_missing_sub_claim(self, mock_key) -> None:
        """Test decode_jwt raises AuthError when sub claim is missing."""
        now = int(time.time())
        payload = {
            "email": "test@example.com",
            "exp": now + 3600,
            "iat": now,
        }
        token = jose_jwt.encode(payload, _test_private_key, algorithm="ES256")

        with pytest.raises(AuthError) as exc_info:
            decode_jwt(token)

        assert exc_info.value.code == AuthErrorCode.INVALID_TOKEN
        assert "sub" in exc_info.value.message.lower()

    @patch("src.api.middleware.auth.get_signing_key", return_value=_test_public_key)
    def test_decode_jwt_converts_to_user_context(self, mock_key) -> None:
        """Test that token payload can be converted to UserContext."""
        token = create_test_token()
        payload = decode_jwt(token)
        user_context = payload.to_user_context()

        assert str(user_context.user_id) == "550e8400-e29b-41d4-a716-446655440000"
        assert user_context.email == "test@example.com"
        assert user_context.role == "user"

    @patch("src.api.middleware.auth.get_signing_key", return_value=_test_public_key)
    def test_decode_jwt_optional_fields(self, mock_key) -> None:
        """Test decode_jwt handles missing optional fields."""
        token = create_test_token(email=None, role=None)
        payload = decode_jwt(token)

        assert payload.sub == "550e8400-e29b-41d4-a716-446655440000"
        assert payload.email is None
        assert payload.role is None

"""Pytest configuration and fixtures."""

import os
import time
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

# Set test environment variables before importing application modules
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SUPABASE_SIGNING_KEY_JWK", '{"kty":"EC","crv":"P-256","x":"test","y":"test"}')
os.environ.setdefault("AUTH_REDIRECT_URL", "https://test.example.com")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-openai-key")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")
os.environ.setdefault("PINECONE_ENVIRONMENT", "test-environment")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_stripe_secret_key")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_webhook_secret")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_stripe_publishable_key")

# Generate test EC key pair for JWT signing (ES256)
_test_ec_private_key = ec.generate_private_key(ec.SECP256R1())
_test_ec_public_key = _test_ec_private_key.public_key()


def create_test_token(
    sub: str = "550e8400-e29b-41d4-a716-446655440000",
    email: str | None = "test@example.com",
    role: str | None = "user",
    exp_offset: int = 3600,
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
    payload = {k: v for k, v in payload.items() if v is not None}
    return jose_jwt.encode(payload, _test_ec_private_key, algorithm="ES256")


@pytest.fixture(scope="session")
def test_settings() -> Generator[Any, None, None]:
    """Provide test settings with cleared cache.

    Yields:
        Settings: Test configuration settings.
    """
    from src.core.config import get_settings

    # Clear the cache to ensure fresh settings
    get_settings.cache_clear()

    settings = get_settings()
    yield settings

    # Clean up cache after tests
    get_settings.cache_clear()


@pytest.fixture
def mock_supabase_client() -> Generator[MagicMock, None, None]:
    """Provide a mocked Supabase client.

    Yields:
        MagicMock: Mocked Supabase client for testing.
    """
    mock_client = MagicMock()

    # Configure default mock responses
    mock_response = MagicMock()
    mock_response.data = []
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        mock_response
    )

    with patch("src.core.supabase.get_supabase_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def client(mock_supabase_client: MagicMock) -> Generator[TestClient, None, None]:
    """Provide a test client for the FastAPI application.

    Also patches the JWT signing key so test tokens work with ES256 auth.

    Args:
        mock_supabase_client: Mocked Supabase client fixture.

    Yields:
        TestClient: FastAPI test client.
    """
    from src.main import app

    with patch(
        "src.api.middleware.auth.get_signing_key",
        return_value=_test_ec_public_key,
    ):
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def client_without_mocks() -> Generator[TestClient, None, None]:
    """Provide a test client without any mocked dependencies.

    Use this fixture when you want to test actual integration
    with external services.

    Yields:
        TestClient: FastAPI test client without mocks.
    """
    from src.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_token() -> str:
    """Provide a valid test JWT token."""
    return create_test_token()


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Provide auth headers with a valid test token."""
    return {"Authorization": f"Bearer {auth_token}"}

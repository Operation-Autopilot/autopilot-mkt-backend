"""Flow test fixtures: FakeSupabase, test client, seed data.

These fixtures provide an in-memory Supabase mock that actually stores
and retrieves data (unlike MagicMock), enabling multi-endpoint integration
tests that verify cross-service interactions.
"""

import copy
import os
import time
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient

# Set test environment before importing app modules
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

# Generate test EC key pair
_test_ec_private_key = ec.generate_private_key(ec.SECP256R1())
_test_ec_public_key = _test_ec_private_key.public_key()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_ROBOTS = [
    {
        "id": "aaaaaaaa-0001-4000-8000-000000000001",
        "name": "CleanBot Pro",
        "vendor": "RoboClean",
        "manufacturer": "RoboClean",
        "category": "Floor Scrubber",
        "monthly_lease": 800.0,
        "time_efficiency": 0.85,
        "active": True,
        "image_url": "https://example.com/cleanbot.jpg",
        "modes": ["Vacuum", "Mop"],
        "surfaces": ["Hard Floor", "Carpet"],
        "key_reasons": ["High efficiency", "Low noise"],
        "specs": ["700-1000 m²/h", "Battery: 4h"],
        "best_for": "Office and commercial spaces",
        "embedding_id": None,
        "stripe_product_id": "prod_test_1",
        "stripe_lease_price_id": "price_test_1",
        "stripe_product_id_test": "prod_test_1_test",
        "stripe_lease_price_id_test": "price_test_1_test",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    },
    {
        "id": "aaaaaaaa-0002-4000-8000-000000000002",
        "name": "CourtSweeper X1",
        "vendor": "SportFloor",
        "manufacturer": "SportFloor",
        "category": "Court Cleaner",
        "monthly_lease": 1200.0,
        "time_efficiency": 0.92,
        "active": True,
        "image_url": "https://example.com/courtsweeper.jpg",
        "modes": ["Sweep", "Vacuum"],
        "surfaces": ["Sport Court", "Hard Floor"],
        "key_reasons": ["Designed for courts", "Quick setup"],
        "specs": ["1000-1500 m²/h", "Battery: 3h"],
        "best_for": "Tennis and pickleball courts",
        "embedding_id": None,
        "stripe_product_id": "prod_test_2",
        "stripe_lease_price_id": "price_test_2",
        "stripe_product_id_test": "prod_test_2_test",
        "stripe_lease_price_id_test": "price_test_2_test",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    },
    {
        "id": "aaaaaaaa-0003-4000-8000-000000000003",
        "name": "MegaScrub 3000",
        "vendor": "IndustrialBot",
        "manufacturer": "IndustrialBot",
        "category": "Floor Scrubber",
        "monthly_lease": 2500.0,
        "time_efficiency": 0.95,
        "active": True,
        "image_url": "https://example.com/megascrub.jpg",
        "modes": ["Vacuum", "Mop", "Scrub"],
        "surfaces": ["Hard Floor", "Concrete"],
        "key_reasons": ["Industrial grade", "Large coverage"],
        "specs": ["2000-2600 m²/h", "Battery: 6h"],
        "best_for": "Warehouses and large facilities",
        "embedding_id": None,
        "stripe_product_id": "prod_test_3",
        "stripe_lease_price_id": "price_test_3",
        "stripe_product_id_test": None,
        "stripe_lease_price_id_test": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    },
    {
        "id": "aaaaaaaa-0004-4000-8000-000000000004",
        "name": "EcoClean Lite",
        "vendor": "GreenBot",
        "manufacturer": "GreenBot",
        "category": "Floor Scrubber",
        "monthly_lease": 500.0,
        "time_efficiency": 0.7,
        "active": True,
        "image_url": "https://example.com/ecoclean.jpg",
        "modes": ["Vacuum"],
        "surfaces": ["Carpet", "Hard Floor"],
        "key_reasons": ["Budget friendly", "Easy to use"],
        "specs": ["400-500 m²/h", "Battery: 2h"],
        "best_for": "Small offices and retail",
        "embedding_id": None,
        "stripe_product_id": "prod_test_4",
        "stripe_lease_price_id": "price_test_4",
        "stripe_product_id_test": "prod_test_4_test",
        "stripe_lease_price_id_test": "price_test_4_test",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    },
    {
        "id": "aaaaaaaa-0005-4000-8000-000000000005",
        "name": "AutoVac Restaurant",
        "vendor": "FoodFloor",
        "manufacturer": "FoodFloor",
        "category": "Restaurant Cleaner",
        "monthly_lease": 900.0,
        "time_efficiency": 0.88,
        "active": True,
        "image_url": "https://example.com/autovac.jpg",
        "modes": ["Vacuum", "Mop", "Sanitize"],
        "surfaces": ["Tile", "Hard Floor"],
        "key_reasons": ["FDA approved", "Silent operation"],
        "specs": ["600-800 m²/h", "Battery: 3h"],
        "best_for": "Restaurants and food service",
        "embedding_id": None,
        "stripe_product_id": "prod_test_5",
        "stripe_lease_price_id": "price_test_5",
        "stripe_product_id_test": "prod_test_5_test",
        "stripe_lease_price_id_test": "price_test_5_test",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    },
    {
        "id": "aaaaaaaa-0006-4000-8000-000000000006",
        "name": "CourtMaster Elite",
        "vendor": "SportFloor",
        "manufacturer": "SportFloor",
        "category": "Court Cleaner",
        "monthly_lease": 1800.0,
        "time_efficiency": 0.96,
        "active": True,
        "image_url": "https://example.com/courtmaster.jpg",
        "modes": ["Sweep", "Vacuum", "Polish"],
        "surfaces": ["Sport Court", "Acrylic Court"],
        "key_reasons": ["Premium build", "Court-specific"],
        "specs": ["1200-1800 m²/h", "Battery: 5h"],
        "best_for": "Premium sports facilities",
        "embedding_id": None,
        "stripe_product_id": "prod_test_6",
        "stripe_lease_price_id": "price_test_6",
        "stripe_product_id_test": "prod_test_6_test",
        "stripe_lease_price_id_test": "price_test_6_test",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    },
]

# Complete set of discovery answers for a pickleball club
COMPLETE_DISCOVERY_ANSWERS = {
    "company_name": {
        "questionId": 1,
        "key": "company_name",
        "label": "Company Name",
        "value": "Downtown Pickleball Club",
        "group": "Company",
    },
    "company_type": {
        "questionId": 2,
        "key": "company_type",
        "label": "Company Type",
        "value": "Pickleball Club",
        "group": "Company",
    },
    "courts_count": {
        "questionId": 6,
        "key": "courts_count",
        "label": "Indoor Courts",
        "value": "8",
        "group": "Facility",
    },
    "method": {
        "questionId": 9,
        "key": "method",
        "label": "Cleaning Method",
        "value": "Vacuum",
        "group": "Operations",
    },
    "frequency": {
        "questionId": 13,
        "key": "frequency",
        "label": "Cleaning Frequency",
        "value": "Daily",
        "group": "Operations",
    },
    "duration": {
        "questionId": 15,
        "key": "duration",
        "label": "Session Duration",
        "value": "2 hr",
        "group": "Operations",
    },
    "monthly_spend": {
        "questionId": 12,
        "key": "monthly_spend",
        "label": "Monthly Spend",
        "value": "$2,000 - $5,000",
        "group": "Economics",
    },
}

TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_PROFILE_ID = "660e8400-e29b-41d4-a716-446655440000"


# ---------------------------------------------------------------------------
# FakeSupabase — in-memory dict-based mock
# ---------------------------------------------------------------------------

class FakeResponse:
    """Mimics the Supabase API response object."""

    def __init__(self, data: list[dict] | dict | None = None):
        if isinstance(data, dict):
            self.data = data
        elif isinstance(data, list):
            self.data = data
        else:
            self.data = data


class FakeQueryBuilder:
    """Supports chained .select/.insert/.update/.delete/.eq/.in_/.execute calls."""

    def __init__(self, table_data: list[dict], table_name: str, fake_db: "FakeSupabase"):
        self._table_data = table_data
        self._table_name = table_name
        self._fake_db = fake_db
        self._operation: str = "select"
        self._select_columns: str = "*"
        self._insert_data: dict | list | None = None
        self._update_data: dict | None = None
        self._filters: list[tuple[str, str, Any]] = []
        self._order_by: str | None = None
        self._order_desc: bool = False
        self._limit_val: int | None = None
        self._maybe_single: bool = False

    # --- Operation setters ---

    def select(self, columns: str = "*") -> "FakeQueryBuilder":
        self._operation = "select"
        self._select_columns = columns
        return self

    def insert(self, data: dict | list) -> "FakeQueryBuilder":
        self._operation = "insert"
        self._insert_data = data
        return self

    def update(self, data: dict) -> "FakeQueryBuilder":
        self._operation = "update"
        self._update_data = data
        return self

    def delete(self) -> "FakeQueryBuilder":
        self._operation = "delete"
        return self

    # --- Filter methods ---

    def eq(self, column: str, value: Any) -> "FakeQueryBuilder":
        self._filters.append(("eq", column, value))
        return self

    def neq(self, column: str, value: Any) -> "FakeQueryBuilder":
        self._filters.append(("neq", column, value))
        return self

    def in_(self, column: str, values: list) -> "FakeQueryBuilder":
        self._filters.append(("in_", column, values))
        return self

    def lt(self, column: str, value: Any) -> "FakeQueryBuilder":
        self._filters.append(("lt", column, value))
        return self

    def gt(self, column: str, value: Any) -> "FakeQueryBuilder":
        self._filters.append(("gt", column, value))
        return self

    def gte(self, column: str, value: Any) -> "FakeQueryBuilder":
        self._filters.append(("gte", column, value))
        return self

    def lte(self, column: str, value: Any) -> "FakeQueryBuilder":
        self._filters.append(("lte", column, value))
        return self

    def ilike(self, column: str, pattern: str) -> "FakeQueryBuilder":
        self._filters.append(("ilike", column, pattern))
        return self

    def or_(self, filter_str: str) -> "FakeQueryBuilder":
        # Simplified: no-op for flow tests (returns all matching rows)
        return self

    # --- Ordering / Limiting ---

    def order(self, column: str, desc: bool = False) -> "FakeQueryBuilder":
        self._order_by = column
        self._order_desc = desc
        return self

    def limit(self, count: int) -> "FakeQueryBuilder":
        self._limit_val = count
        return self

    def maybe_single(self) -> "FakeQueryBuilder":
        self._maybe_single = True
        return self

    # --- Execute ---

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        result = rows
        for op, col, val in self._filters:
            if op == "eq":
                result = [r for r in result if str(r.get(col)) == str(val)]
            elif op == "neq":
                result = [r for r in result if str(r.get(col)) != str(val)]
            elif op == "in_":
                vals_str = [str(v) for v in val]
                result = [r for r in result if str(r.get(col)) in vals_str]
            elif op == "lt":
                result = [r for r in result if r.get(col, "") < val]
            elif op == "gt":
                result = [r for r in result if r.get(col, "") > val]
            elif op == "gte":
                result = [r for r in result if r.get(col, 0) >= val]
            elif op == "lte":
                result = [r for r in result if r.get(col, 0) <= val]
            elif op == "ilike":
                pattern = val.replace("%", "").lower()
                result = [r for r in result if pattern in str(r.get(col, "")).lower()]
        return result

    def execute(self) -> FakeResponse:
        now_iso = datetime.now(timezone.utc).isoformat()

        if self._operation == "insert":
            items = self._insert_data if isinstance(self._insert_data, list) else [self._insert_data]
            inserted = []
            for item in items:
                row = copy.deepcopy(item)
                if "id" not in row:
                    row["id"] = str(uuid.uuid4())
                row.setdefault("created_at", now_iso)
                row.setdefault("updated_at", now_iso)
                # For sessions, set default expires_at
                if self._table_name == "sessions":
                    if "expires_at" not in row:
                        from datetime import timedelta
                        row["expires_at"] = (
                            datetime.now(timezone.utc) + timedelta(hours=24)
                        ).isoformat()
                self._table_data.append(row)
                # Return a copy without session_token for sessions table
                # to match real Supabase behavior where the route passes it separately
                return_row = copy.deepcopy(row)
                if self._table_name == "sessions" and "session_token" in return_row:
                    return_row.pop("session_token")
                inserted.append(return_row)
            return FakeResponse(data=inserted)

        if self._operation == "update":
            filtered = self._apply_filters(self._table_data)
            updated = []
            for row in filtered:
                for k, v in self._update_data.items():
                    row[k] = v
                row["updated_at"] = now_iso
                updated.append(copy.deepcopy(row))
            return FakeResponse(data=updated)

        if self._operation == "delete":
            filtered = self._apply_filters(self._table_data)
            ids_to_remove = {id(r) for r in filtered}
            self._table_data[:] = [r for r in self._table_data if id(r) not in ids_to_remove]
            return FakeResponse(data=[copy.deepcopy(r) for r in filtered])

        # SELECT
        filtered = self._apply_filters(list(self._table_data))
        if self._order_by:
            filtered.sort(
                key=lambda r: r.get(self._order_by, ""),
                reverse=self._order_desc,
            )
        if self._limit_val:
            filtered = filtered[: self._limit_val]

        data = [copy.deepcopy(r) for r in filtered]

        if self._maybe_single:
            if len(data) == 0:
                return FakeResponse(data=None)
            return FakeResponse(data=data[0])

        return FakeResponse(data=data)


class FakeSupabase:
    """In-memory dict-based Supabase client replacement.

    Supports chained queries with actual data storage/retrieval so
    flow tests can verify multi-service interactions end-to-end.
    """

    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}

    def table(self, name: str) -> FakeQueryBuilder:
        data = self.tables.setdefault(name, [])
        return FakeQueryBuilder(data, name, self)

    # Alias used by some services
    def from_(self, name: str) -> FakeQueryBuilder:
        return self.table(name)

    def seed_table(self, name: str, rows: list[dict]) -> None:
        """Seed a table with initial data."""
        self.tables[name] = [copy.deepcopy(r) for r in rows]

    def get_table(self, name: str) -> list[dict]:
        """Get all rows for a table (for assertions)."""
        return self.tables.get(name, [])

    def clear(self) -> None:
        """Clear all tables."""
        self.tables.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def create_test_token(
    sub: str = TEST_USER_ID,
    email: str | None = "test@example.com",
    role: str | None = "user",
    exp_offset: int = 3600,
) -> str:
    """Create a test JWT token signed with ES256."""
    from jose import jwt as jose_jwt

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


@pytest.fixture
def fake_supabase() -> FakeSupabase:
    """Provide a FakeSupabase instance seeded with robot catalog."""
    db = FakeSupabase()
    db.seed_table("robot_catalog", SEED_ROBOTS)
    # Ensure profiles table exists with test profile
    db.seed_table("profiles", [
        {
            "id": TEST_PROFILE_ID,
            "user_id": TEST_USER_ID,
            "email": "test@example.com",
            "full_name": "Test User",
            "is_test_account": False,
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
        }
    ])
    return db


@pytest.fixture
def _patch_supabase(fake_supabase: FakeSupabase):
    """Patch get_supabase_client at every import site."""
    from src.core.supabase import get_supabase_client

    get_supabase_client.cache_clear()

    # Must patch at every module that does `from src.core.supabase import get_supabase_client`
    patch_targets = [
        "src.core.supabase.get_supabase_client",
        "src.services.session_service.get_supabase_client",
        "src.services.conversation_service.get_supabase_client",
        "src.services.robot_catalog_service.get_supabase_client",
        "src.services.discovery_profile_service.get_supabase_client",
        "src.services.profile_service.get_supabase_client",
        "src.services.company_service.get_supabase_client",
        "src.services.checkout_service.get_supabase_client",
        "src.services.invitation_service.get_supabase_client",
        "src.services.floor_plan_service.get_supabase_client",
    ]

    patches = [patch(target, return_value=fake_supabase) for target in patch_targets]
    for p in patches:
        p.start()

    yield fake_supabase

    for p in patches:
        p.stop()
    get_supabase_client.cache_clear()


@pytest.fixture
def _patch_jwt():
    """Patch JWT signing key for test token verification."""
    with patch(
        "src.api.middleware.auth.get_signing_key",
        return_value=_test_ec_public_key,
    ):
        yield


@pytest.fixture
def _patch_openai():
    """Patch OpenAI client for agent service tests."""
    mock_openai = AsyncMock()

    # Default chat completion response
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello! I'm Autopilot, your robotics procurement consultant. What is the name of your company?"
    mock_choice.message.tool_calls = None
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(total_tokens=100)
    mock_openai.chat.create = AsyncMock(return_value=mock_response)

    with patch("src.core.openai.get_openai_client", return_value=mock_openai):
        yield mock_openai


@pytest.fixture
def _patch_rag():
    """Patch RAG service for tests."""
    mock_rag = AsyncMock()
    mock_rag.search_robots_for_discovery = AsyncMock(return_value=[
        {"robot_id": r["id"], "semantic_score": 0.8 - i * 0.05}
        for i, r in enumerate(SEED_ROBOTS)
    ])
    mock_rag.search_robots = AsyncMock(return_value=[])

    with patch("src.services.rag_service.get_rag_service", return_value=mock_rag):
        with patch("src.services.robot_catalog_service.get_rag_service", return_value=mock_rag):
            yield mock_rag


@pytest.fixture
def _patch_rate_limiter():
    """Patch rate limiter to always allow."""
    mock_limiter = AsyncMock()
    mock_limiter.check_and_increment = AsyncMock(return_value=(True, 100, 0))
    with patch("src.core.rate_limiter.get_rate_limiter", return_value=mock_limiter):
        yield mock_limiter


@pytest.fixture
def _patch_token_budget():
    """Patch token budget to always allow."""
    mock_budget = AsyncMock()
    mock_budget.check_budget = AsyncMock(return_value=(True, 10000, 50000))
    mock_budget.record_usage = AsyncMock()
    with patch("src.core.token_budget.get_token_budget", return_value=mock_budget):
        yield mock_budget


@pytest.fixture
def _patch_recommendation_cache():
    """Provide a fresh recommendation cache for each test."""
    from src.services.recommendation_cache import RecommendationCache, RecommendationCacheConfig

    cache = RecommendationCache(RecommendationCacheConfig(max_size=100, ttl_seconds=3600))
    with patch("src.services.recommendation_cache.get_recommendation_cache", return_value=cache):
        with patch("src.services.recommendation_service.get_recommendation_cache", return_value=cache):
            yield cache


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset module-level singletons between tests to avoid state leaks."""
    import src.services.agent_service as agent_mod
    import src.services.recommendation_service as rec_mod

    # Reset robot catalog cache
    agent_mod._robot_cache = None

    # Reset recommendation service singleton
    rec_mod._recommendation_service = None

    yield

    agent_mod._robot_cache = None
    rec_mod._recommendation_service = None


@pytest.fixture
def _patch_all(
    _patch_supabase,
    _patch_jwt,
    _patch_openai,
    _patch_rag,
    _patch_rate_limiter,
    _patch_token_budget,
    _patch_recommendation_cache,
):
    """Combine all patches into a single fixture for convenience."""
    yield


@pytest_asyncio.fixture
async def async_client(_patch_all) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTPX client for the FastAPI app."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_token() -> str:
    """Provide a valid test JWT token."""
    return create_test_token()


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Provide auth headers with a valid test token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def session_token() -> str:
    """Provide a dummy session token."""
    return "test-session-token-" + uuid.uuid4().hex[:16]


@pytest.fixture
def complete_answers() -> dict[str, dict]:
    """Provide a complete set of discovery answers."""
    return copy.deepcopy(COMPLETE_DISCOVERY_ANSWERS)

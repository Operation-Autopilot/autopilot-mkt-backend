# Phase 6: Test Quality Audit

## Test Coverage Overview
- **Test files**: 53 files
- **Test functions**: 406
- **Assertions**: 711 (average ~1.75 assertions/test — low, ideally 3-5)
- **Source files**: 76 Python files in `src/`
- **Test-to-source ratio**: 0.79 (60 test files / 76 source files) — reasonable

## Test Organization
- `tests/unit/` — 31 files, unit tests with mocking
- `tests/integration/` — 16 files, integration tests with FastAPI TestClient
- `tests/contract/` — 1 file, response schema contracts
- `tests/flow/` — 4 files, end-to-end flow tests

## Key Findings

### 1. Good Test Coverage Areas
- `test_auth_security.py` — tests JWT expiry, invalid signatures, claims
- `test_webhook_security.py` — tests Stripe signature verification
- `test_checkout_validation.py` — tests URL validation
- `test_robot_cache_concurrency.py` — tests race conditions in cache
- `test_async_safety.py` — tests async patterns
- `test_recommendation_deterministic.py` — tests scoring algorithm

### 2. Critical Gap: No Tests for P0 Bug
- `supabase_auth` import failure in `src/core/supabase.py` is not caught by any test
- All tests that mock Supabase would not catch this import error
- The `conftest.py` likely patches the Supabase client before the import error triggers

### 3. Missing Test Coverage for High-Risk Areas
- **No rate limiting tests for auth endpoints** (`/auth/signup`, `/auth/login`, `/auth/forgot-password`)
- **No test for logout actually invalidating tokens** — the phantom bug in `auth.py:219-234` is untested
- **No Gynger integration tests against actual API** — only mock tests
- **No multi-worker webhook deduplication tests**
- **No test for `company_service` blocking event loop**

### 4. Test Quality Concerns

**Empty/minimal tests**: Some tests check existence but not correctness:
```python
# tests/contract/test_response_schemas.py — Creates objects to verify schema
# but doesn't validate actual API responses match schemas
```

**Datetime warnings**: `tests/contract/test_response_schemas.py` uses `datetime.utcnow()` in test fixtures (deprecated).

### 5. Test Infrastructure
- `conftest.py` uses `AsyncMock` and `patch` properly
- `pytest-asyncio` configured in auto mode (asyncio_mode = "auto") ✓
- Tests set `os.environ.setdefault("DEBUG", "true")` and mock required env vars ✓

### 6. Integration Test Quality
Integration tests in `tests/integration/` use `TestClient` from FastAPI. These test the actual HTTP layer including validation and middleware, which is good.

`tests/integration/test_auth_routes.py` tests signup, login, logout flows. However, due to the `supabase_auth` import bug, these tests may fail unless the test environment has the module available or mocks it.

### 7. Performance Tests
`tests/flow/test_concurrent_requests.py` — tests concurrent request handling. This is notable positive test coverage for async safety.

## Test-to-Feature Matrix
| Feature | Unit | Integration | Contract | Notes |
|---------|------|-------------|----------|-------|
| Auth | ✓ | ✓ | - | Missing logout invalidation test |
| Sessions | ✓ | ✓ | - | Good coverage |
| Conversations | ✓ | ✓ | - | Good coverage |
| Checkout | ✓ | ✓ | - | Missing rate limit tests |
| Webhooks | ✓ | ✓ | - | Good security tests |
| Recommendations | ✓ | - | - | Good algorithm tests |
| Floor Plans | ✓ | - | - | Only unit tests |
| Gynger | ✓ | ✓ | - | Only mock tests |
| Rate Limiter | - | - | - | No dedicated rate limit tests |
| Company | ✓ | ✓ | - | Blocking pattern untested |

# Phase 3: LLM-Specific Antipattern Analysis

## CAT 1: Dead Code / Unreachable Blocks
**Finding**: No `if False:` or obviously unreachable code found. `AuthService.logout()` at line 275 is defined but never called from the route handler (`auth.py:219-234` — the route creates a service but doesn't call `service.logout()`). The route just returns `{"message": "Logged out successfully"}` without calling the service method.
- **File**: `src/api/routes/auth.py:219-234`, `src/services/auth_service.py:275-302`
- **Severity**: P2 — logout doesn't actually invalidate server-side sessions

## CAT 2: Unused Imports / Variables
- `Cookie` in `src/api/deps.py:7` — imported but unused
- `python-jose` listed as dependency alongside `PyJWT` — both JWT libraries imported/declared; only `PyJWT` (jwt module) used in `src/api/middleware/auth.py`. `python-jose` appears unused in source code.
- **Severity**: P3

## CAT 3: Duplicate / Near-Duplicate Functions
**Critical Finding**: `_execute_sync` pattern duplicated in 6 service classes:
- `src/services/session_service.py:34-36`
- `src/services/checkout_service.py:37-39`
- `src/services/robot_catalog_service.py:65-67`
- `src/services/conversation_service.py:27-29`
- `src/services/discovery_profile_service.py:50-52`
- `src/services/gynger_service.py:35-37`

All 6 are identical: `async def _execute_sync(self, query): return await asyncio.to_thread(query.execute)`. Should be extracted to a base class or utility function.
- **Severity**: P2 (DRY violation, maintenance risk)

**Also**: `get_current_user_or_session` and `get_required_user_or_session` in `src/api/deps.py` share significant duplicate JWT-parsing logic (lines 235-244 vs 296-303).
- **Severity**: P3

## CAT 4: Over-Abstraction
No significant over-abstraction found. Service layer is appropriately sized.

## CAT 5: Under-Abstraction (Copy-Paste Logic)
**Finding**: Direct `.execute()` calls (blocking, no thread pool) spread across `company_service.py`, `floor_plan_service.py`, `checkout_service.py` (read operations), and `invitation_service.py` — these block the asyncio event loop.
- Example: `src/services/company_service.py:38-42` — synchronous Supabase query inside an `async def` method without `asyncio.to_thread`
- Contrast: `session_service.py`, `checkout_service.py` (write operations) properly use `_execute_sync`
- Inconsistent pattern: some async service methods use `asyncio.to_thread` wrapper, others call `.execute()` directly
- **Files**: `src/services/company_service.py` (all methods), `src/services/floor_plan_service.py` (lines 196, 243, 358, 913, 929, 957, 1008, 1061, 1078), `src/services/invitation_service.py` (all methods)
- **Severity**: P1 — event loop blocking under load

## CAT 6: Defensive Programming at Wrong Boundaries
**Finding**: `src/api/deps.py` `get_current_user_or_session()` at line 243: when JWT is present but invalid, it silently falls through to session handling instead of raising 401. This could allow an expired/invalid JWT to create a new anonymous session, bypassing intended auth rejection.
- **Severity**: P2 (by design in dual-auth systems, but could lead to unexpected behavior)

## CAT 7: Hallucinated Package Imports (P0)
**Critical Finding 1**: `src/core/supabase.py:8`
```python
from supabase_auth import SyncMemoryStorage
```
`supabase_auth` is NOT in `requirements.txt`, NOT in `pyproject.toml`.
- Testing confirmed: `ModuleNotFoundError: No module named 'supabase_auth'`
- This is a hallucinated import — likely the LLM confused the `gotrue-py` package internal module path. In older versions of `supabase-py`, `SyncMemoryStorage` was at `gotrue.storage.SyncMemoryStorage`. In newer versions it may be at a different path.
- **This import prevents the entire application from starting.**
- **Severity: P0**

**Critical Finding 2**: `scripts/index_products.py:19`
```python
from src.services.product_service import ProductService
```
`src/services/product_service.py` does not exist. The actual service is `robot_catalog_service.py` / `RobotCatalogService`. This is a hallucinated service name.
- **Severity: P0** (script broken)

## CAT 8: Hardcoded Credentials / Secrets
No hardcoded credentials found. All secrets properly loaded via `src/core/config.py` from environment variables. The `.env.example` file contains placeholder values only.

## CAT 9: Missing Resource Lifecycle Management
**Finding**: `src/services/floor_plan_service.py` uses synchronous Supabase operations (blocking):
- Lines 194-196: `self.client.table("floor_plan_analyses").update(...).execute()` — synchronous inside async method
- Lines 233-243: Same pattern
- These are called from async methods but are not wrapped in `asyncio.to_thread`
- **Severity**: P1 (event loop blocking)

**Finding**: `src/services/checkout_service.py:203-210` — creates a Stripe Customer synchronously within async code:
```python
customer = self.stripe.Customer.create(email=customer_email, api_key=stripe_api_key)
```
Stripe Python SDK is synchronous. This blocks the event loop for Stripe API calls.
- **Severity**: P1

## CAT 10: Incorrect Error Handling
**Finding 1**: `src/services/auth_service.py` uses broad `except Exception as e:` in all methods, with string-matching on error messages (e.g., `"already registered" in error_msg.lower()`). This pattern is fragile — Supabase error message changes would silently break error routing.
- **Severity**: P2

**Finding 2**: `src/services/gynger_service.py:161-165` — `hmac.new()` is used instead of the canonical `hmac.HMAC()` constructor. While `hmac.new` is actually an alias that works in Python 3, it's documented as an implementation detail/alias. The canonical form is `hmac.new(key, msg, digestmod)` which matches what's being called — this is actually fine.

**Finding 3**: `src/api/routes/auth.py:232` — logout route comment says "The frontend should clear the token" without actually invalidating it server-side. The service `logout()` method IS implemented with Supabase `sign_out()` but is never called.
- **Severity**: P2 (security: tokens not invalidated)

**Finding 4**: `src/services/checkout_service.py:107-110` — `except Exception: pass` for cleanup_orphaned_orders. Acceptable as noted in comment (non-critical).

## CAT 11: Type Safety Violations
**Finding**: Multiple uses of `Any` type throughout services:
- `dict[str, Any]` as return types in most service methods — acceptable for Supabase dict responses
- `src/services/gynger_service.py:39,44,47` — untyped dict parameters `dict` instead of `dict[str, Any]`
- **Severity**: P3

## CAT 12: Incorrect Async/Await Patterns
**Critical Finding**: Multiple service classes call Supabase `.execute()` directly without `asyncio.to_thread()`:
- All methods in `src/services/company_service.py` (async defs calling sync .execute())
- Most methods in `src/services/floor_plan_service.py`
- Most methods in `src/services/invitation_service.py`
- Read methods in `src/services/checkout_service.py` (lines 427, 446, 465, 488)

This means these async route handlers are blocking the event loop on every DB operation.

**Finding**: Stripe API calls in `checkout_service.py` are synchronous (Stripe Python SDK) called from async routes without `asyncio.to_thread`:
- Line 203: `self.stripe.Customer.list(...)` — WRAPPED in `asyncio.to_thread` ✓
- Line 206: `self.stripe.Customer.create(...)` — NOT wrapped, blocking! ✗
- Line 212: `self.stripe.checkout.Session.create(...)` — NOT wrapped, blocking! ✗
- **Severity**: P1

## CAT 13: N+1 Patterns and Performance
**Finding**: `src/services/recommendation_service.py:218-231` — calls `get_robots_by_ids()` after getting search results from RAG. This is a proper batch fetch, not N+1.

**Finding**: `src/api/routes/conversations.py:541` — `get_messages(..., limit=1)` called just to get count, then full `get_messages(..., limit=50)` on same conversation. Minor but could be optimized.
- **Severity**: P3

## CAT 14: Inconsistent Naming Conventions
**Finding**: `_execute_sync` is a synchronous-sounding name for an async method. Should be `_run_query` or `_execute_async`.
- **Severity**: P3

**Finding**: Route files use instantiation pattern `service = ConversationService()` on every request rather than dependency injection. Consistent within codebase but creates fresh objects per request.
- **Severity**: P3

## CAT 15: Over/Under Documentation
Documentation quality is generally HIGH. Almost all public functions, classes, and routes have docstrings. README.md is comprehensive.

## CAT 16: Magic Numbers and Strings
**Finding**: `src/api/middleware/error_handler.py:178` — `"15"` hardcoded as X-RateLimit-Limit header value, while actual limit is `settings.rate_limit_anonymous_requests` (default 15 but configurable).
- **Severity**: P2

**Finding**: `src/services/floor_plan_service.py:784` — `ceil(daily_hours / 6)` — magic number 6 (6-hour shifts). Has inline comment explaining it, acceptable.

**Finding**: `src/services/recommendation_service.py:268` — `semantic_boost = semantic_score * 15.0` — magic 15. Module-level constant would be cleaner.
- **Severity**: P3

## CAT 17: Phantom Bugs
**Finding**: `src/api/routes/auth.py:231-234` — Logout route does nothing server-side:
```python
async def logout(user: CurrentUser) -> dict[str, str]:
    # Note: For proper logout, we'd need the access token
    # Since we only have the decoded user context, we return success
    # The frontend should clear the token
    return {"message": "Logged out successfully"}
```
The `AuthService.logout()` method exists and properly calls `supabase.auth.sign_out()`. The route just doesn't call it. This is a bug — JWTs remain valid until expiry even after "logout".
- **Severity**: P2 (security gap: token not invalidated on logout)

**Finding**: `src/services/session_service.py:213-219` — `is_session_valid()` checks expiry twice (once in `get_session_by_token` and once in `is_session_valid`). Double expiry check is redundant.
- **Severity**: P3

## CAT 18: Reinventing the Wheel
**Finding**: Custom in-memory rate limiter (`src/core/rate_limiter.py`) and token budget tracker (`src/core/token_budget.py`) are reasonably well-implemented but reinvent standard functionality. In production with multiple workers, these fail (documented in code).
- **Severity**: P2 (multi-worker deployment breaks rate limiting and token budgets)

## CAT 19: Dependency Bloat
**Finding**: `python-jose[cryptography]` AND `PyJWT` both listed as dependencies. Only PyJWT is used in source code. `python-jose` appears to be an unused dependency.
- **Severity**: P2

## CAT 20: Architectural Drift
**Finding**: `ALLOWED_REDIRECT_DOMAINS` in `src/services/checkout_service.py:20-24` — hardcoded set of domains that doesn't include all possible deployment domains. New deploy domains would require code changes.
- **Severity**: P2

**Finding**: `scripts/index_products.py` references `product_service.ProductService` which doesn't exist — script completely broken. The repository has evolved (renamed to `RobotCatalogService`) but the script was not updated.
- **Severity**: P0

## CAT 21: API Misuse
**Finding**: `src/services/floor_plan_service.py:447` — `max_tokens=4000` used in GPT-4o call when the correct parameter name for the newer API is `max_completion_tokens`. The `max_tokens` parameter still works but is deprecated.
- **Severity**: P3

**Finding**: In `src/services/gynger_service.py`, the Gynger integration has extensive `# TODO: confirm with Gynger docs` comments on request body field names, response field names, endpoint paths, event type names, and signature format. This integration is essentially speculative and untested against actual Gynger API.
- **Severity**: P1 (not operational)

## CAT 22: Concurrency Issues
**Finding**: `src/api/routes/webhooks.py:20-21` — In-memory webhook deduplication dict `_processed_events` is not thread-safe under multiple workers (documented) but also has lock overhead under high traffic. More importantly, the lock is per-worker only.
- **Severity**: P2 (documented, but design concern)

**Finding**: `src/services/recommendation_service.py:557-565` — Module-level singleton `_recommendation_service` is mutable global state that could cause race conditions in async context.
- **Severity**: P3 (Python GIL limits race window)

## CAT 23: Excessive Data Exposure
**Finding**: Most service methods return `dict[str, Any]` with all DB columns via `select("*")`. For example, `get_order()` returns all order fields. Some of these (like `stripe_customer_id`, `stripe_subscription_id`) may be sensitive. Responses are filtered by Pydantic `response_model` in routes, but service layer overfetches.
- **Severity**: P3 (mitigated by route-level Pydantic filtering)

## CAT 24: Rate Limiting
**Finding**: `/api/v1/checkout/session` (create checkout), `/api/v1/checkout/gynger-session` — these endpoints have **no rate limiting** applied. An attacker could spam checkout session creation.
- **Severity**: P1

**Finding**: Auth endpoints `/auth/signup`, `/auth/forgot-password` — no rate limiting. Email enumeration and spam vectors.
- **Severity**: P1

## CAT 25: Insecure Deserialization
No `pickle`, `yaml.load`, `eval`, or `exec` found in source code. Clean.

## CAT 26: License Issues
Proprietary license. No open-source license concerns.

## CAT 27: Unverified Third-Party Integration
**Finding**: Gynger integration (`src/services/gynger_service.py`) has 8 `# TODO: confirm with Gynger docs` comments on critical API contract details (endpoint path, field names, response format, webhook signature format, event type names). The integration is deployed-ready in code but may fail entirely at runtime when Gynger API is actually called.
- **Severity**: P1 (functional risk)

# Phase 4: Cross-File Consistency Audit

## Logging Consistency
**PASS**: All source files use `logging.getLogger(__name__)` consistently. No `print()` statements found in `src/` code. Scripts use print() for CLI output, which is appropriate.

## Environment Variable Access
**PASS**: All env access goes through `src/core/config.py` `get_settings()`. No raw `os.environ` or `os.getenv` calls found in `src/` (only in test fixtures which is acceptable).

## Exception Handling Consistency
**INCONSISTENCY FOUND**:
- Routes raise `HTTPException` directly ✓
- Services raise custom errors: `ValidationError`, `ValueError`, `AuthorizationError`, `NotFoundError` — routes catch these and convert
- Some service methods (auth_service) raise `ValidationError` (custom)
- Some service methods (checkout_service) raise `ValueError`
- Routes catch both patterns but not always consistently
- Example: `checkout.py:91-95` catches `ValueError`, `auth.py:62-66` catches `ValidationError`
- No single error protocol — mixed `ValueError` vs custom `APIError` subclasses
- **Severity**: P2

## Response Shape Consistency
**INCONSISTENCY**: Some routes return Pydantic response models (proper), some return `dict[str, str]`:
- `src/api/routes/auth.py:242` — returns `dict[str, str | None]` directly (no response model)
- `src/api/routes/auth.py:219` — returns `dict[str, str]`
- `src/api/routes/conversations.py:748` — returns `dict` (no response model annotation)
- Most other routes use proper `response_model=` annotation
- **Severity**: P2 (breaks OpenAPI schema generation)

## Supabase Access Pattern
**INCONSISTENCY**: Two patterns in use simultaneously:
1. **Async-wrapped**: `await self._execute_sync(query)` — used in session_service, checkout_service (writes), robot_catalog_service, conversation_service, discovery_profile_service
2. **Sync direct**: `.execute()` called directly inside `async def` — used in company_service, floor_plan_service, invitation_service, checkout_service (reads)

This inconsistency means approximately half the service layer blocks the event loop, while the other half properly yields. The codebase appears to have been refactored partway — newer services use the thread pool pattern, older ones don't.
- **Files with blocking pattern**: `company_service.py`, `floor_plan_service.py`, `invitation_service.py`, `checkout_service.py` (read methods at lines 422-488)
- **Severity**: P1

## Service Instantiation Pattern
**INCONSISTENCY**: Routes instantiate services per-request (`service = ConversationService()`) rather than using FastAPI dependency injection. Some services have a singleton getter (`get_recommendation_service()`), others don't. The pattern is inconsistent across the codebase.
- Recommendation_service: singleton via `_recommendation_service` global
- Floor_plan_service: singleton via `_floor_plan_service` global
- ROI_service: singleton via `get_roi_service()`
- All other services: instantiated fresh per-request
- **Severity**: P3

## Datetime Handling
**INCONSISTENCY**: Mix of timezone-aware and naive datetime:
- `src/services/checkout_service.py:275,332` — uses `datetime.now(timezone.utc)` ✓ (timezone-aware)
- `src/services/checkout_service.py:64` — uses `datetime.utcnow()` ✗ (naive)
- `src/services/gynger_service.py:225` — `datetime.datetime.utcnow()` ✗ (naive)
- `src/services/roi_service.py:287,705` — `datetime.utcnow()` ✗
- Mixing naive and aware datetimes can cause comparison errors
- **Severity**: P2

## Import Organization
**Minor inconsistency**: `src/services/auth_service.py` uses deferred imports inside methods (`from src.services.profile_service import ProfileService` at line 75). While this avoids circular imports, it's an unusual pattern. `src/services/floor_plan_service.py` uses `if TYPE_CHECKING:` which is the cleaner approach for the same problem.
- **Severity**: P3

## Webhook Event Deduplication Sharing
**Finding**: Both Stripe and Gynger webhooks share the same `_processed_events` dict in `src/api/routes/webhooks.py`. If Stripe and Gynger ever generate events with colliding IDs (both use UUIDs or random strings), they could erroneously skip processing the other's event. Very low probability but an architectural smell.
- **Severity**: P3

## Stripe API Calls in Async Context
**INCONSISTENCY**: Within the same `create_checkout_session` method in `checkout_service.py`:
- `stripe.Customer.list(...)` — wrapped in `asyncio.to_thread` ✓ (line 197-199)
- `stripe.Customer.create(...)` — NOT wrapped (line 203-210)
- `stripe.checkout.Session.create(...)` — NOT wrapped (line 212-213)
- **Severity**: P1

# Phase 5: Security Audit (OWASP + LLM-Specific)

## A01: Broken Access Control

### Positive Findings
- JWT validation uses ES256 (asymmetric) with `verify_signature: True`, `verify_exp: True` ✓
- `src/api/deps.py` defines clear dependency hierarchy: `CurrentUser`, `DualAuth`, `RequiredDualAuth` ✓
- Conversation access checks in `_check_conversation_access()` verify profile/session ownership ✓
- Order access uses `can_access_order()` with proper ownership check ✓
- Floor plan ownership enforced in `get_analysis()` and `delete_analysis()` ✓

### Concerns
- **`src/api/routes/auth.py:219-234` — Logout does not invalidate tokens**: The route returns `{"message": "Logged out successfully"}` without calling `service.logout()`. Supabase JWT tokens remain valid until expiry (~1 hour). An attacker who obtains a JWT before logout can continue using it.
  - **Severity**: P2

- **`src/api/deps.py:235-244` — Silent JWT failure in DualAuth**: When an Authorization header contains an invalid/expired JWT, the system silently falls back to anonymous session creation instead of returning 401. This could allow a revoked user to continue with anonymous access.
  - **Severity**: P2 (by design for dual-auth, but warrants documentation)

- **`src/core/config.py:51` — `env_file_priority="env_file"`**: If this setting actually has effect (it shouldn't — it's not a valid pydantic-settings key), `.env` file values would override system environment variables, which could allow local config to override production secrets. Since the key is invalid, it has no effect, but the intent is incorrect regardless.
  - **Severity**: P3

## A02: Cryptographic Failures

### Positive Findings
- JWT uses ES256 (ECDSA-256) with public JWK for verification ✓
- Session tokens use `secrets.token_hex(32)` (256-bit entropy) ✓
- Session tokens stored as SHA-256 hashes (not plaintext) ✓
- Stripe webhook verification uses HMAC-SHA256 via official SDK ✓

### Concerns
- **`src/services/sales_knowledge_service.py`** uses `random.sample()` not `secrets.SystemRandom()`. This is for selecting sales knowledge snippets, NOT security-sensitive. Acceptable.
  - **Severity**: P3

## A03: Injection Attacks

### SQL Injection
**PASS**: No raw SQL string formatting found. All DB operations use PostgREST parameterized API (Supabase Python client). SQL injections are not possible through this pattern.

### Input Sanitization
`src/services/robot_catalog_service.py:39-50` — `_sanitize_filter_input()` strips non-alphanumeric chars from filter values. Good defense-in-depth.

### No Shell Injection
No `subprocess`, `os.system`, `shell=True`, `eval()`, or `exec()` found in source code. ✓

## A04: Insecure Design

### Rate Limiting Gaps
**Critical Finding**: Several high-value endpoints lack rate limiting:
- `POST /api/v1/auth/signup` — no rate limit (account creation spam, abuse)
- `POST /api/v1/auth/forgot-password` — no rate limit (email enumeration/spam)
- `POST /api/v1/auth/login` — no rate limit (brute force risk)
- `POST /api/v1/checkout/session` — no rate limit (Stripe session spam)
- `POST /api/v1/checkout/gynger-session` — no rate limit
- `POST /api/v1/floor-plans/analyze` — no rate limit on expensive GPT-4o Vision calls (token budget is per-user, but no IP-based rate limiting)
- **Severity**: P1

### Multi-Worker Webhook Dedup
`src/api/routes/webhooks.py` uses in-memory deduplication. With >1 worker, duplicate webhook processing is possible. This is documented in the code but remains a real operational risk.
- **Severity**: P2

## A05: Security Misconfiguration

### CORS Configuration
`src/main.py:108-114`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    ...
)
```
`allow_credentials=True` with `allow_origins` set to specific domains (not wildcard) is correct. ✓

The default `cors_origins` in config includes multiple Vercel preview URLs and `www.autopilot-marketplace.com` — this is fine but should be managed via env var in production.

### Debug Mode
`src/main.py:101-103` — OpenAPI docs only exposed when `debug=True`. Default is `False`. ✓

`tests/conftest.py:17` and `tests/flow/conftest.py:25` set `os.environ.setdefault("DEBUG", "true")` — this is test-only. ✓

### Stripe Key Defaults
`src/core/config.py:123-127` — Stripe keys default to empty string `""`. If not configured, checkout fails with a `ValueError` (handled). Acceptable fail-safe pattern.

## A07: Authentication Failures

### JWT Configuration
- Algorithm: ES256 (asymmetric public key) ✓
- `verify_exp: True` ✓
- `verify_aud: False` — audience validation disabled with comment "Supabase tokens have varying audiences". This is correct for Supabase but represents a minor risk if tokens from other Supabase projects (same JWKS) are accepted.
- `require: ["exp", "iat", "sub"]` ✓

### Session Token Security
- 256-bit entropy via `secrets.token_hex(32)` ✓
- Stored as SHA-256 hash ✓
- Expiry enforced (30 days) ✓
- Claimed sessions become invalid ✓

### Refresh Token
`AuthService.refresh_token()` uses Supabase `auth.refresh_session()` — relies on Supabase's refresh token security. ✓

## A08: Insecure Deserialization
**PASS**: No `pickle`, `yaml.load()`, `eval()`, or `exec()` found. All deserialization via JSON (`json.loads`) and Pydantic. ✓

## A09: Security Logging and Monitoring
**Concern**: Auth failures are logged but at different levels:
- Login failures: `logger.error("Login failed: %s", error_msg)` — logged with email (potential PII in logs)
- Webhook failures: logged appropriately

**Finding**: User email addresses logged in error conditions in `auth_service.py`. In production, email addresses should not appear in error logs (GDPR/privacy risk).
- **Severity**: P2

## A10: SSRF (Server-Side Request Forgery)
**Finding**: `src/services/gynger_service.py:76,101` — Gynger API URL comes from `self.settings.gynger_api_url` (default: `https://api.gynger.io/v1`). This is NOT user-controlled. ✓

**Finding**: `src/services/floor_plan_service.py:402-406` — Supabase storage signed URL generation. The `storage_path` is constructed from `analysis_id` (UUID) and file extension. Path traversal is prevented by UUID structure. ✓

No SSRF risks identified. External HTTP calls only go to pre-configured API endpoints (Stripe, Gynger, OpenAI, Pinecone, Supabase).

## SQL Migration Security
`supabase/migrations/007_create_orders.sql` — RLS policies properly restrict user access:
- Users can only view their own orders ✓
- Service role has full access ✓
- Backend bypasses RLS via `sb_secret_` key (documented, intentional) ✓

No SQL injection risks in migrations (DDL only, no dynamic SQL). ✓

## Additional Security Note: Open Redirect
`src/services/checkout_service.py:41-57` — `_validate_redirect_url()` properly validates against allowlist of domains. Well-implemented open redirect prevention. ✓

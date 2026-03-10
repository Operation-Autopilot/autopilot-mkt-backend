# Phase 2: Static Analysis Results

## Tool Availability
- **ruff**: Not available (output was empty/19 bytes = "ruff not available")
- **mypy**: Not available (0 lines output)
- **bandit**: Not available (output was empty/21 bytes)
- **vulture**: Not available
- **radon**: Not installed
- **pip-audit**: Not run in this env (no packages installed globally)
- **semgrep**: Not run

Note: The project does have ruff/mypy configured in `pyproject.toml` as dev dependencies, but these tools are not installed in the current Python environment used for the audit. Analysis was conducted via manual code review and pattern matching instead.

## Manual Static Analysis Findings

### Import Errors (P0)
1. **`src/core/supabase.py:8`** — `from supabase_auth import SyncMemoryStorage`
   - `supabase_auth` is NOT listed in `pyproject.toml` OR `requirements.txt`
   - When executed: `ModuleNotFoundError: No module named 'supabase_auth'`
   - This causes `ImportError` at startup, blocking the entire application from starting
   - **Severity: P0 — Application cannot start**

2. **`scripts/index_products.py:19`** — `from src.services.product_service import ProductService`
   - `src/services/product_service.py` does NOT exist in the repository
   - **Severity: P0 — Script broken**

### Dependency Mismatches
3. **`pyproject.toml` vs `requirements.txt` conflict**:
   - `pyproject.toml`: `pinecone-client>=3.0.0` (old SDK name)
   - `requirements.txt`: `pinecone>=5.0.0` (new SDK name)
   - Code uses `from pinecone import Pinecone` (correct for new SDK)
   - If someone installs only from `pyproject.toml`, pinecone v3 client API is different
   - **Severity: P1**

4. **`resend` and `PyMuPDF`** in `requirements.txt` but NOT in `pyproject.toml`
   - Production deployment using `pyproject.toml` only would be missing these
   - `resend` is used in `src/services/email_service.py`
   - `PyMuPDF` (as `fitz`) is used in `scripts/extract_call_knowledge.py`
   - **Severity: P2** (scripts only for PyMuPDF; P1 for resend affecting production emails)

### Type/Config Issues
5. **`src/core/config.py:51`** — `env_file_priority="env_file"` in `SettingsConfigDict`
   - This is not a documented parameter in pydantic-settings 2.x
   - pydantic-settings will silently ignore unknown keys in `SettingsConfigDict` due to TypedDict not enforcing unknown keys at runtime, so it may not crash but has no effect
   - **Severity: P3**

### Unused Imports
6. **`src/api/deps.py:7`** — `Cookie` imported from fastapi but never used in the file
   - **Severity: P3**

### Deprecated APIs
7. **`datetime.utcnow()`** used in multiple places:
   - `src/services/checkout_service.py:64`
   - `src/services/conversation_service.py:327`
   - `src/services/roi_service.py:287,705`
   - `src/services/recommendation_service.py:541`
   - `src/services/gynger_service.py:225`
   - `src/schemas/roi.py:144,267`
   - `src/schemas/common.py:26,53,82`
   - `datetime.utcnow()` is deprecated in Python 3.12; use `datetime.now(timezone.utc)` instead
   - **Severity: P3**

### Hardcoded Magic Values
8. **`src/api/middleware/error_handler.py:178`** — `response.headers["X-RateLimit-Limit"] = "15"` hardcoded
   - The actual limit is configurable via `settings.rate_limit_anonymous_requests` (default 15)
   - This header always shows 15 even if configuration is different
   - **Severity: P2**

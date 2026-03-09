# Authentication Architecture

Autopilot Marketplace uses Supabase Auth with JWT tokens for authentication. This page covers the authentication flow, the two-client pattern for Supabase, RLS policies, and how protected routes work in FastAPI.

## Authentication Flow

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│  Browser  │────▶│  FastAPI     │────▶│  Supabase Auth  │
│           │     │  /auth/*     │     │                 │
│  1. Login │     │  2. Forward  │     │  3. Verify      │
│  request  │     │  credentials │     │  credentials    │
│           │◀────│◀─────────────│◀────│  4. Return JWT  │
│  5. Store │     │              │     │                 │
│  token    │     │              │     │                 │
└──────────┘     └──────────────┘     └─────────────────┘
       │
       │  Subsequent requests:
       │  Authorization: Bearer <jwt>
       ▼
┌──────────────┐     ┌─────────────────┐
│  FastAPI     │────▶│  Supabase       │
│  Protected   │     │  auth.get_user()│
│  Route       │     │  Verify JWT     │
└──────────────┘     └─────────────────┘
```

1. The frontend sends credentials to the backend auth endpoints.
2. The backend forwards them to Supabase Auth.
3. Supabase verifies credentials and returns a JWT access token and refresh token.
4. The frontend stores the JWT and sends it as a `Bearer` token on all subsequent API requests.
5. Protected routes verify the JWT via `Depends(get_current_user)`.

## The Two-Client Pattern

This is the most important architectural detail in the authentication system. The backend maintains two types of Supabase client instances:

### Singleton Client (Database Operations)

```python
from functools import lru_cache
from supabase import create_client

@lru_cache()
def get_supabase_client():
    """Cached singleton for all database read/write operations.

    Uses the service role key for full database access.
    RLS policies still apply based on the request context.
    """
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],  # sb_secret_ prefixed key
    )
```

This client is created once and reused across all requests. It handles all database queries, inserts, updates, and deletes.

### Fresh Client (Auth Operations)

```python
def create_auth_client():
    """Fresh instance for authentication operations.

    A new client is created for each auth request to avoid
    header contamination.
    """
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],
    )
```

A new client is created for every authentication operation (sign-in, sign-up, token refresh).

### Why Two Clients?

The Supabase Python client stores the auth session internally. When you call `auth.set_session()` or `auth.sign_in()`, the client overwrites its `Authorization` header with the user's JWT token.

If this happens on the singleton client, subsequent database operations would use the user's token instead of the service role key. This causes **RLS policy violations** -- the service role key bypasses RLS, but a user JWT is subject to RLS policies that may not permit the operation the backend needs to perform.

```
PROBLEM: Using one client for everything

  sign_in(user_credentials)
      │
      ▼
  client.auth.set_session(user_jwt)
      │
      ▼
  client.headers["Authorization"] = "Bearer user_jwt"  ← OVERWRITTEN
      │
      ▼
  client.table("admin_data").select("*")  ← FAILS: RLS denies access
```

```
SOLUTION: Two-client pattern

  Singleton client                    Fresh auth client
  ─────────────────                   ──────────────────
  headers: service_role_key           sign_in(user_creds)
  table("admin_data").select("*")     → returns JWT
  → WORKS: service role bypasses RLS  → client discarded
```

## Supabase Key Format

The project uses the newer `sb_secret_` key format rather than the legacy JWT service role key. This key is set as the `SUPABASE_KEY` environment variable.

```
# Legacy format (deprecated)
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# New format
sb_secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The `sb_secret_` key provides the same service-role access but follows Supabase's updated key management conventions. Both formats work with the Supabase Python client, but new projects should use the `sb_secret_` format.

## Row Level Security (RLS)

Supabase RLS policies enforce data isolation at the database level. Even if application code has a bug, RLS prevents unauthorized data access.

### Policy Examples

```sql
-- Users can only read their own profile
CREATE POLICY "Users read own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = user_id);

-- Users can only read conversations in their sessions
CREATE POLICY "Users read own conversations"
  ON conversations FOR SELECT
  USING (
    session_id IN (
      SELECT id FROM sessions WHERE user_id = auth.uid()
    )
  );

-- Company members can read company data
CREATE POLICY "Company members read company"
  ON companies FOR SELECT
  USING (
    id IN (
      SELECT company_id FROM company_members
      WHERE user_id = auth.uid()
    )
  );
```

### Service Role Bypass

The singleton Supabase client uses the service role key, which bypasses RLS entirely. This is intentional -- the backend needs unrestricted database access for operations like:

- Cross-user data aggregation
- Admin operations
- Webhook processing (no user context)
- Background jobs

RLS primarily protects against direct Supabase client access from the frontend (if ever enabled) and provides defense-in-depth against backend bugs.

## Protected Routes in FastAPI

Routes are protected by adding `Depends(get_current_user)` to the handler signature:

```python
from src.api.deps import get_current_user

@router.get("/profiles/me")
async def get_my_profile(
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client),
):
    """This route requires a valid JWT token."""
    service = ProfileService(supabase)
    return await service.get_by_user_id(user.id)
```

The `get_current_user` dependency:

1. Extracts the `Authorization` header.
2. Strips the `Bearer ` prefix.
3. Calls `supabase.auth.get_user(token)` to verify the JWT.
4. Returns the user object if valid, or raises `HTTPException(401)`.

### Public Routes

Some routes do not require authentication (e.g., health checks, webhook receivers, anonymous session creation):

```python
@router.get("/health")
async def health_check():
    """No Depends(get_current_user) — this route is public."""
    return {"status": "ok"}
```

## Token Refresh

The frontend handles token refresh using Supabase's built-in `onAuthStateChange` listener. When the access token nears expiration, the Supabase client automatically refreshes it using the stored refresh token. The new access token is then used for subsequent API calls.

```typescript
// Frontend: automatic token refresh via Supabase client
supabase.auth.onAuthStateChange((event, session) => {
  if (event === "TOKEN_REFRESHED" && session) {
    // New access token is automatically available
    // via supabase.auth.getSession()
  }
});
```

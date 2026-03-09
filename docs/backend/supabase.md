---
title: Supabase Integration
---

# Supabase Integration

The backend uses **Supabase** as its PostgreSQL database provider and authentication service. This page covers the client architecture, key format, and RLS policy guidelines.

## The `sb_secret_` Key Format

Supabase has transitioned to a new key format prefixed with `sb_secret_`. This replaces the older JWT-based service role key.

```
# Old format (deprecated)
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3Mi...

# New format
sb_secret_aBcDeFgHiJkLmNoPqRsTuVwXyZ...
```

The new key is set via the `SUPABASE_SERVICE_ROLE_KEY` environment variable and is used for both database operations and auth admin actions.

## Two-Client Pattern

The backend uses **two separate Supabase client instances** for different purposes. This is a critical architectural decision.

### Database Client: `get_supabase_client()`

A **singleton** client instance cached with `@lru_cache` for all database read/write operations:

```python
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Singleton Supabase client for database operations.
    Cached to reuse connection across requests.
    """
    return create_client(
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_SERVICE_ROLE_KEY,
    )
```

Usage:

```python
db = get_supabase_client()
result = db.table("profiles").select("*").eq("id", profile_id).execute()
```

### Auth Client: `create_auth_client()`

A **fresh client instance** created for every auth operation:

```python
def create_auth_client() -> Client:
    """
    Fresh Supabase client for auth operations.
    Must NOT be shared with the DB singleton.
    """
    return create_client(
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_SERVICE_ROLE_KEY,
    )
```

Usage:

```python
auth_client = create_auth_client()
auth_client.auth.set_session(access_token, refresh_token)
user = auth_client.auth.get_user()
```

### Why Two Clients?

::: danger Critical
**`auth.set_session()` overwrites the `Authorization` header** on the client instance. If you call `set_session()` on the singleton DB client, all subsequent database queries will use the user's JWT instead of the service role key. This causes **RLS policy violations** because the service role key bypasses RLS, but the user JWT does not.
:::

The failure mode:

1. Request A calls `auth.set_session(user_token)` on the singleton client
2. The singleton's `Authorization` header is now set to the user's JWT
3. Request B (different user) makes a DB query on the same singleton
4. The query runs with Request A's user token, not the service role key
5. RLS policies reject the query or return wrong data

**Solution:** Always use `create_auth_client()` for any operation that calls `auth.set_session()` or `auth.get_user()` with a user token. The fresh instance is discarded after use.

## Row Level Security Guidelines

All tables have RLS enabled. The service role key bypasses RLS, but policies are critical for direct Supabase client access and for defense-in-depth.

### General RLS Patterns

```sql
-- Users can read their own profile
CREATE POLICY "Users can read own profile"
ON profiles FOR SELECT
USING (auth.uid() = auth_user_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
ON profiles FOR UPDATE
USING (auth.uid() = auth_user_id);
```

### Company Member Policies: Avoid Self-Referencing

::: warning
**Do not create self-referencing RLS policies on `company_members`.** A policy that checks `company_members` to authorize access to `company_members` creates an infinite recursion that PostgreSQL silently resolves by returning no rows.
:::

**Bad** - self-referencing policy:

```sql
-- DO NOT DO THIS
CREATE POLICY "Members can view company members"
ON company_members FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM company_members cm
        WHERE cm.company_id = company_members.company_id
        AND cm.profile_id = auth.uid()
    )
);
```

**Good** - use the `profiles` table for identity checks:

```sql
-- Use profiles table instead
CREATE POLICY "Members can view company members"
ON company_members FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM profiles p
        WHERE p.auth_user_id = auth.uid()
        AND p.id = company_members.profile_id
    )
);
```

### RLS Debugging Tips

1. **Test policies in the Supabase SQL editor** using `SET ROLE authenticated; SET request.jwt.claims = '{"sub": "user-uuid"}';`
2. **Check for infinite recursion** by examining query plans when policies reference the same table
3. **Use the service role key** for admin operations that need to bypass RLS
4. **Log RLS failures** — they often appear as empty result sets rather than errors

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL (e.g., `https://xxxxx.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (`sb_secret_...` format) |

## Common Operations

### Insert with Returning

```python
db = get_supabase_client()
result = (
    db.table("conversations")
    .insert({
        "profile_id": profile_id,
        "title": title,
    })
    .execute()
)
new_conversation = result.data[0]
```

### Upsert

```python
db = get_supabase_client()
result = (
    db.table("profiles")
    .upsert({
        "auth_user_id": auth_user_id,
        "email": email,
        "full_name": full_name,
    }, on_conflict="auth_user_id")
    .execute()
)
```

### Filtered Query

```python
db = get_supabase_client()
result = (
    db.table("robots")
    .select("*")
    .eq("category", "AMR")
    .gte("price_usd", 10000)
    .lte("price_usd", 50000)
    .order("price_usd")
    .limit(20)
    .execute()
)
```

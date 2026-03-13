# Claude Code Project Guidelines

## Supabase Authentication

**Important:** Supabase has deprecated JWT-based service role keys. Always use the `SUPABASE_SECRET_KEY` format (`sb_secret_...`) now.

Reference: <https://github.com/orgs/supabase/discussions/29260>

### Configuration

```bash
# .env
SUPABASE_SECRET_KEY=sb_secret_...  # New format - use this
```

The secret key format `sb_secret_...` replaces the old JWT-based service role key (`eyJ...`). This key bypasses RLS at the PostgREST API level.

### Supabase Client Patterns

**Two client factories exist in `src/core/supabase.py`:**

1. **`get_supabase_client()`** - Singleton for database operations
   - Use for: SELECT, INSERT, UPDATE, DELETE on tables
   - Cached via `@lru_cache` for performance
   - RLS is bypassed via the `sb_secret_` key

2. **`create_auth_client()`** - Fresh instance for auth operations
   - Use for: signup, login, logout, password reset, set_session()
   - Creates a new isolated client each time
   - Prevents session pollution of the singleton

**Why two clients?** When `auth.set_session()` is called, it overwrites the client's `Authorization` header. If this happens on the singleton, ALL subsequent database operations would use the user's JWT instead of the service key, causing RLS violations.

## Database Migrations

Migrations are located in `supabase/migrations/` and follow sequential numbering. **26 migrations exist (001–026).**

- `001_create_profiles.sql` - User profiles linked to auth.users
- `002_create_companies.sql` - Companies, members, invitations (with non-recursive RLS)
- `003_create_conversations.sql` - Conversations and messages
- `004_create_sessions.sql` - Anonymous session management
- `005_create_discovery_profiles.sql` - Authenticated user discovery progress
- `006_create_robot_catalog.sql` - Robot products with Stripe integration (seeds 22 robots, 13 active)
- `007_create_orders.sql` - Checkout orders (`order_status` enum: pending/payment_pending/completed/cancelled/refunded)
- `008_rename_conversations_user_id.sql` - Rename user_id → profile_id on conversations
- `009_add_cached_recommendations.sql` - `answers_hash` + `cached_recommendations` on discovery_profiles
- `010_make_stripe_checkout_session_id_nullable.sql` - Make `stripe_checkout_session_id` nullable (supports Gynger)
- `011_add_test_account_flag.sql` - `is_test_account` boolean on profiles
- `012_create_floor_plan_analysis.sql` - Floor plan upload + GPT-4o Vision analysis results
- `013_add_payment_pending_status.sql` - Add `payment_pending` to order_status enum (ACH)
- `014_add_gynger_to_orders.sql` - `gynger_application_id` + `payment_provider` columns on orders
- `015_add_purchase_price_ids.sql` - Stripe purchase price IDs for one-time purchase mode
- `016_enable_sessions_rls.sql` - Enable RLS policies on sessions table
- `017_pickleball_messaging.sql` - Pickleball robot messaging (CC1 Pro/C40/C30 court types)
- `018_data_corrections.sql` - Spec corrections (Neo 2W nav, T380AMR runtime, Scrubber/Omnie/Vacuum 40)
- `019_add_purchase_price_ids.sql` - *(duplicate of 015 — no-op)*
- `020_enable_sessions_rls.sql` - *(duplicate of 016 — no-op)*
- `021_set_inactive_robots.sql` - Mark 9 robots inactive (Beetle, Omnie, Scrubber 50/75, T16AMR, C20, C55, Marvel, Mira)
- `022_robot_image_updates.sql` - Update robot images to OEM photos
- `023_add_test_robot.sql` - Seed Penny test robot for E2E testing
- `024_court_type_surfaces.sql` - Add CushionX, Acrylic, Concrete court surface types
- `025_mt1_vac_image_updates.sql` - Update MT1 Vac images
- `026_company_scoped_discovery_profiles.sql` - Add `company_id` to discovery_profiles for shared company discovery data

> **Note:** Migrations 019 and 020 are accidental duplicates of 015 and 016 (idempotent no-ops).

### RLS Policy Guidelines

- Avoid self-referencing policies on `company_members` to prevent infinite recursion
- Use `profiles` table for user identity checks (via `auth.uid()`)
- The `sb_secret_` key bypasses RLS at PostgREST level - no special RLS policies needed for backend access

## Stripe Integration

The robot catalog supports both test and production Stripe environments:

- `stripe_product_id` / `stripe_lease_price_id` - Production
- `stripe_product_id_test` / `stripe_lease_price_id_test` - Test

Run `python scripts/sync_stripe_products.py` to sync products to Stripe. The script auto-detects test vs production mode based on the `STRIPE_SECRET_KEY` prefix (`sk_test_` vs `sk_live_`).

### Test Accounts in Production

Profiles can be marked as "test accounts" to use Stripe test mode in production. This allows testing the full checkout flow without real charges.

**Configuration:**

```bash
# .env (production)
STRIPE_SECRET_KEY=sk_live_...           # Production Stripe key
STRIPE_WEBHOOK_SECRET=whsec_...         # Production webhook secret
STRIPE_SECRET_KEY_TEST=sk_test_...      # Test Stripe key (for test accounts)
STRIPE_WEBHOOK_SECRET_TEST=whsec_...    # Test webhook secret
```

**Enable test mode for an account:**

```bash
# Via API (authenticated user)
POST /api/v1/profiles/me/test-account
{"is_test_account": true}

# Via SQL (direct database)
UPDATE profiles SET is_test_account = true WHERE email = 'test@example.com';
```

**How it works:**

1. When `is_test_account=true`, checkout uses `STRIPE_SECRET_KEY_TEST` and test price IDs
2. Webhooks try production secret first, then test secret (supports both in parallel)
3. The `is_test_mode` flag is stored in order metadata for reference

**Setting up test webhooks:**

You need a separate webhook endpoint in Stripe test mode pointing to the same `/api/v1/webhooks/stripe` URL. The backend automatically routes based on which secret successfully verifies the signature.

---
title: Database
---

# Database

The backend uses **Supabase PostgreSQL** as its primary database, with **Row Level Security (RLS)** policies for data isolation between tenants.

## Schema Overview

<DatabaseSchema />

<details>
<summary>Text fallback</summary>

```
profiles → companies (via company_members), conversations → messages, sessions, discovery_profiles, orders
robots (standalone catalog)
```

</details>

## Tables

### profiles

Stores user profile information, linked to Supabase Auth users.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `auth_user_id` | `uuid` | FK to `auth.users` |
| `email` | `text` | User email |
| `full_name` | `text` | Display name |
| `company_name` | `text` | Company name (denormalized) |
| `job_title` | `text` | Job title |
| `phone` | `text` | Phone number |
| `is_test_account` | `boolean` | Flag for test accounts in production |
| `created_at` | `timestamptz` | Row creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

### companies

Company entities that users belong to.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `name` | `text` | Company name |
| `industry` | `text` | Industry vertical |
| `size` | `text` | Company size range |
| `website` | `text` | Company website URL |
| `metadata` | `jsonb` | Flexible additional data |
| `created_at` | `timestamptz` | Row creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

### company_members

Join table linking profiles to companies with roles.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `company_id` | `uuid` | FK to `companies` |
| `profile_id` | `uuid` | FK to `profiles` |
| `role` | `text` | Member role (admin, member) |
| `joined_at` | `timestamptz` | When member joined |

### conversations

Chat conversations between users and the AI agent.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `profile_id` | `uuid` | FK to `profiles` (nullable for anonymous) |
| `session_id` | `uuid` | FK to `sessions` (nullable) |
| `title` | `text` | Conversation title |
| `metadata` | `jsonb` | Flexible additional data |
| `created_at` | `timestamptz` | Row creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

### messages

Individual messages within conversations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `conversation_id` | `uuid` | FK to `conversations` |
| `role` | `text` | Message role: `user`, `assistant`, `system` |
| `content` | `text` | Message content |
| `metadata` | `jsonb` | Token counts, model info, etc. |
| `created_at` | `timestamptz` | Row creation timestamp |

### sessions

Anonymous sessions for unauthenticated users.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `metadata` | `jsonb` | Session metadata |
| `created_at` | `timestamptz` | Row creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

### discovery_profiles

Structured profiles storing discovery progress for authenticated users. Company-scoped since migration 026 — members of the same company share a single discovery profile.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `profile_id` | `uuid` | FK to `profiles` |
| `company_id` | `uuid` | FK to `companies` (nullable — shared across company members, added in 026) |
| `current_question_index` | `integer` | Current question index in discovery flow |
| `phase` | `text` | Current phase: `discovery`, `roi`, or `greenlight` |
| `answers` | `jsonb` | Discovery answers keyed by question key |
| `roi_inputs` | `jsonb` | ROI calculation inputs (monthly_spend, sqft, hours, frequency) |
| `selected_product_ids` | `uuid[]` | Selected robot IDs from recommendations |
| `timeframe` | `text` | ROI display timeframe (`monthly` or `yearly`) |
| `greenlight` | `jsonb` | Greenlight phase data (team members, target date) |
| `answers_hash` | `text` | Hash of answers for recommendation cache invalidation (added in 009) |
| `cached_recommendations` | `jsonb` | Cached recommendation results (added in 009) |
| `created_at` | `timestamptz` | Row creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

### robot_catalog

The robot product catalog (table name is `robot_catalog`, not `robots`). Seeded with 22 robots in migration 006; 13 active, 9 inactive (set in 021).

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `sku` | `text` | Unique SKU identifier (e.g., `cc1_pro`, `t7amr`) |
| `name` | `text` | Robot display name |
| `manufacturer` | `text` | Manufacturer name |
| `monthly_lease` | `numeric` | Monthly lease price (USD) |
| `purchase_price` | `numeric` | One-time purchase price (USD) |
| `active` | `boolean` | Whether robot is shown in marketplace |
| `stripe_product_id` | `text` | Production Stripe product ID |
| `stripe_lease_price_id` | `text` | Production Stripe lease price ID |
| `stripe_product_id_test` | `text` | Test Stripe product ID |
| `stripe_lease_price_id_test` | `text` | Test Stripe lease price ID |
| `image_url` | `text` | Product image URL (Supabase Storage) |
| `specs` | `jsonb` | Technical specifications |
| `created_at` | `timestamptz` | Row creation timestamp |

### floor_plan_analyses

Floor plan uploads with GPT-4o Vision analysis results (added in migration 012).

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `profile_id` | `uuid` | FK to `profiles` |
| `file_path` | `text` | Storage path in Supabase |
| `analysis_result` | `jsonb` | GPT-4o Vision analysis output (sqft, layout, surface types) |
| `created_at` | `timestamptz` | Row creation timestamp |

### orders

Records of purchases and financing applications.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `profile_id` | `uuid` | FK to `profiles` |
| `session_id` | `uuid` | FK to `sessions` |
| `stripe_checkout_session_id` | `text` | Stripe checkout session ID (nullable for Gynger) |
| `gynger_application_id` | `text` | Gynger financing application ID (added in 014) |
| `payment_provider` | `text` | `stripe` or `gynger` (added in 014) |
| `status` | `order_status` | Enum: `pending`, `payment_pending`, `completed`, `cancelled`, `refunded` |
| `total_cents` | `integer` | Order total in cents |
| `line_items` | `jsonb` | Order line items (robot details, quantities) |
| `metadata` | `jsonb` | Order metadata (is_test_mode, etc.) |
| `created_at` | `timestamptz` | Row creation timestamp |

## JSONB Usage

Several tables use `jsonb` columns for flexible, schema-less metadata:

```sql
-- Store arbitrary key-value metadata
UPDATE conversations
SET metadata = metadata || '{"source": "discovery", "version": 2}'::jsonb
WHERE id = '...';

-- Query JSONB fields
SELECT * FROM discovery_profiles
WHERE requirements->>'autonomy_level' = 'fully_autonomous';
```

This approach provides flexibility for evolving requirements without schema migrations.

## Migrations

Migrations are managed in `supabase/migrations/` and applied via the Supabase CLI:

| Migration | Description |
|-----------|-------------|
| `001_create_profiles` | Profiles table and RLS policies |
| `002_create_companies` | Companies and company_members tables |
| `003_create_conversations` | Conversations and messages tables |
| `004_create_sessions` | Anonymous sessions table |
| `005_create_discovery_profiles` | AI-extracted discovery profiles |
| `006_create_robot_catalog` | Robot product catalog (seeds 13 robots) |
| `007_create_orders` | Order records with `order_status` enum |
| `008_rename_conversations_user_id` | Rename `user_id` → `profile_id` on conversations |
| `009_add_cached_recommendations` | `answers_hash` + `cached_recommendations` on discovery_profiles |
| `010_make_stripe_checkout_session_id_nullable` | Make `stripe_checkout_session_id` nullable (supports Gynger orders) |
| `011_add_test_account_flag` | Add `is_test_account` boolean to profiles |
| `012_create_floor_plan_analysis` | `floor_plan_analyses` table with GPT-4o Vision results |
| `013_add_payment_pending_status` | Add `payment_pending` to `order_status` enum (ACH / delayed payments) |
| `014_add_gynger_to_orders` | `gynger_application_id` + `payment_provider` columns on orders |
| `015_add_purchase_price_ids` | Stripe purchase price IDs for one-time purchase mode |
| `016_enable_sessions_rls` | Enable RLS policies on sessions table |
| `017_pickleball_messaging` | Pickleball robot messaging updates (CC1 Pro/C40/C30 court types) |
| `018_data_corrections` | Spec corrections: Neo 2W nav, T380AMR runtime, Scrubber 50/75/Omnie/Vacuum 40 |
| `019_add_purchase_price_ids` | *(duplicate of 015 — safe no-op)* |
| `020_enable_sessions_rls` | *(duplicate of 016 — safe no-op)* |
| `021_set_inactive_robots` | Mark 9 robots inactive (Beetle, Omnie, Scrubber 50/75, T16AMR, C20, C55, Marvel, Mira) |
| `022_robot_image_updates` | Update robot images to OEM photos in Supabase Storage |
| `023_add_test_robot` | Seed Penny test robot for E2E testing |
| `024_court_type_surfaces` | Add CushionX, Acrylic, Concrete court surface types for pickleball robots |
| `025_mt1_vac_image_updates` | Update MT1 Vac images |
| `026_company_scoped_discovery_profiles` | Add `company_id` to `discovery_profiles` for shared company discovery data |

> **Note:** Migrations 019 and 020 are accidental duplicates of 015 and 016 respectively. They are idempotent no-ops.

> See [Database Migrations](../status/migrations.md) for the auto-generated version of this table.

```bash
# Apply all pending migrations
supabase db push

# Create a new migration
supabase migration new my_migration_name
```

## Row Level Security

All tables have RLS enabled. See [Supabase Integration](./supabase.md) for RLS policy details and gotchas.

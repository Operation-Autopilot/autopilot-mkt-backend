---
title: Database
---

# Database

The backend uses **Supabase PostgreSQL** as its primary database, with **Row Level Security (RLS)** policies for data isolation between tenants.

## Schema Overview

```
profiles
├── companies (via company_members join)
│   └── company_members
├── conversations
│   └── messages
├── sessions
├── discovery_profiles
└── orders

robots (standalone catalog)
```

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

Structured profiles extracted from discovery conversations by AI.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `conversation_id` | `uuid` | FK to `conversations` |
| `profile_id` | `uuid` | FK to `profiles` |
| `industry` | `text` | Extracted industry |
| `facility_size` | `text` | Facility dimensions/category |
| `use_cases` | `jsonb` | Array of identified use cases |
| `budget_range` | `jsonb` | Min/max budget |
| `requirements` | `jsonb` | Structured requirements object |
| `created_at` | `timestamptz` | Row creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

### robots

The robot product catalog.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `name` | `text` | Robot name |
| `manufacturer` | `text` | Manufacturer name |
| `category` | `text` | Robot category |
| `description` | `text` | Product description |
| `specs` | `jsonb` | Technical specifications |
| `price_usd` | `numeric` | List price |
| `stripe_product_id` | `text` | Production Stripe product ID |
| `stripe_price_id` | `text` | Production Stripe price ID |
| `stripe_product_id_test` | `text` | Test Stripe product ID |
| `stripe_price_id_test` | `text` | Test Stripe price ID |
| `image_url` | `text` | Product image URL |
| `created_at` | `timestamptz` | Row creation timestamp |

### orders

Records of completed purchases.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `profile_id` | `uuid` | FK to `profiles` |
| `robot_id` | `uuid` | FK to `robots` |
| `stripe_session_id` | `text` | Stripe checkout session ID |
| `status` | `text` | Order status |
| `amount` | `numeric` | Order total |
| `metadata` | `jsonb` | Order metadata |
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
| `006_create_robot_catalog` | Robot product catalog |
| `007_create_orders` | Order records |
| `011_add_test_account_flag` | Add `is_test_account` to profiles |

```bash
# Apply all pending migrations
supabase db push

# Create a new migration
supabase migration new my_migration_name
```

## Row Level Security

All tables have RLS enabled. See [Supabase Integration](./supabase.md) for RLS policy details and gotchas.

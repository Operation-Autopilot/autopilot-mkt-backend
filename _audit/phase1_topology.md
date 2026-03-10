# Phase 1: Repository Topology Mapping

## Repository Overview
- **Name**: autopilot-mkt-backend
- **Description**: Agent-led robotics procurement platform backend
- **Size Category**: MEDIUM (320 files, 143 Python source files + 60 test files)
- **Python version**: >=3.11 required

## Tech Stack
- **Framework**: FastAPI 0.109+
- **Runtime**: Python 3.11/3.12, uvicorn[standard]
- **Data layer**: Supabase (PostgreSQL), PostgREST API via `supabase-py 2.4+`
- **Auth**: Supabase JWT (ES256), `PyJWT 2.8+`, `python-jose[cryptography]`
- **AI/ML**: OpenAI `gpt-4o` / `gpt-4o-mini`, Pinecone `5.x` for RAG
- **Payments**: Stripe `7.x`, Gynger B2B financing
- **Email**: Resend SDK
- **PDF**: PyMuPDF (fitz)

## Entry Points
- `src/main.py` — `create_app()` factory, `app = create_app()` at module level
- `uvicorn src.main:app` — production startup

## Architecture
```
FastAPI App
├── middleware/ (error_handler, latency_logging, auth, request_size)
├── routes/ (auth, profiles, companies, invitations, sessions, discovery,
│            conversations, robots, floor_plans, roi, checkout, webhooks)
├── services/ (22 service modules)
├── schemas/ (Pydantic v2 models)
├── models/ (TypedDict domain models)
└── core/ (config, supabase, openai, pinecone, stripe, rate_limiter, token_budget)
```

## Dependency Analysis
- `pyproject.toml` lists 13 runtime dependencies
- `requirements.txt` lists 16 runtime dependencies (superset with slight version diffs)
- **DISCREPANCY**: `pyproject.toml` uses `pinecone-client>=3.0.0` but `requirements.txt` uses `pinecone>=5.0.0` — actual import uses `from pinecone import Pinecone` (new SDK style, not `pinecone-client`)
- `supabase_auth` imported in `src/core/supabase.py` but NOT listed in either dependency file
- `resend` in `requirements.txt` only, not in `pyproject.toml`
- `PyMuPDF` in `requirements.txt` only, not in `pyproject.toml`

## Test Framework
- pytest 7.4+, pytest-asyncio 0.23+, pytest-cov 4.1+
- 53 test files, 406 test functions
- 711 assertions
- Tests located in: `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/flow/`

## Database Migrations
- 14 migration files in `supabase/migrations/`
- Most recent: `014_add_gynger_to_orders.sql`
- (Note: MEMORY.md references 016_session_shares.sql which does NOT exist in this branch)

## LLM-Generation Indicators
- Multiple `# TODO: confirm with Gynger docs` comments in `gynger_service.py`
- `scripts/index_products.py` imports `src.services.product_service.ProductService` which does not exist
- Redundant `_execute_sync` helper duplicated across 6+ service classes
- `env_file_priority="env_file"` in `SettingsConfigDict` — invalid option in tested pydantic-settings versions
- `Cookie` imported in `deps.py` but unused
- `datetime.utcnow()` used in 8+ places (deprecated since Python 3.12)

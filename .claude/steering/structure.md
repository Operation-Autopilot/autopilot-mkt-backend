# Project Structure

## Directory Organization

<!-- AUTO-TREE:START -->
```
autopilot-mkt-backend/
├── src/api/routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── checkout.py
│   ├── companies.py
│   ├── conversations.py
│   ├── discovery.py
│   ├── floor_plans.py
│   ├── health.py
│   ├── invitations.py
│   ├── profiles.py
│   ├── robots.py
│   ├── roi.py
│   ├── sessions.py
│   ├── webhooks.py
├── src/api/middleware/
│   ├── __init__.py
│   ├── auth.py
│   ├── error_handler.py
│   ├── latency_logging.py
│   ├── request_size.py
├── src/services/
│   ├── __init__.py
│   ├── agent_service.py
│   ├── auth_service.py
│   ├── base_service.py
│   ├── checkout_service.py
│   ├── company_service.py
│   ├── conversation_service.py
│   ├── discovery_profile_service.py
│   ├── email_service.py
│   ├── extraction_constants.py
│   ├── floor_plan_prompts.py
│   ├── floor_plan_service.py
│   ├── gynger_service.py
│   ├── hubspot_service.py
│   ├── invitation_service.py
│   ├── profile_extraction_service.py
│   ├── profile_service.py
│   ├── rag_service.py
│   ├── recommendation_cache.py
│   ├── recommendation_prompts.py
│   ├── recommendation_service.py
│   ├── robot_catalog_service.py
│   ├── roi_service.py
│   ├── sales_knowledge_service.py
│   ├── session_service.py
├── src/schemas/
│   ├── __init__.py
│   ├── auth.py
│   ├── checkout.py
│   ├── common.py
│   ├── company.py
│   ├── conversation.py
│   ├── discovery.py
│   ├── floor_plan.py
│   ├── message.py
│   ├── profile.py
│   ├── robot.py
│   ├── roi.py
│   ├── session.py
├── src/models/
│   ├── __init__.py
│   ├── company.py
│   ├── conversation.py
│   ├── discovery_profile.py
│   ├── message.py
│   ├── order.py
│   ├── profile.py
│   ├── robot.py
│   ├── session.py
├── src/core/
│   ├── __init__.py
│   ├── config.py
│   ├── openai.py
│   ├── pinecone.py
│   ├── rate_limiter.py
│   ├── stripe.py
│   ├── supabase.py
│   ├── token_budget.py
├── scripts/
│   ├── deploy-cloud-run.sh
│   ├── dev-server.sh
│   ├── e2e_stripe_test.py
│   ├── export-openapi.mjs
│   ├── extract_call_knowledge.py
│   ├── generate-dmms-docs.mjs
│   ├── index_products.py
│   ├── install-git-hooks.mjs
│   ├── migrate-dmms-hierarchy.mjs
│   ├── seed_test_robot.py
│   ├── setup-secrets.sh
│   ├── stripe_dev.sh
│   ├── sync_stripe_products.py
│   ├── update-steering.mjs
│   ├── upload_robot_images.py
│   ├── validate_robot_images.py
└── supabase/migrations/  (21 files)
    └── ...021_set_inactive_robots.sql  ← last applied
```
<!-- AUTO-TREE:END -->

## Naming Conventions

### Files
- **Modules**: `snake_case.py` (e.g., `profile_service.py`, `error_handler.py`)
- **Routes**: Named by resource (e.g., `profiles.py`, `conversations.py`)
- **Tests**: `test_{module_name}.py` (e.g., `test_profile_service.py`)

### Code
- **Classes**: `PascalCase` (e.g., `ProfileService`, `ConversationCreate`)
- **Functions/Methods**: `snake_case` (e.g., `get_profile`, `create_conversation`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PAGE_SIZE`, `MAX_CONTEXT_TOKENS`)
- **Variables**: `snake_case` (e.g., `user_id`, `conversation_history`)
- **Pydantic Schemas**: `{Resource}{Action}` (e.g., `ProfileUpdate`, `ConversationCreate`, `MessageResponse`)

### Database
- **Tables**: `snake_case` plural (e.g., `profiles`, `conversations`, `company_members`)
- **Columns**: `snake_case` (e.g., `user_id`, `created_at`, `display_name`)
- **Foreign Keys**: `{referenced_table_singular}_id` (e.g., `profile_id`, `company_id`)

## Import Patterns

### Import Order
1. Standard library imports
2. Third-party imports
3. Local application imports (absolute from `src`)

### Example
```python
# Standard library
from datetime import datetime
from typing import Optional
from uuid import UUID

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# Local application
from src.core.supabase import get_supabase_client
from src.schemas.profile import ProfileResponse
from src.services.profile_service import ProfileService
```

### Module Organization
- Use absolute imports from `src` package
- Group related imports together
- Avoid circular imports by keeping clear layer boundaries

## Code Structure Patterns

### Router Module Pattern
```python
# src/api/routes/{resource}.py
from fastapi import APIRouter, Depends, HTTPException, status
from src.api.deps import get_current_user
from src.schemas.{resource} import {Resource}Create, {Resource}Response
from src.services.{resource}_service import {Resource}Service

router = APIRouter(prefix="/{resources}", tags=["{resources}"])

@router.post("/", response_model={Resource}Response, status_code=status.HTTP_201_CREATED)
async def create_{resource}(
    data: {Resource}Create,
    user = Depends(get_current_user)
):
    service = {Resource}Service()
    return await service.create(data, user.id)
```

### Service Module Pattern
```python
# src/services/{resource}_service.py
from uuid import UUID
from src.core.supabase import get_supabase_client
from src.schemas.{resource} import {Resource}Create, {Resource}Update

class {Resource}Service:
    def __init__(self):
        self.client = get_supabase_client()

    async def create(self, data: {Resource}Create, user_id: UUID) -> dict:
        # Implementation
        pass

    async def get_by_id(self, id: UUID) -> dict | None:
        # Implementation
        pass
```

### Schema Module Pattern
```python
# src/schemas/{resource}.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class {Resource}Base(BaseModel):
    # Shared fields
    pass

class {Resource}Create({Resource}Base):
    # Fields for creation
    pass

class {Resource}Update(BaseModel):
    # Optional fields for update
    pass

class {Resource}Response({Resource}Base):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

## Code Organization Principles

1. **Single Responsibility**: Each module has one clear purpose
2. **Layer Isolation**: Routes → Services → Models (no skipping layers)
3. **Dependency Direction**: Higher layers depend on lower layers, never reverse
4. **Testability**: Services are stateless and can be tested with mocked dependencies

## Module Boundaries

### API Layer (`src/api/`)
- Handles HTTP request/response
- Input validation via Pydantic schemas
- Authentication via middleware
- Calls service layer for business logic
- **Never accesses database directly**

### Service Layer (`src/services/`)
- Contains all business logic
- Orchestrates multiple operations
- Handles errors and edge cases
- Calls core clients for external services
- **Never handles HTTP concerns**

### Core Layer (`src/core/`)
- Client singletons (Supabase, OpenAI, Pinecone)
- Configuration management
- Shared utilities
- **No business logic**

### Schema Layer (`src/schemas/`)
- Pydantic models for API contracts
- Request validation
- Response serialization
- **No business logic**

### Model Layer (`src/models/`)
- Database table representations
- Type hints for database operations
- **No business logic**

## Code Size Guidelines

- **File size**: Target <300 lines per file; split if exceeding 500
- **Function size**: Target <30 lines per function; extract helpers if longer
- **Class complexity**: Target <10 methods per class
- **Nesting depth**: Maximum 3 levels of nesting

## Documentation Standards

- All public functions must have docstrings with parameter and return descriptions
- Complex logic should include inline comments explaining "why"
- Each module should have a module-level docstring describing its purpose
- API endpoints are documented via FastAPI's automatic OpenAPI generation

## Applied Migrations

<!-- AUTO-MIGRATIONS:START -->
- `001_create_profiles.sql` — Create profiles table
- `002_create_companies.sql` — Create companies table
- `003_create_conversations.sql` — Create conversations and messages tables
- `004_create_sessions.sql` — Create sessions table
- `005_create_discovery_profiles.sql` — Create discovery_profiles table
- `006_create_robot_catalog.sql` — Create robot_catalog table
- `007_create_orders.sql` — Create orders table
- `008_rename_conversations_user_id.sql` — Rename conversations.user_id to profile_id for clarity
- `009_add_cached_recommendations.sql` — Add cached recommendations columns to discovery_profiles
- `010_make_stripe_checkout_session_id_nullable.sql` — Make stripe_checkout_session_id nullable to allow orders to be created
- `011_add_test_account_flag.sql` — Add is_test_account flag to profiles table
- `012_create_floor_plan_analysis.sql` — Create floor_plan_analyses table
- `013_add_payment_pending_status.sql` — Add 'payment_pending' status to order_status enum for ACH delayed payments
- `014_add_gynger_to_orders.sql` — Add Gynger financing columns to orders table
- `015_add_purchase_price_ids.sql` — Add Stripe purchase price IDs to robot_catalog for one-time purchase support
- `016_enable_sessions_rls.sql` — Enable RLS on sessions table to protect sensitive session_token column
- `017_pickleball_messaging.sql` — 017_pickleball_messaging.sql
- `018_data_corrections.sql` — 018_data_corrections.sql
- `019_add_purchase_price_ids.sql` — Add Stripe purchase price IDs to robot_catalog for one-time purchase support
- `020_enable_sessions_rls.sql` — Enable RLS on sessions table to protect sensitive session_token column
- `021_set_inactive_robots.sql` — 021_set_inactive_robots.sql
<!-- AUTO-MIGRATIONS:END -->

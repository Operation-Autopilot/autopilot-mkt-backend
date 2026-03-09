# API Layer

The API layer is implemented with FastAPI and lives in `src/api/routes/`. Each route module defines an `APIRouter` with a URL prefix and OpenAPI tags. Routers handle HTTP concerns only -- validation, serialization, auth dependency injection -- and delegate all business logic to the service layer.

## Router Structure

All route modules follow a consistent pattern:

```python
from fastapi import APIRouter, Depends
from src.api.deps import get_current_user, get_supabase_client

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.post("/")
async def create_conversation(
    payload: CreateConversationRequest,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client),
):
    service = ConversationService(supabase)
    return await service.create(payload, user)
```

Key conventions:

- `APIRouter` is instantiated with a `prefix` (URL namespace) and `tags` (OpenAPI grouping).
- `Depends(get_current_user)` injects the authenticated user, returning 401 if the token is invalid.
- `Depends(get_supabase_client)` injects the database client.
- The handler constructs a service instance and calls it. No business logic lives in the router.

## Route Modules

| Module | Prefix | Description |
|---|---|---|
| `health.py` | `/health` | Liveness and readiness probes |
| `auth.py` | `/auth` | Sign-up, sign-in, token refresh, password reset |
| `profiles.py` | `/profiles` | User profile CRUD |
| `companies.py` | `/companies` | Company registration and management |
| `conversations.py` | `/conversations` | Chat message exchange with the AI agent |
| `discovery.py` | `/discovery` | Discovery profile and needs assessment |
| `sessions.py` | `/sessions` | Session lifecycle (create, get, update phases) |
| `robots.py` | `/robots` | Robot catalog browsing and details |
| `checkout.py` | `/checkout` | Stripe checkout session creation |
| `roi.py` | `/roi` | ROI calculation and report generation |
| `webhooks.py` | `/webhooks` | Stripe and external service webhook handlers |
| `invitations.py` | `/invitations` | Team invitation management |
| `floor_plans.py` | `/floor_plans` | Facility floor plan upload and analysis |

## Dependency Injection

Dependencies are defined in `src/api/deps.py` and injected via FastAPI's `Depends` mechanism.

```python
# src/api/deps.py

from functools import lru_cache
from supabase import create_client
from fastapi import Depends, HTTPException, Header

@lru_cache()
def get_supabase_client():
    """Singleton Supabase client for database operations."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def get_current_user(
    authorization: str = Header(...),
    supabase=Depends(get_supabase_client),
):
    """Extract and verify the JWT from the Authorization header.

    Returns the authenticated user or raises 401.
    """
    token = authorization.replace("Bearer ", "")
    try:
        user = supabase.auth.get_user(token)
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

### Common Dependencies

- **`get_supabase_client`**: Returns the cached Supabase client for database queries.
- **`get_current_user`**: Validates the JWT token and returns the user object. Used on all protected routes.
- **`get_supabase_client` (fresh)**: For auth operations, a fresh client is created to avoid header conflicts (see [Authentication](./authentication.md)).

## Middleware

### Authentication Verification

Protected routes use `Depends(get_current_user)` which verifies the JWT token from the `Authorization` header. Unauthenticated requests receive a `401 Unauthorized` response.

### Error Handling

A global exception handler catches unhandled exceptions and returns structured JSON error responses:

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
```

Service-layer exceptions (e.g., `NotFoundException`, `ValidationError`) are caught and mapped to appropriate HTTP status codes (404, 422, etc.).

### CORS

CORS middleware is configured to allow requests from the frontend origin, with credentials enabled for cookie-based auth flows.

## Request/Response Flow

<RequestPipeline />

<details>
<summary>Text fallback</summary>

```
Client Request → Middleware (CORS) → Router → Depends() (Auth) → Service → JSON Response
```

</details>

## Adding a New Route

1. Create a new file in `src/api/routes/` (e.g., `widgets.py`).
2. Define an `APIRouter` with prefix and tags.
3. Add route handlers that inject dependencies and call service methods.
4. Register the router in the main app (typically `src/main.py` or a router aggregator).

```python
# src/api/routes/widgets.py
from fastapi import APIRouter, Depends
from src.api.deps import get_current_user, get_supabase_client
from src.services.widget_service import WidgetService

router = APIRouter(prefix="/widgets", tags=["widgets"])

@router.get("/")
async def list_widgets(
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client),
):
    service = WidgetService(supabase)
    return await service.list_for_user(user.id)
```

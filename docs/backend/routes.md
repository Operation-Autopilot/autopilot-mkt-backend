---
title: API Routes
---

# API Routes

All route modules live in `src/api/routes/`. Each module defines a FastAPI `APIRouter` that is registered in `src/main.py`.

## Route Modules

### health.py

Health check endpoint for load balancers and uptime monitoring.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Returns service health status |

```python
@router.get("/health")
async def health_check():
    return {"status": "ok"}
```

### auth.py

Authentication endpoints powered by Supabase Auth.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/signup` | Register a new user account |
| `POST` | `/api/auth/login` | Authenticate and receive tokens |
| `POST` | `/api/auth/logout` | Invalidate current session |
| `POST` | `/api/auth/refresh` | Refresh an expired access token |
| `POST` | `/api/auth/password-reset` | Initiate password reset flow |

### profiles.py

User profile management.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/profiles/me` | Get current user's profile |
| `PUT` | `/api/profiles/me` | Update current user's profile |
| `GET` | `/api/profiles/{id}` | Get a profile by ID |

### companies.py

Company and team member management.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/companies` | Create a new company |
| `GET` | `/api/companies/{id}` | Get company details |
| `PUT` | `/api/companies/{id}` | Update company information |
| `GET` | `/api/companies/{id}/members` | List company members |
| `POST` | `/api/companies/{id}/members` | Add a member to company |
| `DELETE` | `/api/companies/{id}/members/{member_id}` | Remove a company member |

### conversations.py

Conversation and message management for the AI agent chat.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/conversations` | Create a new conversation |
| `GET` | `/api/conversations` | List user's conversations |
| `GET` | `/api/conversations/{id}` | Get conversation with messages |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |
| `POST` | `/api/conversations/{id}/messages` | Send a message (triggers AI response) |
| `GET` | `/api/conversations/{id}/messages` | List messages in a conversation |

### discovery.py

Discovery flow endpoints for guided product recommendation.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/discovery/start` | Start a new discovery session |
| `GET` | `/api/discovery/{id}` | Get discovery session state |
| `POST` | `/api/discovery/{id}/respond` | Submit a discovery response |
| `GET` | `/api/discovery/{id}/profile` | Get extracted discovery profile |

### sessions.py

Anonymous session management for unauthenticated users.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions` | Create an anonymous session |
| `GET` | `/api/sessions/{id}` | Get session details |
| `PUT` | `/api/sessions/{id}` | Update session metadata |

### robots.py

Robot catalog browsing with filtering and AI-powered recommendations.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/robots` | List robots with pagination |
| `GET` | `/api/robots/{id}` | Get robot details |
| `GET` | `/api/robots/filters` | Get available filter options |
| `GET` | `/api/robots/search` | Search robots by query |
| `POST` | `/api/robots/recommendations` | Get AI-powered robot recommendations |

### checkout.py

Stripe checkout session creation for purchasing robots.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/checkout/sessions` | Create a Stripe checkout session |
| `GET` | `/api/checkout/sessions/{id}` | Get checkout session status |

### roi.py

ROI (Return on Investment) calculation endpoints.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/roi/calculate` | Calculate ROI for a robot deployment |
| `GET` | `/api/roi/{id}` | Get a saved ROI calculation |

### webhooks.py

Stripe webhook handlers for payment event processing.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/webhooks/stripe` | Handle Stripe webhook events |

::: warning
Webhook endpoints skip standard auth middleware. They verify requests using Stripe's webhook signature instead.
:::

### invitations.py

Company invitation management.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/invitations` | Send a company invitation |
| `GET` | `/api/invitations` | List pending invitations |
| `POST` | `/api/invitations/{id}/accept` | Accept an invitation |
| `POST` | `/api/invitations/{id}/decline` | Decline an invitation |

### floor_plans.py

Floor plan upload and management for facility mapping.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/floor-plans` | Upload a floor plan file |
| `GET` | `/api/floor-plans` | List uploaded floor plans |
| `GET` | `/api/floor-plans/{id}` | Get floor plan details |
| `DELETE` | `/api/floor-plans/{id}` | Delete a floor plan |

## Route Registration Pattern

All routers follow a consistent registration pattern in `src/main.py`:

```python
from src.api.routes import (
    health, auth, profiles, companies,
    conversations, discovery, sessions,
    robots, checkout, roi, webhooks,
    invitations, floor_plans,
)

app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(profiles.router, prefix="/api", tags=["Profiles"])
app.include_router(companies.router, prefix="/api", tags=["Companies"])
# ... etc.
```

## Authentication

Most routes require a valid JWT access token passed in the `Authorization: Bearer <token>` header. Exceptions include:

- `GET /health` — No auth required
- `POST /api/auth/signup` and `POST /api/auth/login` — No auth required
- `POST /api/sessions` — No auth required (anonymous access)
- `POST /api/webhooks/stripe` — Uses Stripe signature verification

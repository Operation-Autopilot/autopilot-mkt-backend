---
title: API Routes
---

# API Routes

All endpoints are prefixed with `/api/v1` except health checks (mounted at root). Authentication modes:

- **JWT** — `Authorization: Bearer <token>` (Supabase JWT)
- **Session** — cookie `autopilot_session` or `X-Session-Token` header (anonymous users)
- **Dual** — accepts either JWT or session token
- **Signature** — HMAC webhook signature verification (no user auth)
- **Public** — no authentication required

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | Public | Liveness check — returns 200 if service is running |
| `GET` | `/health/ready` | Public | Readiness check — verifies DB and Pinecone connectivity |
| `GET` | `/health/auth` | JWT | Authenticated health check — validates JWT token |
| `GET` | `/health/knowledge` | Public | Knowledge files status for debugging |

---

## Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/signup` | Public | Create new account with email + password |
| `POST` | `/api/v1/auth/verify-email` | Public | Verify email with token (POST form) |
| `GET` | `/api/v1/auth/verify-email` | Public | Verify email via GET (email link redirect) |
| `POST` | `/api/v1/auth/resend-verification` | Public | Resend verification email |
| `POST` | `/api/v1/auth/login` | Public | Authenticate and receive JWT |
| `POST` | `/api/v1/auth/logout` | JWT | Invalidate session |
| `GET` | `/api/v1/auth/me` | JWT | Get current user info |
| `POST` | `/api/v1/auth/forgot-password` | Public | Request password reset email |
| `POST` | `/api/v1/auth/reset-password` | Public | Reset password using email token |
| `POST` | `/api/v1/auth/change-password` | JWT | Change password (requires current password) |
| `POST` | `/api/v1/auth/refresh` | Public | Refresh access token using refresh token |

---

## Profiles

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/profiles/me` | JWT | Get authenticated user's profile |
| `PUT` | `/api/v1/profiles/me` | JWT | Update authenticated user's profile |
| `GET` | `/api/v1/profiles/me/companies` | JWT | List companies the user belongs to |
| `POST` | `/api/v1/profiles/me/test-account` | JWT | Enable or disable Stripe test mode for account |

---

## Companies

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/companies` | JWT | Create new company (caller becomes owner) |
| `GET` | `/api/v1/companies/me` | JWT | Get current user's company |
| `GET` | `/api/v1/companies/{company_id}` | JWT | Get company details (member access required) |
| `GET` | `/api/v1/companies/{company_id}/members` | JWT | List company members |
| `DELETE` | `/api/v1/companies/{company_id}/members/{member_profile_id}` | JWT | Remove member (owner only) |
| `POST` | `/api/v1/companies/{company_id}/invitations` | JWT | Create invitation (owner only) |
| `GET` | `/api/v1/companies/{company_id}/invitations` | JWT | List invitations (member access) |

---

## Invitations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/invitations` | JWT | List pending invitations for current user |
| `POST` | `/api/v1/invitations/{invitation_id}/accept` | JWT | Accept invitation and join company |
| `POST` | `/api/v1/invitations/{invitation_id}/decline` | JWT | Decline invitation |

---

## Sessions

Anonymous sessions persist discovery state for unauthenticated users. Authenticated users use the [Discovery Profile](#discovery) endpoints instead.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/sessions` | Public | Create anonymous session; sets httpOnly cookie |
| `GET` | `/api/v1/sessions/me` | Session | Get current session — returns 400 if caller has a JWT |
| `PUT` | `/api/v1/sessions/me` | Session | Update session: phase, answers, ROI inputs, product selection |
| `POST` | `/api/v1/sessions/claim` | JWT + Session | Claim anonymous session after signup; transfers conversation + orders |

---

## Discovery

Authenticated counterpart to sessions — persists discovery data per user profile.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/discovery` | JWT | Get discovery profile (auto-created on first access) |
| `PUT` | `/api/v1/discovery` | JWT | Update discovery profile |

---

## Conversations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/conversations` | Dual | Create new conversation |
| `GET` | `/api/v1/conversations` | JWT | List user's conversations (paginated) |
| `POST` | `/api/v1/conversations/reset` | Dual | Soft-reset — start fresh conversation |
| `GET` | `/api/v1/conversations/current` | Dual | Get or create current conversation with message context |
| `GET` | `/api/v1/conversations/{conversation_id}` | Dual | Get conversation details |
| `DELETE` | `/api/v1/conversations/{conversation_id}` | JWT | Delete conversation and all messages |
| `POST` | `/api/v1/conversations/{conversation_id}/messages` | Dual | Send message; returns GPT-4o agent response (rate-limited for sessions) |
| `GET` | `/api/v1/conversations/{conversation_id}/messages` | Dual | List messages (paginated) |
| `POST` | `/api/v1/conversations/{conversation_id}/transition` | Dual | Generate AI phase-transition message (discovery → ROI → greenlight) |

---

## Robots

Public — no authentication required.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/robots` | Public | List robots with filtering, sorting, pagination, and search |
| `GET` | `/api/v1/robots/filters` | Public | Available filter options (categories, methods, price ranges) |
| `GET` | `/api/v1/robots/{robot_id}` | Public | Get single robot details |

See [Robot Catalog](./services.md) for the 13 active SKUs.

---

## Floor Plans

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/floor-plans/analyze` | Dual | Upload floor plan image; GPT-4o Vision extracts sqft and cleanable zones |
| `GET` | `/api/v1/floor-plans` | Dual | List floor plan analyses |
| `GET` | `/api/v1/floor-plans/{analysis_id}` | Dual | Get specific analysis result |
| `DELETE` | `/api/v1/floor-plans/{analysis_id}` | Dual | Delete floor plan analysis |

---

## ROI & Recommendations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/roi/calculate` | Dual | Calculate ROI for a specific robot given discovery answers |
| `POST` | `/api/v1/roi/recommendations` | Dual | Get ranked robot recommendations for provided answers |
| `POST` | `/api/v1/roi/recommendations/session` | Session | Get recommendations using current session's answers |
| `POST` | `/api/v1/roi/recommendations/discovery` | JWT | Get recommendations from discovery profile (result cached per answers hash) |

---

## Greenlight

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/greenlight/validate` | Dual | Validate greenlight selections before checkout |
| `POST` | `/api/v1/greenlight/confirm` | Dual | Confirm greenlight; returns `next_step`: `checkout` \| `contact_sales` \| `schedule_demo` |

---

## Checkout & Orders

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/checkout/session` | Dual | Create Stripe Checkout Session (`mode: subscription` for lease, `payment` for purchase) |
| `POST` | `/api/v1/checkout/gynger-session` | Dual | Create Gynger B2B financing application |
| `GET` | `/api/v1/orders` | Dual | List orders for current user or session |
| `GET` | `/api/v1/orders/{order_id}` | Dual | Get order details — returns 403 if not owner |

---

## Webhooks

Raw body required for HMAC signature verification. No user authentication.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/webhooks/stripe` | Signature | Stripe events: `checkout.session.completed`, `checkout.session.expired`, async payment events |
| `POST` | `/api/v1/webhooks/gynger` | Signature | Gynger financing events: application approved / rejected / pending |

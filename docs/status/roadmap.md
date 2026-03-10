---
title: Roadmap
---

# Roadmap

## Shipped (as of March 2026)

### Core Platform
- ✅ FastAPI backend, Supabase PostgreSQL, GCP Cloud Run
- ✅ React 19 + Vite 6 SPA, Tailwind CSS 3 (PostCSS pipeline)
- ✅ Anonymous sessions (cookie + `X-Session-Token` header dual-path)
- ✅ JWT auth — signup, login, refresh, session claim

### Discovery & Agent
- ✅ Chat-driven discovery (OpenAI GPT-4o agent, multi-phase)
- ✅ Background profile extraction from conversation
- ✅ Floor plan upload + GPT-4o Vision analysis (auto-fills sqft)
- ✅ `ready_for_roi` gate — transitions to ROI phase when ≥4 answers

### Robot Catalog & ROI
- ✅ 13 active SKUs in Supabase (Pudu, Avidbots, Tennant, Gausium, Keenon)
- ✅ Deterministic recommendation scoring + optional LLM summaries
- ✅ ROI calculation v2.1.0 (formula-based, not LLM)
- ✅ Recommendation cache (in-memory, TTL 3600s)

### Checkout & Payments
- ✅ Stripe monthly lease subscription (`mode: "subscription"`)
- ✅ Stripe full purchase (one-time)
- ✅ Gynger B2B financing (`POST /checkout/gynger-session`)
- ✅ Stripe + Gynger webhooks with HMAC signature verification
- ✅ Test account mode (`is_test_account` flag, uses `STRIPE_SECRET_KEY_TEST`)
- ✅ All 13 robots synced to Stripe production

### Testing
- ✅ Playwright E2E suite — 689 tests, 39 files across journeys/nonlinear/payment/procurement/multiuser
- ✅ 16 pre-existing E2E specs (auth, chat, discovery, ROI, greenlight, session, mobile)
- ✅ Vitest unit tests for components and services

---

## In Progress / Planned

### Admin Layer
- 🔲 `src/api/routes/admin.py` — admin-only endpoints
- 🔲 `src/api/routes/shares.py` — public share link endpoints
- 🔲 `src/services/hubspot_service.py` — HubSpot OAuth + meetings API
- 🔲 `src/services/fireflies_service.py` — Fireflies GraphQL meeting extraction
- 🔲 Migration 015: `hubspot_connections` table
- 🔲 Migration 016: `session_shares` table
- 🔲 Frontend: `AdminPanel`, `HubSpotPanel`, `FirefliesPanel`, `SharedROIPage`

### Procurement Paths
- 🔲 Quote request standalone endpoint + confirmation state
- 🔲 Demo booking calendar integration (Calendly or equivalent)
- 🔲 Order confirmation transactional emails (Resend, via `EmailService`)

### Multi-User & Permissions
- 🔲 Owner vs GM role enforcement at checkout
- 🔲 Approval gate for non-owner purchasers
- 🔲 Share link — pre-filled configuration URL for staff review

### Notifications
- 🔲 HubSpot deal creation on checkout
- 🔲 Deal stage change → Slack/email notification triggers
- 🔲 Order confirmation email via Resend

### Infrastructure
- 🔲 Supabase Realtime for concurrent session sync
- 🔲 Multi-worker webhook replay prevention (current: in-memory, per-worker only)

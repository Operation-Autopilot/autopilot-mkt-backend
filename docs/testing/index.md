---
title: Test Strategy Overview
---

# Test Strategy Overview

The Autopilot Marketplace maintains separate testing strategies for the backend and frontend, each using tools best suited to their runtime and architecture.

## Backend: pytest

The backend test suite is built on **pytest** with **pytest-asyncio** for async endpoint and service testing. Tests are organized into two main directories:

- `tests/unit/` -- Fast, isolated tests for services, schemas, and utility functions.
- `tests/integration/` -- Tests that exercise API routes with mocked external dependencies.

Shared fixtures live in `conftest.py` files at each level of the test directory tree.

## Frontend: Vitest + React Testing Library

The frontend uses **Vitest** as the test runner (configured with the `jsdom` environment) and **React Testing Library** for component-level tests. API calls are intercepted using **MSW (Mock Service Worker)**, which provides realistic network-level mocking without patching fetch or axios directly.

## Frontend: Playwright E2E

A full Playwright E2E test suite covers all customer journey archetypes, payment flows, nonlinear sessions, and multi-user scenarios. Tests run against the local dev server (`http://localhost:3000`) with API mocked via `page.route()`.

**Suite structure** (`e2e/` directory):

| Folder | Coverage |
|--------|----------|
| `journeys/` | J-01–J-10: 5 success + 5 failure journey archetypes |
| `nonlinear/` | NL-01–NL-05: session persistence, mid-flow edits, notifications |
| `payment/` | PM-01–PM-03: Stripe card, Gynger financing, RaaS/lease |
| `procurement/` | PM-04–PM-05: quote request, demo booking (fixme — not yet implemented) |
| `multiuser/` | MU-01–MU-03: concurrent sessions, share links (fixme — not yet implemented) |
| `fixtures/` | `sku_data.ts`, `deal_profiles.ts`, `test_users.ts`, `notifications.ts` |
| `helpers/` | `marketplace.ts`, `roi_calculator.ts`, `auth.ts`, `payment.ts`, `email.ts`, `supabase.ts` |

Tests for unimplemented features use `test.fixme(true, 'reason')` so they're tracked without failing CI.

```bash
# Run full E2E suite
npx playwright test

# By folder
npx playwright test e2e/journeys/
npx playwright test e2e/payment/

# By tag
npx playwright test --grep @success
npx playwright test --grep @failure
npx playwright test --grep @payment

# Debug UI
npx playwright test --ui
```

## General Principles

- **Test isolation** -- Each test starts with a clean state. Backend tests use fresh client instances; frontend Playwright tests use `storageState: undefined`; Vitest tests reset MSW handlers after each suite.
- **External services are always mocked** -- Supabase, OpenAI, Pinecone, Stripe, and Gynger are never called in tests.
- **Fast feedback loop** -- Unit tests should run in seconds. Integration tests may take longer but remain under a minute for the full suite.
- **CI parity** -- Tests run the same way locally and in CI. No environment-specific flags or skip markers in normal operation.
- **Fixme over skip** -- Features under development use `test.fixme` with a reason string, not `test.skip`, so they appear in reports.

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

## General Principles

- **Test isolation** -- Each test starts with a clean state. Backend tests use fresh client instances; frontend tests reset MSW handlers after each suite.
- **External services are always mocked** -- Supabase, OpenAI, Pinecone, and Stripe are never called in tests.
- **Fast feedback loop** -- Unit tests should run in seconds. Integration tests may take longer but remain under a minute for the full suite.
- **CI parity** -- Tests run the same way locally and in CI. No environment-specific flags or skip markers in normal operation.

# System Architecture Overview

Autopilot Marketplace is an agent-led procurement platform that guides buyers through robot discovery, evaluation, and purchase using AI-driven conversations. This page describes the high-level system architecture and how the major components interact.

## Architecture Diagram

<SystemArchitecture />

<details>
<summary>Text fallback</summary>

```
Browser (React 19 SPA) → FastAPI (Routers → Services → External Clients)
  → Supabase PostgreSQL, Pinecone Vector DB, OpenAI GPT-4o, Stripe, Gynger
```

</details>

## Component Summary

### Frontend: React SPA

The frontend is a single-page application built with React 19 and TypeScript. It communicates exclusively with the FastAPI backend over HTTPS using REST JSON endpoints. State management combines React Context for session and auth state with TanStack React Query for server state caching and synchronization.

### Backend: FastAPI

The Python backend follows a layered architecture:

- **Routers** handle HTTP request/response concerns, input validation, and route definitions.
- **Services** contain all business logic, orchestrating calls to the database and external APIs.
- **Middleware** provides cross-cutting concerns like authentication verification and error handling.

### Database: Supabase PostgreSQL

Supabase provides a managed PostgreSQL database with Row Level Security (RLS) policies for data isolation. The backend uses the Supabase Python client for all database operations. Tables store user profiles, sessions, conversations, robot catalog data, companies, floor plans, and more.

### AI: OpenAI GPT-4o + Pinecone RAG

The conversational agent uses GPT-4o for natural language understanding and response generation. Pinecone provides vector storage and semantic search over the robot product catalog, enabling Retrieval-Augmented Generation (RAG) so the agent can recommend products based on conversational context.

### Payments: Stripe

Stripe handles checkout sessions, payment processing, and webhook notifications for order fulfillment. The backend creates Stripe checkout sessions and processes webhook events to update order status.

## Key Design Principles

1. **Separation of concerns**: HTTP handling, business logic, and data access are cleanly separated across layers.
2. **Service orchestration**: The service layer coordinates multiple external services (OpenAI, Pinecone, Supabase, Stripe) without leaking HTTP concerns.
3. **Stateless API**: The backend is stateless; all session state lives in the database. This enables horizontal scaling.
4. **Client-side caching**: React Query manages server state caching, reducing redundant API calls and keeping the UI responsive.
5. **Security by default**: Supabase RLS policies enforce data isolation at the database level, and JWT-based auth protects all API routes.

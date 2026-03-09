---
title: Backend Overview
---

# Backend Overview

The Autopilot Marketplace backend is a **Python 3.11+ FastAPI** REST API that powers the marketplace platform. It follows a layered architecture designed for clarity, testability, and maintainability.

## Architecture

```
API Routes → Services → Models/Schemas → Core Clients
```

| Layer | Responsibility | Location |
|-------|---------------|----------|
| **API Routes** | HTTP endpoints, request validation, response formatting | `src/api/routes/` |
| **Services** | Business logic, orchestration, external API calls | `src/services/` |
| **Schemas** | Pydantic models for request/response validation | `src/schemas/` |
| **Core Clients** | Database, OpenAI, Pinecone, Stripe client singletons | `src/core/` |

## Entry Point

The application entry point is `src/main.py`, which bootstraps the FastAPI app:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Autopilot Marketplace API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration
app.include_router(health_router)
app.include_router(auth_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
# ... additional routers
```

## Configuration

All configuration is managed via **environment variables**, loaded through Pydantic settings or direct `os.getenv()` calls. Key variable groups:

| Group | Variables |
|-------|-----------|
| **Supabase** | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| **OpenAI** | `OPENAI_API_KEY` |
| **Pinecone** | `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` |
| **Stripe** | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY_TEST`, `STRIPE_WEBHOOK_SECRET_TEST` |
| **App** | `FRONTEND_URL`, `ENVIRONMENT` |

## Middleware

The backend uses two primary middleware layers:

- **CORS Middleware** — Allows cross-origin requests from the frontend application.
- **Error Handling Middleware** — Catches unhandled exceptions and returns structured JSON error responses.

## Running Locally

Start the development server with hot-reload:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Deployment

The backend is containerized with **Docker** and deployed on **GCP Cloud Run**. The Dockerfile builds a production image with uvicorn as the ASGI server.

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Tech Stack Summary

| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Web framework |
| **Supabase PostgreSQL** | Database with Row Level Security |
| **OpenAI GPT-4o** | AI agent orchestration |
| **Pinecone** | Vector database for RAG |
| **Stripe** | Payment processing |
| **GCP Cloud Run** | Container hosting |
| **Docker** | Containerization |

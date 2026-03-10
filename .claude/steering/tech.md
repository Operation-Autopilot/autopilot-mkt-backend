# Technology Stack

## Project Type
REST API backend service for an agent-led procurement platform. Provides authentication, user/company management, conversation handling, and AI-powered product recommendations.

## Core Technologies

### Primary Language
- **Language**: Python 3.11+
- **Runtime**: CPython
- **Package Manager**: pip with pyproject.toml (PEP 517/518)

### Key Dependencies/Libraries
- **FastAPI**: Web framework for REST API (v0.109+)
- **Pydantic v2**: Data validation and serialization
- **Supabase Python**: Database and auth client (v2.0+)
- **OpenAI SDK**: LLM integration for agent conversations (v1.0+)
- **Pinecone Client**: Vector database for RAG (v3.0+)
- **Stripe**: Payment processing — lease subscriptions, one-time purchases (v7.0+)
- **python-jose**: JWT token handling
- **httpx**: Async HTTP client for Gynger B2B financing API
- **uvicorn**: ASGI server

### Application Architecture
Layered architecture with clear separation of concerns:
- **API Layer**: FastAPI routers handle HTTP requests/responses
- **Service Layer**: Business logic and orchestration
- **Model Layer**: Database table representations
- **Schema Layer**: Pydantic models for request/response contracts
- **Core Layer**: Client singletons and configuration

### Data Storage
- **Primary Database**: Supabase PostgreSQL with Row-Level Security (RLS)
- **Vector Store**: Pinecone for product embeddings and semantic search
- **Caching**: None for MVP (add Redis if needed later)
- **Data Formats**: JSON for API, JSONB for flexible metadata in Postgres

### External Integrations
- **Supabase Auth**: JWT-based authentication and user management
- **OpenAI API**: GPT-4o for agent conversations + vision analysis
- **Pinecone API**: Vector similarity search for product recommendations
- **Stripe API**: Checkout sessions, subscription management, webhooks
- **Gynger API**: B2B financing application flow + HMAC webhooks
- **Protocols**: HTTPS/REST for all external APIs

## Development Environment

### Build & Development Tools
- **Build System**: pyproject.toml with setuptools
- **Package Management**: pip + requirements.txt (pinned versions)
- **Development Workflow**: uvicorn with --reload for hot reloading
- **Environment Management**: python-dotenv for local .env files

### Code Quality Tools
- **Linting**: ruff (fast Python linter)
- **Formatting**: ruff format (or black)
- **Type Checking**: mypy with strict mode
- **Testing Framework**: pytest + pytest-asyncio
- **API Documentation**: Auto-generated OpenAPI/Swagger via FastAPI

### Version Control & Collaboration
- **VCS**: Git
- **Branching Strategy**: Feature branches → main
- **Code Review Process**: PR reviews before merge

## Deployment & Distribution

### Target Platform
- **Runtime**: Docker container on GCP Cloud Run
- **Database**: Supabase managed PostgreSQL
- **Vector DB**: Pinecone managed service

### Distribution Method
- **Container Registry**: Google Container Registry (GCR) or Artifact Registry
- **Deployment**: Cloud Run with automatic scaling
- **Configuration**: Environment variables via Cloud Run secrets

### Installation Requirements
- Docker 20.10+
- Python 3.11+ (for local development)
- Supabase project with auth enabled
- OpenAI API key
- Pinecone project and API key

## Technical Requirements & Constraints

### Performance Requirements
- API response time: <500ms for non-LLM endpoints
- LLM response time: <10s for agent responses (streaming not required for MVP)
- Concurrent users: Support 10-50 concurrent users for MVP

### Compatibility Requirements
- **Platform Support**: Linux containers (Cloud Run)
- **Python Version**: 3.11+ required
- **API Versioning**: `/api/v1/` prefix for all endpoints

### Security & Compliance
- **Authentication**: Supabase JWT tokens required for protected endpoints
- **Authorization**: Row-Level Security in Supabase for data isolation
- **Secrets**: Environment variables, never committed to repo
- **HTTPS**: Enforced by Cloud Run

### Scalability & Reliability
- **Expected Load**: 10-50 concurrent users for MVP demo
- **Availability**: Best-effort (no SLA for MVP)
- **Scaling**: Cloud Run auto-scaling 0-10 instances

## Technical Decisions & Rationale

### Decision Log
1. **FastAPI over Flask/Django**: Async support, automatic OpenAPI docs, Pydantic integration, modern Python patterns
2. **Supabase over raw Postgres**: Built-in auth, RLS, hosted solution reduces ops burden for MVP
3. **Pydantic v2**: Significant performance improvements, better validation, required by modern FastAPI
4. **Pinecone over pgvector**: Managed service, proven at scale, simpler setup for MVP
5. **REST over WebSocket**: Simpler implementation for MVP; can add SSE/WebSocket for streaming later
6. **Single service over microservices**: MVP scope doesn't justify distributed complexity

## Known Limitations

- **No real-time streaming**: Agent responses are not streamed (can add SSE later)
- **In-memory recommendation cache only**: Per-worker TTL cache (3600s); no shared Redis cache across Cloud Run instances
- **Rate limiting**: In-memory per-worker only — no cross-instance coordination
- **No background jobs**: All processing is synchronous in request lifecycle
- **Single region**: Deployed to single GCP region

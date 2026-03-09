---
title: Quick Start
---

# Quick Start

Get the Autopilot Marketplace running locally in a few minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for containerized deployment)
- Access to required API keys (see below)

## Clone the Repositories

```bash
git clone <backend-repo-url> autopilot-mkt-backend
git clone <frontend-repo-url> autopilot-mkt-frontend
```

## Backend Setup

### 1. Create a virtual environment

```bash
cd autopilot-mkt-backend
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the backend root with the following keys:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_SECRET_KEY=your_supabase_service_role_key
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
STRIPE_SECRET_KEY=your_stripe_secret_key
```

### 4. Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Verify the health endpoint

```bash
curl http://localhost:8000/health
```

You should receive a `200 OK` response confirming the service is running.

## Frontend Setup

### 1. Install dependencies

```bash
cd autopilot-mkt-frontend
npm install
```

### 2. Start the development server

```bash
npm run dev
```

The frontend will start on `http://localhost:5173` by default (Vite).

## Tech Stack Reference

| Layer    | Technology                          |
| -------- | ----------------------------------- |
| Backend  | Python 3.11+, FastAPI              |
| Database | Supabase PostgreSQL with RLS        |
| AI       | OpenAI GPT-4o                       |
| Search   | Pinecone vector DB                  |
| Payments | Stripe                              |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Deploy   | GCP Cloud Run via Docker            |

---
title: Roadmap
---

# Roadmap

## MVP Milestones (Completed)

All MVP milestones have been delivered. Each phase built on the previous one to form the core marketplace platform.

### Core Infrastructure
- FastAPI application scaffold with async support
- Supabase project setup (database, auth, storage)
- GCP Cloud Run deployment pipeline
- Vite SPA frontend with React and TypeScript

### Authentication
- Supabase Auth integration (email/password, OAuth)
- JWT validation middleware
- Role-based access control (buyer, vendor, admin)
- Protected route guards on frontend

### Conversations and Agent
- Real-time conversation API endpoints
- AI agent powered by OpenAI chat completions
- Message history persistence in Supabase
- Streaming response support

### Profiles and Companies
- User profile CRUD operations
- Company entity management
- Vendor onboarding flow
- Buyer organization setup

### Sessions and Discovery
- Browsing session tracking
- Vendor and product discovery search
- Filtering and sorting capabilities
- Session-based recommendations

### RAG Integration
- Document ingestion pipeline
- Pinecone vector store for embeddings
- OpenAI embedding generation
- Context-aware retrieval for agent responses

### Checkout and Stripe
- Stripe Connect for vendor payouts
- Checkout session creation
- Payment intent handling
- Order confirmation and receipt generation

### Frontend Phases
- Component library and design system
- Conversation UI with streaming messages
- Discovery and search pages
- Profile management views
- Checkout flow

---

## Future Vision

The following areas represent the next wave of development beyond the MVP.

### Self-Serve Journey
- Guided vendor onboarding wizard
- Automated document upload and processing
- Self-service billing and subscription management
- Buyer-side saved searches and alerts

### Multi-Tenant Architecture
- Workspace isolation per organization
- Tenant-scoped data access policies
- Custom branding per tenant
- Admin console for tenant management

### Advanced Analytics
- Vendor performance dashboards
- Buyer engagement metrics
- Conversion funnel tracking
- Agent effectiveness scoring (response quality, resolution rate)

### Mobile Optimization
- Responsive layout refinements
- Touch-optimized conversation interface
- Progressive Web App (PWA) support
- Push notifications for conversation updates

### Integration APIs
- CRM integrations (Salesforce, HubSpot)
- Procurement system connectors (Coupa, SAP Ariba)
- Webhook support for external event consumers
- Public REST API with OAuth2 client credentials flow

# Data Flow

This page describes how data flows through the Autopilot Marketplace system, from session creation through checkout. Understanding these flows is essential for debugging and extending the platform.

## Session Lifecycle

A session represents one buyer's journey through the procurement process. Sessions move through three phases in strict order:

```
┌─────────────┐      ┌─────────┐      ┌──────────────┐
│  Discovery   │─────▶│   ROI   │─────▶│  Greenlight   │
│              │      │         │      │               │
│  Needs       │      │  Cost   │      │  Purchase     │
│  assessment  │      │  analysis│     │  decision     │
└─────────────┘      └─────────┘      └──────────────┘
```

### Phase 1: Discovery

The buyer converses with the AI agent to identify their needs.

```
1. Anonymous session created (no auth required)
2. User sends messages describing their use case
3. Agent asks clarifying questions about:
   - Industry and application
   - Facility size and layout
   - Budget constraints
   - Payload and performance requirements
4. ProfileExtractionService extracts structured data after each turn
5. RagService searches for matching products
6. Agent recommends robots based on extracted profile
7. User selects a robot → triggers phase transition to ROI
```

### Phase 2: ROI

The system calculates return on investment for the selected robot.

```
1. ROI calculation runs using extracted profile data:
   - Labor cost savings
   - Throughput improvements
   - Implementation costs
   - Payback period
2. User reviews ROI report
3. User can adjust assumptions and recalculate
4. User approves ROI → triggers phase transition to Greenlight
```

### Phase 3: Greenlight

The buyer proceeds to purchase.

```
1. Greenlight state assembled:
   - Selected robot details
   - ROI summary
   - Pricing breakdown
2. User initiates checkout
3. Stripe checkout session created
4. User completes payment on Stripe
5. Webhook confirms payment → order recorded
```

## Conversation Flow (Detailed)

The conversation flow is the core interaction loop. Here is the detailed data flow for a single message exchange:

```
┌──────────┐
│  User    │
│  types   │
│  message │
└────┬─────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│  Frontend: useConversation.sendMessage(message)          │
│  POST /conversations/{session_id}/messages               │
└────┬─────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│  Router: conversations.py                                │
│  Validates input, injects auth + supabase                │
└────┬─────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│  ConversationService.create(session_id, message)         │
│                                                          │
│  Step 1: Store user message in conversations table       │
│                                                          │
│  Step 2: Reconstruct context                             │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Load conversation history (last N messages)       │  │
│  │  Load extracted profile (discovery_profiles table) │  │
│  │  Load session metadata (current phase, robot)      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Step 3: RAG product search                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  RagService.search(query=message, context=profile) │  │
│  │  → Embed query with OpenAI                         │  │
│  │  → Search Pinecone index (top 5 matches)           │  │
│  │  → Return product metadata                         │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Step 4: GPT-4o agent generation                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │  AgentService.generate(context, products)          │  │
│  │  → Build system prompt with:                       │  │
│  │      - Agent persona and instructions              │  │
│  │      - Extracted buyer profile                     │  │
│  │      - RAG product results                         │  │
│  │      - Current session phase                       │  │
│  │  → Send to GPT-4o                                  │  │
│  │  → Parse response                                  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Step 5: Profile extraction                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  ProfileExtractionService.extract(session_id, msgs)│  │
│  │  → Send conversation to GPT-4o with extraction     │  │
│  │    schema                                          │  │
│  │  → Parse structured JSON output                    │  │
│  │  → Upsert into discovery_profiles table            │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Step 6: Store assistant message                         │
│  Step 7: Return response to router                       │
└────┬─────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│  Frontend: React Query cache invalidated                 │
│  Conversation history re-fetched and rendered            │
└──────────────────────────────────────────────────────────┘
```

## Checkout Flow

```
┌────────────┐     ┌──────────────┐     ┌─────────┐     ┌──────────┐
│  Frontend   │────▶│  CheckoutSvc │────▶│  Stripe │────▶│  Webhook │
│  initiate   │     │  create      │     │  hosted │     │  confirm │
│  checkout   │     │  session     │     │  page   │     │  payment │
└────────────┘     └──────────────┘     └─────────┘     └──────┬───┘
                                                               │
                                                               ▼
                                                        ┌──────────┐
                                                        │  Update  │
                                                        │  order   │
                                                        │  status  │
                                                        └──────────┘
```

1. Frontend calls `POST /checkout/create-session` with robot and session IDs.
2. `CheckoutService` creates a Stripe Checkout Session with line items, success/cancel URLs.
3. Frontend redirects to the Stripe-hosted checkout page.
4. After payment, Stripe sends a webhook to `POST /webhooks/stripe`.
5. Webhook handler verifies the signature and updates the order status in the database.

## Database Tables Involved

| Table | Written During | Read During |
|---|---|---|
| `sessions` | Session creation, phase transitions | Every API call (session lookup) |
| `conversations` | Each message (user + assistant) | Context reconstruction |
| `discovery_profiles` | After profile extraction | Context reconstruction, ROI calc |
| `robot_catalog` | Admin seeding | RAG search result enrichment |
| `checkout_sessions` | Checkout creation | Webhook processing |
| `companies` | Company registration | Profile display |
| `floor_plans` | Floor plan upload | Discovery context |

## Key Design Decisions

**Context reconstruction per turn**: The full conversation context is rebuilt on every message rather than maintained in memory. This enables stateless scaling -- any backend instance can handle any request.

**Extraction after every turn**: Profile extraction runs after each conversation turn, not just at the end of discovery. This ensures the profile is always up-to-date and enables the agent to reference extracted data in subsequent turns.

**Strict phase ordering**: Sessions can only move forward through phases (Discovery -> ROI -> Greenlight). There is no backward transition. If a user needs to change requirements, they continue the conversation within the current phase.

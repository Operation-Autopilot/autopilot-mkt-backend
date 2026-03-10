# Data Flow

This page describes how data flows through the Autopilot Marketplace system, from session creation through checkout. Understanding these flows is essential for debugging and extending the platform.

## Session Lifecycle

A session represents one buyer's journey through the procurement process. Sessions move through three phases in strict order:

<SessionLifecycle />

<details>
<summary>Text fallback</summary>

```
Discovery (Needs assessment) → ROI (Cost analysis) → Greenlight (Purchase decision)
```

</details>

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

<ConversationFlow />

<details>
<summary>Text fallback</summary>

```
User message → Frontend POST → Router → ConversationService
  → Store msg → Context → RAG search + GPT-4o agent → Profile extraction
  → Store response → React Query invalidated → UI render
```

</details>

## Checkout Flow

<CheckoutFlow />

<details>
<summary>Text fallback</summary>

```
Frontend → CheckoutService → Stripe hosted page → Webhook → Update order status
```

</details>

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

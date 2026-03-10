---
title: Services
---

# Services

Services contain the core business logic of the backend. They are located in `src/services/` and are called by route handlers.

## Service Inventory

<ServiceInventoryTable />

## Key Services

### agent_service.py

The agent service orchestrates AI-powered conversations using **OpenAI GPT-4o**. It is the central intelligence layer of the platform.

**Responsibilities:**

- Manages the GPT-4o chat completion lifecycle
- Reconstructs conversation context from message history
- Injects RAG-retrieved product data into system prompts
- Handles structured output parsing for profile extraction triggers

```python
class AgentService:
    def __init__(self, openai_client, rag_service):
        self.openai = openai_client
        self.rag_service = rag_service

    async def generate_response(
        self,
        conversation_id: str,
        user_message: str,
        message_history: list[dict],
    ) -> AgentResponse:
        # 1. Reconstruct context from message history
        context = self._build_context(message_history)

        # 2. Query Pinecone for relevant product info
        product_context = await self.rag_service.search(user_message)

        # 3. Build system prompt with injected context
        system_prompt = self._build_system_prompt(
            context=context,
            product_context=product_context,
        )

        # 4. Call GPT-4o
        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                *message_history,
                {"role": "user", "content": user_message},
            ],
        )

        return self._parse_response(response)
```

**Context Reconstruction:** The agent rebuilds conversational context from stored messages, ensuring coherent multi-turn conversations even across sessions.

**RAG Injection:** Before each GPT-4o call, the service queries Pinecone for semantically relevant product information and injects the top results into the system prompt. See [RAG Integration](./rag.md) for details.

---

### conversation_service.py

Handles all conversation and message CRUD operations.

**Responsibilities:**

- Create, read, update, delete conversations
- Append messages (user and assistant) to conversations
- Retrieve message history with pagination
- Link conversations to sessions and profiles

```python
class ConversationService:
    async def create_conversation(
        self, profile_id: str, title: str | None = None
    ) -> Conversation:
        """Create a new conversation for a user."""
        ...

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> Message:
        """Append a message to a conversation."""
        ...

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Retrieve paginated message history."""
        ...
```

---

### profile_extraction_service.py

Uses AI to extract structured discovery profile data from free-form conversation text.

**Responsibilities:**

- Analyzes conversation history to identify user requirements
- Uses GPT-4o **structured output** to produce typed profile data
- Extracts fields like industry, facility size, budget range, use cases, and constraints

```python
class ProfileExtractionService:
    async def extract_profile(
        self, conversation_id: str
    ) -> DiscoveryProfile:
        """
        Extract a discovery profile from conversation history
        using GPT-4o structured output.
        """
        messages = await self.conversation_service.get_messages(
            conversation_id
        )

        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                *self._format_messages(messages),
            ],
            response_format=DiscoveryProfileSchema,
        )

        return self._parse_extraction(response)
```

The extraction prompt guides GPT-4o to identify and structure:

- **Industry vertical** (e.g., manufacturing, warehousing, healthcare)
- **Facility characteristics** (size, layout, floor type)
- **Operational requirements** (payload, speed, autonomy level)
- **Budget constraints** (purchase vs. lease, price range)
- **Use cases** (material transport, inspection, cleaning)

---

### checkout_service.py

Manages Stripe checkout session creation with support for both test and production modes.

**Responsibilities:**

- Creates Stripe checkout sessions for robot purchases
- Selects test or production Stripe keys based on account flags
- Handles success/cancel URL configuration
- Records order metadata for webhook processing

```python
class CheckoutService:
    async def create_checkout_session(
        self,
        profile_id: str,
        robot_id: str,
        quantity: int = 1,
    ) -> CheckoutSession:
        """Create a Stripe checkout session."""
        profile = await self.profile_service.get(profile_id)
        robot = await self.robot_service.get(robot_id)

        # Select test or production Stripe config
        stripe_key = self._get_stripe_key(profile)
        price_id = self._get_price_id(robot, profile)

        session = stripe.checkout.Session.create(
            api_key=stripe_key,
            line_items=[{
                "price": price_id,
                "quantity": quantity,
            }],
            mode="payment",
            success_url=f"{FRONTEND_URL}/checkout/success",
            cancel_url=f"{FRONTEND_URL}/checkout/cancel",
            metadata={
                "profile_id": profile_id,
                "robot_id": robot_id,
            },
        )

        return CheckoutSession(
            id=session.id,
            url=session.url,
        )
```

See [Stripe Integration](./stripe.md) for details on test/production mode selection.

## Service Patterns

All services follow consistent patterns:

1. **Dependency Injection** — Services receive their dependencies (clients, other services) via constructor injection.
2. **Async by Default** — All service methods are `async` for non-blocking I/O.
3. **Error Propagation** — Services raise domain-specific exceptions that routes translate to HTTP responses.
4. **Single Responsibility** — Each service owns one domain area of business logic.

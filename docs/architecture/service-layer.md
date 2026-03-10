# Service Layer

The service layer contains all business logic for the application. Services live in `src/services/` and are responsible for orchestrating database operations, external API calls, and cross-cutting business rules. Services never handle HTTP concerns -- they receive typed inputs and return data objects.

## Service Pattern

Every service follows a consistent structure:

```python
# src/services/conversation_service.py

class ConversationService:
    def __init__(self, supabase):
        """Initialize with a Supabase client instance."""
        self.supabase = supabase

    async def create(self, session_id: str, user_message: str) -> dict:
        """Create a new conversation turn.

        1. Store the user message
        2. Reconstruct conversation context
        3. Query RAG for relevant products
        4. Send to GPT-4o agent
        5. Extract profile updates
        6. Store and return the agent response
        """
        await self._store_message(session_id, "user", user_message)
        context = await self._build_context(session_id)
        products = await self.rag_service.search(user_message, context)
        response = await self.agent_service.generate(context, products)
        await self._extract_profile(session_id, response)
        await self._store_message(session_id, "assistant", response.content)
        return {"message": response.content, "products": products}

    async def get_history(self, session_id: str) -> list[dict]:
        """Retrieve the full conversation history for a session."""
        result = self.supabase.table("conversations") \
            .select("*") \
            .eq("session_id", session_id) \
            .order("created_at") \
            .execute()
        return result.data
```

Key conventions:

- **Constructor receives the Supabase client** -- injected from the router via `Depends`.
- **Methods are async** -- enabling non-blocking calls to external services.
- **Services compose other services** -- e.g., `ConversationService` uses `RagService` and `AgentService`.
- **No HTTP status codes or response objects** -- services raise domain exceptions that routers translate to HTTP responses.

## Service Inventory

| Service | File | Responsibility |
|---|---|---|
| `AuthService` | `auth_service.py` | User registration, login, token management |
| `ProfileService` | `profile_service.py` | User profile CRUD and updates |
| `CompanyService` | `company_service.py` | Company creation, member management |
| `ConversationService` | `conversation_service.py` | Chat message handling, context assembly |
| `AgentService` | `agent_service.py` | OpenAI GPT-4o integration, prompt construction |
| `RagService` | `rag_service.py` | Pinecone vector search, context retrieval |
| `ProfileExtractionService` | `profile_extraction_service.py` | Structured data extraction from conversations |
| `DiscoveryProfileService` | `discovery_profile_service.py` | Buyer needs assessment and profile building |
| `SessionService` | `session_service.py` | Session lifecycle and phase transitions |
| `CheckoutService` | `checkout_service.py` | Stripe checkout session creation, order processing |
| `RobotCatalogService` | `robot_catalog_service.py` | Robot product listing, filtering, details |
| `RecommendationService` | `recommendation_service.py` | Product recommendations based on profile |
| `FloorPlanService` | `floor_plan_service.py` | Floor plan upload, storage, analysis |
| `EmailService` | `email_service.py` | Transactional email sending |
| `InvitationService` | `invitation_service.py` | Team invite creation and acceptance |

## Service Composition

Services frequently compose each other to implement complex workflows. For example, processing a conversation message involves multiple services:

<ServiceComposition />

<details>
<summary>Text fallback</summary>

```
ConversationService
    ├── RagService              (search product catalog)
    ├── AgentService            (generate AI response)
    ├── ProfileExtractionService (extract structured data)
    └── SessionService          (update session phase)
```

</details>

Services receive collaborators through initialization or construct them internally:

```python
class ConversationService:
    def __init__(self, supabase):
        self.supabase = supabase
        self.rag_service = RagService()
        self.agent_service = AgentService()
        self.profile_extraction = ProfileExtractionService(supabase)
        self.session_service = SessionService(supabase)
```

## Key Services in Detail

### AgentService

Handles all OpenAI GPT-4o interactions. Constructs system prompts, manages conversation history windows, and parses structured responses.

```python
class AgentService:
    def __init__(self):
        self.client = OpenAI()
        self.model = "gpt-4o"

    async def generate(self, context: ConversationContext, products: list) -> AgentResponse:
        messages = self._build_messages(context, products)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
        )
        return self._parse_response(response)
```

### RagService

Queries Pinecone for semantically relevant products based on the conversation context. Embeds the query, searches the vector index, and returns matching product metadata.

```python
class RagService:
    def __init__(self):
        self.index = pinecone.Index("robot-catalog")
        self.embedder = OpenAI()

    async def search(self, query: str, context: dict) -> list[dict]:
        embedding = self._embed(query)
        results = self.index.query(vector=embedding, top_k=5, include_metadata=True)
        return [match.metadata for match in results.matches]
```

### ProfileExtractionService

Analyzes conversation turns to extract structured buyer profile data (industry, budget, use case, facility size, etc.). Uses GPT-4o with a structured output schema.

```python
class ProfileExtractionService:
    def __init__(self, supabase):
        self.supabase = supabase
        self.client = OpenAI()

    async def extract(self, session_id: str, conversation: list[dict]) -> dict:
        """Extract structured profile fields from conversation history."""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                *conversation,
            ],
            response_format={"type": "json_object"},
        )
        profile = json.loads(response.choices[0].message.content)
        await self._update_profile(session_id, profile)
        return profile
```

### SessionService

Manages the session lifecycle including phase transitions (Discovery, ROI, Greenlight). Validates that transitions follow the allowed sequence.

```python
class SessionService:
    PHASE_ORDER = ["discovery", "roi", "greenlight"]

    async def transition_phase(self, session_id: str, target_phase: str):
        session = await self.get(session_id)
        current_idx = self.PHASE_ORDER.index(session["phase"])
        target_idx = self.PHASE_ORDER.index(target_phase)
        if target_idx != current_idx + 1:
            raise InvalidPhaseTransition(session["phase"], target_phase)
        await self._update_phase(session_id, target_phase)
```

## Error Handling

Services raise domain-specific exceptions rather than HTTP exceptions:

```python
class NotFoundException(Exception):
    """Raised when a requested resource does not exist."""
    pass

class InvalidPhaseTransition(Exception):
    """Raised when a session phase transition is not allowed."""
    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from {current} to {target}")
```

Routers catch these exceptions and map them to appropriate HTTP status codes. This keeps the service layer decoupled from the transport layer.

## Adding a New Service

1. Create a new file in `src/services/` (e.g., `widget_service.py`).
2. Define a class that accepts `supabase` in `__init__`.
3. Implement async methods for each operation.
4. Raise domain exceptions for error cases.
5. Use the service from a router via dependency injection.

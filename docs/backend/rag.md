---
title: RAG Integration
---

# RAG Integration

The backend uses **Retrieval-Augmented Generation (RAG)** to inject relevant product knowledge into AI agent conversations. This combines **Pinecone** vector search with **OpenAI GPT-4o** to provide accurate, grounded robot recommendations.

## Architecture

```
User Message
    │
    ▼
Context Reconstruction (message history)
    │
    ▼
OpenAI Embeddings API ──► Text → Vector
    │
    ▼
Pinecone Similarity Search ──► Top-K product matches
    │
    ▼
Inject product context into GPT-4o system prompt
    │
    ▼
GPT-4o generates grounded response
```

## RAG Service

The RAG logic lives in `src/services/rag_service.py`:

```python
from openai import AsyncOpenAI
from pinecone import Pinecone


class RAGService:
    def __init__(self, openai_client: AsyncOpenAI, pinecone_index):
        self.openai = openai_client
        self.index = pinecone_index

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[ProductContext]:
        """
        Search for products semantically similar to the query.

        1. Convert query text to embedding vector
        2. Search Pinecone for nearest neighbors
        3. Return structured product context
        """
        # Generate embedding for the query
        embedding_response = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        query_vector = embedding_response.data[0].embedding

        # Search Pinecone
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=filter,
        )

        # Convert to structured context
        return [
            ProductContext(
                name=match.metadata["name"],
                manufacturer=match.metadata["manufacturer"],
                category=match.metadata["category"],
                description=match.metadata["description"],
                specs=match.metadata.get("specs", {}),
                price_usd=match.metadata.get("price_usd"),
                score=match.score,
            )
            for match in results.matches
        ]
```

## Product Indexing

Products are indexed into Pinecone using the `scripts/index_products.py` script. This is a **one-time operation** (re-run when the catalog changes).

```bash
python scripts/index_products.py
```

The script:

1. Fetches all robots from the database
2. Builds a text representation of each product (name, description, specs, category)
3. Generates embedding vectors via OpenAI's `text-embedding-3-small` model
4. Upserts vectors into the Pinecone index with product metadata

```python
async def index_all_products():
    db = get_supabase_client()
    robots = db.table("robots").select("*").execute().data

    vectors = []
    for robot in robots:
        # Build text for embedding
        text = build_product_text(robot)

        # Generate embedding
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )

        vectors.append({
            "id": str(robot["id"]),
            "values": response.data[0].embedding,
            "metadata": {
                "name": robot["name"],
                "manufacturer": robot["manufacturer"],
                "category": robot["category"],
                "description": robot["description"],
                "specs": robot.get("specs", {}),
                "price_usd": robot.get("price_usd"),
            },
        })

    # Batch upsert to Pinecone
    index.upsert(vectors=vectors, batch_size=100)
```

### Product Text Construction

The text representation combines multiple fields to create a rich embedding:

```python
def build_product_text(robot: dict) -> str:
    """Build a text string for embedding from robot data."""
    parts = [
        f"Name: {robot['name']}",
        f"Manufacturer: {robot['manufacturer']}",
        f"Category: {robot['category']}",
    ]
    if robot.get("description"):
        parts.append(f"Description: {robot['description']}")
    if robot.get("specs"):
        specs = robot["specs"]
        for key, value in specs.items():
            parts.append(f"{key}: {value}")
    return "\n".join(parts)
```

## Context Injection

The agent service injects RAG results into the GPT-4o system prompt:

```python
def _build_system_prompt(
    self,
    context: str,
    product_context: list[ProductContext],
) -> str:
    product_section = "\n\n".join(
        f"**{p.name}** by {p.manufacturer}\n"
        f"Category: {p.category}\n"
        f"Description: {p.description}\n"
        f"Price: ${p.price_usd:,.2f}\n"
        f"Relevance Score: {p.score:.2f}"
        for p in product_context
    )

    return f"""You are the Autopilot procurement assistant.

Use the following product information to make recommendations.
Only recommend products listed below. If no products match, say so.

## Available Products
{product_section}

## Conversation Context
{context}
"""
```

## End-to-End Flow

Here is the complete flow when a user sends a message:

1. **User sends message** via `POST /api/conversations/{id}/messages`
2. **Route handler** calls `agent_service.generate_response()`
3. **Context reconstruction** — Agent rebuilds conversation state from message history
4. **RAG search** — User message is embedded and searched against Pinecone
5. **Prompt assembly** — Top-K product matches are injected into the system prompt
6. **GPT-4o call** — Full message history + system prompt sent to OpenAI
7. **Response parsing** — Agent extracts text response and any structured actions
8. **Message storage** — Both user message and assistant response are persisted
9. **Response returned** to the frontend

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings and chat completions |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Name of the Pinecone index (e.g., `autopilot-products`) |

## Performance Considerations

- **Embedding model**: `text-embedding-3-small` is used for cost efficiency. Upgrade to `text-embedding-3-large` if retrieval quality needs improvement.
- **Top-K**: Default is 5 results. Increasing this provides more context but increases prompt token usage.
- **Metadata filtering**: Pinecone supports metadata filters (e.g., `{"category": "AMR"}`) to narrow results before similarity scoring.
- **Caching**: Frequent identical queries could benefit from an embedding cache to reduce OpenAI API calls.

---
title: Common Test Patterns
---

# Common Test Patterns

This page documents recurring patterns used across the backend and frontend test suites.

## Mocking External Services

### Supabase Client

The Supabase client is replaced with a mock that returns controlled data. The mock must replicate the builder pattern used by the real client:

```python
from unittest.mock import MagicMock, AsyncMock

def make_mock_supabase():
    client = MagicMock()
    # Chain: client.table("x").select("*").eq("id", val).execute()
    query = MagicMock()
    query.execute.return_value = MagicMock(data=[{"id": "abc", "name": "Test"}])
    client.table.return_value.select.return_value.eq.return_value = query
    client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "new-1"}]
    )
    return client
```

### OpenAI Responses

Mock embedding and chat completion responses separately:

```python
mock_embedding_response = MagicMock(
    data=[MagicMock(embedding=[0.01] * 1536)]
)

mock_chat_response = MagicMock(
    choices=[MagicMock(message=MagicMock(content="Hello, I can help with that."))]
)
```

### Pinecone Queries

```python
mock_pinecone = MagicMock()
mock_pinecone.query.return_value = MagicMock(
    matches=[
        MagicMock(id="doc-1", score=0.95, metadata={"text": "Relevant chunk"}),
        MagicMock(id="doc-2", score=0.87, metadata={"text": "Another chunk"}),
    ]
)
```

## Factory Functions for Test Data

Avoid duplicating test data across files. Define factory functions that produce valid objects with sensible defaults and optional overrides:

```python
def make_user(**overrides):
    defaults = {
        "id": "user-001",
        "email": "test@example.com",
        "role": "buyer",
        "company_id": "comp-001",
    }
    return {**defaults, **overrides}


def make_conversation(**overrides):
    defaults = {
        "id": "conv-001",
        "title": "Test Conversation",
        "user_id": "user-001",
        "created_at": "2025-01-15T10:00:00Z",
    }
    return {**defaults, **overrides}
```

The same pattern applies in the frontend:

```ts
export function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: "conv-001",
    title: "Test Conversation",
    userId: "user-001",
    createdAt: "2025-01-15T10:00:00Z",
    ...overrides,
  };
}
```

## Test Isolation for Authentication

Auth state can leak between tests if the same client instance is reused. Always create a fresh client per test or per test class:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def authed_client():
    """Yields an async client with a valid auth header."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers["Authorization"] = "Bearer test-token-valid"
        yield client

@pytest.mark.asyncio
async def test_get_profile(authed_client):
    response = await authed_client.get("/api/profile")
    assert response.status_code == 200
```

## Async Test Patterns with pytest-asyncio

### Awaiting Multiple Calls

When a test needs to exercise several endpoints in sequence, keep everything within a single async function:

```python
@pytest.mark.asyncio
async def test_conversation_lifecycle(authed_client, mock_supabase):
    # Create
    create_resp = await authed_client.post("/api/conversations", json={
        "title": "Lifecycle test"
    })
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    # Read
    get_resp = await authed_client.get(f"/api/conversations/{conv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Lifecycle test"

    # Delete
    del_resp = await authed_client.delete(f"/api/conversations/{conv_id}")
    assert del_resp.status_code == 204
```

### Asserting on Side Effects

Use `AsyncMock` to verify that a dependency was called with expected arguments:

```python
@pytest.mark.asyncio
async def test_rag_query_calls_pinecone(mocker, authed_client):
    mock_query = AsyncMock(return_value=mock_pinecone_results)
    mocker.patch("app.services.rag_service.query_vectors", mock_query)

    await authed_client.post("/api/search", json={"query": "CRM integrations"})

    mock_query.assert_called_once()
    call_args = mock_query.call_args
    assert "CRM integrations" in str(call_args)
```

## Snapshot Testing (Frontend)

For complex rendered output, Vitest supports inline snapshots:

```tsx
test("renders conversation list item", () => {
  const { container } = render(
    <ConversationItem title="Demo Chat" lastMessage="Hello" />
  );
  expect(container.firstChild).toMatchSnapshot();
});
```

Use snapshots sparingly -- they are most useful for catching unintended markup changes, not for validating logic.

---
title: Backend Testing
---

# Backend Testing

The backend test suite uses **pytest** and **pytest-asyncio** to test services, schemas, and API endpoints.

## Test Structure

```
tests/
├── conftest.py              # Root-level shared fixtures
├── unit/
│   ├── conftest.py          # Unit test fixtures
│   ├── test_services/       # Service layer tests
│   └── test_schemas/        # Pydantic schema validation tests
└── integration/
    ├── conftest.py          # Integration test fixtures
    └── test_api/            # API route tests
```

## Running Tests

```bash
# Run the full suite
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests matching a keyword
pytest -k test_auth

# Run with verbose output
pytest -v

# Run a specific file
pytest tests/unit/test_services/test_conversation_service.py
```

## Fixtures

Shared fixtures are defined in `conftest.py` files. pytest automatically discovers fixtures based on the directory hierarchy.

### Common Fixtures

- **`test_client`** -- An async HTTP client configured for the FastAPI app.
- **`mock_supabase`** -- A patched Supabase client that returns controlled responses.
- **`mock_openai`** -- A patched OpenAI client for embedding and chat completion calls.
- **`mock_pinecone`** -- A patched Pinecone client for vector query and upsert operations.
- **`sample_user`** -- A dictionary representing an authenticated user payload.

## Async Tests

All async test functions must be decorated with `@pytest.mark.asyncio` or use the `asyncio_mode = "auto"` setting in `pyproject.toml`:

```python
import pytest

@pytest.mark.asyncio
async def test_create_conversation(test_client, mock_supabase):
    response = await test_client.post("/api/conversations", json={
        "title": "Test conversation"
    })
    assert response.status_code == 201
```

## Mocking External Clients

External services should never be called during tests. Use `unittest.mock.patch` or pytest-mock's `mocker` fixture to replace clients:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_embedding_generation(mocker):
    mock_client = AsyncMock()
    mock_client.embeddings.create.return_value = MockEmbeddingResponse(
        data=[MockEmbedding(embedding=[0.1] * 1536)]
    )
    mocker.patch("app.services.rag_service.get_openai_client", return_value=mock_client)

    result = await generate_embedding("test query")
    assert len(result) == 1536
```

## Configuration

Test configuration lives in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
filterwarnings = ["ignore::DeprecationWarning"]
```

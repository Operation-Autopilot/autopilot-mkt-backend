---
title: Contributing Guide
---

# Contributing Guide

Standards and patterns to follow when contributing to the Autopilot Marketplace codebase.

## Naming Conventions

### Files

All Python files use `snake_case`:

```
user_service.py
conversation_router.py
product_schema.py
```

### Code

- **Classes**: `PascalCase` (e.g., `ConversationService`, `ProductSchema`)
- **Functions and variables**: `snake_case` (e.g., `get_user_by_id`, `conversation_id`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`, `DEFAULT_PAGE_SIZE`)

### Database

Tables and columns use `snake_case` to match Python conventions and Supabase defaults:

```sql
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL,
    message_content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Import Patterns

Imports follow a strict ordering: standard library, then third-party, then local modules. Separate each group with a blank line.

```python
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.user_service import UserService
from app.schemas.user_schema import UserResponse
```

## Code Structure Patterns

### Router

Routers handle HTTP concerns only. They parse requests, call services, and return responses.

```python
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.product_schema import ProductResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    product = await ProductService.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
```

### Service

Services contain business logic. They orchestrate calls to models and external APIs.

```python
from app.models.product_model import ProductModel
from app.schemas.product_schema import ProductCreate


class ProductService:
    @staticmethod
    async def get_by_id(product_id: str):
        return await ProductModel.find_by_id(product_id)

    @staticmethod
    async def create(data: ProductCreate):
        return await ProductModel.insert(data.model_dump())
```

### Schema

Schemas define data shapes for validation and serialization using Pydantic.

```python
from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    description: str
    category: str


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
```

## Code Size Guidelines

| Scope    | Target       |
| -------- | ------------ |
| File     | < 300 lines  |
| Function | < 30 lines   |

When a file or function grows beyond these targets, refactor by extracting logic into separate modules or helper functions.

## Documentation Standards

- Add docstrings to public functions and classes
- Keep docstrings concise: one line for simple functions, a short paragraph for complex ones
- Use inline comments sparingly and only to explain non-obvious logic
- Update relevant docs pages when changing public APIs or adding features

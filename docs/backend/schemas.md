---
title: Pydantic Schemas
---

# Pydantic Schemas

All request/response schemas are defined in `src/schemas/` using **Pydantic v2** models. They enforce validation at the API boundary and provide automatic OpenAPI documentation.

## Schema Pattern

Every domain entity follows a **Base / Create / Update / Response** pattern:

```
EntityBase          ← Shared fields
├── EntityCreate    ← Fields required for creation
├── EntityUpdate    ← Optional fields for partial updates
└── EntityResponse  ← Full entity with DB-generated fields
```

### Example: Profile Schemas

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class ProfileBase(BaseModel):
    """Shared profile fields."""
    full_name: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    phone: str | None = None


class ProfileCreate(ProfileBase):
    """Fields required when creating a profile."""
    email: str
    auth_user_id: UUID


class ProfileUpdate(ProfileBase):
    """All fields optional for partial updates."""
    email: str | None = None


class ProfileResponse(ProfileBase):
    """Full profile returned from the API."""
    id: UUID
    email: str
    auth_user_id: UUID
    is_test_account: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Key Conventions

- **`ConfigDict(from_attributes=True)`** — Enables constructing response schemas directly from ORM/dict objects via `ProfileResponse.model_validate(db_row)`.
- **`BaseModel`** — All schemas inherit from Pydantic's `BaseModel`.
- **Optional fields in Update schemas** — Every field is `None` by default, allowing partial (PATCH-style) updates.
- **UUIDs and datetimes** — Database-generated fields use `UUID` and `datetime` types with automatic serialization.

## Schema Modules

### `src/schemas/auth.py`

```python
class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class PasswordResetRequest(BaseModel):
    email: str
```

### `src/schemas/profile.py`

Follows the Base/Create/Update/Response pattern as shown above. Includes fields for user identity, contact information, and the `is_test_account` flag.

### `src/schemas/company.py`

```python
class CompanyBase(BaseModel):
    name: str
    industry: str | None = None
    size: str | None = None
    website: str | None = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    size: str | None = None
    website: str | None = None

class CompanyResponse(CompanyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CompanyMemberResponse(BaseModel):
    id: UUID
    company_id: UUID
    profile_id: UUID
    role: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `src/schemas/conversation.py`

```python
class ConversationCreate(BaseModel):
    title: str | None = None
    session_id: UUID | None = None

class ConversationResponse(BaseModel):
    id: UUID
    profile_id: UUID | None
    session_id: UUID | None
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `src/schemas/message.py`

```python
class MessageCreate(BaseModel):
    content: str
    role: str = "user"
    metadata: dict | None = None

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    metadata: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `src/schemas/product.py`

```python
class RobotBase(BaseModel):
    name: str
    manufacturer: str
    category: str
    description: str | None = None
    payload_kg: float | None = None
    speed_ms: float | None = None
    battery_hours: float | None = None
    price_usd: float | None = None

class RobotResponse(RobotBase):
    id: UUID
    stripe_product_id: str | None = None
    stripe_price_id: str | None = None
    image_url: str | None = None
    specs: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RobotFilterOptions(BaseModel):
    categories: list[str]
    manufacturers: list[str]
    payload_range: tuple[float, float]
    price_range: tuple[float, float]
```

## Validation Tips

Use Pydantic's built-in validators for field-level constraints:

```python
from pydantic import BaseModel, field_validator, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
```

## Response Wrapping

List endpoints return paginated responses:

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

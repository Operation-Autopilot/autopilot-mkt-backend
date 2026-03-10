# API Reference

## Overview

The Autopilot Marketplace API is a RESTful JSON API built with FastAPI. All endpoints are prefixed with `/api/v1/`.

## Base URL

```
https://api.autopilot.com/api/v1/
```

## Content Type

All requests and responses use JSON. Set the `Content-Type` header on all requests that include a body:

```
Content-Type: application/json
```

## Authentication

The API uses Supabase JWT tokens for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

Tokens are obtained via the [Auth endpoints](auth.md). Some endpoints (such as anonymous session creation and the robot catalog) are accessible without authentication.

## Request Format

Request bodies must be valid JSON. Query parameters are used for filtering and pagination on `GET` endpoints.

```http
POST /api/v1/conversations HTTP/1.1
Host: api.autopilot.com
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "session_id": "sess_abc123"
}
```

## Response Format

All responses return JSON. Successful responses include the resource data directly or wrapped in a standard envelope:

```json
{
  "id": "conv_abc123",
  "created_at": "2026-01-15T10:30:00Z",
  "session_id": "sess_abc123"
}
```

List endpoints return an array of resources:

```json
[
  { "id": "conv_abc123", "created_at": "2026-01-15T10:30:00Z" },
  { "id": "conv_def456", "created_at": "2026-01-16T11:00:00Z" }
]
```

## Error Format

Errors return a JSON object with a `detail` field describing the problem:

```json
{
  "detail": "Invalid authentication credentials"
}
```

Validation errors (422) include additional detail about which fields failed:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## HTTP Status Codes

| Code | Meaning                  | Description                                      |
|------|--------------------------|--------------------------------------------------|
| 200  | OK                       | Request succeeded.                                |
| 201  | Created                  | Resource successfully created.                    |
| 400  | Bad Request              | The request was malformed or invalid.             |
| 401  | Unauthorized             | Missing or invalid authentication token.          |
| 403  | Forbidden                | Authenticated but lacking permission.             |
| 404  | Not Found                | The requested resource does not exist.            |
| 422  | Unprocessable Entity     | Request body failed validation.                   |
| 500  | Internal Server Error    | An unexpected error occurred on the server.       |

## Pagination

List endpoints support pagination via query parameters:

| Parameter | Type    | Default | Description              |
|-----------|---------|---------|--------------------------|
| `limit`   | integer | 20      | Maximum items to return.  |
| `offset`  | integer | 0       | Number of items to skip.  |

## Rate Limiting

The API enforces rate limits per authenticated user. If you exceed the limit, you will receive a `429 Too Many Requests` response. Retry after the interval specified in the `Retry-After` header.

## API Sections

- [Authentication](auth.md) - Sign up, log in, token management
- [Sessions](sessions.md) - Anonymous and authenticated sessions
- [Conversations](conversations.md) - Conversations and messages
- [Profiles](profiles.md) - User profiles
- [Companies](companies.md) - Company management and members
- [Robots](robots.md) - Robot catalog and recommendations
- [Checkout](checkout.md) - Stripe checkout and orders
- [Discovery](discovery.md) - Discovery profiles
- [Webhooks](webhooks.md) - Stripe webhook handling

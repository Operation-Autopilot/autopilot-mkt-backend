# Conversations

Conversations represent chat threads between a user and the Autopilot agent. Each conversation contains messages and can optionally be tied to a session.

## POST /conversations

Create a new conversation.

**Auth required:** No (if session_id provided) / Yes (for authenticated conversations)

### Request

```http
POST /api/v1/conversations HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "session_id": "sess_abc123"
}
```

### Body Parameters

| Field        | Type   | Required | Description                                     |
|--------------|--------|----------|-------------------------------------------------|
| `session_id` | string | No       | Session ID to associate with the conversation.  |

### Response

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "conv_abc123",
  "session_id": "sess_abc123",
  "user_id": "usr_abc123",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

---

## GET /conversations

List all conversations for the authenticated user.

**Auth required:** Yes

### Request

```http
GET /api/v1/conversations?limit=10&offset=0 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Query Parameters

| Parameter | Type    | Default | Description              |
|-----------|---------|---------|--------------------------|
| `limit`   | integer | 20      | Maximum items to return. |
| `offset`  | integer | 0       | Number of items to skip. |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

[
  {
    "id": "conv_abc123",
    "session_id": "sess_abc123",
    "user_id": "usr_abc123",
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-15T11:00:00Z"
  },
  {
    "id": "conv_def456",
    "session_id": null,
    "user_id": "usr_abc123",
    "created_at": "2026-01-16T09:00:00Z",
    "updated_at": "2026-01-16T09:45:00Z"
  }
]
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |

---

## GET /conversations/:id

Retrieve a single conversation by ID.

**Auth required:** Yes

### Request

```http
GET /api/v1/conversations/conv_abc123 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description            |
|-----------|--------|------------------------|
| `id`      | string | The conversation ID.   |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "conv_abc123",
  "session_id": "sess_abc123",
  "user_id": "usr_abc123",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T11:00:00Z"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |
| 403  | `"Not authorized to access this conversation"` |
| 404  | `"Conversation not found"`                |

---

## POST /conversations/:id/messages

Send a message in a conversation. This triggers an agent response that is returned in the same response.

**Auth required:** Yes

### Request

```http
POST /api/v1/conversations/conv_abc123/messages HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "content": "I need a floor cleaning robot for a 50,000 sq ft warehouse."
}
```

### Path Parameters

| Parameter | Type   | Description            |
|-----------|--------|------------------------|
| `id`      | string | The conversation ID.   |

### Body Parameters

| Field     | Type   | Required | Description               |
|-----------|--------|----------|---------------------------|
| `content` | string | Yes      | The message text content. |

### Response

The response includes both the user message and the agent's reply:

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "user_message": {
    "id": "msg_abc123",
    "conversation_id": "conv_abc123",
    "role": "user",
    "content": "I need a floor cleaning robot for a 50,000 sq ft warehouse.",
    "created_at": "2026-01-15T11:00:00Z"
  },
  "agent_message": {
    "id": "msg_def456",
    "conversation_id": "conv_abc123",
    "role": "assistant",
    "content": "I can help with that! For a warehouse of that size, I'd recommend looking at our industrial floor scrubbers. Could you tell me more about the flooring type and your cleaning frequency needs?",
    "created_at": "2026-01-15T11:00:02Z"
  }
}
```

### Errors

| Code | Detail                                          |
|------|-------------------------------------------------|
| 401  | `"Invalid authentication credentials"`          |
| 403  | `"Not authorized to access this conversation"`  |
| 404  | `"Conversation not found"`                      |
| 422  | Validation error on content                     |

---

## GET /conversations/:id/messages

Retrieve all messages in a conversation, ordered chronologically.

**Auth required:** Yes

### Request

```http
GET /api/v1/conversations/conv_abc123/messages?limit=50&offset=0 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description            |
|-----------|--------|------------------------|
| `id`      | string | The conversation ID.   |

### Query Parameters

| Parameter | Type    | Default | Description              |
|-----------|---------|---------|--------------------------|
| `limit`   | integer | 50      | Maximum items to return. |
| `offset`  | integer | 0       | Number of items to skip. |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

[
  {
    "id": "msg_001",
    "conversation_id": "conv_abc123",
    "role": "assistant",
    "content": "Welcome! I'm your Autopilot procurement assistant. How can I help you find the right cleaning robot?",
    "created_at": "2026-01-15T10:30:00Z"
  },
  {
    "id": "msg_002",
    "conversation_id": "conv_abc123",
    "role": "user",
    "content": "I need a floor cleaning robot for a 50,000 sq ft warehouse.",
    "created_at": "2026-01-15T11:00:00Z"
  },
  {
    "id": "msg_003",
    "conversation_id": "conv_abc123",
    "role": "assistant",
    "content": "I can help with that! For a warehouse of that size, I'd recommend looking at our industrial floor scrubbers.",
    "created_at": "2026-01-15T11:00:02Z"
  }
]
```

### Errors

| Code | Detail                                          |
|------|-------------------------------------------------|
| 401  | `"Invalid authentication credentials"`          |
| 403  | `"Not authorized to access this conversation"`  |
| 404  | `"Conversation not found"`                      |

## Message Schema

| Field             | Type   | Description                                    |
|-------------------|--------|------------------------------------------------|
| `id`              | string | Unique message identifier.                     |
| `conversation_id` | string | Parent conversation ID.                        |
| `role`            | string | Either `"user"` or `"assistant"`.              |
| `content`         | string | The message text.                              |
| `created_at`      | string | ISO 8601 timestamp of message creation.        |

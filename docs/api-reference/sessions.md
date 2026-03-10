# Sessions

Sessions track user activity across the platform. Anonymous sessions can be created without authentication and later linked to an authenticated user account.

## POST /sessions

Create a new anonymous session.

**Auth required:** No

### Request

```http
POST /api/v1/sessions HTTP/1.1
Content-Type: application/json

{}
```

### Response

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "sess_abc123",
  "user_id": null,
  "data": {},
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

---

## GET /sessions/:id

Retrieve a session by ID.

**Auth required:** No (for anonymous sessions) / Yes (for linked sessions)

### Request

```http
GET /api/v1/sessions/sess_abc123 HTTP/1.1
```

### Path Parameters

| Parameter | Type   | Description        |
|-----------|--------|--------------------|
| `id`      | string | The session ID.    |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "sess_abc123",
  "user_id": null,
  "data": {
    "discovery_started": true,
    "pages_visited": ["catalog", "robot_detail"]
  },
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T11:00:00Z"
}
```

### Errors

| Code | Detail                        |
|------|-------------------------------|
| 404  | `"Session not found"`         |

---

## PUT /sessions/:id

Update session data. Performs a merge with existing session data.

**Auth required:** No (for anonymous sessions) / Yes (for linked sessions)

### Request

```http
PUT /api/v1/sessions/sess_abc123 HTTP/1.1
Content-Type: application/json

{
  "data": {
    "discovery_completed": true,
    "preferred_robot_type": "floor_cleaner"
  }
}
```

### Path Parameters

| Parameter | Type   | Description        |
|-----------|--------|--------------------|
| `id`      | string | The session ID.    |

### Body Parameters

| Field  | Type   | Required | Description                              |
|--------|--------|----------|------------------------------------------|
| `data` | object | Yes      | Key-value pairs to merge into session data. |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "sess_abc123",
  "user_id": null,
  "data": {
    "discovery_started": true,
    "pages_visited": ["catalog", "robot_detail"],
    "discovery_completed": true,
    "preferred_robot_type": "floor_cleaner"
  },
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T11:15:00Z"
}
```

### Errors

| Code | Detail                        |
|------|-------------------------------|
| 404  | `"Session not found"`         |
| 422  | Validation error on data      |

---

## POST /sessions/:id/link

Link an anonymous session to an authenticated user account. This associates any session data (discovery profile, conversations, etc.) with the user.

**Auth required:** Yes

### Request

```http
POST /api/v1/sessions/sess_abc123/link HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description        |
|-----------|--------|--------------------|
| `id`      | string | The session ID.    |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "sess_abc123",
  "user_id": "usr_abc123",
  "data": {
    "discovery_started": true,
    "pages_visited": ["catalog", "robot_detail"],
    "discovery_completed": true
  },
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T11:20:00Z"
}
```

### Errors

| Code | Detail                                         |
|------|-------------------------------------------------|
| 400  | `"Session is already linked to a user"`         |
| 401  | `"Invalid authentication credentials"`          |
| 404  | `"Session not found"`                           |

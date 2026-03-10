# Profiles

User profiles contain account details and preferences. Users can view and update their own profile, toggle test account status, and view public profiles of other users.

## GET /profiles/me

Retrieve the authenticated user's profile.

**Auth required:** Yes

### Request

```http
GET /api/v1/profiles/me HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "usr_abc123",
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "company_id": "comp_abc123",
  "phone": "+1-555-0100",
  "job_title": "Facilities Manager",
  "is_test_account": false,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-20T14:00:00Z"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |

---

## PUT /profiles/me

Update the authenticated user's profile. Only provided fields are updated.

**Auth required:** Yes

### Request

```http
PUT /api/v1/profiles/me HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "first_name": "Jane",
  "last_name": "Smith",
  "phone": "+1-555-0100",
  "job_title": "Senior Facilities Manager"
}
```

### Body Parameters

| Field        | Type   | Required | Description               |
|--------------|--------|----------|---------------------------|
| `first_name` | string | No       | User's first name.        |
| `last_name`  | string | No       | User's last name.         |
| `phone`      | string | No       | Phone number.             |
| `job_title`  | string | No       | Job title or role.        |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "usr_abc123",
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "company_id": "comp_abc123",
  "phone": "+1-555-0100",
  "job_title": "Senior Facilities Manager",
  "is_test_account": false,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-21T09:00:00Z"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |
| 422  | Validation error on fields                |

---

## POST /profiles/me/test-account

Toggle the test account flag on the authenticated user's profile. Test accounts can access sandbox environments and test data without affecting production.

**Auth required:** Yes

### Request

```http
POST /api/v1/profiles/me/test-account HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "is_test_account": true
}
```

### Body Parameters

| Field             | Type    | Required | Description                      |
|-------------------|---------|----------|----------------------------------|
| `is_test_account` | boolean | Yes      | Whether to enable test mode.     |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "usr_abc123",
  "email": "user@example.com",
  "is_test_account": true,
  "updated_at": "2026-01-21T09:30:00Z"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |

---

## GET /profiles/:id

View the public profile of another user. Returns a limited subset of profile data.

**Auth required:** Yes

### Request

```http
GET /api/v1/profiles/usr_def456 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description        |
|-----------|--------|--------------------|
| `id`      | string | The user ID.       |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "usr_def456",
  "first_name": "John",
  "last_name": "Doe",
  "company_id": "comp_def456",
  "job_title": "Operations Director"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |
| 404  | `"Profile not found"`                     |

## Profile Schema

| Field             | Type    | Description                                    |
|-------------------|---------|------------------------------------------------|
| `id`              | string  | Unique user identifier.                        |
| `email`           | string  | User's email address (private, own profile only). |
| `first_name`      | string  | First name.                                    |
| `last_name`       | string  | Last name.                                     |
| `company_id`      | string  | Associated company ID.                         |
| `phone`           | string  | Phone number (private, own profile only).      |
| `job_title`       | string  | Job title or role.                             |
| `is_test_account` | boolean | Whether the account is in test mode.           |
| `created_at`      | string  | ISO 8601 creation timestamp.                   |
| `updated_at`      | string  | ISO 8601 last update timestamp.                |

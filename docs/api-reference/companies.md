# Companies

Company endpoints manage organization accounts and team membership. Companies can have multiple members with different roles.

## POST /companies

Create a new company. The authenticated user becomes the company owner.

**Auth required:** Yes

### Request

```http
POST /api/v1/companies HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "name": "Acme Facilities Inc.",
  "industry": "manufacturing",
  "size": "51-200",
  "address": {
    "street": "123 Industrial Blvd",
    "city": "Chicago",
    "state": "IL",
    "zip": "60601",
    "country": "US"
  }
}
```

### Body Parameters

| Field      | Type   | Required | Description                                          |
|------------|--------|----------|------------------------------------------------------|
| `name`     | string | Yes      | Company name.                                        |
| `industry` | string | No       | Industry sector.                                     |
| `size`     | string | No       | Employee count range (e.g., `"1-10"`, `"51-200"`).   |
| `address`  | object | No       | Company address with street, city, state, zip, country. |

### Response

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "comp_abc123",
  "name": "Acme Facilities Inc.",
  "industry": "manufacturing",
  "size": "51-200",
  "address": {
    "street": "123 Industrial Blvd",
    "city": "Chicago",
    "state": "IL",
    "zip": "60601",
    "country": "US"
  },
  "owner_id": "usr_abc123",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |
| 422  | Validation error on fields                |

---

## GET /companies/:id

Retrieve a company by ID.

**Auth required:** Yes (must be a member of the company)

### Request

```http
GET /api/v1/companies/comp_abc123 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description         |
|-----------|--------|---------------------|
| `id`      | string | The company ID.     |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "comp_abc123",
  "name": "Acme Facilities Inc.",
  "industry": "manufacturing",
  "size": "51-200",
  "address": {
    "street": "123 Industrial Blvd",
    "city": "Chicago",
    "state": "IL",
    "zip": "60601",
    "country": "US"
  },
  "owner_id": "usr_abc123",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

### Errors

| Code | Detail                                      |
|------|---------------------------------------------|
| 401  | `"Invalid authentication credentials"`      |
| 403  | `"Not authorized to access this company"`   |
| 404  | `"Company not found"`                       |

---

## PUT /companies/:id

Update company details. Only the owner can update company information.

**Auth required:** Yes (owner only)

### Request

```http
PUT /api/v1/companies/comp_abc123 HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "name": "Acme Facilities Corporation",
  "size": "201-500"
}
```

### Path Parameters

| Parameter | Type   | Description         |
|-----------|--------|---------------------|
| `id`      | string | The company ID.     |

### Body Parameters

| Field      | Type   | Required | Description             |
|------------|--------|----------|-------------------------|
| `name`     | string | No       | Company name.           |
| `industry` | string | No       | Industry sector.        |
| `size`     | string | No       | Employee count range.   |
| `address`  | object | No       | Company address.        |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "comp_abc123",
  "name": "Acme Facilities Corporation",
  "industry": "manufacturing",
  "size": "201-500",
  "address": {
    "street": "123 Industrial Blvd",
    "city": "Chicago",
    "state": "IL",
    "zip": "60601",
    "country": "US"
  },
  "owner_id": "usr_abc123",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-20T14:00:00Z"
}
```

### Errors

| Code | Detail                                      |
|------|---------------------------------------------|
| 401  | `"Invalid authentication credentials"`      |
| 403  | `"Only the company owner can update"`       |
| 404  | `"Company not found"`                       |

---

## GET /companies/:id/members

List all members of a company.

**Auth required:** Yes (must be a member of the company)

### Request

```http
GET /api/v1/companies/comp_abc123/members HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description         |
|-----------|--------|---------------------|
| `id`      | string | The company ID.     |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

[
  {
    "user_id": "usr_abc123",
    "first_name": "Jane",
    "last_name": "Smith",
    "role": "owner",
    "joined_at": "2026-01-15T10:30:00Z"
  },
  {
    "user_id": "usr_def456",
    "first_name": "John",
    "last_name": "Doe",
    "role": "member",
    "joined_at": "2026-01-16T09:00:00Z"
  }
]
```

### Errors

| Code | Detail                                      |
|------|---------------------------------------------|
| 401  | `"Invalid authentication credentials"`      |
| 403  | `"Not authorized to access this company"`   |
| 404  | `"Company not found"`                       |

---

## POST /companies/:id/members

Add a member to the company. Only the owner can add members.

**Auth required:** Yes (owner only)

### Request

```http
POST /api/v1/companies/comp_abc123/members HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "user_id": "usr_ghi789",
  "role": "member"
}
```

### Path Parameters

| Parameter | Type   | Description         |
|-----------|--------|---------------------|
| `id`      | string | The company ID.     |

### Body Parameters

| Field     | Type   | Required | Description                              |
|-----------|--------|----------|------------------------------------------|
| `user_id` | string | Yes      | ID of the user to add.                   |
| `role`    | string | No       | Role within the company (default: `"member"`). |

### Response

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "user_id": "usr_ghi789",
  "company_id": "comp_abc123",
  "role": "member",
  "joined_at": "2026-01-20T14:00:00Z"
}
```

### Errors

| Code | Detail                                      |
|------|---------------------------------------------|
| 400  | `"User is already a member of this company"` |
| 401  | `"Invalid authentication credentials"`      |
| 403  | `"Only the company owner can add members"`  |
| 404  | `"Company not found"` or `"User not found"` |

---

## DELETE /companies/:id/members/:user_id

Remove a member from the company. Only the owner can remove members. The owner cannot remove themselves.

**Auth required:** Yes (owner only)

### Request

```http
DELETE /api/v1/companies/comp_abc123/members/usr_def456 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description                    |
|-----------|--------|--------------------------------|
| `id`      | string | The company ID.                |
| `user_id` | string | ID of the member to remove.    |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "detail": "Member removed successfully"
}
```

### Errors

| Code | Detail                                        |
|------|-----------------------------------------------|
| 400  | `"Cannot remove the company owner"`           |
| 401  | `"Invalid authentication credentials"`        |
| 403  | `"Only the company owner can remove members"` |
| 404  | `"Company not found"` or `"Member not found"` |

# Authentication

All authentication endpoints handle user registration, login, token management, and password recovery. Tokens are Supabase JWTs.

## POST /auth/signup

Create a new user account.

**Auth required:** No

### Request

```http
POST /api/v1/auth/signup HTTP/1.1
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

### Parameters

| Field      | Type   | Required | Description                          |
|------------|--------|----------|--------------------------------------|
| `email`    | string | Yes      | Valid email address.                  |
| `password` | string | Yes      | Password (minimum 8 characters).     |

### Response

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "user": {
    "id": "usr_abc123",
    "email": "user@example.com",
    "created_at": "2026-01-15T10:30:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Errors

| Code | Detail                              |
|------|-------------------------------------|
| 400  | `"User already exists"`             |
| 422  | Validation error on email/password  |

---

## POST /auth/login

Authenticate an existing user and receive tokens.

**Auth required:** No

### Request

```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

### Parameters

| Field      | Type   | Required | Description          |
|------------|--------|----------|----------------------|
| `email`    | string | Yes      | Registered email.    |
| `password` | string | Yes      | Account password.    |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "usr_abc123",
    "email": "user@example.com"
  }
}
```

### Errors

| Code | Detail                              |
|------|-------------------------------------|
| 401  | `"Invalid email or password"`       |

---

## POST /auth/logout

Invalidate the current session and tokens.

**Auth required:** Yes

### Request

```http
POST /api/v1/auth/logout HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "detail": "Successfully logged out"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |

---

## POST /auth/refresh

Exchange a refresh token for a new access token.

**Auth required:** No (uses refresh token in body)

### Request

```http
POST /api/v1/auth/refresh HTTP/1.1
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Parameters

| Field           | Type   | Required | Description                  |
|-----------------|--------|----------|------------------------------|
| `refresh_token` | string | Yes      | A valid refresh token.       |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Errors

| Code | Detail                          |
|------|---------------------------------|
| 401  | `"Invalid or expired refresh token"` |

---

## POST /auth/password-reset/request

Request a password reset email. Always returns 200 regardless of whether the email exists (to prevent user enumeration).

**Auth required:** No

### Request

```http
POST /api/v1/auth/password-reset/request HTTP/1.1
Content-Type: application/json

{
  "email": "user@example.com"
}
```

### Parameters

| Field   | Type   | Required | Description                     |
|---------|--------|----------|---------------------------------|
| `email` | string | Yes      | Email address for the account.  |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "detail": "If the email exists, a password reset link has been sent"
}
```

---

## POST /auth/password-reset/confirm

Set a new password using the reset token received via email.

**Auth required:** No

### Request

```http
POST /api/v1/auth/password-reset/confirm HTTP/1.1
Content-Type: application/json

{
  "token": "reset_token_from_email",
  "new_password": "newsecurepassword456"
}
```

### Parameters

| Field          | Type   | Required | Description                          |
|----------------|--------|----------|--------------------------------------|
| `token`        | string | Yes      | Password reset token from the email. |
| `new_password` | string | Yes      | New password (minimum 8 characters). |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "detail": "Password has been reset successfully"
}
```

### Errors

| Code | Detail                                |
|------|---------------------------------------|
| 400  | `"Invalid or expired reset token"`    |
| 422  | Validation error on new_password      |

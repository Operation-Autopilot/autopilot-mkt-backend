# Checkout

Checkout endpoints handle the purchase flow via Stripe. Users create checkout sessions, verify payment status, and view their order history.

## POST /checkout/sessions

Create a Stripe checkout session for purchasing a robot. Returns a URL to redirect the user to Stripe's hosted checkout page.

**Auth required:** Yes

### Request

```http
POST /api/v1/checkout/sessions HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

{
  "robot_id": "robot_abc123",
  "quantity": 1,
  "success_url": "https://marketplace.autopilot.com/checkout/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://marketplace.autopilot.com/checkout/cancel"
}
```

### Body Parameters

| Field         | Type    | Required | Description                                                  |
|---------------|---------|----------|--------------------------------------------------------------|
| `robot_id`    | string  | Yes      | ID of the robot to purchase.                                 |
| `quantity`    | integer | No       | Number of units (default: 1).                                |
| `success_url` | string | No       | URL to redirect to after successful payment.                 |
| `cancel_url`  | string | No       | URL to redirect to if the user cancels.                      |

### Response

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "cs_abc123",
  "url": "https://checkout.stripe.com/c/pay/cs_abc123...",
  "status": "open",
  "robot_id": "robot_abc123",
  "quantity": 1,
  "amount_total": 24999.00,
  "currency": "USD",
  "expires_at": "2026-01-15T11:30:00Z",
  "created_at": "2026-01-15T10:30:00Z"
}
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |
| 404  | `"Robot not found"`                       |
| 400  | `"Robot is not available for purchase"`   |

---

## GET /checkout/sessions/:id

Check the status of a checkout session.

**Auth required:** Yes

### Request

```http
GET /api/v1/checkout/sessions/cs_abc123 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description                 |
|-----------|--------|-----------------------------|
| `id`      | string | The checkout session ID.    |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "cs_abc123",
  "status": "complete",
  "payment_status": "paid",
  "robot_id": "robot_abc123",
  "quantity": 1,
  "amount_total": 24999.00,
  "currency": "USD",
  "order_id": "ord_abc123",
  "created_at": "2026-01-15T10:30:00Z",
  "completed_at": "2026-01-15T10:35:00Z"
}
```

### Checkout Session Statuses

| Status     | Description                                    |
|------------|------------------------------------------------|
| `open`     | Session is active, awaiting payment.           |
| `complete` | Payment succeeded, order created.              |
| `expired`  | Session expired before payment was completed.  |

### Errors

| Code | Detail                                        |
|------|-----------------------------------------------|
| 401  | `"Invalid authentication credentials"`        |
| 403  | `"Not authorized to view this session"`       |
| 404  | `"Checkout session not found"`                |

---

## GET /orders

List all orders for the authenticated user.

**Auth required:** Yes

### Request

```http
GET /api/v1/orders?limit=10&offset=0 HTTP/1.1
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
    "id": "ord_abc123",
    "user_id": "usr_abc123",
    "robot_id": "robot_abc123",
    "robot_name": "CleanBot Pro X500",
    "quantity": 1,
    "amount_total": 24999.00,
    "currency": "USD",
    "status": "confirmed",
    "stripe_checkout_session_id": "cs_abc123",
    "created_at": "2026-01-15T10:35:00Z",
    "updated_at": "2026-01-15T10:35:00Z"
  }
]
```

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |

---

## GET /orders/:id

Retrieve details of a specific order.

**Auth required:** Yes

### Request

```http
GET /api/v1/orders/ord_abc123 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Path Parameters

| Parameter | Type   | Description       |
|-----------|--------|-------------------|
| `id`      | string | The order ID.     |

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "ord_abc123",
  "user_id": "usr_abc123",
  "robot_id": "robot_abc123",
  "robot_name": "CleanBot Pro X500",
  "quantity": 1,
  "amount_total": 24999.00,
  "currency": "USD",
  "status": "confirmed",
  "stripe_checkout_session_id": "cs_abc123",
  "stripe_payment_intent_id": "pi_abc123",
  "billing_details": {
    "name": "Jane Smith",
    "email": "user@example.com",
    "address": {
      "city": "Chicago",
      "state": "IL",
      "country": "US"
    }
  },
  "created_at": "2026-01-15T10:35:00Z",
  "updated_at": "2026-01-15T10:35:00Z"
}
```

### Order Statuses

| Status       | Description                                |
|--------------|--------------------------------------------|
| `pending`    | Payment is being processed.                |
| `confirmed`  | Payment succeeded, order is confirmed.     |
| `failed`     | Payment failed.                            |
| `refunded`   | Order has been refunded.                   |

### Errors

| Code | Detail                                    |
|------|-------------------------------------------|
| 401  | `"Invalid authentication credentials"`    |
| 403  | `"Not authorized to view this order"`     |
| 404  | `"Order not found"`                       |

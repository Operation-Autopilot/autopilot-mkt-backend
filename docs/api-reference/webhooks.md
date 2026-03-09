# Webhooks

The API receives webhook events from Stripe to process payment outcomes and update order statuses. These endpoints are not called by API consumers directly -- they are called by Stripe's infrastructure.

## POST /webhooks/stripe

Receives and processes Stripe webhook events.

**Auth required:** No (uses Stripe signature verification instead)

### Request

Stripe sends a `POST` request with a JSON event payload and a signature header:

```http
POST /api/v1/webhooks/stripe HTTP/1.1
Content-Type: application/json
Stripe-Signature: t=1234567890,v1=abc123...

{
  "id": "evt_abc123",
  "object": "event",
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "id": "cs_abc123",
      "payment_status": "paid",
      "metadata": {
        "user_id": "usr_abc123",
        "robot_id": "robot_abc123"
      }
    }
  }
}
```

### Response

The endpoint returns a `200 OK` to acknowledge receipt:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ok"
}
```

On failure, a non-200 status is returned and Stripe will retry the delivery:

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": "Invalid signature"
}
```

---

## Handled Events

### checkout.session.completed

Triggered when a customer completes the Stripe checkout flow. This event creates a new order in the system.

**Actions taken:**

1. Validates the checkout session metadata (user_id, robot_id).
2. Creates an order record with status `confirmed`.
3. Associates the order with the user and robot.

**Event payload (relevant fields):**

```json
{
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "id": "cs_abc123",
      "payment_status": "paid",
      "amount_total": 2499900,
      "currency": "usd",
      "metadata": {
        "user_id": "usr_abc123",
        "robot_id": "robot_abc123",
        "quantity": "1"
      }
    }
  }
}
```

### payment_intent.succeeded

Triggered when a payment is successfully processed. Used to confirm payment status on existing orders.

**Actions taken:**

1. Looks up the order by the associated payment intent ID.
2. Updates the order payment status to `paid`.

**Event payload (relevant fields):**

```json
{
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_abc123",
      "status": "succeeded",
      "amount": 2499900,
      "currency": "usd",
      "metadata": {
        "order_id": "ord_abc123"
      }
    }
  }
}
```

### payment_intent.failed

Triggered when a payment fails. Updates the corresponding order status.

**Actions taken:**

1. Looks up the order by the associated payment intent ID.
2. Updates the order status to `failed`.
3. Records the failure reason.

**Event payload (relevant fields):**

```json
{
  "type": "payment_intent.payment_failed",
  "data": {
    "object": {
      "id": "pi_abc123",
      "status": "requires_payment_method",
      "last_payment_error": {
        "code": "card_declined",
        "message": "Your card was declined."
      },
      "metadata": {
        "order_id": "ord_abc123"
      }
    }
  }
}
```

---

## Signature Verification

All incoming webhook requests are verified using Stripe's signature verification mechanism. The `Stripe-Signature` header contains a timestamp and signature hash that are validated against the webhook secret.

### Verification Process

1. The endpoint first attempts to verify the signature using the **production webhook secret**.
2. If that fails, it falls back to the **test webhook secret**.
3. If both verifications fail, the request is rejected with a `400 Bad Request`.

This dual-secret approach allows the system to handle both live and test mode Stripe events.

### Configuration

The webhook secrets are configured via environment variables:

| Variable                        | Description                          |
|---------------------------------|--------------------------------------|
| `STRIPE_WEBHOOK_SECRET`         | Production webhook signing secret.   |
| `STRIPE_WEBHOOK_SECRET_TEST`    | Test mode webhook signing secret.    |

### Security Considerations

- **Always verify signatures.** Never process webhook events without validating the `Stripe-Signature` header.
- **Use HTTPS.** The webhook endpoint must be served over HTTPS in production.
- **Idempotency.** The endpoint handles duplicate events gracefully by checking if the event has already been processed (using the Stripe event ID).
- **Respond quickly.** The endpoint returns a `200 OK` promptly and processes any heavy work asynchronously to avoid Stripe timeouts.

### Error Responses

| Code | Detail                                          |
|------|-------------------------------------------------|
| 400  | `"Invalid signature"` - Signature verification failed with both secrets. |
| 400  | `"Unhandled event type"` - The event type is not supported. |
| 500  | `"Internal server error"` - Processing failed after signature verification. |

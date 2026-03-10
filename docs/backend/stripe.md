---
title: Stripe Integration
---

# Stripe Integration

The backend integrates with **Stripe** for payment processing. The integration supports both test and production modes simultaneously, allowing test accounts to operate in production without affecting real transactions.

## Dual-Mode Architecture

The robot catalog stores **both test and production Stripe IDs** for each product:

| Column | Description |
|--------|-------------|
| `stripe_product_id` | Production Stripe product ID |
| `stripe_price_id` | Production Stripe price ID |
| `stripe_product_id_test` | Test-mode Stripe product ID |
| `stripe_price_id_test` | Test-mode Stripe price ID |

This allows the same database to serve both real customers and test accounts.

## Test Accounts in Production

The `profiles` table includes an `is_test_account` boolean flag (added in migration `011_add_test_account_flag`). When this flag is `true`, the backend routes all Stripe operations through test-mode keys.

```python
def _get_stripe_key(self, profile: Profile) -> str:
    """Select Stripe key based on account type."""
    if profile.is_test_account:
        return os.getenv("STRIPE_SECRET_KEY_TEST")
    return os.getenv("STRIPE_SECRET_KEY")


def _get_price_id(self, robot: Robot, profile: Profile) -> str:
    """Select price ID based on account type."""
    if profile.is_test_account:
        return robot.stripe_price_id_test
    return robot.stripe_price_id
```

## Product Sync Script

The `sync_stripe_products.py` script synchronizes the robot catalog with Stripe products and prices. It **auto-detects** whether to use test or production mode based on the provided API key.

```bash
# Sync with production Stripe
STRIPE_SECRET_KEY=sk_live_... python scripts/sync_stripe_products.py

# Sync with test Stripe
STRIPE_SECRET_KEY=sk_test_... python scripts/sync_stripe_products.py
```

The script:

1. Reads all robots from the database
2. For each robot, creates or updates a Stripe product
3. Creates or updates a Stripe price for the product
4. Writes the Stripe IDs back to the appropriate columns (`stripe_product_id` / `stripe_product_id_test`)

```python
# Auto-detect test vs production mode
is_test_mode = stripe_key.startswith("sk_test_")

product_id_column = (
    "stripe_product_id_test" if is_test_mode
    else "stripe_product_id"
)
price_id_column = (
    "stripe_price_id_test" if is_test_mode
    else "stripe_price_id"
)
```

## Checkout Flow

1. Frontend requests a checkout session via `POST /api/checkout/sessions`
2. Backend determines if user is a test account
3. Backend creates a Stripe Checkout Session with the appropriate keys and price IDs
4. Frontend redirects user to the Stripe-hosted checkout page
5. On completion, Stripe sends a webhook event

```python
session = stripe.checkout.Session.create(
    api_key=stripe_key,
    line_items=[{
        "price": price_id,
        "quantity": quantity,
    }],
    mode="payment",
    success_url=f"{FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
    cancel_url=f"{FRONTEND_URL}/checkout/cancel",
    metadata={
        "profile_id": str(profile_id),
        "robot_id": str(robot_id),
        "is_test": str(profile.is_test_account),
    },
)
```

## Webhook Handling

Stripe webhooks are received at `POST /api/webhooks/stripe`. The handler implements a **fallback verification strategy** to support both production and test webhook signatures:

```python
@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Try production webhook secret first
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        # Fall back to test webhook secret
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET_TEST
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

    # Process the verified event
    if event["type"] == "checkout.session.completed":
        await handle_checkout_completed(event["data"]["object"])
    elif event["type"] == "payment_intent.succeeded":
        await handle_payment_succeeded(event["data"]["object"])

    return {"status": "ok"}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Production Stripe secret key (`sk_live_...`) |
| `STRIPE_WEBHOOK_SECRET` | Production webhook signing secret (`whsec_...`) |
| `STRIPE_SECRET_KEY_TEST` | Test Stripe secret key (`sk_test_...`) |
| `STRIPE_WEBHOOK_SECRET_TEST` | Test webhook signing secret (`whsec_...`) |

## Local Development

For local testing with Stripe webhooks, use the Stripe CLI to forward events:

```bash
# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# Trigger a test event
stripe trigger checkout.session.completed
```

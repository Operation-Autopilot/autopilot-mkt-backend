#!/usr/bin/env python
"""End-to-end Stripe checkout test using real Stripe test API.

Tests the full checkout → webhook → order lifecycle without a browser.
Constructs a signed webhook payload so the backend processes it as if
Stripe delivered it.

Prerequisites:
  - Backend running at localhost:8080
  - .env has STRIPE_SECRET_KEY_TEST (sk_test_...) and STRIPE_WEBHOOK_SECRET_TEST (whsec_...)
  - TestBot ($0.01) must exist in the database (run seed_test_robot.py first)

Usage:
    python scripts/e2e_stripe_test.py
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import httpx
import stripe

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8080/api/v1"


def get_testbot_product_id(client: httpx.Client) -> str:
    """Fetch TestBot product ID from the catalog endpoint."""
    resp = client.get(f"{BASE_URL}/robots/catalog", params={"search": "TestBot"})
    resp.raise_for_status()
    data = resp.json()
    robots = data.get("robots", [])
    for robot in robots:
        if robot.get("name") == "TestBot":
            return robot["id"]
    raise RuntimeError(
        "TestBot not found in catalog. Run scripts/seed_test_robot.py first."
    )


def create_session(client: httpx.Client, product_id: str) -> dict:
    """POST /checkout/session to create a pending order and Stripe session."""
    payload = {
        "product_id": product_id,
        "success_url": "http://localhost:3000/checkout/success?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "http://localhost:3000/greenlight",
    }
    resp = client.post(f"{BASE_URL}/checkout/session", json=payload)
    resp.raise_for_status()
    return resp.json()


def build_signed_webhook(
    event_type: str,
    session_data: dict,
    webhook_secret: str,
) -> tuple[bytes, str]:
    """Build a Stripe-signed webhook payload.

    Constructs a minimal checkout.session.* event payload and signs it with
    the webhook secret using Stripe's HMAC-SHA256 scheme.

    Args:
        event_type: Stripe event type string (e.g. "checkout.session.completed").
        session_data: Dict containing at least stripe_session_id and order_id.
        webhook_secret: The whsec_... secret from STRIPE_WEBHOOK_SECRET_TEST.

    Returns:
        tuple: (raw_payload_bytes, stripe_signature_header)
    """
    session_id = session_data["stripe_session_id"]

    # Retrieve the actual Stripe session to get real metadata
    stripe_session = stripe.checkout.Session.retrieve(session_id)

    event_payload = {
        "id": f"evt_test_{int(time.time())}",
        "object": "event",
        "type": event_type,
        "created": int(time.time()),
        "livemode": False,
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "payment_status": "paid" if "completed" in event_type else "unpaid",
                "status": "complete" if "completed" in event_type else "expired",
                "customer_email": stripe_session.get("customer_email"),
                "metadata": stripe_session.get("metadata", {}),
                "subscription": stripe_session.get("subscription"),
                "payment_intent": stripe_session.get("payment_intent"),
                "amount_total": stripe_session.get("amount_total"),
                "currency": stripe_session.get("currency", "usd"),
            }
        },
    }

    payload_bytes = json.dumps(event_payload).encode()
    timestamp = int(time.time())

    # Build the Stripe signature header: t=<ts>,v1=<hmac>
    signed_payload = f"{timestamp}.{payload_bytes.decode()}"
    import hashlib
    import hmac

    secret = webhook_secret.lstrip("whsec_")
    # Stripe uses the raw bytes after "whsec_" as the secret
    # The actual secret is base64-encoded in whsec_ format
    import base64
    try:
        secret_bytes = base64.b64decode(secret)
    except Exception:
        secret_bytes = webhook_secret.encode()

    mac = hmac.new(secret_bytes, signed_payload.encode(), hashlib.sha256).hexdigest()
    sig_header = f"t={timestamp},v1={mac}"

    return payload_bytes, sig_header


def post_webhook(client: httpx.Client, payload: bytes, sig_header: str) -> dict:
    """POST signed webhook payload to the backend."""
    resp = client.post(
        f"{BASE_URL}/webhooks/stripe",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "stripe-signature": sig_header,
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_order(client: httpx.Client, order_id: str) -> dict:
    """GET /orders/{order_id}."""
    resp = client.get(f"{BASE_URL}/orders/{order_id}")
    resp.raise_for_status()
    return resp.json()


def run_tests() -> None:
    settings = get_settings()

    # Validate prerequisites
    test_key = settings.stripe_secret_key_test
    webhook_secret = settings.stripe_webhook_secret_test

    if not test_key or not test_key.startswith("sk_test_"):
        logger.error("STRIPE_SECRET_KEY_TEST must be set to a sk_test_... value")
        sys.exit(1)

    if not webhook_secret or not webhook_secret.startswith("whsec_"):
        logger.error(
            "STRIPE_WEBHOOK_SECRET_TEST must be set. "
            "Run ./scripts/stripe_dev.sh, copy the whsec_... value, and set it in .env."
        )
        sys.exit(1)

    stripe.api_key = test_key

    logger.info("=== Autopilot Stripe E2E Test ===")
    logger.info("Backend: %s", BASE_URL)
    logger.info("Stripe key: %s...", test_key[:20])

    with httpx.Client(timeout=30) as client:
        # ------------------------------------------------------------------
        # Test A: checkout.session.completed → order "completed"
        # ------------------------------------------------------------------
        logger.info("\n--- Test A: checkout.session.completed ---")

        logger.info("Step 1: Fetching TestBot product ID...")
        product_id = get_testbot_product_id(client)
        logger.info("  TestBot id: %s", product_id)

        logger.info("Step 2: Creating checkout session...")
        session_data = create_session(client, product_id)
        logger.info("  order_id: %s", session_data["order_id"])
        logger.info("  stripe_session_id: %s", session_data["stripe_session_id"])
        logger.info("  checkout_url: %s", session_data.get("checkout_url", "")[:60] + "...")

        logger.info("Step 3: Verifying session exists in Stripe...")
        stripe_session = stripe.checkout.Session.retrieve(session_data["stripe_session_id"])
        assert stripe_session.id == session_data["stripe_session_id"], "Session ID mismatch"
        logger.info("  ✅ Stripe session confirmed: %s", stripe_session.id)

        logger.info("Step 4: Constructing signed webhook payload...")
        payload, sig_header = build_signed_webhook(
            "checkout.session.completed", session_data, webhook_secret
        )
        logger.info("  Payload size: %d bytes", len(payload))

        logger.info("Step 5: Posting webhook to backend...")
        webhook_resp = post_webhook(client, payload, sig_header)
        logger.info("  Webhook response: %s", webhook_resp)

        logger.info("Step 6: Verifying order status...")
        order = get_order(client, session_data["order_id"])
        status = order.get("status")
        if status == "completed":
            logger.info("  ✅ Order status: completed")
        else:
            logger.error("  ❌ Expected 'completed', got '%s'", status)
            sys.exit(1)

        # ------------------------------------------------------------------
        # Test B: checkout.session.expired → order "cancelled"
        # ------------------------------------------------------------------
        logger.info("\n--- Test B: checkout.session.expired ---")

        logger.info("Step 1: Creating second checkout session...")
        session_data_b = create_session(client, product_id)
        logger.info("  order_id: %s", session_data_b["order_id"])

        logger.info("Step 2: Triggering checkout.session.expired webhook...")
        payload_b, sig_header_b = build_signed_webhook(
            "checkout.session.expired", session_data_b, webhook_secret
        )
        post_webhook(client, payload_b, sig_header_b)

        logger.info("Step 3: Verifying order status...")
        order_b = get_order(client, session_data_b["order_id"])
        status_b = order_b.get("status")
        if status_b == "cancelled":
            logger.info("  ✅ Expired order status: cancelled")
        else:
            logger.error("  ❌ Expected 'cancelled', got '%s'", status_b)
            sys.exit(1)

    logger.info("\n=== All tests passed ✅ ===")


if __name__ == "__main__":
    run_tests()

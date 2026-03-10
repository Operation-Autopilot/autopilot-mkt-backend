"""Webhook API routes for external service integrations."""

import logging
import threading
import time

from fastapi import APIRouter, HTTPException, Request, status

from src.services.checkout_service import CheckoutService
from src.services.gynger_service import GyngerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Webhook replay prevention — in-memory event ID tracking
# NOTE: This dedup is per-worker only. For multi-worker deployments,
# use --workers 1 OR replace with Redis/DB-backed dedup.
# See: https://stripe.com/docs/webhooks/best-practices#duplicate-events
_processed_events: dict[str, float] = {}  # event_id -> timestamp
_processed_events_lock = threading.Lock()
_EVENT_TTL = 3600  # 1 hour


def _warn_if_multiworker() -> None:
    """Emit a startup warning if running under a multi-worker process manager.

    Gunicorn sets the ``WEB_CONCURRENCY`` environment variable (and forks
    worker processes), uvicorn ``--workers N`` sets ``UVICORN_WORKERS``.
    We detect these to alert operators that in-memory dedup is unsafe.
    """
    import os

    web_concurrency = int(os.environ.get("WEB_CONCURRENCY", "1"))
    uvicorn_workers = int(os.environ.get("UVICORN_WORKERS", "1"))
    workers = max(web_concurrency, uvicorn_workers)
    if workers > 1:
        logger.warning(
            "WEBHOOK DEDUP WARNING: %d workers detected but deduplication is "
            "in-memory (per-worker). Stripe may deliver duplicate events to "
            "different workers and both will be processed. Use --workers 1 or "
            "switch to Redis/DB-backed dedup to fix this.",
            workers,
        )


# Emit a warning at import time (once per worker process) if multiple workers
# are configured, since the in-memory dedup dict is not shared across workers.
_warn_if_multiworker()


@router.post(
    "/stripe",
    status_code=status.HTTP_200_OK,
    summary="Handle Stripe webhooks",
    description="Receives and processes Stripe webhook events. Requires valid signature.",
)
async def stripe_webhook(request: Request) -> dict[str, str]:
    """Handle Stripe webhook events.

    This endpoint receives webhook events from Stripe and processes them.
    The Stripe signature is verified before processing.

    Handles:
    - checkout.session.completed: Updates order to completed (card) or payment_pending (ACH)
    - checkout.session.async_payment_succeeded: ACH payment settled, marks order completed
    - checkout.session.async_payment_failed: ACH payment failed, marks order cancelled
    - checkout.session.expired: Updates order to cancelled status

    Args:
        request: FastAPI request object for reading raw body and headers.

    Returns:
        dict: Acknowledgment message.

    Raises:
        HTTPException: 400 if signature is invalid.
    """
    # Get raw body for signature verification
    payload = await request.body()

    # Get Stripe signature header
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        logger.error("Missing Stripe-Signature header in webhook request")
        logger.debug("Request headers: %s", dict(request.headers))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    logger.info("Received webhook with signature header (length: %d)", len(sig_header))
    logger.debug("Payload size: %d bytes", len(payload))

    service = CheckoutService()

    try:
        # Verify signature and get event (tries both production and test secrets)
        event, is_test_mode = service.verify_webhook_signature(payload, sig_header)
    except ValueError as e:
        logger.error("Invalid webhook signature: %s", str(e))
        logger.debug("Signature header: %s...", sig_header[:50] if sig_header else "None")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        ) from e

    # Replay prevention: check if event was already processed
    event_id = event.get("id")
    if event_id:
        now = time.time()
        with _processed_events_lock:
            # Clean up expired entries
            expired = [k for k, v in _processed_events.items() if now - v > _EVENT_TTL]
            for k in expired:
                del _processed_events[k]

            if event_id in _processed_events:
                logger.info("Duplicate webhook event %s, skipping", event_id)
                return {"status": "already_processed"}
            _processed_events[event_id] = now

    # Process the event
    event_type = event.get("type", "")
    logger.info(
        "Processing Stripe webhook event: %s (test_mode=%s)",
        event_type,
        is_test_mode,
    )

    if event_type == "checkout.session.completed":
        await service.handle_checkout_completed(event)
        logger.info("Processed checkout.session.completed")

    elif event_type == "checkout.session.async_payment_succeeded":
        await service.handle_async_payment_succeeded(event)
        logger.info("Processed checkout.session.async_payment_succeeded")

    elif event_type == "checkout.session.async_payment_failed":
        await service.handle_async_payment_failed(event)
        logger.info("Processed checkout.session.async_payment_failed")

    elif event_type == "checkout.session.expired":
        await service.handle_checkout_expired(event)
        logger.info("Processed checkout.session.expired")

    else:
        # Log unhandled events but return 200 to acknowledge receipt
        logger.debug("Unhandled webhook event type: %s", event_type)

    # Always return 200 OK to acknowledge receipt (idempotent)
    return {"status": "received"}


@router.post(
    "/gynger",
    status_code=status.HTTP_200_OK,
    summary="Handle Gynger webhooks",
    description="Receives and processes Gynger financing webhook events. Requires valid signature.",
)
async def gynger_webhook(request: Request) -> dict[str, str]:
    """Handle Gynger webhook events.

    Processes Gynger financing application status updates.

    Handles:
    - application.approved: Updates order to completed status
    - application.rejected: Updates order to cancelled status
    - application.pending: Logged only (no action needed)

    Args:
        request: FastAPI request object.

    Returns:
        dict: Acknowledgment message.

    Raises:
        HTTPException: 400 if signature is invalid.
    """
    # Get raw body for signature verification
    payload = await request.body()

    # TODO: confirm header name with Gynger docs
    sig_header = request.headers.get("x-gynger-signature") or request.headers.get("x-signature")
    if not sig_header:
        logger.error("Missing Gynger signature header in webhook request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing webhook signature header",
        )

    service = GyngerService()

    try:
        event = service.verify_webhook_signature(payload, sig_header)
    except ValueError as e:
        logger.error("Invalid Gynger webhook signature: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        ) from e

    # Replay prevention using same in-memory pattern as Stripe webhook handler
    event_id = event.get("id")
    if event_id:
        now = time.time()
        with _processed_events_lock:
            expired = [k for k, v in _processed_events.items() if now - v > _EVENT_TTL]
            for k in expired:
                del _processed_events[k]

            if event_id in _processed_events:
                logger.info("Duplicate Gynger webhook event %s, skipping", event_id)
                return {"status": "already_processed"}
            _processed_events[event_id] = now

    event_type = event.get("type", "")
    logger.info("Processing Gynger webhook event: %s", event_type)

    # TODO: confirm event type names with Gynger docs
    if event_type == "application.approved":
        await service.handle_application_approved(event)
        logger.info("Processed application.approved")

    elif event_type == "application.rejected":
        await service.handle_application_rejected(event)
        logger.info("Processed application.rejected")

    elif event_type == "application.pending":
        # No action needed — just acknowledge
        logger.info("Gynger application in pending state (no action required)")

    else:
        logger.debug("Unhandled Gynger webhook event type: %s", event_type)

    return {"status": "received"}

"""Gynger B2B financing service.

Handles creating financing applications on Gynger's platform and processing
webhook notifications when applications are approved or rejected.

NOTE: Gynger's vendor API requires login to access full documentation.
      Fields and endpoint paths marked with `# TODO: confirm with Gynger docs`
      will need one-time verification once credentials are obtained.
      The integration assumes standard B2B financing REST patterns.
"""

import asyncio
import hashlib
import hmac
import logging
from typing import Any
from uuid import UUID

import httpx

from src.core.config import get_settings
from src.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class GyngerService:
    """Service for Gynger embedded financing integration."""

    def __init__(self) -> None:
        """Initialize Gynger service with Supabase client and settings."""
        self.client = get_supabase_client()
        self.settings = get_settings()

    async def _execute_sync(self, query: Any) -> Any:
        """Run synchronous Supabase query in thread pool to avoid blocking event loop."""
        return await asyncio.to_thread(query.execute)

    async def create_financing_application(
        self,
        robot: dict,
        amount_cents: int,
        customer_email: str | None,
        success_url: str,
        cancel_url: str,
        order_id: str,
    ) -> dict:
        """Create a Gynger financing application for a robot purchase.

        Calls POST /applications on the Gynger vendor API to initiate a
        financing application and returns a URL to redirect the user to.

        Args:
            robot: Robot catalog row (must have at least 'name' and 'id').
            amount_cents: Total financing amount in cents.
            customer_email: Customer email (optional, pre-fills Gynger form).
            success_url: URL Gynger redirects to on approval.
            cancel_url: URL Gynger redirects to on cancellation.
            order_id: Internal order UUID (stored as metadata on the application).

        Returns:
            dict with keys:
                application_id (str): Gynger's application reference ID.
                application_url (str): URL to redirect the user to Gynger.

        Raises:
            ValueError: If Gynger API key is not configured.
            httpx.HTTPStatusError: If Gynger API returns an error response.
        """
        api_key = self.settings.gynger_api_key
        if not api_key:
            raise ValueError(
                "Gynger is not configured. Please set GYNGER_API_KEY environment variable."
            )

        base_url = self.settings.gynger_api_url

        # TODO: confirm endpoint path with Gynger docs
        # TODO: confirm request body field names with Gynger docs
        request_body = {
            "amount_cents": amount_cents,
            "currency": "usd",
            "customer_email": customer_email,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "order_id": order_id,
                "robot_id": str(robot.get("id", "")),
                "robot_name": robot.get("name", ""),
                "source": "autopilot_marketplace",
            },
        }

        logger.info(
            "Creating Gynger financing application for order %s (amount: $%.2f)",
            order_id,
            amount_cents / 100,
        )

        async with httpx.AsyncClient(timeout=30) as http_client:
            response = await http_client.post(
                f"{base_url}/applications",  # TODO: confirm endpoint
                json=request_body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "X-Autopilot-Source": "marketplace",
                },
            )
            response.raise_for_status()
            data = response.json()

        # TODO: confirm response field names with Gynger docs
        application_id = data.get("application_id") or data.get("id")
        application_url = data.get("application_url") or data.get("url")

        if not application_id or not application_url:
            raise ValueError(
                f"Unexpected Gynger API response: missing application_id or application_url. "
                f"Response keys: {list(data.keys())}"
            )

        logger.info(
            "Gynger application created: id=%s for order %s",
            application_id,
            order_id,
        )

        return {
            "application_id": application_id,
            "application_url": application_url,
        }

    def verify_webhook_signature(self, payload: bytes, sig_header: str) -> dict:
        """Validate Gynger webhook signature and parse the event.

        Assumes HMAC-SHA256 signed with GYNGER_WEBHOOK_SECRET, using a
        'X-Gynger-Signature' or similar header format.

        NOTE: Signature algorithm and header format should be confirmed with
        Gynger docs once credentials are available.

        Args:
            payload: Raw request body bytes.
            sig_header: Value of the signature header from the webhook request.

        Returns:
            dict: Parsed event payload.

        Raises:
            ValueError: If webhook secret is not configured or signature is invalid.
        """
        webhook_secret = self.settings.gynger_webhook_secret
        if not webhook_secret:
            raise ValueError(
                "GYNGER_WEBHOOK_SECRET is not configured. Cannot verify webhook signature."
            )

        # TODO: confirm exact signature format with Gynger docs
        # Assumed: HMAC-SHA256 hex digest of raw payload body
        expected_sig = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # The header may be a plain hex digest or "sha256=<hex>" format
        # Support both
        provided_sig = sig_header.lstrip("sha256=")

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise ValueError("Invalid Gynger webhook signature")

        import json

        try:
            event = json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Gynger webhook payload: {e}") from e

        return event

    async def handle_application_approved(self, event: dict) -> dict:
        """Process a Gynger 'application.approved' webhook event.

        Updates the associated order status to 'completed' and stores
        the Gynger application ID on the order row.

        Args:
            event: Parsed Gynger webhook event dict.

        Returns:
            dict: Updated order row.

        Raises:
            ValueError: If order cannot be found from event data.
        """
        # TODO: confirm event data structure with Gynger docs
        event_data = event.get("data", event)
        application_id = event_data.get("application_id") or event_data.get("id")
        metadata = event_data.get("metadata", {})
        order_id = metadata.get("order_id")

        if not order_id:
            raise ValueError(
                f"Cannot process application.approved: missing order_id in metadata. "
                f"event_data keys: {list(event_data.keys())}"
            )

        logger.info(
            "Processing Gynger application.approved: application_id=%s order_id=%s",
            application_id,
            order_id,
        )

        import datetime

        update_query = (
            self.client.table("orders")
            .update(
                {
                    "status": "completed",
                    "gynger_application_id": application_id,
                    "payment_provider": "gynger",
                    "completed_at": datetime.datetime.utcnow().isoformat(),
                }
            )
            .eq("id", order_id)
        )
        result = await self._execute_sync(update_query)

        if not result.data:
            raise ValueError(f"Order {order_id} not found or update failed")

        logger.info("Order %s marked as completed via Gynger financing", order_id)
        return result.data[0]

    async def handle_application_rejected(self, event: dict) -> dict:
        """Process a Gynger 'application.rejected' webhook event.

        Updates the associated order status to 'cancelled'.

        Args:
            event: Parsed Gynger webhook event dict.

        Returns:
            dict: Updated order row.

        Raises:
            ValueError: If order cannot be found from event data.
        """
        # TODO: confirm event data structure with Gynger docs
        event_data = event.get("data", event)
        application_id = event_data.get("application_id") or event_data.get("id")
        metadata = event_data.get("metadata", {})
        order_id = metadata.get("order_id")

        if not order_id:
            raise ValueError(
                f"Cannot process application.rejected: missing order_id in metadata. "
                f"event_data keys: {list(event_data.keys())}"
            )

        logger.info(
            "Processing Gynger application.rejected: application_id=%s order_id=%s",
            application_id,
            order_id,
        )

        update_query = (
            self.client.table("orders")
            .update(
                {
                    "status": "cancelled",
                    "gynger_application_id": application_id,
                    "payment_provider": "gynger",
                }
            )
            .eq("id", order_id)
        )
        result = await self._execute_sync(update_query)

        if not result.data:
            raise ValueError(f"Order {order_id} not found or update failed")

        logger.info("Order %s marked as cancelled (Gynger application rejected)", order_id)
        return result.data[0]

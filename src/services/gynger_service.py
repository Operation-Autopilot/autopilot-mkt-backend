"""Gynger B2B financing service.

Handles creating checkout sessions on Gynger's platform and processing
webhook notifications when financing offers are approved or declined.

API reference: https://api.gynger.io/v1
Auth: Authorization: {GYNGER_API_KEY}  (no "Bearer" prefix)

Webhook verification: Gynger sends Authorization: {webhook_secret}
where webhook_secret is the 'secret' returned when registering the webhook.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.config import get_settings
from src.core.supabase import get_supabase_client
from src.services.base_service import BaseService

logger = logging.getLogger(__name__)

# Offer statuses that mean financing was approved
_APPROVED_STATUSES = {"ACTIVE", "ACCEPTED", "PAID"}
# Offer statuses that mean financing was declined
_DECLINED_STATUSES = {"DECLINED", "CANCELED"}


class GyngerService(BaseService):
    """Service for Gynger embedded financing integration."""

    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.settings = get_settings()

    def _headers(self) -> dict[str, str]:
        """Build Gynger API request headers.

        Note: Gynger uses plain Authorization without a 'Bearer' prefix.
        """
        return {
            "Authorization": self.settings.gynger_api_key,
            "Content-Type": "application/json",
        }

    async def create_checkout_session(
        self,
        robot: dict,
        amount_cents: int,
        customer_email: str | None,
        order_id: str,
    ) -> dict:
        """Create a Gynger checkout session for a robot purchase.

        Calls POST /v1/checkout/sessions and constructs the buyer redirect URL
        from the returned session ID (the URL is not included in the response).

        Args:
            robot: Robot catalog row (must have 'name').
            amount_cents: Total financing amount in cents.
            customer_email: Optional — pre-fills the Gynger form.
            order_id: Internal order UUID (stored on the order row for webhook lookup).

        Returns:
            dict with keys:
                application_id (str): Gynger session ID (gyn_sess_...).
                application_url (str): URL to redirect the user to Gynger checkout.

        Raises:
            ValueError: If Gynger API key is not configured or response is unexpected.
            httpx.HTTPStatusError: If Gynger API returns an error response.
        """
        if not self.settings.gynger_api_key:
            raise ValueError(
                "Gynger is not configured. Please set GYNGER_API_KEY environment variable."
            )

        product_description = f"{robot.get('name', 'Robot')} — Autopilot Marketplace"

        request_body: dict[str, Any] = {
            "amount": amount_cents,
            "productDescription": product_description[:255],
            "contractType": "SINGLE",
            "autoBillCreation": True,
        }
        if customer_email:
            request_body["buyerEmail"] = customer_email

        logger.info(
            "Creating Gynger checkout session for order %s (amount: $%.2f)",
            order_id,
            amount_cents / 100,
        )

        async with httpx.AsyncClient(timeout=30) as http_client:
            response = await http_client.post(
                f"{self.settings.gynger_api_url}/checkout/sessions",
                json=request_body,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        session_id = data.get("id")
        if not session_id:
            raise ValueError(
                f"Unexpected Gynger API response: missing 'id'. Response keys: {list(data.keys())}"
            )

        # The buyer redirect URL is not returned by the API — construct it.
        checkout_base = self.settings.gynger_checkout_base_url.rstrip("/")
        application_url = f"{checkout_base}/{session_id}"

        logger.info("Gynger checkout session created: id=%s for order %s", session_id, order_id)

        return {
            "application_id": session_id,
            "application_url": application_url,
        }

    def verify_webhook_secret(self, auth_header: str) -> None:
        """Verify a Gynger webhook request by comparing the Authorization header.

        Gynger sends the webhook secret directly as the Authorization header value
        (no 'Bearer' prefix, no HMAC — just a direct string comparison).

        Args:
            auth_header: Value of the Authorization header from the webhook request.

        Raises:
            ValueError: If webhook secret is not configured or the header doesn't match.
        """
        webhook_secret = self.settings.gynger_webhook_secret
        if not webhook_secret:
            raise ValueError(
                "GYNGER_WEBHOOK_SECRET is not configured. Cannot verify webhook."
            )
        if auth_header != webhook_secret:
            raise ValueError("Invalid Gynger webhook Authorization header")

    async def handle_offer_status_updated(self, event: dict) -> dict | None:
        """Process a Gynger 'offer.status.updated' webhook event.

        Maps offer status to our order status:
            ACTIVE / ACCEPTED / PAID  → completed
            DECLINED / CANCELED       → cancelled
            VIEWED / CREATED          → no change (informational)

        Looks up the order by gynger_application_id = event.data.checkoutSessionId.

        Returns:
            Updated order row, or None if no action was taken.
        """
        event_data = event.get("data", {})
        checkout_session_id = event_data.get("checkoutSessionId")
        offer_status = event_data.get("status", "")
        offer_id = event_data.get("id", "")

        if not checkout_session_id:
            raise ValueError(
                f"offer.status.updated missing checkoutSessionId. "
                f"event_data keys: {list(event_data.keys())}"
            )

        logger.info(
            "Gynger offer.status.updated: offer=%s session=%s status=%s",
            offer_id,
            checkout_session_id,
            offer_status,
        )

        if offer_status in _APPROVED_STATUSES:
            new_order_status = "completed"
            extra: dict[str, Any] = {"completed_at": datetime.now(timezone.utc).isoformat()}
        elif offer_status in _DECLINED_STATUSES:
            new_order_status = "cancelled"
            extra = {}
        else:
            logger.info("Offer status %s is informational — no order update needed", offer_status)
            return None

        update_payload: dict[str, Any] = {
            "status": new_order_status,
            "payment_provider": "gynger",
            **extra,
        }
        query = (
            self.client.table("orders")
            .update(update_payload)
            .eq("gynger_application_id", checkout_session_id)
        )
        result = await self._execute_sync(query)

        if not result.data:
            raise ValueError(
                f"No order found with gynger_application_id={checkout_session_id}"
            )

        order = result.data[0]
        logger.info(
            "Order %s marked as %s (Gynger offer %s)",
            order.get("id"),
            new_order_status,
            offer_status,
        )

        # HubSpot: move Lead deal to Closed Won (fire-and-forget)
        if new_order_status == "completed":
            try:
                from src.core.config import get_settings as _gs
                from src.services.hubspot_service import HubSpotService
                if _gs().hubspot_access_token:
                    hs_deal_id = (order.get("metadata") or {}).get("hubspot_deal_id")
                    if hs_deal_id:
                        asyncio.create_task(
                            HubSpotService().on_deal_closed(
                                deal_id=hs_deal_id,
                                amount_usd=order.get("total_cents", 0) / 100,
                            )
                        )
            except Exception:
                logger.exception("HubSpot task creation failed after Gynger approval (non-fatal)")

            # Send order confirmation email (fire-and-forget)
            customer_email = order.get("customer_email")
            if customer_email:
                try:
                    from src.services.email_service import EmailService
                    line_items = order.get("line_items") or []
                    robot_name = line_items[0]["product_name"] if line_items else "Robot"
                    total_cents = order.get("total_cents", 0)
                    amount_display = f"${total_cents / 100:,.0f}"
                    tsd = ""
                    sid = order.get("session_id")
                    if sid:
                        try:
                            sr = await self._execute_sync(
                                self.client.table("sessions")
                                .select("greenlight")
                                .eq("id", sid)
                                .maybe_single()
                            )
                            if sr.data:
                                tsd = (sr.data.get("greenlight") or {}).get("target_start_date") or ""
                        except Exception:
                            pass
                    asyncio.create_task(
                        EmailService().send_order_confirmation_email(
                            to_email=customer_email,
                            robot_name=robot_name,
                            amount_display=amount_display,
                            payment_type="gynger",
                            order_id=str(order.get("id", "")),
                            target_start_date=tsd or None,
                        )
                    )
                except Exception:
                    logger.debug("Order confirmation email task creation failed (non-fatal)")

        return order

    async def handle_session_status_updated(self, event: dict) -> None:
        """Process a Gynger 'checkout.session.status.updated' webhook event.

        OFFER_CREATED: session has moved to offer stage — informational only.
        EXPIRED: session expired — cancel the pending order if still pending.
        """
        event_data = event.get("data", {})
        session_id = event_data.get("id", "")
        session_status = event_data.get("status", "")

        logger.info(
            "Gynger checkout.session.status.updated: session=%s status=%s",
            session_id,
            session_status,
        )

        if session_status == "EXPIRED" and session_id:
            query = (
                self.client.table("orders")
                .update({"status": "cancelled"})
                .eq("gynger_application_id", session_id)
                .eq("status", "pending")
            )
            result = await self._execute_sync(query)
            if result.data:
                logger.info(
                    "Order cancelled due to expired Gynger session %s", session_id
                )

    def parse_webhook_payload(self, payload: bytes) -> dict:
        """Parse raw webhook payload bytes into a dict.

        Raises:
            ValueError: If payload is not valid JSON.
        """
        try:
            return json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Gynger webhook payload: {e}") from e

"""Checkout and order business logic service."""

import asyncio
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import stripe

from src.core.config import get_settings
from src.core.stripe import get_stripe, get_stripe_api_key
from src.core.supabase import get_supabase_client
from src.services.base_service import BaseService
from src.services.robot_catalog_service import RobotCatalogService

logger = logging.getLogger(__name__)


def _answer_val(answers: dict, key: str) -> str:
    """Extract the value string from a discovery answer dict entry.

    Handles both `{value: "..."}` dicts and plain strings.
    Returns empty string if key is missing or value is falsy.
    """
    answer = answers.get(key)
    if answer is None:
        return ""
    if isinstance(answer, dict):
        return str(answer.get("value", "")) if answer.get("value") else ""
    return str(answer) if answer else ""

ALLOWED_REDIRECT_DOMAINS = {
    "localhost",
    "tryautopilot.com",
    "autopilot-marketplace-discovery-to.vercel.app",
}


class CheckoutService(BaseService):
    """Service for Stripe checkout and order management."""

    def __init__(self) -> None:
        """Initialize checkout service with clients."""
        self.client = get_supabase_client()
        self.stripe = get_stripe()
        self.settings = get_settings()
        self.robot_service = RobotCatalogService()

    def _validate_redirect_url(self, url: str) -> str:
        """Validate that a redirect URL uses an allowed domain to prevent open redirects.

        Args:
            url: The redirect URL to validate.

        Returns:
            The validated URL (unchanged).

        Raises:
            ValueError: If the URL's domain is not in ALLOWED_REDIRECT_DOMAINS.
        """
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname or ""
        if not any(hostname == d or hostname.endswith("." + d) for d in ALLOWED_REDIRECT_DOMAINS):
            raise ValueError(f"Redirect URL domain not allowed: {hostname}")
        return url

    async def cleanup_orphaned_orders(self, max_age_minutes: int = 60) -> int:
        """
        Cancel orders that have been in 'pending' state without a Stripe session ID
        for longer than max_age_minutes. Returns number of orders cleaned up.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).isoformat()
        query = (
            self.client.table("orders")
            .update({"status": "cancelled", "metadata": {"cancellation_reason": "orphaned_pending"}})
            .eq("status", "pending")
            .is_("stripe_checkout_session_id", "null")
            .lt("created_at", cutoff)
        )
        result = await self._execute_sync(query)
        count = len(result.data) if result.data else 0
        if count > 0:
            logger.warning("Cleaned up %d orphaned pending orders", count)
        return count

    async def create_checkout_session(
        self,
        product_id: UUID,
        success_url: str,
        cancel_url: str,
        profile_id: UUID | None = None,
        session_id: UUID | None = None,
        customer_email: str | None = None,
        is_test_account: bool | None = None,
        payment_type: str = "lease",
    ) -> dict[str, Any]:
        """Create a Stripe Checkout Session and pending order.

        Args:
            product_id: Robot product UUID.
            success_url: URL to redirect after successful checkout.
            cancel_url: URL to redirect if checkout is cancelled.
            profile_id: Optional profile ID for authenticated users.
            session_id: Optional session ID for anonymous users.
            customer_email: Optional pre-fill email.
            is_test_account: If True, use Stripe test mode. If None, auto-detect from environment.

        Returns:
            dict: Contains checkout_url, order_id, stripe_session_id, is_test_mode.

        Raises:
            ValueError: If product not found or inactive, or Stripe not configured.
            Exception: If Stripe API call fails.
        """
        # Clean up any orphaned orders from previous failed attempts (best-effort)
        try:
            await self.cleanup_orphaned_orders()
        except Exception:
            pass  # Non-critical, don't fail the checkout

        # Validate redirect URLs to prevent open redirect attacks
        self._validate_redirect_url(success_url)
        self._validate_redirect_url(cancel_url)

        # Resolve test mode: explicit flag > environment-based detection
        settings = get_settings()
        use_test_mode = is_test_account if is_test_account is not None else settings.is_stripe_test_mode

        # Get appropriate Stripe API key
        stripe_api_key = get_stripe_api_key(use_test_mode=use_test_mode)
        if not stripe_api_key:
            raise ValueError("Stripe is not configured. Please set STRIPE_SECRET_KEY environment variable.")

        # Get product with appropriate Stripe IDs (test or production)
        robot = await self.robot_service.get_robot_with_stripe_ids(product_id, use_test_mode=use_test_mode)
        if not robot:
            raise ValueError("Product not found")

        if not robot.get("active", False):
            raise ValueError("Product is no longer available")

        # Calculate total and select price based on payment type
        if payment_type == "purchase":
            price_value = robot.get("purchase_price", 0)
            if not price_value:
                raise ValueError("Purchase price is not configured for this product")
            stripe_price_id = None  # Will use price_data inline instead
        else:
            if not robot.get("stripe_lease_price_id"):
                raise ValueError("Robot is not available for checkout — missing price configuration")
            price_value = robot.get("monthly_lease", 0)
            stripe_price_id = robot.get("stripe_lease_price_id", "")

        if isinstance(price_value, str):
            price_value = Decimal(price_value)
        total_cents = int(price_value * 100)

        # Create line items for the order
        line_items = [
            {
                "product_id": str(product_id),
                "product_name": robot["name"],
                "quantity": 1,
                "unit_amount_cents": total_cents,
                "stripe_price_id": stripe_price_id,
            }
        ]

        # Create pending order first
        order_data = {
            "profile_id": str(profile_id) if profile_id else None,
            "session_id": str(session_id) if session_id else None,
            "stripe_checkout_session_id": None,  # Will update after Stripe call
            "status": "pending",
            "payment_type": payment_type,
            "line_items": line_items,
            "total_cents": total_cents,
            "currency": "usd",
            "customer_email": customer_email,
            "metadata": {},
        }

        order_query = self.client.table("orders").insert(order_data)
        order_response = await self._execute_sync(order_query)
        if not order_response.data:
            raise ValueError("Database operation returned no data")
        order = order_response.data[0]
        order_id = order["id"]

        # Resolve customer email from profile if not provided (defense in depth for HubSpot)
        if not customer_email and profile_id:
            try:
                profile_row = await self._execute_sync(
                    self.client.table("profiles")
                    .select("email")
                    .eq("id", str(profile_id))
                    .maybe_single()
                )
                if profile_row.data:
                    customer_email = profile_row.data.get("email")
            except Exception:
                logger.debug("Could not resolve email from profile %s", profile_id)

        # Load session data for HubSpot enrichment
        session_answers: dict = {}
        target_start_date = ""
        if session_id:
            try:
                sess_row = await self._execute_sync(
                    self.client.table("sessions")
                    .select("answers, greenlight")
                    .eq("id", str(session_id))
                    .maybe_single()
                )
                if sess_row.data:
                    session_answers = sess_row.data.get("answers") or {}
                    gl = sess_row.data.get("greenlight") or {}
                    target_start_date = gl.get("target_start_date") or ""
            except Exception:
                logger.debug("Could not load session %s for HubSpot enrichment", session_id)

        # HubSpot: create Lead deal at checkout initiation (awaited so we get the deal_id back)
        hubspot_deal_id: str | None = None
        if self.settings.hubspot_access_token and customer_email:
            try:
                from src.services.hubspot_service import HubSpotService
                company_name: str | None = None
                if profile_id:
                    co = await self._execute_sync(
                        self.client.table("companies")
                        .select("name")
                        .eq("owner_id", str(profile_id))
                        .maybe_single()
                    )
                    if co.data:
                        company_name = co.data.get("name")
                hubspot_deal_id = await HubSpotService().on_checkout_initiated(
                    email=customer_email,
                    company_name=company_name,
                    robot_name=robot["name"],
                    amount_usd=total_cents / 100,
                    order_id=str(order_id),
                    payment_type=payment_type,
                    payment_provider="stripe",
                    sqft=_answer_val(session_answers, "sqft"),
                    monthly_spend=_answer_val(session_answers, "monthly_spend"),
                    company_type=_answer_val(session_answers, "company_type"),
                    cleaning_method=_answer_val(session_answers, "method"),
                    cleaning_frequency=_answer_val(session_answers, "frequency"),
                    target_start_date=target_start_date,
                )
            except Exception:
                logger.exception("HubSpot checkout deal creation failed for order %s (non-fatal)", order_id)

        try:
            # Create Stripe Checkout Session
            stripe_mode = "payment" if payment_type == "purchase" else "subscription"
            checkout_params: dict[str, Any] = {
                "mode": stripe_mode,
                "payment_method_types": ["card", "us_bank_account"],
                "line_items": [
                    {
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": total_cents,
                            "product_data": {"name": robot["name"]},
                        },
                        "quantity": 1,
                    } if payment_type == "purchase" else {
                        "price": stripe_price_id,
                        "quantity": 1,
                    }
                ],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {
                    "order_id": str(order_id),
                    "session_id": str(session_id) if session_id else "",
                    "is_test_mode": "true" if use_test_mode else "false",
                    "payment_type": payment_type,
                },
            }

            # For Stripe Accounts V2 in test mode, we need to create a customer first
            # In production mode, Stripe handles customer creation automatically
            if customer_email:
                # Create or find existing customer
                existing_customers = await asyncio.to_thread(
                    self.stripe.Customer.list, email=customer_email, limit=1, api_key=stripe_api_key
                )
                if existing_customers.data:
                    checkout_params["customer"] = existing_customers.data[0].id
                else:
                    customer = await asyncio.to_thread(
                        self.stripe.Customer.create,
                        email=customer_email,
                        api_key=stripe_api_key,
                    )
                    checkout_params["customer"] = customer.id
            else:
                # Create anonymous customer for test mode compatibility
                customer = await asyncio.to_thread(
                    self.stripe.Customer.create,
                    api_key=stripe_api_key,
                )
                checkout_params["customer"] = customer.id

            stripe_session = await asyncio.to_thread(
                self.stripe.checkout.Session.create,
                **checkout_params,
                api_key=stripe_api_key,
            )

            # Update order with Stripe session ID, test mode flag, and HubSpot deal ID
            existing_metadata = order.get("metadata", {}) or {}
            merged_metadata = {**existing_metadata, "is_test_mode": use_test_mode}
            if hubspot_deal_id:
                merged_metadata["hubspot_deal_id"] = hubspot_deal_id
            query = self.client.table("orders").update({
                "stripe_checkout_session_id": stripe_session.id,
                "metadata": merged_metadata,
            }).eq("id", order_id)
            await self._execute_sync(query)

            return {
                "checkout_url": stripe_session.url,
                "order_id": UUID(order_id),
                "stripe_session_id": stripe_session.id,
                "is_test_mode": use_test_mode,
            }

        except stripe.error.StripeError as e:
            # Clean up the order if Stripe fails
            logger.error("Stripe error creating checkout session: %s", str(e))
            query = self.client.table("orders").update(
                {"status": "cancelled"}
            ).eq("id", order_id)
            await self._execute_sync(query)
            raise

    async def handle_checkout_completed(self, event: dict[str, Any]) -> dict[str, Any]:
        """Process checkout.session.completed webhook event.

        For card payments (payment_status="paid"), marks the order as completed immediately.
        For ACH/bank transfers (payment_status="unpaid"), marks the order as payment_pending
        since funds take ~4 business days to settle.

        Args:
            event: Stripe webhook event data.

        Returns:
            dict: Updated order data.
        """
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")

        if not order_id:
            logger.warning("Webhook missing order_id in metadata: %s", session.get("id"))
            return {}

        customer_email = None
        customer_details = session.get("customer_details", {})
        if customer_details:
            customer_email = customer_details.get("email")

        payment_status = session.get("payment_status", "")
        metadata = session.get("metadata", {})
        is_purchase = metadata.get("payment_type") == "purchase"

        # For purchases, use payment_intent; for leases, use subscription
        stripe_ref_id = session.get("payment_intent") if is_purchase else session.get("subscription")

        if payment_status == "paid":
            # Card or instant payment — funds available immediately
            update_data: dict[str, Any] = {
                "status": "completed",
                "stripe_customer_id": session.get("customer"),
                "stripe_subscription_id": stripe_ref_id,
                "customer_email": customer_email,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            log_status = "completed"
        else:
            # ACH / delayed payment — authorized but funds not yet settled
            update_data = {
                "status": "payment_pending",
                "stripe_customer_id": session.get("customer"),
                "stripe_subscription_id": stripe_ref_id,
                "customer_email": customer_email,
            }
            log_status = "payment_pending"

        query = (
            self.client.table("orders")
            .update(update_data)
            .eq("id", order_id)
        )
        response = await self._execute_sync(query)

        if response.data:
            logger.info("Order %s marked as %s", order_id, log_status)
            order = response.data[0]

            # HubSpot: move Lead deal to Closed Won (fire-and-forget)
            if log_status == "completed" and self.settings.hubspot_access_token:
                hs_deal_id = (order.get("metadata") or {}).get("hubspot_deal_id")
                if hs_deal_id:
                    from src.services.hubspot_service import HubSpotService
                    asyncio.create_task(
                        HubSpotService().on_deal_closed(
                            deal_id=hs_deal_id,
                            amount_usd=order.get("total_cents", 0) / 100,
                        )
                    )

            # Send order confirmation email (fire-and-forget)
            if log_status == "completed" and customer_email:
                try:
                    from src.services.email_service import EmailService
                    line_items = order.get("line_items") or []
                    robot_name = line_items[0]["product_name"] if line_items else "Robot"
                    total_cents = order.get("total_cents", 0)
                    pay_type = (order.get("metadata") or {}).get("payment_type", "lease")
                    if pay_type == "purchase":
                        amount_display = f"${total_cents / 100:,.0f}"
                    else:
                        amount_display = f"${total_cents / 100:,.0f}/mo"
                    # Load target_start_date from session if available
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
                            payment_type=pay_type,
                            order_id=str(order.get("id", "")),
                            target_start_date=tsd or None,
                        )
                    )
                except Exception:
                    logger.debug("Order confirmation email task creation failed (non-fatal)")

            return order

        logger.warning("Order not found for completion: %s", order_id)
        return {}

    async def handle_async_payment_succeeded(self, event: dict[str, Any]) -> dict[str, Any]:
        """Process checkout.session.async_payment_succeeded webhook event.

        Called when an ACH/bank transfer payment settles successfully (~4 business days).
        Transitions the order from payment_pending to completed.

        Args:
            event: Stripe webhook event data.

        Returns:
            dict: Updated order data.
        """
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")

        if not order_id:
            logger.warning("Webhook missing order_id in metadata: %s", session.get("id"))
            return {}

        # Check current order status — skip if already in terminal state
        current_order = await self.get_order(UUID(order_id))
        if current_order and current_order.get("status") in ("completed", "cancelled"):
            logger.info(
                "Order %s already in terminal state '%s', skipping async payment update",
                order_id,
                current_order["status"],
            )
            return current_order

        update_data = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        query = (
            self.client.table("orders")
            .update(update_data)
            .eq("id", order_id)
        )
        response = await self._execute_sync(query)

        if response.data:
            logger.info("Order %s async payment succeeded, marked as completed", order_id)
            order = response.data[0]

            # HubSpot: move Lead deal to Closed Won (fire-and-forget)
            if self.settings.hubspot_access_token:
                hs_deal_id = (order.get("metadata") or {}).get("hubspot_deal_id")
                if hs_deal_id:
                    from src.services.hubspot_service import HubSpotService
                    asyncio.create_task(
                        HubSpotService().on_deal_closed(
                            deal_id=hs_deal_id,
                            amount_usd=order.get("total_cents", 0) / 100,
                        )
                    )

            # Send order confirmation email (fire-and-forget)
            customer_email = order.get("customer_email")
            if customer_email:
                try:
                    from src.services.email_service import EmailService
                    line_items = order.get("line_items") or []
                    robot_name = line_items[0]["product_name"] if line_items else "Robot"
                    total_cents = order.get("total_cents", 0)
                    pay_type = (order.get("metadata") or {}).get("payment_type", "lease")
                    if pay_type == "purchase":
                        amount_display = f"${total_cents / 100:,.0f}"
                    else:
                        amount_display = f"${total_cents / 100:,.0f}/mo"
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
                            payment_type=pay_type,
                            order_id=str(order.get("id", "")),
                            target_start_date=tsd or None,
                        )
                    )
                except Exception:
                    logger.debug("Order confirmation email task creation failed (non-fatal)")

            return order

        logger.warning("Order not found for async payment success: %s", order_id)
        return {}

    async def handle_async_payment_failed(self, event: dict[str, Any]) -> dict[str, Any]:
        """Process checkout.session.async_payment_failed webhook event.

        Called when an ACH/bank transfer payment fails (insufficient funds, closed account, etc.).
        Transitions the order from payment_pending to cancelled.

        Args:
            event: Stripe webhook event data.

        Returns:
            dict: Updated order data.
        """
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")

        if not order_id:
            logger.warning("Webhook missing order_id in metadata: %s", session.get("id"))
            return {}

        # Fetch existing order to merge metadata
        existing_order = await self.get_order(UUID(order_id))
        existing_metadata = (existing_order.get("metadata", {}) or {}) if existing_order else {}
        merged_metadata = {**existing_metadata, "failure_reason": "async_payment_failed"}

        update_data: dict[str, Any] = {
            "status": "cancelled",
            "metadata": merged_metadata,
        }

        query = (
            self.client.table("orders")
            .update(update_data)
            .eq("id", order_id)
        )
        response = await self._execute_sync(query)

        if response.data:
            logger.info("Order %s async payment failed, marked as cancelled", order_id)
            return response.data[0]

        logger.warning("Order not found for async payment failure: %s", order_id)
        return {}

    async def handle_checkout_expired(self, event: dict[str, Any]) -> None:
        """Process checkout.session.expired webhook event.

        Args:
            event: Stripe webhook event data.
        """
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")

        if not order_id:
            logger.warning("Webhook missing order_id in metadata: %s", session.get("id"))
            return

        query = self.client.table("orders").update(
            {"status": "cancelled"}
        ).eq("id", order_id)
        await self._execute_sync(query)

        logger.info("Order %s marked as cancelled (expired)", order_id)

    async def get_order(self, order_id: UUID) -> dict[str, Any] | None:
        """Get an order by ID.

        Args:
            order_id: The order's UUID.

        Returns:
            dict | None: The order data or None if not found.
        """
        response = await self._execute_sync(
            self.client.table("orders")
            .select("*")
            .eq("id", str(order_id))
            .maybe_single()
        )

        return response.data if response and response.data else None

    async def get_orders_for_profile(self, profile_id: UUID) -> list[dict[str, Any]]:
        """Get all orders for a profile.

        Args:
            profile_id: The profile's UUID.

        Returns:
            list[dict]: List of order data.
        """
        response = await self._execute_sync(
            self.client.table("orders")
            .select("*")
            .eq("profile_id", str(profile_id))
            .order("created_at", desc=True)
        )

        return response.data or []

    async def get_orders_for_session(self, session_id: UUID) -> list[dict[str, Any]]:
        """Get all orders for a session.

        Args:
            session_id: The session's UUID.

        Returns:
            list[dict]: List of order data.
        """
        response = await self._execute_sync(
            self.client.table("orders")
            .select("*")
            .eq("session_id", str(session_id))
            .order("created_at", desc=True)
        )

        return response.data or []

    async def transfer_orders_to_profile(
        self, session_id: UUID, profile_id: UUID
    ) -> int:
        """Transfer session orders to a profile.

        Called when a session is claimed by an authenticated user.

        Args:
            session_id: The session's UUID.
            profile_id: The profile's UUID to transfer to.

        Returns:
            int: Number of orders transferred.
        """
        response = await self._execute_sync(
            self.client.table("orders")
            .update({"profile_id": str(profile_id)})
            .eq("session_id", str(session_id))
        )

        return len(response.data) if response.data else 0

    def verify_webhook_signature(
        self, payload: bytes, sig_header: str
    ) -> tuple[dict[str, Any], bool]:
        """Verify Stripe webhook signature and return event.

        Tries production webhook secret first, then test webhook secret.
        This allows handling webhooks from both test accounts and production
        accounts in the same production environment.

        Args:
            payload: Raw webhook payload bytes.
            sig_header: Stripe-Signature header value.

        Returns:
            tuple: (Verified Stripe event, is_test_mode boolean).

        Raises:
            ValueError: If signature is invalid or Stripe not configured.
        """
        secrets_to_try = []

        # Try production secret first
        if self.settings.stripe_webhook_secret:
            secrets_to_try.append((self.settings.stripe_webhook_secret, False))

        # Then try test secret
        if self.settings.stripe_webhook_secret_test:
            secrets_to_try.append((self.settings.stripe_webhook_secret_test, True))

        if not secrets_to_try:
            raise ValueError("Stripe webhook secret is not configured. Please set STRIPE_WEBHOOK_SECRET environment variable.")

        logger.info("Attempting webhook verification with %d secret(s)", len(secrets_to_try))

        last_error = None
        production_secret_failed = False
        for secret, is_test in secrets_to_try:
            try:
                event = self.stripe.Webhook.construct_event(
                    payload, sig_header, secret
                )
                if is_test and production_secret_failed:
                    logger.warning(
                        "Webhook verified with TEST secret (production secret failed) - check Stripe webhook config"
                    )
                else:
                    logger.info("Webhook verified with %s secret", "test" if is_test else "production")
                return event, is_test
            except stripe.error.SignatureVerificationError as e:
                last_error = e
                if not is_test:
                    production_secret_failed = True
                continue

        logger.warning("Invalid webhook signature: %s", str(last_error))
        raise ValueError("Invalid webhook signature") from last_error

    async def can_access_order(
        self,
        order_id: UUID,
        profile_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> bool:
        """Check if a user or session can access an order.

        Args:
            order_id: The order's UUID.
            profile_id: Optional profile ID for authenticated users.
            session_id: Optional session ID for anonymous users.

        Returns:
            bool: True if access is allowed.
        """
        order = await self.get_order(order_id)
        if not order:
            return False

        # Check profile ownership
        if profile_id and order.get("profile_id") == str(profile_id):
            return True

        # Check session ownership
        if session_id and order.get("session_id") == str(session_id):
            return True

        return False

"""Checkout API routes for Stripe and Gynger payment integrations."""

from decimal import Decimal
from uuid import UUID

import stripe
from fastapi import APIRouter, HTTPException, status

from src.api.deps import AuthContext, DualAuth
from src.schemas.checkout import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    GyngerSessionCreate,
    GyngerSessionResponse,
    OrderListResponse,
    OrderResponse,
)
from src.services.checkout_service import CheckoutService
from src.services.gynger_service import GyngerService
from src.services.profile_service import ProfileService
from src.services.robot_catalog_service import RobotCatalogService

router = APIRouter(prefix="/checkout", tags=["checkout"])


async def _get_profile_for_auth(auth: AuthContext) -> tuple[UUID | None, bool | None]:
    """Get the profile ID and test account flag for an authenticated user.

    Creates profile if needed.

    Returns:
        tuple: (profile_id, is_test_account) - is_test_account is None for
               anonymous sessions so checkout falls through to environment-based detection.
    """
    if not auth.is_authenticated or not auth.user:
        return None, None
    service = ProfileService()
    profile = await service.get_or_create_profile(auth.user.user_id, auth.user.email)
    return UUID(profile["id"]), profile.get("is_test_account", False)


@router.post(
    "/session",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Stripe Checkout Session",
    description="Creates a Stripe Checkout Session for a robot subscription. Supports both authenticated users and anonymous sessions.",
)
async def create_checkout_session(
    data: CheckoutSessionCreate,
    auth: DualAuth,
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout Session for robot subscription.

    This endpoint creates a pending order and a Stripe Checkout Session.
    The frontend should redirect to the returned checkout_url.

    Args:
        data: Checkout session creation data.
        auth: Dual auth context (user or session).

    Returns:
        CheckoutSessionResponse: Contains checkout_url for redirect.

    Raises:
        HTTPException: 400 if product not found or inactive.
    """
    service = CheckoutService()

    # Extract profile_id, is_test_account, or session_id from auth context
    profile_id, is_test_account = await _get_profile_for_auth(auth)
    session_id = auth.session.session_id if auth.session else None

    try:
        result = await service.create_checkout_session(
            product_id=data.product_id,
            success_url=str(data.success_url),
            cancel_url=str(data.cancel_url),
            profile_id=profile_id,
            session_id=session_id,
            customer_email=data.customer_email,
            is_test_account=is_test_account,
            payment_type=data.payment_type,
        )

        return CheckoutSessionResponse(
            checkout_url=result["checkout_url"],
            order_id=result["order_id"],
            stripe_session_id=result["stripe_session_id"],
            is_test_mode=result.get("is_test_mode", False),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.user_message or e),
        ) from e


@router.post(
    "/gynger-session",
    response_model=GyngerSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Gynger Financing Session",
    description="Initiates a Gynger B2B financing application for a robot. Returns a URL to redirect the user to Gynger's application form.",
)
async def create_gynger_session(
    data: GyngerSessionCreate,
    auth: DualAuth,
) -> GyngerSessionResponse:
    """Create a Gynger financing application for a robot.

    This endpoint creates a pending order and initiates a Gynger financing
    application. The frontend should redirect to the returned application_url.
    Order status transitions to 'completed' or 'cancelled' via the Gynger webhook.

    Args:
        data: Gynger session creation data.
        auth: Dual auth context (user or session).

    Returns:
        GyngerSessionResponse: Contains application_url for redirect.

    Raises:
        HTTPException: 400 if product not found, inactive, or Gynger not configured.
    """
    checkout_service = CheckoutService()
    gynger_service = GyngerService()
    robot_service = RobotCatalogService()

    # Get profile context
    profile_id, _ = await _get_profile_for_auth(auth)
    session_id = auth.session.session_id if auth.session else None

    try:
        # Look up robot
        robot = await robot_service.get_robot(data.product_id)
        if not robot:
            raise ValueError("Product not found")
        if not robot.get("active", False):
            raise ValueError("Product is no longer available")

        # Calculate total in cents (use purchase_price for Gynger — financing a full purchase)
        purchase_price = robot.get("purchase_price", robot.get("monthly_lease", 0))
        if isinstance(purchase_price, str):
            purchase_price = Decimal(purchase_price)
        amount_cents = int(Decimal(str(purchase_price)) * 100)

        # Create pending order
        line_items = [
            {
                "product_id": str(data.product_id),
                "product_name": robot["name"],
                "quantity": 1,
                "unit_amount_cents": amount_cents,
                "stripe_price_id": "gynger",  # Not a Stripe price
            }
        ]
        order_data = {
            "profile_id": str(profile_id) if profile_id else None,
            "session_id": str(session_id) if session_id else None,
            "stripe_checkout_session_id": None,
            "status": "pending",
            "line_items": line_items,
            "total_cents": amount_cents,
            "currency": "usd",
            "customer_email": data.customer_email,
            "payment_provider": "gynger",
            "metadata": {"payment_method": "gynger"},
        }
        order_result = await checkout_service._execute_sync(
            checkout_service.client.table("orders").insert(order_data)
        )
        if not order_result.data:
            raise ValueError("Failed to create order")
        order = order_result.data[0]
        order_id = order["id"]

        # Create Gynger checkout session
        gynger_result = await gynger_service.create_checkout_session(
            robot=robot,
            amount_cents=amount_cents,
            customer_email=data.customer_email,
            order_id=str(order_id),
        )

        # Resolve customer email from profile if not provided (defense in depth for HubSpot)
        customer_email = data.customer_email
        if not customer_email and profile_id:
            try:
                profile_row = await checkout_service._execute_sync(
                    checkout_service.client.table("profiles")
                    .select("email")
                    .eq("id", str(profile_id))
                    .maybe_single()
                )
                if profile_row.data:
                    customer_email = profile_row.data.get("email")
            except Exception:
                import logging as _log2
                _log2.getLogger(__name__).debug("Could not resolve email from profile %s", profile_id)

        # Load session data for HubSpot enrichment
        session_answers: dict = {}
        target_start_date = ""
        if session_id:
            try:
                sess_row = await checkout_service._execute_sync(
                    checkout_service.client.table("sessions")
                    .select("answers, greenlight")
                    .eq("id", str(session_id))
                    .maybe_single()
                )
                if sess_row.data:
                    session_answers = sess_row.data.get("answers") or {}
                    gl = sess_row.data.get("greenlight") or {}
                    target_start_date = gl.get("target_start_date") or ""
            except Exception:
                import logging as _log3
                _log3.getLogger(__name__).debug("Could not load session %s for HubSpot enrichment", session_id)

        # HubSpot: create Lead deal at checkout initiation (awaited so we get the deal_id back)
        hubspot_deal_id: str | None = None
        from src.core.config import get_settings as _gs
        if _gs().hubspot_access_token.get_secret_value() and customer_email:
            try:
                from src.services.hubspot_service import HubSpotService
                from src.services.checkout_service import _answer_val
                company_name: str | None = None
                if profile_id:
                    co = await checkout_service._execute_sync(
                        checkout_service.client.table("companies")
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
                    amount_usd=amount_cents / 100,
                    order_id=str(order_id),
                    payment_type="purchase",
                    payment_provider="gynger",
                    sqft=_answer_val(session_answers, "sqft"),
                    monthly_spend=_answer_val(session_answers, "monthly_spend"),
                    company_type=_answer_val(session_answers, "company_type"),
                    cleaning_method=_answer_val(session_answers, "method"),
                    cleaning_frequency=_answer_val(session_answers, "frequency"),
                    target_start_date=target_start_date,
                )
            except Exception:
                import logging as _log
                _log.getLogger(__name__).exception(
                    "HubSpot Gynger deal creation failed for order %s (non-fatal)", order_id
                )

        # Store Gynger application ID (and HubSpot deal ID) on the order
        order_metadata_update: dict = {"gynger_application_id": gynger_result["application_id"]}
        if hubspot_deal_id:
            existing_meta = order.get("metadata") or {}
            order_metadata_update["metadata"] = {**existing_meta, "hubspot_deal_id": hubspot_deal_id}
        await checkout_service._execute_sync(
            checkout_service.client.table("orders")
            .update(order_metadata_update)
            .eq("id", str(order_id))
        )

        return GyngerSessionResponse(
            application_url=gynger_result["application_url"],
            order_id=order_id,
            gynger_application_id=gynger_result["application_id"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Orders router - mounted separately at /orders
orders_router = APIRouter(prefix="/orders", tags=["orders"])


@orders_router.get(
    "",
    response_model=OrderListResponse,
    summary="List my orders",
    description="Returns all orders for the authenticated user or session.",
)
async def list_orders(auth: DualAuth) -> OrderListResponse:
    """List all orders for the current user or session.

    Args:
        auth: Dual auth context (user or session).

    Returns:
        OrderListResponse: List of orders.
    """
    service = CheckoutService()
    profile_id, _ = await _get_profile_for_auth(auth)

    if profile_id:
        orders = await service.get_orders_for_profile(profile_id)
    elif auth.session:
        orders = await service.get_orders_for_session(auth.session.session_id)
    else:
        # No auth context - return empty list
        orders = []

    return OrderListResponse(items=[OrderResponse(**order) for order in orders])


@orders_router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
    description="Returns a single order by ID. Only accessible by the order owner.",
)
async def get_order(order_id: UUID, auth: DualAuth) -> OrderResponse:
    """Get a single order by ID.

    Args:
        order_id: The order's UUID.
        auth: Dual auth context (user or session).

    Returns:
        OrderResponse: The order data.

    Raises:
        HTTPException: 404 if order not found.
        HTTPException: 403 if not authorized to view this order.
    """
    service = CheckoutService()

    # Check if user can access this order
    profile_id, _ = await _get_profile_for_auth(auth)
    session_id = auth.session.session_id if auth.session else None

    can_access = await service.can_access_order(
        order_id=order_id,
        profile_id=profile_id,
        session_id=session_id,
    )

    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    order = await service.get_order(order_id)
    return OrderResponse(**order)

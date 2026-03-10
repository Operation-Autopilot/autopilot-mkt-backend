"""Checkout API routes for Stripe and Gynger payment integrations."""

from decimal import Decimal
from uuid import UUID

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

    # Validate redirect URLs (reuse existing open-redirect protection)
    try:
        checkout_service._validate_redirect_url(str(data.success_url))
        checkout_service._validate_redirect_url(str(data.cancel_url))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

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

        # Create Gynger financing application
        gynger_result = await gynger_service.create_financing_application(
            robot=robot,
            amount_cents=amount_cents,
            customer_email=data.customer_email,
            success_url=str(data.success_url),
            cancel_url=str(data.cancel_url),
            order_id=str(order_id),
        )

        # Store Gynger application ID on the order
        await checkout_service._execute_sync(
            checkout_service.client.table("orders")
            .update({"gynger_application_id": gynger_result["application_id"]})
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

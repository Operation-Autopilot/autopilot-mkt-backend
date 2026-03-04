#!/usr/bin/env python
"""Script to sync robot catalog products to Stripe.

This script:
1. Reads all robots from the robot_catalog table
2. Creates or updates Stripe products and recurring monthly prices for each robot
3. Updates the database with real Stripe product and price IDs

Usage:
    python scripts/sync_stripe_products.py

Requirements:
    - STRIPE_SECRET_KEY environment variable must be set
    - Database must have robot_catalog table populated
    - Robots should have placeholder Stripe IDs (will be replaced) or can be created fresh

Note:
    - Creates new Stripe products if IDs don't exist
    - Updates existing products if name/description changed
    - Creates new prices if amount changed (Stripe prices are immutable)
    - Archives old prices when creating new ones
"""

import asyncio
import logging
import sys
from decimal import Decimal
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings
from src.core.stripe import configure_stripe, get_stripe
from src.core.supabase import get_supabase_client
from src.services.robot_catalog_service import RobotCatalogService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def is_placeholder_stripe_id(stripe_id: str) -> bool:
    """Check if a Stripe ID is a placeholder (not a real Stripe ID format).

    Real Stripe IDs start with 'prod_' followed by a long alphanumeric string.
    Placeholders are simple strings like 'prod_pudu_cc1_pro'.

    Args:
        stripe_id: The Stripe ID to check.

    Returns:
        bool: True if it's a placeholder, False if it looks like a real Stripe ID.
    """
    if not stripe_id or not stripe_id.startswith("prod_"):
        return True

    # Real Stripe IDs are much longer (e.g., 'prod_ABC123xyz...')
    # Placeholders are shorter (e.g., 'prod_pudu_cc1_pro')
    # If it has underscores but is short, it's likely a placeholder
    parts = stripe_id.split("_")
    if len(parts) <= 4 and len(stripe_id) < 30:
        return True

    return False


def get_robot_description(robot: dict) -> str:
    """Build product description from robot attributes.

    Args:
        robot: Robot data dictionary.

    Returns:
        str: Product description for Stripe.
    """
    description_parts = []
    if robot.get("best_for"):
        description_parts.append(f"Best for: {robot['best_for']}")
    if robot.get("modes"):
        description_parts.append(f"Modes: {', '.join(robot['modes'])}")
    if robot.get("surfaces"):
        description_parts.append(f"Surfaces: {', '.join(robot['surfaces'])}")
    if robot.get("specs"):
        description_parts.append(f"Specs: {'; '.join(robot['specs'][:3])}")  # First 3 specs

    return " | ".join(description_parts) if description_parts else f"Robot cleaning solution by {robot.get('manufacturer', 'Unknown')}"


def get_robot_price_cents(robot: dict) -> int:
    """Get robot monthly lease price in cents.

    Args:
        robot: Robot data dictionary.

    Returns:
        int: Price in cents.
    """
    monthly_lease = robot.get("monthly_lease", 0)
    if isinstance(monthly_lease, (str, Decimal)):
        monthly_lease = float(Decimal(str(monthly_lease)))
    return int(monthly_lease * 100)


def get_robot_purchase_price_cents(robot: dict) -> int:
    """Get robot one-time purchase price in cents.

    Args:
        robot: Robot data dictionary.

    Returns:
        int: Price in cents.
    """
    purchase_price = robot.get("purchase_price", 0)
    if isinstance(purchase_price, (str, Decimal)):
        purchase_price = float(Decimal(str(purchase_price)))
    return int(purchase_price * 100)


def create_stripe_product_and_prices(robot: dict) -> tuple[str, str, str]:
    """Create a Stripe product with both recurring and one-time prices for a robot.

    Args:
        robot: Robot data dictionary with name, monthly_lease, purchase_price, etc.

    Returns:
        tuple: (stripe_product_id, stripe_lease_price_id, stripe_purchase_price_id)
    """
    stripe = get_stripe()

    description = get_robot_description(robot)

    # Create Stripe Product
    product_name = f"{robot.get('manufacturer', '')} {robot['name']}".strip()
    product = stripe.Product.create(
        name=product_name,
        description=description[:500],  # Stripe description limit
        metadata={
            "robot_sku": robot.get("sku", ""),
            "robot_id": str(robot["id"]),
            "category": robot.get("category", ""),
        },
    )

    logger.info(f"Created Stripe product: {product.id} - {product_name}")

    # Create recurring monthly price
    lease_amount_cents = get_robot_price_cents(robot)
    lease_price = stripe.Price.create(
        product=product.id,
        unit_amount=lease_amount_cents,
        currency="usd",
        recurring={"interval": "month"},
        metadata={
            "robot_id": str(robot["id"]),
            "robot_sku": robot.get("sku", ""),
            "price_type": "lease",
        },
    )
    logger.info(f"Created Stripe lease price: {lease_price.id} - ${lease_amount_cents / 100}/month")

    # Create one-time purchase price
    purchase_amount_cents = get_robot_purchase_price_cents(robot)
    purchase_price = stripe.Price.create(
        product=product.id,
        unit_amount=purchase_amount_cents,
        currency="usd",
        metadata={
            "robot_id": str(robot["id"]),
            "robot_sku": robot.get("sku", ""),
            "price_type": "purchase",
        },
    )
    logger.info(f"Created Stripe purchase price: {purchase_price.id} - ${purchase_amount_cents / 100} one-time")

    return product.id, lease_price.id, purchase_price.id


def update_stripe_product(product_id: str, robot: dict) -> None:
    """Update an existing Stripe product's name and description.

    Args:
        product_id: Stripe product ID.
        robot: Robot data dictionary.
    """
    stripe = get_stripe()

    product_name = f"{robot.get('manufacturer', '')} {robot['name']}".strip()
    description = get_robot_description(robot)

    stripe.Product.modify(
        product_id,
        name=product_name,
        description=description[:500],
        metadata={
            "robot_sku": robot.get("sku", ""),
            "robot_id": str(robot["id"]),
            "category": robot.get("category", ""),
        },
    )

    logger.info(f"Updated Stripe product: {product_id} - {product_name}")


def create_new_price_for_product(
    product_id: str, robot: dict, old_price_id: str | None = None, price_type: str = "lease"
) -> str:
    """Create a new price for an existing product.

    Stripe prices are immutable, so we create a new one and optionally archive the old one.

    Args:
        product_id: Stripe product ID.
        robot: Robot data dictionary.
        old_price_id: Optional old price ID to archive.
        price_type: "lease" for recurring monthly, "purchase" for one-time.

    Returns:
        str: New Stripe price ID.
    """
    stripe = get_stripe()

    if price_type == "purchase":
        amount_cents = get_robot_purchase_price_cents(robot)
        recurring = None
        label = "one-time"
    else:
        amount_cents = get_robot_price_cents(robot)
        recurring = {"interval": "month"}
        label = "/month"

    # Create new price
    price_params: dict = {
        "product": product_id,
        "unit_amount": amount_cents,
        "currency": "usd",
        "metadata": {
            "robot_id": str(robot["id"]),
            "robot_sku": robot.get("sku", ""),
            "price_type": price_type,
        },
    }
    if recurring:
        price_params["recurring"] = recurring

    price = stripe.Price.create(**price_params)

    logger.info(f"Created new Stripe price: {price.id} - ${amount_cents / 100} {label}")

    # Archive old price if provided
    if old_price_id:
        try:
            stripe.Price.modify(old_price_id, active=False)
            logger.info(f"Archived old price: {old_price_id}")
        except Exception as e:
            logger.warning(f"Could not archive old price {old_price_id}: {e}")

    return price.id


async def sync_all_robots_to_stripe() -> dict:
    """Sync all robots in catalog to Stripe.

    Returns:
        dict: Results with counts of processed, created, updated, and failed robots.
    """
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY environment variable is not set. Cannot sync to Stripe.")

    configure_stripe()

    service = RobotCatalogService()
    client = get_supabase_client()
    stripe = get_stripe()

    # Determine which columns to use based on Stripe key
    is_test_mode = settings.is_stripe_test_mode
    product_col = "stripe_product_id_test" if is_test_mode else "stripe_product_id"
    lease_price_col = "stripe_lease_price_id_test" if is_test_mode else "stripe_lease_price_id"
    purchase_price_col = "stripe_purchase_price_id_test" if is_test_mode else "stripe_purchase_price_id"
    mode_label = "TEST" if is_test_mode else "PRODUCTION"

    logger.info(f"Running in {mode_label} mode - writing to {product_col}, {lease_price_col}, {purchase_price_col}")

    # Get all robots (including inactive for sync purposes)
    robots = await service.list_robots(active_only=False)

    processed = 0
    created = 0
    updated = 0
    price_updated = 0
    skipped = 0
    failed = 0

    for robot in robots:
        processed += 1
        robot_id = robot["id"]
        robot_name = robot.get("name", "Unknown")
        current_product_id = robot.get(product_col, "") or ""
        current_lease_price_id = robot.get(lease_price_col, "") or ""
        current_purchase_price_id = robot.get(purchase_price_col, "") or ""
        expected_lease_cents = get_robot_price_cents(robot)
        expected_purchase_cents = get_robot_purchase_price_cents(robot)

        try:
            # Check if we need to create Stripe products
            needs_create = (
                is_placeholder_stripe_id(current_product_id) or
                is_placeholder_stripe_id(current_lease_price_id) or
                not current_product_id or
                not current_lease_price_id
            )

            if not needs_create:
                # Verify the Stripe IDs actually exist and check if prices match
                try:
                    stripe_product = stripe.Product.retrieve(current_product_id)
                    stripe_lease_price = stripe.Price.retrieve(current_lease_price_id)

                    db_update = {}

                    # Check lease price
                    if stripe_lease_price.unit_amount != expected_lease_cents:
                        logger.warning(
                            f"{robot_name}: Lease price mismatch! "
                            f"DB: ${expected_lease_cents/100}, Stripe: ${stripe_lease_price.unit_amount/100}. "
                            f"Creating new price..."
                        )
                        new_lease_id = create_new_price_for_product(
                            current_product_id, robot, current_lease_price_id, price_type="lease"
                        )
                        db_update[lease_price_col] = new_lease_id
                        price_updated += 1

                    # Check purchase price
                    if current_purchase_price_id and expected_purchase_cents > 0:
                        try:
                            stripe_purchase_price = stripe.Price.retrieve(current_purchase_price_id)
                            if stripe_purchase_price.unit_amount != expected_purchase_cents:
                                logger.warning(
                                    f"{robot_name}: Purchase price mismatch! Creating new price..."
                                )
                                new_purchase_id = create_new_price_for_product(
                                    current_product_id, robot, current_purchase_price_id, price_type="purchase"
                                )
                                db_update[purchase_price_col] = new_purchase_id
                                price_updated += 1
                        except stripe.error.InvalidRequestError:
                            # Purchase price doesn't exist yet, create it
                            new_purchase_id = create_new_price_for_product(
                                current_product_id, robot, price_type="purchase"
                            )
                            db_update[purchase_price_col] = new_purchase_id
                    elif not current_purchase_price_id and expected_purchase_cents > 0:
                        # No purchase price yet, create one
                        new_purchase_id = create_new_price_for_product(
                            current_product_id, robot, price_type="purchase"
                        )
                        db_update[purchase_price_col] = new_purchase_id

                    # Update product metadata/description
                    update_stripe_product(current_product_id, robot)

                    if db_update:
                        client.table("robot_catalog").update(db_update).eq("id", robot_id).execute()
                        updated += 1
                        logger.info(f"Updated {robot_name} prices")
                    else:
                        logger.info(f"Verified {robot_name} - prices match")
                        skipped += 1

                    continue

                except stripe.error.InvalidRequestError:
                    # Product or price doesn't exist in Stripe, need to create
                    logger.warning(f"{robot_name} has invalid Stripe IDs, creating new ones")
                    needs_create = True

            if needs_create:
                # Create Stripe product and both prices
                product_id, lease_price_id, purchase_price_id = create_stripe_product_and_prices(robot)

                # Update database with real Stripe IDs
                client.table("robot_catalog").update({
                    product_col: product_id,
                    lease_price_col: lease_price_id,
                    purchase_price_col: purchase_price_id,
                }).eq("id", robot_id).execute()

                created += 1
                updated += 1
                logger.info(f"Created and updated {robot_name} with Stripe IDs: {product_id}, lease={lease_price_id}, purchase={purchase_price_id}")

        except Exception as e:
            failed += 1
            logger.error(f"Failed to sync {robot_name} (ID: {robot_id}): {e}", exc_info=True)

    return {
        "processed": processed,
        "created": created,
        "updated": updated,
        "price_updated": price_updated,
        "skipped": skipped,
        "failed": failed,
    }


async def main() -> None:
    """Main entry point for the sync script."""
    logger.info("Starting Stripe product synchronization...")

    try:
        results = await sync_all_robots_to_stripe()

        logger.info("=" * 60)
        logger.info("Stripe synchronization complete!")
        logger.info(f"Total robots processed: {results['processed']}")
        logger.info(f"Stripe products created: {results['created']}")
        logger.info(f"Prices updated (amount changed): {results['price_updated']}")
        logger.info(f"Database records updated: {results['updated']}")
        logger.info(f"Skipped (no changes needed): {results['skipped']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info("=" * 60)

        if results["failed"] > 0:
            logger.warning("Some robots failed to sync. Check logs for details.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Synchronization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
"""Seed a $0.01 TestBot product into the robot catalog and sync it to Stripe test mode.

This creates a minimal TestBot entry for end-to-end checkout testing without
real charges. Idempotent: if a robot with name "TestBot" already exists, it
skips the insert and proceeds to Stripe sync.

Usage:
    python scripts/seed_test_robot.py

Requirements:
    - STRIPE_SECRET_KEY_TEST (sk_test_...) must be set in .env
    - Supabase credentials must be set in .env
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings
from src.core.supabase import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def seed_test_robot() -> dict:
    """Insert TestBot into robot_catalog if not already present.

    Returns:
        dict: The robot row (existing or newly created).
    """
    client = get_supabase_client()

    # Check for existing TestBot
    result = await asyncio.to_thread(
        lambda: client.table("robot_catalog").select("*").eq("name", "TestBot").execute()
    )

    if result.data:
        robot = result.data[0]
        logger.info("TestBot already exists (id=%s), skipping insert.", robot["id"])
        return robot

    # Insert minimal TestBot
    robot_data = {
        "name": "TestBot",
        "category": "Test",
        "monthly_lease": 0.01,
        "purchase_price": 0.01,
        "time_efficiency": 0.5,
        "modes": ["Test"],
        "surfaces": ["Test"],
        "active": True,
        "stripe_product_id": "placeholder",
        "stripe_lease_price_id": "placeholder",
        # best_for and other optional fields left as defaults/null
    }

    insert_result = await asyncio.to_thread(
        lambda: client.table("robot_catalog").insert(robot_data).execute()
    )

    if not insert_result.data:
        raise RuntimeError("Failed to insert TestBot into robot_catalog")

    robot = insert_result.data[0]
    logger.info("Inserted TestBot (id=%s).", robot["id"])
    return robot


async def sync_testbot_to_stripe(robot: dict) -> None:
    """Sync TestBot to Stripe test mode, updating the DB row with real IDs.

    Uses the same logic as sync_stripe_products.py but scoped to a single robot
    and always targeting test mode keys.

    Args:
        robot: The robot_catalog row for TestBot.
    """
    settings = get_settings()

    # Require a test key
    test_key = settings.stripe_secret_key_test
    if not test_key or not test_key.startswith("sk_test_"):
        raise EnvironmentError(
            "STRIPE_SECRET_KEY_TEST must be set to a sk_test_... value. "
            "Check your .env file."
        )

    import stripe as stripe_lib

    stripe_lib.api_key = test_key

    # Import helpers from sync script
    from scripts.sync_stripe_products import (
        get_robot_description,
        is_placeholder_stripe_id,
    )

    robot_id = robot["id"]
    name = robot["name"]
    description = get_robot_description(robot)
    price_cents = int(float(robot.get("monthly_lease", 0)) * 100)

    current_product_id = robot.get("stripe_product_id_test") or robot.get("stripe_product_id", "")
    current_price_id = robot.get("stripe_lease_price_id_test") or robot.get("stripe_lease_price_id", "")

    if is_placeholder_stripe_id(current_product_id):
        # Create product
        product = await asyncio.to_thread(
            lambda: stripe_lib.Product.create(
                name=name,
                description=description,
                metadata={"robot_id": str(robot_id), "source": "autopilot_test"},
            )
        )
        stripe_product_id = product.id
        logger.info("Created Stripe test product: %s", stripe_product_id)
    else:
        stripe_product_id = current_product_id
        logger.info("Reusing existing Stripe test product: %s", stripe_product_id)

    if is_placeholder_stripe_id(current_price_id):
        # Create $0.01/month recurring price
        price = await asyncio.to_thread(
            lambda: stripe_lib.Price.create(
                product=stripe_product_id,
                unit_amount=price_cents,
                currency="usd",
                recurring={"interval": "month"},
                metadata={"robot_id": str(robot_id), "source": "autopilot_test"},
            )
        )
        stripe_price_id = price.id
        logger.info("Created Stripe test price: %s ($%.2f/mo)", stripe_price_id, price_cents / 100)
    else:
        stripe_price_id = current_price_id
        logger.info("Reusing existing Stripe test price: %s", stripe_price_id)

    # Update DB row with test IDs
    client = get_supabase_client()
    update_result = await asyncio.to_thread(
        lambda: client.table("robot_catalog")
        .update(
            {
                "stripe_product_id_test": stripe_product_id,
                "stripe_lease_price_id_test": stripe_price_id,
            }
        )
        .eq("id", str(robot_id))
        .execute()
    )

    if not update_result.data:
        raise RuntimeError("Failed to update TestBot with Stripe test IDs")

    logger.info(
        "TestBot synced to Stripe test mode:\n"
        "  Product ID: %s\n"
        "  Price ID:   %s",
        stripe_product_id,
        stripe_price_id,
    )


async def main() -> None:
    logger.info("=== Seeding $0.01 TestBot for Stripe testing ===")
    robot = await seed_test_robot()
    await sync_testbot_to_stripe(robot)
    logger.info("=== Done. TestBot is ready for E2E checkout testing. ===")


if __name__ == "__main__":
    asyncio.run(main())

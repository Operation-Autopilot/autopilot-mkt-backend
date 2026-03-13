#!/usr/bin/env python3
"""Diagnostic script to validate HubSpot Private App integration.

Tests the real code path used during checkout:
  1. Auth — verify the access token works
  2. Create (or find) a contact
  3. Create (or find) a company
  4. Associate contact → company
  5. Create a deal (Lead stage)
  6. Update deal stage → Closed Won

Run:
    cd autopilot-mkt-backend
    source venv/bin/activate
    python scripts/test_hubspot.py
"""

import asyncio
import sys
import os

# Ensure the project root is on sys.path so `src.*` imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.config import get_settings
from src.services.hubspot_service import HubSpotService


async def main() -> None:
    settings = get_settings()

    if not settings.hubspot_access_token:
        print("HUBSPOT_ACCESS_TOKEN is not set — aborting.")
        sys.exit(1)

    print(f"Pipeline ID : {settings.hubspot_pipeline_id}")
    print(f"Lead stage  : {settings.hubspot_deal_stage_lead}")
    print(f"Won stage   : {settings.hubspot_deal_stage_closed_won}")
    print()

    hs = HubSpotService()

    # 1. Auth check — list 1 contact
    import httpx

    print("[1/6] Auth check (GET contacts?limit=1) …")
    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.get(
            f"{hs.BASE_URL}/crm/v3/objects/contacts",
            headers=hs._headers(),
            params={"limit": 1},
        )
        resp.raise_for_status()
        print(f"  ✓ OK — {resp.status_code}")

    # 2. Find or create contact
    test_email = "hubspot-test@tryautopilot.com"
    print(f"\n[2/6] Find or create contact ({test_email}) …")
    contact_id = await hs.find_or_create_contact(
        email=test_email,
        firstname="HubSpot",
        lastname="Test",
        company_name="Autopilot Test Co",
    )
    print(f"  ✓ contact_id = {contact_id}")

    # 3. Find or create company
    test_company = "Autopilot Test Co"
    print(f"\n[3/6] Find or create company ({test_company}) …")
    company_id = await hs.find_or_create_company(test_company)
    print(f"  ✓ company_id = {company_id}")

    # 4. Associate contact → company
    print(f"\n[4/6] Associate contact {contact_id} → company {company_id} …")
    await hs.associate_contact_to_company(contact_id, company_id)
    print("  ✓ OK")

    # 5. Create deal (Lead stage)
    print(f"\n[5/6] Create deal (stage={settings.hubspot_deal_stage_lead}) …")
    deal_id = await hs.create_deal(
        contact_id=contact_id,
        company_id=company_id,
        deal_name="CC1 Pro — Autopilot Diag Test",
        amount_usd=1100.00,
        stage_id=settings.hubspot_deal_stage_lead,
        robot_name="CC1 Pro",
        payment_provider="diagnostic",
        order_id="diag-test",
    )
    print(f"  ✓ deal_id = {deal_id}")

    # 6. Update deal → Closed Won
    print(f"\n[6/6] Update deal {deal_id} → Closed Won (stage={settings.hubspot_deal_stage_closed_won}) …")
    await hs.update_deal_stage(
        deal_id=deal_id,
        stage_id=settings.hubspot_deal_stage_closed_won,
        amount_usd=1100.00,
    )
    print("  ✓ OK")

    print("\n=== All 6 checks passed ===")


if __name__ == "__main__":
    asyncio.run(main())

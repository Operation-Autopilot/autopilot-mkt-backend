"""HubSpot CRM integration service.

Creates and updates Contacts and Deals in HubSpot when users sign up
and when payments are completed. All failures are fire-and-forget —
HubSpot errors never block the main user flow.

Auth model: Private App access token (not OAuth).
"""

import logging
from datetime import date
from typing import Any

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class HubSpotService:
    """Service for HubSpot CRM automation."""

    BASE_URL = "https://api.hubapi.com"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.hubspot_access_token}",
            "Content-Type": "application/json",
        }

    async def find_or_create_contact(
        self,
        email: str,
        firstname: str,
        lastname: str,
        company_name: str | None,
    ) -> str:
        """Find existing HubSpot contact by email or create a new one.

        Returns:
            HubSpot contact id (string).
        """
        async with httpx.AsyncClient(timeout=15) as http:
            # Search by email
            search_resp = await http.post(
                f"{self.BASE_URL}/crm/v3/objects/contacts/search",
                headers=self._headers(),
                json={
                    "filterGroups": [
                        {
                            "filters": [
                                {"propertyName": "email", "operator": "EQ", "value": email}
                            ]
                        }
                    ],
                    "limit": 1,
                },
            )
            search_resp.raise_for_status()
            results = search_resp.json().get("results", [])
            if results:
                contact_id = results[0]["id"]
                logger.debug("HubSpot: found existing contact %s for %s", contact_id, email)
                return contact_id

            # Create new contact
            props: dict[str, Any] = {
                "email": email,
                "firstname": firstname,
                "lastname": lastname,
            }
            if company_name:
                props["company"] = company_name

            create_resp = await http.post(
                f"{self.BASE_URL}/crm/v3/objects/contacts",
                headers=self._headers(),
                json={"properties": props},
            )
            create_resp.raise_for_status()
            contact_id = create_resp.json()["id"]
            logger.info("HubSpot: created contact %s for %s", contact_id, email)
            return contact_id

    async def find_or_create_company(self, name: str) -> str:
        """Find existing HubSpot company by name or create a new one.

        Returns:
            HubSpot company id (string).
        """
        async with httpx.AsyncClient(timeout=15) as http:
            search_resp = await http.post(
                f"{self.BASE_URL}/crm/v3/objects/companies/search",
                headers=self._headers(),
                json={
                    "filterGroups": [
                        {
                            "filters": [
                                {"propertyName": "name", "operator": "EQ", "value": name}
                            ]
                        }
                    ],
                    "limit": 1,
                },
            )
            search_resp.raise_for_status()
            results = search_resp.json().get("results", [])
            if results:
                return results[0]["id"]

            create_resp = await http.post(
                f"{self.BASE_URL}/crm/v3/objects/companies",
                headers=self._headers(),
                json={"properties": {"name": name}},
            )
            create_resp.raise_for_status()
            company_id = create_resp.json()["id"]
            logger.info("HubSpot: created company %s (%s)", company_id, name)
            return company_id

    async def create_deal(
        self,
        contact_id: str,
        company_id: str | None,
        deal_name: str,
        amount_usd: float,
        stage_id: str,
        robot_name: str,
        payment_provider: str,
        order_id: str,
    ) -> str:
        """Create a HubSpot deal with inline associations to contact and company.

        Returns:
            HubSpot deal id (string).
        """
        properties = {
            "dealname": deal_name,
            "amount": str(round(amount_usd, 2)),
            "dealstage": stage_id,
            "pipeline": self.settings.hubspot_pipeline_id,
            "closedate": date.today().isoformat(),
            "hs_note_body": f"order_id={order_id} robot={robot_name} provider={payment_provider}",
        }

        associations = [
            {
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}],
            }
        ]
        if company_id:
            associations.append(
                {
                    "to": {"id": company_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}],
                }
            )

        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                f"{self.BASE_URL}/crm/v3/objects/deals",
                headers=self._headers(),
                json={"properties": properties, "associations": associations},
            )
            resp.raise_for_status()
            deal_id = resp.json()["id"]
            logger.info("HubSpot: created deal %s (stage=%s)", deal_id, stage_id)
            return deal_id

    async def on_signup(
        self,
        email: str,
        display_name: str,
        company_name: str | None,
    ) -> None:
        """Fire-and-forget: create Lead deal when a user signs up.

        Splits display_name on first space to get firstname/lastname.
        All errors are caught and logged — never raised.
        """
        try:
            parts = display_name.split(" ", 1)
            firstname = parts[0]
            lastname = parts[1] if len(parts) > 1 else ""

            contact_id = await self.find_or_create_contact(
                email=email,
                firstname=firstname,
                lastname=lastname,
                company_name=company_name,
            )

            company_id: str | None = None
            if company_name:
                company_id = await self.find_or_create_company(company_name)

            await self.create_deal(
                contact_id=contact_id,
                company_id=company_id,
                deal_name=f"{display_name} — Autopilot Lead",
                amount_usd=0.0,
                stage_id=self.settings.hubspot_deal_stage_lead,
                robot_name="",
                payment_provider="signup",
                order_id="",
            )
            logger.info("HubSpot on_signup complete for %s", email)

        except Exception:
            logger.exception("HubSpot on_signup failed for %s (non-fatal)", email)

    async def on_payment_completed(
        self,
        email: str,
        order_id: str,
        robot_name: str,
        total_cents: int,
        payment_provider: str,
        company_name: str | None,
    ) -> None:
        """Fire-and-forget: create Closed Won deal when payment completes.

        All errors are caught and logged — never raised.
        """
        try:
            parts = email.split("@", 1)
            firstname = parts[0]
            lastname = ""

            contact_id = await self.find_or_create_contact(
                email=email,
                firstname=firstname,
                lastname=lastname,
                company_name=company_name,
            )

            company_id: str | None = None
            if company_name:
                company_id = await self.find_or_create_company(company_name)

            amount_usd = total_cents / 100
            await self.create_deal(
                contact_id=contact_id,
                company_id=company_id,
                deal_name=f"{robot_name} — Autopilot Closed Won",
                amount_usd=amount_usd,
                stage_id=self.settings.hubspot_deal_stage_closed_won,
                robot_name=robot_name,
                payment_provider=payment_provider,
                order_id=order_id,
            )
            logger.info(
                "HubSpot on_payment_completed for %s order=%s robot=%s",
                email,
                order_id,
                robot_name,
            )

        except Exception:
            logger.exception("HubSpot on_payment_completed failed for %s order=%s (non-fatal)", email, order_id)

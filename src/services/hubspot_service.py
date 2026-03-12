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

    async def associate_contact_to_company(self, contact_id: str, company_id: str) -> None:
        """Associate a HubSpot contact with a company (primary association).

        Uses the v4 associations API. Idempotent — safe to call if already associated.
        Association type 1 = Contact → Company (primary, HUBSPOT_DEFINED).
        """
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.put(
                f"{self.BASE_URL}/crm/v4/objects/contacts/{contact_id}/associations/companies/{company_id}",
                headers=self._headers(),
                json=[{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 1}],
            )
            resp.raise_for_status()
            logger.debug("HubSpot: associated contact %s → company %s", contact_id, company_id)

    async def get_company_deal_ids(self, company_id: str) -> list[str]:
        """Return all deal IDs associated with a HubSpot company.

        Returns an empty list on any error (safe for fire-and-forget callers).
        """
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                resp = await http.get(
                    f"{self.BASE_URL}/crm/v3/objects/companies/{company_id}/associations/deals",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                return [r["id"] for r in results]
        except Exception:
            logger.debug("HubSpot: could not fetch deals for company %s", company_id)
            return []

    async def associate_contact_to_deal(self, contact_id: str, deal_id: str) -> None:
        """Associate a HubSpot contact with a deal.

        Association type 4 = Contact → Deal (HUBSPOT_DEFINED).
        """
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.put(
                f"{self.BASE_URL}/crm/v4/objects/contacts/{contact_id}/associations/deals/{deal_id}",
                headers=self._headers(),
                json=[{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 4}],
            )
            resp.raise_for_status()
            logger.debug("HubSpot: associated contact %s → deal %s", contact_id, deal_id)

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
            "description": f"order_id={order_id} robot={robot_name} provider={payment_provider}",
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

    async def on_checkout_initiated(
        self,
        email: str,
        company_name: str | None,
        robot_name: str,
        amount_usd: float,
    ) -> str | None:
        """Create a Lead deal when a user initiates checkout.

        Called synchronously during checkout session creation so the returned
        deal_id can be stored in the order metadata and used later to update
        the deal stage on payment completion.

        Does NOT catch exceptions — callers must wrap in try/except so that
        HubSpot failures never block checkout.

        Returns:
            HubSpot deal id, or None if creation failed.
        """
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
            await self.associate_contact_to_company(contact_id, company_id)

        deal_id = await self.create_deal(
            contact_id=contact_id,
            company_id=company_id,
            deal_name=f"{robot_name} — Autopilot Lead",
            amount_usd=amount_usd,
            stage_id=self.settings.hubspot_deal_stage_lead,
            robot_name=robot_name,
            payment_provider="checkout",
            order_id="",
        )
        logger.info("HubSpot on_checkout_initiated: deal %s for %s (%s)", deal_id, email, robot_name)
        return deal_id

    async def update_deal_stage(self, deal_id: str, stage_id: str, amount_usd: float) -> None:
        """Update a deal's stage and amount.

        Does NOT catch exceptions — use on_deal_closed for fire-and-forget calls.
        """
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.patch(
                f"{self.BASE_URL}/crm/v3/objects/deals/{deal_id}",
                headers=self._headers(),
                json={
                    "properties": {
                        "dealstage": stage_id,
                        "amount": str(round(amount_usd, 2)),
                        "closedate": date.today().isoformat(),
                    }
                },
            )
            resp.raise_for_status()
            logger.info("HubSpot: deal %s → stage %s (amount=%.2f)", deal_id, stage_id, amount_usd)

    async def on_deal_closed(self, deal_id: str, amount_usd: float) -> None:
        """Fire-and-forget: move a deal to Closed Won when payment completes.

        All errors are caught and logged — never raised.
        """
        try:
            await self.update_deal_stage(
                deal_id=deal_id,
                stage_id=self.settings.hubspot_deal_stage_closed_won,
                amount_usd=amount_usd,
            )
        except Exception:
            logger.exception("HubSpot on_deal_closed failed for deal %s (non-fatal)", deal_id)

    async def on_signup(
        self,
        email: str,
        display_name: str,
        company_name: str | None,
    ) -> None:
        """Fire-and-forget: create Contact + Company on signup (no deal).

        The Lead deal is created later at checkout initiation so it only
        appears in HubSpot when the user shows real purchase intent.
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

            if company_name:
                company_id = await self.find_or_create_company(company_name)
                await self.associate_contact_to_company(contact_id, company_id)

            logger.info("HubSpot on_signup complete for %s", email)

        except Exception:
            logger.exception("HubSpot on_signup failed for %s (non-fatal)", email)

    async def on_team_invite(
        self,
        email: str,
        company_name: str,
        display_name: str | None = None,
    ) -> None:
        """Fire-and-forget: create/update a Contact for an invited team member.

        Associates the contact with the company and with any existing deals on
        that company (so they appear on the Lead in HubSpot).
        All errors are caught and logged — never raised.
        """
        try:
            parts = (display_name or email.split("@")[0]).split(" ", 1)
            firstname = parts[0]
            lastname = parts[1] if len(parts) > 1 else ""

            contact_id = await self.find_or_create_contact(
                email=email,
                firstname=firstname,
                lastname=lastname,
                company_name=company_name,
            )

            company_id = await self.find_or_create_company(company_name)
            await self.associate_contact_to_company(contact_id, company_id)

            deal_ids = await self.get_company_deal_ids(company_id)
            for deal_id in deal_ids:
                await self.associate_contact_to_deal(contact_id, deal_id)

            logger.info(
                "HubSpot on_team_invite complete for %s → company %s (%d deal(s))",
                email,
                company_name,
                len(deal_ids),
            )

        except Exception:
            logger.exception("HubSpot on_team_invite failed for %s (non-fatal)", email)


"""HubSpot OAuth service — token management, meetings, and contact/company lookups."""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx

from src.core.config import get_settings
from src.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
HUBSPOT_API_BASE = "https://api.hubapi.com"
HUBSPOT_SCOPES = "crm.objects.contacts.read crm.objects.companies.read crm.objects.deals.read crm.objects.meetings.read"


# ---------------------------------------------------------------------------
# Token encryption helpers (AES-256-GCM via cryptography package)
# ---------------------------------------------------------------------------

def _get_aes_key() -> bytes:
    settings = get_settings()
    if not settings.encryption_key:
        raise ValueError("ENCRYPTION_KEY not configured")
    key = base64.b64decode(settings.encryption_key)
    if len(key) != 32:
        raise ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def encrypt_token(plaintext: str) -> str:
    """Encrypt a string using AES-256-GCM. Returns base64-encoded nonce+ciphertext."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a string encrypted with encrypt_token."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    data = base64.b64decode(encrypted)
    nonce, ciphertext = data[:12], data[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


# ---------------------------------------------------------------------------
# OAuth state helpers (signed, stateless)
# ---------------------------------------------------------------------------

def _get_state_secret() -> str:
    settings = get_settings()
    return settings.encryption_key or "fallback-dev-secret-not-for-production"


def create_oauth_state(profile_id: str) -> str:
    """Create a signed OAuth state parameter containing profile_id."""
    payload = json.dumps({"pid": profile_id, "exp": int(time.time()) + 600}).encode()
    payload_b64 = base64.urlsafe_b64encode(payload).decode()
    sig = hmac.new(_get_state_secret().encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_oauth_state(state: str) -> str | None:
    """Verify signed OAuth state. Returns profile_id if valid, None otherwise."""
    try:
        payload_b64, sig = state.rsplit(".", 1)
        expected_sig = hmac.new(
            _get_state_secret().encode(), payload_b64.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        # Add padding if needed for base64 decode
        padding = 4 - len(payload_b64) % 4
        padded = payload_b64 + ("=" * (padding % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded))
        if payload["exp"] < time.time():
            return None
        return payload["pid"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

async def get_profile_id(user_id: UUID) -> str | None:
    """Look up the profile ID for a given auth user_id."""
    client = get_supabase_client()
    result = (
        client.table("profiles")
        .select("id")
        .eq("user_id", str(user_id))
        .single()
        .execute()
    )
    if result.data:
        return result.data["id"]
    return None


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------

def build_auth_url(state: str) -> str:
    """Build HubSpot OAuth authorization URL."""
    settings = get_settings()
    params = {
        "client_id": settings.hubspot_client_id,
        "redirect_uri": settings.hubspot_redirect_uri,
        "scope": HUBSPOT_SCOPES,
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{HUBSPOT_AUTH_URL}?{query}"


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange authorization code for access + refresh tokens."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            HUBSPOT_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.hubspot_client_id,
                "client_secret": settings.hubspot_client_secret,
                "redirect_uri": settings.hubspot_redirect_uri,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


async def store_tokens(profile_id: str, token_data: dict[str, Any]) -> None:
    """Encrypt and store HubSpot tokens for a profile."""
    client = get_supabase_client()
    expires_at = None
    if "expires_in" in token_data:
        expires_ts = int(time.time()) + token_data["expires_in"]
        expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc).isoformat()

    encrypted_access = encrypt_token(token_data["access_token"])
    encrypted_refresh = None
    if token_data.get("refresh_token"):
        encrypted_refresh = encrypt_token(token_data["refresh_token"])

    row = {
        "profile_id": profile_id,
        "access_token": encrypted_access,
        "refresh_token": encrypted_refresh,
        "expires_at": expires_at,
        "hub_id": str(token_data.get("hub_id", "")),
    }

    # Upsert (profile_id has UNIQUE constraint)
    client.table("hubspot_connections").upsert(row, on_conflict="profile_id").execute()


async def delete_connection(profile_id: str) -> None:
    """Remove a HubSpot connection for a profile."""
    client = get_supabase_client()
    client.table("hubspot_connections").delete().eq("profile_id", profile_id).execute()


async def get_connection(profile_id: str) -> dict[str, Any] | None:
    """Get stored connection row (with encrypted tokens)."""
    client = get_supabase_client()
    result = (
        client.table("hubspot_connections")
        .select("*")
        .eq("profile_id", profile_id)
        .single()
        .execute()
    )
    return result.data or None


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

async def get_valid_access_token(profile_id: str) -> str | None:
    """Return a valid access token, refreshing if needed. Returns None if disconnected."""
    conn = await get_connection(profile_id)
    if not conn:
        return None

    # Check if token expires within 5 minutes
    needs_refresh = False
    if conn.get("expires_at"):
        expires_at = datetime.fromisoformat(conn["expires_at"].replace("Z", "+00:00"))
        buffer = 5 * 60  # 5 minutes
        needs_refresh = expires_at.timestamp() < time.time() + buffer

    if needs_refresh and conn.get("refresh_token"):
        try:
            settings = get_settings()
            decrypted_refresh = decrypt_token(conn["refresh_token"])
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    HUBSPOT_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": settings.hubspot_client_id,
                        "client_secret": settings.hubspot_client_secret,
                        "refresh_token": decrypted_refresh,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=15,
                )
                if response.status_code == 400:
                    # Refresh token invalid — delete connection
                    await delete_connection(profile_id)
                    return None
                response.raise_for_status()
                new_tokens = response.json()
                await store_tokens(profile_id, new_tokens)
                return new_tokens["access_token"]
        except Exception as exc:
            logger.error("HubSpot token refresh failed for profile %s: %s", profile_id, exc)
            return None

    try:
        return decrypt_token(conn["access_token"])
    except Exception as exc:
        logger.error("Failed to decrypt HubSpot token for profile %s: %s", profile_id, exc)
        return None


# ---------------------------------------------------------------------------
# HubSpot API calls
# ---------------------------------------------------------------------------

async def _hs_get(access_token: str, path: str, params: dict | None = None) -> dict[str, Any]:
    """Make an authenticated GET request to HubSpot API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{HUBSPOT_API_BASE}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params or {},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


async def get_upcoming_meetings(profile_id: str) -> list[dict[str, Any]]:
    """Fetch upcoming meeting_event objects from HubSpot (next 48h)."""
    access_token = await get_valid_access_token(profile_id)
    if not access_token:
        raise ValueError("HubSpot not connected or token expired")

    # Use CRM search to find upcoming meetings
    now_ms = int(time.time() * 1000)
    horizon_ms = now_ms + 48 * 3600 * 1000

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/meetings/search",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "hs_meeting_start_time",
                                "operator": "BETWEEN",
                                "highValue": str(horizon_ms),
                                "value": str(now_ms),
                            }
                        ]
                    }
                ],
                "properties": [
                    "hs_meeting_title",
                    "hs_meeting_start_time",
                    "hs_meeting_end_time",
                    "hs_attendee_owner_ids",
                    "hubspot_owner_id",
                ],
                "limit": 20,
                "sorts": [{"propertyName": "hs_meeting_start_time", "direction": "ASCENDING"}],
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

    meetings = []
    for result in data.get("results", []):
        props = result.get("properties", {})
        meetings.append({
            "id": result["id"],
            "title": props.get("hs_meeting_title") or "Untitled Meeting",
            "start_time": props.get("hs_meeting_start_time"),
            "end_time": props.get("hs_meeting_end_time"),
        })
    return meetings


async def get_meeting_context(profile_id: str, meeting_id: str) -> dict[str, Any]:
    """
    Get contact + company context for a meeting.

    Chain:
    1. CRM Associations: meeting → contacts
    2. Fetch each contact → company
    3. Map to discovery answer candidates
    """
    access_token = await get_valid_access_token(profile_id)
    if not access_token:
        raise ValueError("HubSpot not connected or token expired")

    # Step 1: Get associated contacts
    assoc_data = await _hs_get(
        access_token,
        f"/crm/v4/objects/meetings/{meeting_id}/associations/contacts",
    )
    contact_ids = [a["toObjectId"] for a in assoc_data.get("results", [])]

    if not contact_ids:
        return {"discovery_answers": {}, "contacts": [], "warning": "No contacts associated with this meeting"}

    # Step 2: Fetch first contact details
    contact_id = contact_ids[0]
    contact_data = await _hs_get(
        access_token,
        f"/crm/v3/objects/contacts/{contact_id}",
        params={
            "properties": "firstname,lastname,email,associatedcompanyid",
            "associations": "companies",
        },
    )
    contact_props = contact_data.get("properties", {})

    # Step 3: Get associated company
    company_assocs = contact_data.get("associations", {}).get("companies", {}).get("results", [])
    company_props: dict[str, Any] = {}
    if company_assocs:
        company_id = company_assocs[0]["id"]
        company_data = await _hs_get(
            access_token,
            f"/crm/v3/objects/companies/{company_id}",
            params={
                "properties": "name,industry,city,numberofemployees,annualrevenue",
            },
        )
        company_props = company_data.get("properties", {})

    # Map to discovery answers
    HUBSPOT_FIELD_MAP = {
        "name": ("company_name", "Company Name", "Company"),
        "industry": ("industry", "Industry", "Context"),
        "city": ("city", "City", "Context"),
        "numberofemployees": ("employee_count", "Employee Count", "Context"),
    }

    discovery_answers = {}
    for hs_prop, (key, label, group) in HUBSPOT_FIELD_MAP.items():
        value = company_props.get(hs_prop)
        if value:
            discovery_answers[key] = {
                "questionId": 0,
                "key": key,
                "label": label,
                "value": str(value),
                "group": group,
            }

    contacts = [
        {
            "email": contact_props.get("email"),
            "name": f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip(),
        }
    ]

    warning = None
    if not company_props:
        warning = "No company record found for meeting attendees"

    return {
        "discovery_answers": discovery_answers,
        "contacts": contacts,
        "warning": warning,
    }

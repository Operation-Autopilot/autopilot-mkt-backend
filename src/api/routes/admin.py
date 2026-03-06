"""Admin API routes — HubSpot OAuth, Fireflies, share link creation.

All routes require RequireAdmin (authenticated + @admin_email_domain email).
"""

import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.api.deps import RequireAdmin
from src.core.config import get_settings
from src.core.supabase import get_supabase_client
from src.schemas.auth import UserContext
from src.services import hubspot_service, fireflies_service

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# HubSpot — OAuth
# ---------------------------------------------------------------------------

class HubSpotStatusResponse(BaseModel):
    connected: bool
    hub_id: str | None = None


@router.get("/hubspot/auth", summary="Begin HubSpot OAuth flow")
async def hubspot_auth(user: RequireAdmin) -> dict[str, str]:
    """Return HubSpot authorization URL with signed state."""
    profile_id = await hubspot_service.get_profile_id(user.user_id)
    if not profile_id:
        raise HTTPException(status_code=404, detail="Profile not found")

    state = hubspot_service.create_oauth_state(profile_id)
    auth_url = hubspot_service.build_auth_url(state)
    return {"auth_url": auth_url}


@router.get("/hubspot/callback", response_class=HTMLResponse, summary="HubSpot OAuth callback")
async def hubspot_callback(
    code: str = Query(...),
    state: str = Query(...),
) -> HTMLResponse:
    """Exchange authorization code for tokens and store them.

    Returns an HTML page that calls window.opener.postMessage and closes itself.
    This endpoint is public (no auth header) — identity is in the signed state.
    """
    settings = get_settings()
    frontend_url = settings.frontend_url

    profile_id = hubspot_service.verify_oauth_state(state)
    if not profile_id:
        return HTMLResponse(
            content=_close_popup_html(frontend_url, success=False, error="Invalid or expired OAuth state"),
            status_code=400,
        )

    try:
        token_data = await hubspot_service.exchange_code_for_tokens(code)
        await hubspot_service.store_tokens(profile_id, token_data)
    except Exception as exc:
        return HTMLResponse(
            content=_close_popup_html(frontend_url, success=False, error=str(exc)),
            status_code=400,
        )

    return HTMLResponse(content=_close_popup_html(frontend_url, success=True))


def _close_popup_html(frontend_url: str, success: bool, error: str = "") -> str:
    payload = '{"type":"hubspot_oauth_success"}' if success else f'{{"type":"hubspot_oauth_error","error":"{error}"}}'
    return f"""<!DOCTYPE html>
<html>
<body>
<script>
  if (window.opener) {{
    window.opener.postMessage({payload}, "{frontend_url}");
    window.close();
  }} else {{
    document.body.innerText = "{'OAuth complete — you may close this tab.' if success else f'OAuth failed: {error}'}";
  }}
</script>
</body>
</html>"""


@router.get("/hubspot/status", response_model=HubSpotStatusResponse)
async def hubspot_status(user: RequireAdmin) -> HubSpotStatusResponse:
    """Check whether the current admin has a connected HubSpot account."""
    profile_id = await hubspot_service.get_profile_id(user.user_id)
    if not profile_id:
        return HubSpotStatusResponse(connected=False)

    conn = await hubspot_service.get_connection(profile_id)
    if not conn:
        return HubSpotStatusResponse(connected=False)

    return HubSpotStatusResponse(connected=True, hub_id=conn.get("hub_id"))


@router.delete("/hubspot/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def hubspot_disconnect(user: RequireAdmin) -> None:
    """Remove HubSpot connection for the current admin."""
    profile_id = await hubspot_service.get_profile_id(user.user_id)
    if profile_id:
        await hubspot_service.delete_connection(profile_id)


# ---------------------------------------------------------------------------
# HubSpot — Meetings
# ---------------------------------------------------------------------------

@router.get("/hubspot/meetings")
async def hubspot_meetings(user: RequireAdmin) -> dict[str, Any]:
    """List upcoming meetings (next 48h) from HubSpot."""
    profile_id = await hubspot_service.get_profile_id(user.user_id)
    if not profile_id:
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        meetings = await hubspot_service.get_upcoming_meetings(profile_id)
    except ValueError as exc:
        if "not connected" in str(exc).lower() or "token expired" in str(exc).lower():
            raise HTTPException(status_code=401, detail="HubSpot connection expired — reconnect")
        raise HTTPException(status_code=400, detail=str(exc))

    return {"meetings": meetings}


@router.get("/hubspot/meetings/{meeting_id}/context")
async def hubspot_meeting_context(meeting_id: str, user: RequireAdmin) -> dict[str, Any]:
    """Get contact + company discovery context for a meeting.

    Chains: meeting → contacts associations → company properties.
    """
    profile_id = await hubspot_service.get_profile_id(user.user_id)
    if not profile_id:
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        context = await hubspot_service.get_meeting_context(profile_id, meeting_id)
    except ValueError as exc:
        if "not connected" in str(exc).lower() or "token expired" in str(exc).lower():
            raise HTTPException(status_code=401, detail="HubSpot connection expired — reconnect")
        raise HTTPException(status_code=400, detail=str(exc))

    return context


# ---------------------------------------------------------------------------
# Fireflies — Meetings + Extraction
# ---------------------------------------------------------------------------

@router.get("/fireflies/meetings")
async def fireflies_meetings(user: RequireAdmin) -> dict[str, Any]:
    """List recent completed Fireflies meetings (last 7 days)."""
    try:
        meetings = await fireflies_service.get_recent_meetings()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"meetings": meetings}


@router.post("/fireflies/extract/{meeting_id}")
async def fireflies_extract(meeting_id: str, user: RequireAdmin) -> dict[str, Any]:
    """Extract discovery answers from a Fireflies transcript summary."""
    try:
        result = await fireflies_service.extract_discovery_answers(meeting_id)
    except ValueError as exc:
        # Includes "still processing" and "not found"
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Extraction failed: {exc}")

    return result


# ---------------------------------------------------------------------------
# Share links
# ---------------------------------------------------------------------------

class CreateShareRequest(BaseModel):
    robot_id: str
    robot_name: str
    monthly_lease: float
    monthly_savings: float | None = None
    hours_saved: float | None = None
    company_name: str | None = None
    answers: dict[str, Any] | None = None


class CreateShareResponse(BaseModel):
    token: str
    share_url: str
    expires_in_days: int = 7


@router.post("/shares", response_model=CreateShareResponse, status_code=status.HTTP_201_CREATED)
async def create_share(body: CreateShareRequest, user: RequireAdmin) -> CreateShareResponse:
    """Create a shareable post-call ROI link. Snapshot is captured at creation time."""
    profile_id = await hubspot_service.get_profile_id(user.user_id)

    token = secrets.token_urlsafe(32)
    settings = get_settings()

    client = get_supabase_client()
    row = {
        "token": token,
        "created_by": profile_id,
        "snapshot_robot_id": body.robot_id,
        "snapshot_robot_name": body.robot_name,
        "snapshot_monthly_lease": body.monthly_lease,
        "snapshot_monthly_savings": body.monthly_savings,
        "snapshot_hours_saved": body.hours_saved,
        "snapshot_company_name": body.company_name,
        "snapshot_answers": body.answers,
    }
    client.table("session_shares").insert(row).execute()

    share_url = f"{settings.frontend_url}/share/{token}"
    return CreateShareResponse(token=token, share_url=share_url)

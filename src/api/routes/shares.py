"""Public share link routes — no auth required.

Mounted at root level (no /api/v1 prefix), same pattern as health check.
Rate limited: 60 req/min/IP on GET /shares/{token}.
"""

import re
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from src.core.rate_limiter import get_rate_limiter
from src.core.supabase import get_supabase_client

router = APIRouter(prefix="/shares", tags=["shares"])

# Crawler user-agent patterns — do not set viewed_at for these
_CRAWLER_RE = re.compile(
    r"bot|crawler|spider|facebookexternalhit|twitterbot|linkedinbot|slackbot|"
    r"googlebot|bingbot|yandex|baidu|duckduckbot|semrushbot|ahrefsbot",
    re.IGNORECASE,
)

_SHARE_RATE_LIMIT = 60  # requests per minute per IP


async def _check_share_rate_limit(request: Request) -> None:
    """IP-based rate limiting for public share endpoint."""
    ip = request.client.host if request.client else "unknown"
    limiter = get_rate_limiter()
    allowed, _, retry_after = await limiter.check_and_increment(
        f"share_ip:{ip}",
        max_requests=_SHARE_RATE_LIMIT,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


class ShareResponse(BaseModel):
    robot_id: str
    robot_name: str
    monthly_lease: float
    monthly_savings: float | None = None
    hours_saved: float | None = None
    company_name: str | None = None
    answers: dict[str, Any] | None = None
    expires_at: str


class ClaimRequest(BaseModel):
    pass  # No body needed — token in path is sufficient


class ClaimResponse(BaseModel):
    answers: dict[str, Any] | None = None
    robot_id: str


def _is_expired(expires_at_str: str) -> bool:
    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
    return expires_at < datetime.now(tz=timezone.utc)


@router.get("/{token}", response_model=ShareResponse)
async def get_share(token: str, request: Request) -> ShareResponse:
    """Public — return snapshot data for a share token.

    Returns uniform 404 for both expired and non-existent tokens.
    Sets viewed_at on first non-crawler access.
    """
    await _check_share_rate_limit(request)

    client = get_supabase_client()
    result = (
        client.table("session_shares")
        .select("*")
        .eq("token", token)
        .single()
        .execute()
    )

    row = result.data
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    if _is_expired(row["expires_at"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    # Set viewed_at on first non-crawler access
    user_agent = request.headers.get("user-agent", "")
    is_crawler = bool(_CRAWLER_RE.search(user_agent))
    if not is_crawler and not row.get("viewed_at"):
        client.table("session_shares").update({"viewed_at": _now_iso()}).eq("token", token).execute()

    return ShareResponse(
        robot_id=row["snapshot_robot_id"],
        robot_name=row["snapshot_robot_name"],
        monthly_lease=float(row["snapshot_monthly_lease"]),
        monthly_savings=float(row["snapshot_monthly_savings"]) if row.get("snapshot_monthly_savings") is not None else None,
        hours_saved=float(row["snapshot_hours_saved"]) if row.get("snapshot_hours_saved") is not None else None,
        company_name=row.get("snapshot_company_name"),
        answers=row.get("snapshot_answers"),
        expires_at=row["expires_at"],
    )


@router.post("/{token}/claim", response_model=ClaimResponse)
async def claim_share(token: str, request: Request) -> ClaimResponse:
    """Public — claim a share after prospect signs up.

    Marks the token as claimed and returns snapshot answers + robot_id
    so the frontend can initialize a new session.
    """
    await _check_share_rate_limit(request)

    client = get_supabase_client()
    result = (
        client.table("session_shares")
        .select("*")
        .eq("token", token)
        .single()
        .execute()
    )

    row = result.data
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    if _is_expired(row["expires_at"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    if row.get("claimed_at"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Share already claimed")

    client.table("session_shares").update({"claimed_at": _now_iso()}).eq("token", token).execute()

    return ClaimResponse(
        answers=row.get("snapshot_answers"),
        robot_id=row["snapshot_robot_id"],
    )

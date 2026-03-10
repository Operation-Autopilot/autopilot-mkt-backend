"""Fireflies.ai transcript service — fetch summaries and extract discovery answers."""

import logging
import re
from typing import Any

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)

FIREFLIES_GQL_URL = "https://api.fireflies.ai/graphql"


# ---------------------------------------------------------------------------
# GraphQL helpers
# ---------------------------------------------------------------------------

async def _gql_query(query: str, variables: dict | None = None) -> dict[str, Any]:
    """Execute a Fireflies GraphQL query using the workspace API key."""
    settings = get_settings()
    if not settings.fireflies_api_key:
        raise ValueError("FIREFLIES_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            FIREFLIES_GQL_URL,
            headers={
                "Authorization": f"Bearer {settings.fireflies_api_key}",
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables or {}},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            raise ValueError(f"Fireflies GraphQL error: {data['errors']}")
        return data.get("data", {})


# ---------------------------------------------------------------------------
# API methods
# ---------------------------------------------------------------------------

async def get_recent_meetings(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent completed transcripts (last 7 days)."""
    query = f"""
    query {{
        transcripts(limit: {limit}) {{
            id
            title
            date
            duration
            organizer_email
            summary_status
        }}
    }}
    """

    data = await _gql_query(query)
    meetings: list[dict[str, Any]] = []
    for t in data.get("transcripts", []) or []:
        meetings.append({
            "id": t["id"],
            "title": t.get("title") or "Untitled",
            "date": t.get("date"),
            "duration": t.get("duration"),
            "organizer_email": t.get("organizer_email"),
            "summary_status": t.get("summary_status") or "unknown",
        })
    return meetings


async def get_transcript_summary(meeting_id: str) -> dict[str, Any]:
    """Fetch full summary for a specific transcript."""
    query = """
    query GetTranscript($id: String!) {
        transcript(id: $id) {
            id
            title
            date
            summary_status
            summary {
                overview
                action_items
                keywords
                bullet_gist
                notes
            }
        }
    }
    """
    data = await _gql_query(query, {"id": meeting_id})
    return data.get("transcript") or {}


# ---------------------------------------------------------------------------
# Extraction logic
# ---------------------------------------------------------------------------

_SQFT_PATTERN = re.compile(r"(\d[\d,]*)\s*(?:sq\.?\s*ft\.?|square\s*feet)", re.IGNORECASE)
_DOLLAR_MONTHLY_PATTERN = re.compile(
    r"\$\s*(\d[\d,]*(?:\.\d+)?)\s*(?:k\b)?[^a-z]*(?:per\s*month|monthly|/mo)", re.IGNORECASE
)
_DOLLAR_PATTERN = re.compile(r"\$\s*(\d[\d,]*(?:\.\d+)?)\s*(?:k\b)?", re.IGNORECASE)


def _parse_number(s: str, is_k: bool = False) -> str:
    """Clean and optionally multiply by 1000 if 'k' suffix."""
    val = float(s.replace(",", ""))
    if is_k:
        val *= 1000
    return str(int(val))


def _extract_from_text(text: str) -> dict[str, str]:
    """Regex-based extraction from summary text."""
    extracted: dict[str, str] = {}

    # Square footage
    m = _SQFT_PATTERN.search(text)
    if m:
        extracted["sqft"] = m.group(1).replace(",", "")

    # Monthly spend — look for dollar + "per month" / "monthly"
    m = _DOLLAR_MONTHLY_PATTERN.search(text)
    if m:
        raw = m.group(1)
        is_k = bool(re.search(r"\$\s*\d[\d,]*k", m.group(0), re.IGNORECASE))
        extracted["monthly_spend"] = _parse_number(raw, is_k)

    return extracted


async def _gpt_extract(summary_text: str) -> dict[str, str]:
    """GPT-based extraction fallback using structured JSON response."""
    from src.core.openai import get_openai_client
    client = get_openai_client()

    prompt = (
        "You are extracting facility management data from a sales call summary. "
        "Return ONLY valid JSON (no markdown) with these fields if clearly mentioned. "
        "Use null for unknown fields. All numeric values as strings.\n\n"
        "Fields: company_name, industry, city, sqft (sq footage as numeric string), "
        "facility_type, floors (numeric string), hours_per_day (numeric string), "
        "days_per_week (numeric string), monthly_spend (monthly cleaning cost in $ as numeric string), "
        "budget (available budget in $ as numeric string).\n\n"
        f"Summary:\n{summary_text[:3000]}"
    )

    import json
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        # Filter out null values
        return {k: str(v) for k, v in data.items() if v is not None and str(v).strip()}
    except Exception as exc:
        logger.warning("GPT extraction failed: %s", exc)
        return {}


# Field metadata for building DiscoveryAnswer objects
FIELD_META = {
    "company_name":  ("Company Name",       "Company"),
    "industry":      ("Industry",           "Context"),
    "city":          ("City",               "Context"),
    "sqft":          ("Square Footage",     "Facility"),
    "facility_type": ("Facility Type",      "Facility"),
    "floors":        ("Floors",             "Facility"),
    "hours_per_day": ("Hours Per Day",      "Operations"),
    "days_per_week": ("Days Per Week",      "Operations"),
    "monthly_spend": ("Monthly Spend",      "Economics"),
    "budget":        ("Budget Available",   "Economics"),
}

KNOWN_KEYS = set(FIELD_META.keys())


async def extract_discovery_answers(meeting_id: str) -> dict[str, Any]:
    """
    Fetch Fireflies transcript and extract discovery answers.

    Returns:
        {
            extracted: list of DiscoveryAnswer-like dicts,
            source: "fireflies_summary" | "gpt_extraction",
            warning: str | None
        }
    """
    transcript = await get_transcript_summary(meeting_id)

    if not transcript:
        return {"extracted": [], "source": "fireflies_summary", "warning": "Transcript not found"}

    summary_status = transcript.get("summary_status")
    if summary_status != "processed":
        raise ValueError(f"Transcript still processing (status: {summary_status}), try again in a moment")

    summary = transcript.get("summary") or {}
    overview = summary.get("overview") or ""
    action_items = summary.get("action_items") or ""
    keywords = summary.get("keywords") or []
    notes = summary.get("notes") or ""
    bullet_gist = summary.get("bullet_gist") or ""

    # Combine all text for regex extraction
    combined = "\n".join(filter(None, [
        overview, action_items, notes, bullet_gist,
        " ".join(keywords) if isinstance(keywords, list) else str(keywords),
    ]))

    # Stage 1: regex extraction from Fireflies summary
    extracted_values = _extract_from_text(combined)
    source = "fireflies_summary"

    # Stage 2: GPT fallback if we got very little from regex
    if len(extracted_values) < 2 and combined.strip():
        gpt_values = await _gpt_extract(combined)
        if gpt_values:
            extracted_values = {**gpt_values, **extracted_values}  # regex takes priority
            source = "gpt_extraction"

    # Build DiscoveryAnswer-like dicts
    extracted = []
    unknown_fields = []
    for key, value in extracted_values.items():
        if not value:
            continue
        if key in FIELD_META:
            label, group = FIELD_META[key]
            extracted.append({
                "questionId": 0,
                "key": key,
                "label": label,
                "value": value,
                "group": group,
            })
        else:
            unknown_fields.append({"key": key, "value": value})

    warning = None
    if not extracted:
        warning = "No discovery answers could be extracted from this transcript"

    return {
        "extracted": extracted,
        "unknown_fields": unknown_fields,
        "source": source,
        "warning": warning,
    }

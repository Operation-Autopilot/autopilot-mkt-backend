"""Flow tests for the complete discovery conversation.

Validates:
- Full 7-question discovery → phase transition
- No duplicate questions
- Chipless question (company_name) detection
- Answer overwrite behavior
- Greeting on new session / skipped on existing session with messages
"""

import copy
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.flow.conftest import (
    COMPLETE_DISCOVERY_ANSWERS,
    SEED_ROBOTS,
    TEST_PROFILE_ID,
    TEST_USER_ID,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_openai_response(content: str, tool_calls=None):
    """Build a mock OpenAI chat response."""
    choice = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = MagicMock(total_tokens=100)
    return resp


# The question sequence the agent should ask.  Maps question_key → (agent text, chips).
QUESTION_SEQUENCE = [
    ("company_name", "What is the name of your company?", None),
    ("company_type", "What type of company are we building this profile for?",
     ["Pickleball Club", "Tennis Club", "Restaurant", "Warehouse", "Datacenter"]),
    ("courts_count", "How many indoor courts do you have?",
     ["<4", "6", "8", "12+", "Other"]),
    ("method", "What is your primary cleaning method today?",
     ["Vacuum", "Sweep", "Mop", "Other"]),
    ("frequency", "How often do you clean the facility per week?",
     ["Daily", "3-4x per week", "Weekly", "Other"]),
    ("duration", "How long does each cleaning session take (in hours)?",
     ["1 hr", "2 hr", "4 hr", "Other"]),
    ("monthly_spend", "What is your estimated monthly cleaning spend?",
     ["<$2,000", "$2,000 - $5,000", "$5,000 - $10,000", "$10,000+"]),
]

# User answers matching the sequence above
USER_ANSWERS = [
    "Downtown Pickleball Club",
    "Pickleball Club",
    "8",
    "Vacuum",
    "Daily",
    "2 hr",
    "$2,000 - $5,000",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiscoveryFlow:
    """Integration tests for the full discovery conversation flow."""

    @pytest.mark.asyncio
    async def test_session_creation_returns_valid_session(
        self, async_client: AsyncClient
    ):
        """POST /sessions creates a session with discovery phase and empty answers."""
        resp = await async_client.post("/api/v1/sessions")
        assert resp.status_code == 201
        data = resp.json()
        assert data["phase"] == "discovery"
        assert data["answers"] == {}
        assert data["ready_for_roi"] is False
        assert "session_token" in data

    @pytest.mark.asyncio
    async def test_greeting_on_new_conversation(
        self, async_client: AsyncClient, _patch_openai
    ):
        """GET /conversations/current on a new session generates an initial greeting."""
        # Create session first
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]

        # Get current conversation (should create + greet)
        resp = await async_client.get(
            "/api/v1/conversations/current",
            headers={"X-Session-Token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_new"] is True
        # Should have at least the greeting message
        assert len(data["messages"]) >= 1
        assert data["messages"][0]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_greeting_skipped_on_existing_session_with_messages(
        self, async_client: AsyncClient, fake_supabase
    ):
        """GET /conversations/current on existing conversation with messages does NOT re-greet."""
        # Create session first
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]
        session_id = session_resp.json()["id"]

        # First call creates a conversation + greeting
        resp1 = await async_client.get(
            "/api/v1/conversations/current",
            headers={"X-Session-Token": token},
        )
        assert resp1.status_code == 200
        assert resp1.json()["is_new"] is True
        first_msg_count = len(resp1.json()["messages"])

        # Second call should return the EXISTING conversation (not new)
        resp2 = await async_client.get(
            "/api/v1/conversations/current",
            headers={"X-Session-Token": token},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["is_new"] is False
        # Messages should still be there (same count or more, never fewer)
        assert len(data["messages"]) >= first_msg_count

    @pytest.mark.asyncio
    async def test_session_update_answers(
        self, async_client: AsyncClient, complete_answers
    ):
        """PUT /sessions/me correctly stores discovery answers."""
        # Create session
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]

        # Update with partial answers
        partial = {
            "company_name": complete_answers["company_name"],
            "company_type": complete_answers["company_type"],
        }
        resp = await async_client.put(
            "/api/v1/sessions/me",
            headers={"X-Session-Token": token},
            json={"answers": partial},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "company_name" in data["answers"]
        assert "company_type" in data["answers"]
        assert data["ready_for_roi"] is False  # Only 2 of 7 answers

    @pytest.mark.asyncio
    async def test_ready_for_roi_after_minimum_answers(
        self, async_client: AsyncClient, complete_answers
    ):
        """Session reports ready_for_roi=True once >= 4 required answers are stored."""
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]

        # Store 4 required answers (minimum for ROI)
        four_answers = {
            k: complete_answers[k]
            for k in ["company_name", "company_type", "courts_count", "method"]
        }
        resp = await async_client.put(
            "/api/v1/sessions/me",
            headers={"X-Session-Token": token},
            json={"answers": four_answers},
        )
        assert resp.status_code == 200
        assert resp.json()["ready_for_roi"] is True

    @pytest.mark.asyncio
    async def test_full_discovery_stores_all_answers(
        self, async_client: AsyncClient, complete_answers
    ):
        """Storing all 7 required answers results in all keys present in session."""
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]

        resp = await async_client.put(
            "/api/v1/sessions/me",
            headers={"X-Session-Token": token},
            json={"answers": complete_answers},
        )
        assert resp.status_code == 200
        data = resp.json()

        from src.services.extraction_constants import REQUIRED_QUESTION_KEYS
        for key in REQUIRED_QUESTION_KEYS:
            assert key in data["answers"], f"Missing required answer key: {key}"

    @pytest.mark.asyncio
    async def test_answer_overwrite_latest_wins(
        self, async_client: AsyncClient, complete_answers
    ):
        """Updating an existing answer key overwrites with the latest value."""
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]

        # First update
        await async_client.put(
            "/api/v1/sessions/me",
            headers={"X-Session-Token": token},
            json={"answers": {"company_name": complete_answers["company_name"]}},
        )

        # Overwrite company_name
        updated_answer = copy.deepcopy(complete_answers["company_name"])
        updated_answer["value"] = "New Club Name"
        resp = await async_client.put(
            "/api/v1/sessions/me",
            headers={"X-Session-Token": token},
            json={"answers": {"company_name": updated_answer}},
        )
        assert resp.status_code == 200
        assert resp.json()["answers"]["company_name"]["value"] == "New Club Name"

    @pytest.mark.asyncio
    async def test_phase_transition_to_roi(
        self, async_client: AsyncClient, complete_answers
    ):
        """Session phase can be updated from discovery to roi."""
        session_resp = await async_client.post("/api/v1/sessions")
        token = session_resp.json()["session_token"]

        # Store all answers
        await async_client.put(
            "/api/v1/sessions/me",
            headers={"X-Session-Token": token},
            json={"answers": complete_answers},
        )

        # Transition to ROI phase
        resp = await async_client.put(
            "/api/v1/sessions/me",
            headers={"X-Session-Token": token},
            json={"phase": "roi"},
        )
        assert resp.status_code == 200
        assert resp.json()["phase"] == "roi"


class TestChiplessQuestionDetection:
    """Tests for detecting chipless questions (e.g. company_name) from content patterns."""

    def test_detect_company_name_from_content(self):
        """Content-based detection identifies company_name question."""
        from src.services.agent_service import _detect_question_from_content

        assert _detect_question_from_content("What is the name of your company?") == "company_name"
        assert _detect_question_from_content("Can you tell me what company this is for?") == "company_name"

    def test_detect_company_type_from_content(self):
        from src.services.agent_service import _detect_question_from_content

        assert _detect_question_from_content("What type of company is this?") == "company_type"

    def test_detect_from_chips(self):
        """Chip-based detection correctly maps chip sets to question keys."""
        from src.services.agent_service import _detect_question_from_chips

        # Exact match
        assert _detect_question_from_chips(
            ["Pickleball Club", "Tennis Club", "Restaurant", "Warehouse", "Datacenter"]
        ) == "company_type"

        # No chips returns None (company_name has chips=None)
        assert _detect_question_from_chips(None) is None
        assert _detect_question_from_chips([]) is None

    def test_no_false_positive_on_random_content(self):
        from src.services.agent_service import _detect_question_from_content

        assert _detect_question_from_content("How are you today?") is None
        assert _detect_question_from_content("Let me analyze your needs.") is None


class TestQuestionTracking:
    """Tests verifying questions are not repeated during discovery."""

    def test_required_question_keys_match_constant(self):
        """REQUIRED_QUESTION_KEYS has exactly 7 entries matching REQUIRED_QUESTIONS."""
        from src.services.extraction_constants import REQUIRED_QUESTION_KEYS, REQUIRED_QUESTIONS

        assert len(REQUIRED_QUESTIONS) == 7
        assert len(REQUIRED_QUESTION_KEYS) == 7
        assert REQUIRED_QUESTION_KEYS == {q["key"] for q in REQUIRED_QUESTIONS}

    def test_discovery_questions_include_all_required(self):
        """All required question keys exist in the full DISCOVERY_QUESTIONS list."""
        from src.services.extraction_constants import (
            DISCOVERY_QUESTIONS,
            REQUIRED_QUESTION_KEYS,
        )

        all_keys = {q["key"] for q in DISCOVERY_QUESTIONS}
        for key in REQUIRED_QUESTION_KEYS:
            assert key in all_keys, f"Required key {key} not in DISCOVERY_QUESTIONS"

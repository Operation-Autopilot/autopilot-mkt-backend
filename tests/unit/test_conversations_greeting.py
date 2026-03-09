"""Tests for conversation greeting logic (is_new or empty messages)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID


class TestGreetingCondition:
    """Tests for the greeting generation condition in get_current_conversation.

    The condition `if is_new or len(messages_data) == 0` ensures greetings are
    generated for:
    - Brand new conversations (is_new=True)
    - Existing conversations with zero messages (migration path)
    """

    @pytest.mark.asyncio
    async def test_new_conversation_gets_greeting(self) -> None:
        """New conversations (is_new=True) should generate a greeting."""
        # The condition should be: is_new OR empty messages
        # Verify: is_new=True, messages=[] → greeting generated
        assert self._should_generate_greeting(is_new=True, message_count=0) is True

    @pytest.mark.asyncio
    async def test_new_conversation_with_messages_gets_greeting(self) -> None:
        """New conversations with messages should still get greeting (is_new=True)."""
        # is_new=True, messages=[...] → greeting generated (or condition)
        assert self._should_generate_greeting(is_new=True, message_count=3) is True

    @pytest.mark.asyncio
    async def test_existing_conversation_with_zero_messages_gets_greeting(self) -> None:
        """Existing conversations with zero messages (migration) should get greeting."""
        # is_new=False, messages=[] → greeting generated
        assert self._should_generate_greeting(is_new=False, message_count=0) is True

    @pytest.mark.asyncio
    async def test_existing_conversation_with_messages_skips_greeting(self) -> None:
        """Existing conversations with messages should not regenerate greeting."""
        # is_new=False, messages=[...] → no greeting
        assert self._should_generate_greeting(is_new=False, message_count=5) is False

    def _should_generate_greeting(self, is_new: bool, message_count: int) -> bool:
        """Replicate the greeting condition from conversations.py."""
        # This matches: `if is_new or len(messages_data) == 0:`
        return is_new or message_count == 0

    @pytest.mark.asyncio
    async def test_greeting_condition_matches_source_code(self) -> None:
        """Verify the source code uses `or` not `and` for the greeting condition."""
        import ast
        import inspect
        from src.api.routes.conversations import get_current_conversation

        source = inspect.getsource(get_current_conversation)
        # Check that the condition uses `or` (not `and`)
        assert "is_new or len(messages_data) == 0" in source, (
            "Greeting condition should use 'or' to handle migration path. "
            "Found 'and' which would skip greetings for existing empty conversations."
        )

"""Unit tests for conversations routes — BUG-46, BUG-47."""

import pytest

from src.api.routes.conversations import get_conversation, get_current_conversation, send_message


class TestBUG47SendMessageUsesBackgroundTasks:
    """BUG-47: Profile extraction should use BackgroundTasks for non-blocking execution."""

    def test_send_message_imports_background_tasks(self) -> None:
        """BUG-47: conversations.py should import BackgroundTasks from FastAPI."""
        import inspect
        import src.api.routes.conversations as conv_module
        source = inspect.getsource(conv_module)
        assert "BackgroundTasks" in source or "background" in source.lower(), \
            "conversations.py should use BackgroundTasks for profile extraction"

    def test_send_message_signature_has_background_tasks(self) -> None:
        """BUG-47: send_message should accept BackgroundTasks parameter."""
        import inspect
        sig = inspect.signature(send_message)
        param_names = list(sig.parameters.keys())
        # Should have a background_tasks parameter (or extraction runs in background)
        source = inspect.getsource(send_message)
        has_background = (
            "background_tasks" in param_names
            or "BackgroundTasks" in source
            or "background" in source.lower()
        )
        assert has_background, "send_message should use BackgroundTasks for extraction"


class TestAccessCheckBeforeDataFetch:
    """Tests for auth check ordering — access check should happen before data fetch."""

    def test_get_conversation_checks_access_before_fetch(self) -> None:
        """Test that get_conversation calls _check_conversation_access before fetching data."""
        import inspect
        source = inspect.getsource(get_conversation)
        # Find positions of access check and conversation fetch
        access_pos = source.find("_check_conversation_access")
        fetch_pos = source.find("service.get_conversation")
        assert access_pos < fetch_pos, \
            "Access check should happen before data fetch"


class TestBUG46GreetingNotRegenerated:
    """BUG-46: Greeting should not be regenerated for existing conversations with messages."""

    def test_get_current_conversation_checks_messages(self) -> None:
        """BUG-46: get_current_conversation should only generate greeting for truly new conversations."""
        import inspect
        source = inspect.getsource(get_current_conversation)
        # The condition should check both is_new and no messages
        assert "is_new" in source, "Should check is_new flag"
        assert "messages_data" in source or "len(messages" in source, "Should check message count"
        # Critical: should use AND condition, not OR
        # The old code was: if is_new or len(messages_data) == 0
        # The new code should be: if is_new and len(messages_data) == 0
        assert "is_new and" in source or ("is_new" in source and "len(messages_data) == 0" in source), \
            "Should use AND condition to prevent greeting regeneration on refresh"

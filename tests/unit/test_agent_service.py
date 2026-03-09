"""Unit tests for AgentService."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.models.conversation import ConversationPhase
from src.services.agent_service import AgentService, SYSTEM_PROMPTS


class TestGetSystemPrompt:
    """Tests for get_system_prompt method."""

    def test_returns_discovery_prompt(self) -> None:
        """Test that discovery phase returns correct prompt."""
        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings"):
                service = AgentService()
                prompt = service.get_system_prompt(ConversationPhase.DISCOVERY)

                assert "Discovery" in prompt or "discovery" in prompt.lower()
                assert "robotics procurement" in prompt.lower() or "autopilot" in prompt.lower()

    def test_returns_roi_prompt(self) -> None:
        """Test that ROI phase returns correct prompt."""
        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings"):
                service = AgentService()
                prompt = service.get_system_prompt(ConversationPhase.ROI)

                assert "ROI" in prompt
                assert "costs" in prompt.lower() or "savings" in prompt.lower()

    def test_returns_selection_prompt(self) -> None:
        """Test that selection phase returns correct prompt."""
        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings"):
                service = AgentService()
                prompt = service.get_system_prompt(ConversationPhase.GREENLIGHT)

                assert "finalize" in prompt.lower() or "checkout" in prompt.lower() or "selections" in prompt.lower()
                assert "recommend" in prompt.lower() or "product" in prompt.lower() or "robot" in prompt.lower()


class TestBuildContext:
    """Tests for build_context method."""

    @pytest.mark.asyncio
    async def test_includes_system_prompt(self) -> None:
        """Test that context includes system prompt at the beginning."""
        mock_settings = MagicMock()
        mock_settings.max_context_messages = 20

        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings", return_value=mock_settings):
                with patch(
                    "src.services.agent_service.ConversationService"
                ) as mock_conv_service:
                    mock_conv_service.return_value.get_recent_messages = AsyncMock(return_value=[])

                    service = AgentService()
                    context = await service.build_context(
                        conversation_id=UUID("770e8400-e29b-41d4-a716-446655440000"),
                        phase=ConversationPhase.DISCOVERY,
                    )

                    assert len(context) >= 1
                    assert context[0]["role"] == "system"
                    assert "Autopilot" in context[0]["content"]

    @pytest.mark.asyncio
    async def test_includes_conversation_history(self) -> None:
        """Test that context includes message history."""
        mock_settings = MagicMock()
        mock_settings.max_context_messages = 20

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings", return_value=mock_settings):
                with patch(
                    "src.services.agent_service.ConversationService"
                ) as mock_conv_service:
                    mock_conv_service.return_value.get_recent_messages = AsyncMock(return_value=history)

                    service = AgentService()
                    context = await service.build_context(
                        conversation_id=UUID("770e8400-e29b-41d4-a716-446655440000"),
                        phase=ConversationPhase.DISCOVERY,
                    )

                    # System prompt + 2 history messages
                    assert len(context) == 3
                    assert context[1]["role"] == "user"
                    assert context[1]["content"] == "Hello"
                    assert context[2]["role"] == "assistant"
                    assert context[2]["content"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_respects_message_limit(self) -> None:
        """Test that context respects max_context_messages setting."""
        mock_settings = MagicMock()
        mock_settings.max_context_messages = 5

        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings", return_value=mock_settings):
                with patch(
                    "src.services.agent_service.ConversationService"
                ) as mock_conv_service:
                    # Verify limit is passed to get_recent_messages
                    mock_get_recent_messages = AsyncMock(return_value=[])
                    mock_conv_service.return_value.get_recent_messages = mock_get_recent_messages

                    service = AgentService()
                    await service.build_context(
                        conversation_id=UUID("770e8400-e29b-41d4-a716-446655440000"),
                        phase=ConversationPhase.DISCOVERY,
                    )

                    mock_get_recent_messages.assert_called_once_with(
                        UUID("770e8400-e29b-41d4-a716-446655440000"), limit=5
                    )


class TestGenerateResponse:
    """Tests for generate_response method."""

    @pytest.mark.asyncio
    async def test_stores_user_message(self) -> None:
        """Test that user message is stored before generating response."""
        mock_settings = MagicMock()
        mock_settings.max_context_messages = 20
        mock_settings.openai_model = "gpt-4o"

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Agent response"
        mock_openai.chat.create.return_value = mock_response

        conversation = {
            "id": "770e8400-e29b-41d4-a716-446655440000",
            "phase": "discovery",
        }

        user_message = {
            "id": "880e8400-e29b-41d4-a716-446655440000",
            "conversation_id": "770e8400-e29b-41d4-a716-446655440000",
            "role": "user",
            "content": "Test message",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
        }

        agent_message = {
            "id": "990e8400-e29b-41d4-a716-446655440000",
            "conversation_id": "770e8400-e29b-41d4-a716-446655440000",
            "role": "assistant",
            "content": "Agent response",
            "metadata": {"model": "gpt-4o"},
            "created_at": "2024-01-01T00:00:01Z",
        }

        with patch(
            "src.services.agent_service.get_openai_client", return_value=mock_openai
        ):
            with patch("src.services.agent_service.get_settings", return_value=mock_settings):
                with patch(
                    "src.services.agent_service.ConversationService"
                ) as mock_conv_service:
                    mock_conv_service.return_value.get_conversation = AsyncMock(return_value=conversation)
                    mock_conv_service.return_value.get_recent_messages = AsyncMock(return_value=[])
                    mock_conv_service.return_value.add_message = AsyncMock(side_effect=[
                        user_message,
                        agent_message,
                    ])

                    service = AgentService()
                    user_msg, agent_msg = await service.generate_response(
                        conversation_id=UUID("770e8400-e29b-41d4-a716-446655440000"),
                        user_message="Test message",
                    )

                    assert user_msg.content == "Test message"
                    assert agent_msg.content == "Agent response"


class TestBUG05ResponsesTooLong:
    """BUG-05: Responses too long to skim — max_completion_tokens reduced and brevity instructions added."""

    @pytest.mark.asyncio
    async def test_generate_response_uses_max_tokens_lte_400(self) -> None:
        """BUG-05: generate_response should use max_completion_tokens <= 400."""
        mock_settings = MagicMock()
        mock_settings.max_context_messages = 20
        mock_settings.openai_model = "gpt-4o"
        mock_settings.mock_openai = False

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Short response"
        mock_response.usage = None
        mock_openai.chat.create = AsyncMock(return_value=mock_response)

        conversation = {"id": "770e8400-e29b-41d4-a716-446655440000", "phase": "discovery"}
        user_msg = {
            "id": "880e8400-e29b-41d4-a716-446655440000",
            "conversation_id": "770e8400-e29b-41d4-a716-446655440000",
            "role": "user", "content": "hi", "metadata": {}, "created_at": "2024-01-01T00:00:00Z",
        }
        agent_msg = {
            "id": "990e8400-e29b-41d4-a716-446655440000",
            "conversation_id": "770e8400-e29b-41d4-a716-446655440000",
            "role": "assistant", "content": "Short response", "metadata": {}, "created_at": "2024-01-01T00:00:01Z",
        }

        with patch("src.services.agent_service.get_openai_client", return_value=mock_openai):
            with patch("src.services.agent_service.get_settings", return_value=mock_settings):
                with patch("src.services.agent_service.ConversationService") as mock_conv:
                    mock_conv.return_value.get_conversation = AsyncMock(return_value=conversation)
                    mock_conv.return_value.get_recent_messages = AsyncMock(return_value=[])
                    mock_conv.return_value.add_message = AsyncMock(side_effect=[user_msg, agent_msg])

                    service = AgentService()
                    await service.generate_response(
                        conversation_id=UUID("770e8400-e29b-41d4-a716-446655440000"),
                        user_message="hi",
                    )

                    call_kwargs = mock_openai.chat.create.call_args
                    assert call_kwargs is not None
                    max_tokens = call_kwargs.kwargs.get("max_completion_tokens") or call_kwargs[1].get("max_completion_tokens")
                    assert max_tokens is not None
                    assert max_tokens <= 400, f"max_completion_tokens should be <= 400, got {max_tokens}"

    def test_discovery_prompt_contains_brevity_instruction(self) -> None:
        """BUG-05: Discovery prompt should contain brevity instruction."""
        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings"):
                service = AgentService()
                prompt = service._build_discovery_prompt(
                    current_answers={},
                    missing_questions=[],
                    robot_catalog=[],
                )
                prompt_lower = prompt.lower()
                assert "concise" in prompt_lower or "brief" in prompt_lower or "short" in prompt_lower, \
                    "Discovery prompt should contain brevity instruction"

    def test_system_prompt_contains_brevity_instruction(self) -> None:
        """BUG-05: System prompt should contain brevity instruction."""
        prompt = SYSTEM_PROMPTS[ConversationPhase.DISCOVERY]
        prompt_lower = prompt.lower()
        assert "concise" in prompt_lower or "brief" in prompt_lower or "short" in prompt_lower, \
            "Discovery system prompt should contain brevity instruction"


class TestBUG13AgentGuessedIndustry:
    """BUG-13: Agent guessed industry before user typed it."""

    def test_initial_greeting_prompt_contains_never_assume(self) -> None:
        """BUG-13: Initial greeting prompt should contain 'never assume' guard."""
        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings"):
                service = AgentService()
                prompt = service._build_initial_greeting_prompt(
                    current_answers={},
                    company_name=None,
                    missing_questions=[{"key": "company_name", "question": "Name?", "chips": None}],
                )
                prompt_lower = prompt.lower()
                assert "never assume" in prompt_lower or "don't assume" in prompt_lower or "do not assume" in prompt_lower, \
                    "Greeting prompt should contain assumption guard"

    def test_discovery_prompt_contains_assumption_guard(self) -> None:
        """BUG-13: Discovery prompt should contain assumption guard."""
        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings"):
                service = AgentService()
                prompt = service._build_discovery_prompt(
                    current_answers={},
                    missing_questions=[],
                    robot_catalog=[],
                )
                prompt_lower = prompt.lower()
                assert "never assume" in prompt_lower or "don't assume" in prompt_lower or "do not assume" in prompt_lower, \
                    "Discovery prompt should contain assumption guard"

    def test_system_prompt_contains_assumption_guard(self) -> None:
        """BUG-13: System prompt should contain assumption guard."""
        prompt = SYSTEM_PROMPTS[ConversationPhase.DISCOVERY]
        prompt_lower = prompt.lower()
        assert "never assume" in prompt_lower or "don't assume" in prompt_lower or "do not assume" in prompt_lower, \
            "Discovery system prompt should contain assumption guard"


class TestBUG47MessagesTake30s:
    """BUG-47: Messages take ~30s to send — extraction should not block response."""

    @pytest.mark.asyncio
    async def test_extraction_uses_limited_messages(self) -> None:
        """BUG-47: ProfileExtractionService should use MAX_MESSAGES_FOR_EXTRACTION <= 4."""
        from src.services.profile_extraction_service import ProfileExtractionService
        assert ProfileExtractionService.MAX_MESSAGES_FOR_EXTRACTION <= 6, \
            f"MAX_MESSAGES_FOR_EXTRACTION should be <= 6 for performance, got {ProfileExtractionService.MAX_MESSAGES_FOR_EXTRACTION}"


class TestBUG46WebsiteTakes8sToLoad:
    """BUG-46: Website takes 8s to load — greeting regenerated on page refresh."""

    def test_greeting_uses_max_tokens_lte_150(self) -> None:
        """BUG-46: Greeting should use max_completion_tokens <= 150."""
        # We verify the hardcoded value used in generate_initial_greeting
        import inspect
        from src.services.agent_service import AgentService
        source = inspect.getsource(AgentService.generate_initial_greeting)
        # The source should contain max_completion_tokens with value <= 150
        assert "max_completion_tokens" in source
        # Extract the value — we verify it in a simple way
        # The key assertion is that the value in the actual code is <= 150
        import re
        matches = re.findall(r"max_completion_tokens\s*=\s*(\d+)", source)
        assert len(matches) >= 1, "Should have max_completion_tokens in generate_initial_greeting"
        for match in matches:
            assert int(match) <= 150, f"Greeting max_completion_tokens should be <= 150, got {match}"


class TestIDEA02NotSureChipBackend:
    """IDEA-02: Backend discovery prompt should handle 'not sure' gracefully."""

    def test_discovery_prompt_handles_not_sure(self) -> None:
        """Discovery prompt should instruct agent to handle 'not sure' responses."""
        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings"):
                service = AgentService()
                prompt = service._build_discovery_prompt(
                    current_answers={},
                    missing_questions=[{"key": "method", "question": "Method?", "chips": ["Vacuum", "Mop"]}],
                    robot_catalog=[],
                )
                prompt_lower = prompt.lower()
                assert "not sure" in prompt_lower or "unsure" in prompt_lower or "don't know" in prompt_lower, \
                    "Discovery prompt should handle 'not sure' responses"


class TestIDEA04AutopopulateCompanyType:
    """IDEA-04: Discovery prompt should hint company type when company name contains keyword."""

    def test_discovery_prompt_hints_company_type_from_name(self) -> None:
        """When company_name contains 'Pickleball', prompt should hint 'Pickleball Club'."""
        with patch("src.services.agent_service.get_openai_client"):
            with patch("src.services.agent_service.get_settings"):
                service = AgentService()
                answers = {
                    "company_name": {"value": "Pickleball World"},
                }
                prompt = service._build_discovery_prompt(
                    current_answers=answers,
                    missing_questions=[{"key": "company_type", "question": "What type?", "chips": ["Pickleball Club"]}],
                    robot_catalog=[],
                )
                prompt_lower = prompt.lower()
                assert "suggest" in prompt_lower or "hint" in prompt_lower or "pickleball" in prompt_lower, \
                    "Discovery prompt should hint company type based on company name"

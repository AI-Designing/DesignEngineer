"""
Unit tests for UnifiedLLMProvider (Opper-backed).
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from ai_designer.core.exceptions import LLMError
from ai_designer.core.llm_provider import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMRole,
    UnifiedLLMProvider,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_opper_response():
    """Mock successful Opper call() response."""
    response = MagicMock()
    response.message = "This is a test response from the LLM."
    response.json_payload = None
    return response


@pytest.fixture(autouse=True)
def reset_opper_singleton():
    """Reset the module-level Opper singleton between tests."""
    import ai_designer.core.llm_provider as mod

    original = mod._opper_client
    mod._opper_client = None
    yield
    mod._opper_client = original


# ---------------------------------------------------------------------------
# Schema tests (unchanged from before – no mocking needed)
# ---------------------------------------------------------------------------


class TestLLMMessage:
    """Test LLMMessage schema."""

    def test_create_message(self):
        msg = LLMMessage(role=LLMRole.USER, content="Hello!")
        assert msg.role == LLMRole.USER
        assert msg.content == "Hello!"

    def test_role_enum(self):
        assert LLMRole.SYSTEM.value == "system"
        assert LLMRole.USER.value == "user"
        assert LLMRole.ASSISTANT.value == "assistant"


class TestLLMRequest:
    """Test LLMRequest schema."""

    def test_create_request(self):
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]
        request = LLMRequest(messages=messages, model="openai/gpt-4o")
        assert len(request.messages) == 1
        assert request.model == "openai/gpt-4o"
        assert request.temperature == 0.7

    def test_temperature_bounds(self):
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]
        LLMRequest(messages=messages, model="openai/gpt-4o", temperature=0.0)
        LLMRequest(messages=messages, model="openai/gpt-4o", temperature=2.0)
        with pytest.raises(Exception):
            LLMRequest(messages=messages, model="openai/gpt-4o", temperature=-0.1)
        with pytest.raises(Exception):
            LLMRequest(messages=messages, model="openai/gpt-4o", temperature=2.1)


class TestLLMResponse:
    """Test LLMResponse schema."""

    def test_create_response(self):
        response = LLMResponse(
            content="Test response",
            model="openai/gpt-4o",
            provider="openai",
            usage={"total_tokens": 100},
            latency_ms=250.5,
        )
        assert response.content == "Test response"
        assert response.model == "openai/gpt-4o"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 100
        assert response.latency_ms == 250.5


# ---------------------------------------------------------------------------
# UnifiedLLMProvider tests with Opper mock
# ---------------------------------------------------------------------------


class TestUnifiedLLMProvider:
    """Test UnifiedLLMProvider (Opper backend)."""

    def _make_provider(self, **kwargs) -> UnifiedLLMProvider:
        """Helper to create provider with OPPER_API_KEY set."""
        with patch.dict(
            os.environ, {"OPPER_API_KEY": "test-opper-key"}  # pragma: allowlist secret
        ):
            return UnifiedLLMProvider(**kwargs)

    def test_initialization(self):
        provider = self._make_provider(
            default_model="openai/gpt-4o",
            fallback_models=["anthropic/claude-3-5-sonnet-20241022"],
            max_retries=2,
            agent_name="test_agent",
        )
        assert provider.default_model == "openai/gpt-4o"
        assert len(provider.fallback_models) == 1
        assert provider.max_retries == 2
        assert provider.total_requests == 0
        assert provider.agent_name == "test_agent"

    @patch("ai_designer.core.llm_provider._get_opper")
    def test_generate_success(self, mock_get_opper, mock_opper_response):
        """Test successful generation via Opper."""
        mock_opper = MagicMock()
        mock_opper.call.return_value = mock_opper_response
        mock_get_opper.return_value = mock_opper

        provider = self._make_provider(default_model="openai/gpt-4o")
        messages = [LLMMessage(role=LLMRole.USER, content="Hello")]

        response = provider.generate(messages=messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "This is a test response from the LLM."
        assert response.model == "openai/gpt-4o"
        assert response.provider == "openai"
        assert provider.total_requests == 1
        mock_opper.call.assert_called_once()

    @patch("ai_designer.core.llm_provider._get_opper")
    def test_generate_with_dict_messages(self, mock_get_opper, mock_opper_response):
        """Test generation with dict messages."""
        mock_opper = MagicMock()
        mock_opper.call.return_value = mock_opper_response
        mock_get_opper.return_value = mock_opper

        provider = self._make_provider()
        messages = [{"role": "user", "content": "Hello"}]

        response = provider.generate(messages=messages)
        assert response.content == "This is a test response from the LLM."
        mock_opper.call.assert_called_once()

    @patch("ai_designer.core.llm_provider._get_opper")
    def test_generate_with_system_prompt(self, mock_get_opper, mock_opper_response):
        """Test generate_with_system_prompt convenience method."""
        mock_opper = MagicMock()
        mock_opper.call.return_value = mock_opper_response
        mock_get_opper.return_value = mock_opper

        provider = self._make_provider()
        response = provider.generate_with_system_prompt(
            user_message="Create a cube",
            system_prompt="You are a CAD expert.",
        )

        assert response.content == "This is a test response from the LLM."
        call_kwargs = mock_opper.call.call_args.kwargs
        assert call_kwargs["instructions"] == "You are a CAD expert."
        assert call_kwargs["input"] == "Create a cube"

    @patch("ai_designer.core.llm_provider.time.sleep")
    @patch("ai_designer.core.llm_provider._get_opper")
    def test_retry_on_failure(self, mock_get_opper, mock_sleep, mock_opper_response):
        """Test retry logic on transient Opper failures."""
        mock_opper = MagicMock()
        mock_opper.call.side_effect = [
            Exception("Transient error 1"),
            Exception("Transient error 2"),
            mock_opper_response,
        ]
        mock_get_opper.return_value = mock_opper

        provider = self._make_provider(default_model="openai/gpt-4o", max_retries=3)
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        response = provider.generate(messages=messages)
        assert response.content == "This is a test response from the LLM."
        assert mock_opper.call.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("ai_designer.core.llm_provider.time.sleep")
    @patch("ai_designer.core.llm_provider._get_opper")
    def test_all_models_fail(self, mock_get_opper, mock_sleep):
        """Test LLMError raised when all retries fail."""
        mock_opper = MagicMock()
        mock_opper.call.side_effect = Exception("Opper error")
        mock_get_opper.return_value = mock_opper

        provider = self._make_provider(
            default_model="openai/gpt-4o",
            max_retries=1,
        )
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        with pytest.raises(LLMError) as exc_info:
            provider.generate(messages=messages)

        assert "All Opper LLM requests failed" in str(exc_info.value)

    def test_get_provider_from_model(self):
        """Test provider detection from Opper model string."""
        provider = self._make_provider()

        assert provider._get_provider_from_model("openai/gpt-4o") == "openai"
        assert provider._get_provider_from_model("gpt-4o") == "openai"
        assert (
            provider._get_provider_from_model("anthropic/claude-3-5-sonnet-20241022")
            == "anthropic"
        )
        assert provider._get_provider_from_model("gcp/gemini-2.0-flash") == "google"
        assert provider._get_provider_from_model("google/gemini-pro") == "google"
        assert provider._get_provider_from_model("fireworks/deepseek-v3") == "deepseek"

    @patch("ai_designer.core.llm_provider._get_opper")
    def test_usage_tracking(self, mock_get_opper, mock_opper_response):
        """Test that total_requests increments on each call."""
        mock_opper = MagicMock()
        mock_opper.call.return_value = mock_opper_response
        mock_get_opper.return_value = mock_opper

        provider = self._make_provider()
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        for _ in range(3):
            provider.generate(messages=messages)

        stats = provider.get_usage_stats()
        assert stats["total_requests"] == 3

        provider.reset_usage_stats()
        assert provider.get_usage_stats()["total_requests"] == 0

    def test_missing_opper_api_key_raises(self):
        """Test that missing OPPER_API_KEY raises LLMError on first call."""
        import ai_designer.core.llm_provider as mod

        mod._opper_client = None

        env_without_key = {k: v for k, v in os.environ.items() if k != "OPPER_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            provider = UnifiedLLMProvider(default_model="openai/gpt-4o")
            with pytest.raises(LLMError, match="OPPER_API_KEY"):
                provider.generate(
                    messages=[LLMMessage(role=LLMRole.USER, content="test")]
                )

    @patch("ai_designer.core.llm_provider._get_opper")
    def test_opper_tags_sent(self, mock_get_opper, mock_opper_response):
        """Verify agent tag is forwarded to Opper for analytics."""
        mock_opper = MagicMock()
        mock_opper.call.return_value = mock_opper_response
        mock_get_opper.return_value = mock_opper

        provider = self._make_provider(agent_name="planner")
        provider.generate(messages=[LLMMessage(role=LLMRole.USER, content="plan")])

        call_kwargs = mock_opper.call.call_args.kwargs
        assert call_kwargs["tags"]["agent"] == "planner"

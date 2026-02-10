"""
Unit tests for UnifiedLLMProvider.
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


@pytest.fixture
def mock_litellm_response():
    """Mock successful litellm response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "This is a test response from the LLM."
    response.choices[0].finish_reason = "stop"
    response.usage = MagicMock()
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 20
    response.usage.total_tokens = 30
    return response


class TestLLMMessage:
    """Test LLMMessage schema."""

    def test_create_message(self):
        """Test creating LLM message."""
        msg = LLMMessage(role=LLMRole.USER, content="Hello!")
        assert msg.role == LLMRole.USER
        assert msg.content == "Hello!"

    def test_role_enum(self):
        """Test role enumeration."""
        assert LLMRole.SYSTEM.value == "system"
        assert LLMRole.USER.value == "user"
        assert LLMRole.ASSISTANT.value == "assistant"


class TestLLMRequest:
    """Test LLMRequest schema."""

    def test_create_request(self):
        """Test creating LLM request."""
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]
        request = LLMRequest(messages=messages, model="gpt-4o")

        assert len(request.messages) == 1
        assert request.model == "gpt-4o"
        assert request.temperature == 0.7  # default

    def test_temperature_bounds(self):
        """Test temperature validation."""
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        # Valid
        LLMRequest(messages=messages, model="gpt-4o", temperature=0.0)
        LLMRequest(messages=messages, model="gpt-4o", temperature=2.0)

        # Invalid
        with pytest.raises(Exception):  # Pydantic validation error
            LLMRequest(messages=messages, model="gpt-4o", temperature=-0.1)

        with pytest.raises(Exception):
            LLMRequest(messages=messages, model="gpt-4o", temperature=2.1)


class TestLLMResponse:
    """Test LLMResponse schema."""

    def test_create_response(self):
        """Test creating LLM response."""
        response = LLMResponse(
            content="Test response",
            model="gpt-4o",
            provider="openai",
            usage={"total_tokens": 100},
            latency_ms=250.5,
        )

        assert response.content == "Test response"
        assert response.model == "gpt-4o"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 100
        assert response.latency_ms == 250.5


class TestUnifiedLLMProvider:
    """Test UnifiedLLMProvider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = UnifiedLLMProvider(
            default_model="gpt-4o",
            fallback_models=["claude-3-5-sonnet-20241022"],
            max_retries=2,
        )

        assert provider.default_model == "gpt-4o"
        assert len(provider.fallback_models) == 1
        assert provider.max_retries == 2
        assert provider.total_requests == 0

    @patch("ai_designer.core.llm_provider.litellm.completion")
    def test_generate_success(self, mock_completion, mock_litellm_response):
        """Test successful generation."""
        mock_completion.return_value = mock_litellm_response

        provider = UnifiedLLMProvider(default_model="gpt-4o")
        messages = [LLMMessage(role=LLMRole.USER, content="Hello")]

        response = provider.generate(messages=messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "This is a test response from the LLM."
        assert response.model == "gpt-4o"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 30
        assert provider.total_requests == 1
        assert provider.total_tokens == 30

    @patch("ai_designer.core.llm_provider.litellm.completion")
    def test_generate_with_dict_messages(self, mock_completion, mock_litellm_response):
        """Test generation with dict messages."""
        mock_completion.return_value = mock_litellm_response

        provider = UnifiedLLMProvider()
        messages = [{"role": "user", "content": "Hello"}]

        response = provider.generate(messages=messages)

        assert response.content == "This is a test response from the LLM."
        mock_completion.assert_called_once()

    @patch("ai_designer.core.llm_provider.litellm.completion")
    def test_generate_with_system_prompt(self, mock_completion, mock_litellm_response):
        """Test generate_with_system_prompt convenience method."""
        mock_completion.return_value = mock_litellm_response

        provider = UnifiedLLMProvider()
        response = provider.generate_with_system_prompt(
            user_message="Create a cube",
            system_prompt="You are a CAD expert.",
        )

        assert response.content == "This is a test response from the LLM."

        # Verify system message was included
        call_args = mock_completion.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @patch("ai_designer.core.llm_provider.litellm.completion")
    @patch("ai_designer.core.llm_provider.time.sleep")  # Mock sleep to speed up test
    def test_retry_on_failure(self, mock_sleep, mock_completion, mock_litellm_response):
        """Test retry logic on transient failures."""
        # Fail twice, then succeed
        mock_completion.side_effect = [
            Exception("Transient error 1"),
            Exception("Transient error 2"),
            mock_litellm_response,
        ]

        provider = UnifiedLLMProvider(default_model="gpt-4o", max_retries=3)
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        response = provider.generate(messages=messages)

        assert response.content == "This is a test response from the LLM."
        assert mock_completion.call_count == 3
        assert mock_sleep.call_count == 2  # Backoff after first 2 failures

    @patch("ai_designer.core.llm_provider.litellm.completion")
    @patch("ai_designer.core.llm_provider.time.sleep")
    def test_fallback_to_secondary_model(
        self, mock_sleep, mock_completion, mock_litellm_response
    ):
        """Test fallback to secondary model."""

        # Primary model fails all retries, secondary succeeds
        def side_effect_func(*args, **kwargs):
            if kwargs["model"] == "gpt-4o":
                raise Exception("Primary model failed")
            else:
                return mock_litellm_response

        mock_completion.side_effect = side_effect_func

        provider = UnifiedLLMProvider(
            default_model="gpt-4o",
            fallback_models=["claude-3-5-sonnet-20241022"],
            max_retries=2,
        )
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        response = provider.generate(messages=messages)

        assert response.content == "This is a test response from the LLM."
        assert response.model == "claude-3-5-sonnet-20241022"
        assert response.provider == "anthropic"

    @patch("ai_designer.core.llm_provider.litellm.completion")
    @patch("ai_designer.core.llm_provider.time.sleep")
    def test_all_models_fail(self, mock_sleep, mock_completion):
        """Test error when all models fail."""
        mock_completion.side_effect = Exception("All models failed")

        provider = UnifiedLLMProvider(
            default_model="gpt-4o",
            fallback_models=["claude-3-5-sonnet-20241022"],
            max_retries=1,
        )
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        with pytest.raises(LLMError) as exc_info:
            provider.generate(messages=messages)

        assert "All LLM requests failed" in str(exc_info.value)

    def test_get_provider_from_model(self):
        """Test provider detection from model name."""
        provider = UnifiedLLMProvider()

        assert provider._get_provider_from_model("gpt-4o") == "openai"
        assert (
            provider._get_provider_from_model("claude-3-5-sonnet-20241022")
            == "anthropic"
        )
        assert provider._get_provider_from_model("gemini-1.5-pro") == "google"
        assert provider._get_provider_from_model("deepseek-chat") == "deepseek"
        assert provider._get_provider_from_model("ollama/llama2") == "ollama"
        assert provider._get_provider_from_model("unknown-model") == "unknown"

    @patch("ai_designer.core.llm_provider.litellm.completion")
    def test_usage_tracking(self, mock_completion, mock_litellm_response):
        """Test usage statistics tracking."""
        mock_completion.return_value = mock_litellm_response

        provider = UnifiedLLMProvider()
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        # Make 3 requests
        for _ in range(3):
            provider.generate(messages=messages)

        stats = provider.get_usage_stats()
        assert stats["total_requests"] == 3
        assert stats["total_tokens"] == 90  # 30 tokens * 3 requests

        # Reset stats
        provider.reset_usage_stats()
        stats = provider.get_usage_stats()
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",  # pragma: allowlist secret
            "GOOGLE_API_KEY": "gemini-key",  # pragma: allowlist secret
        },
    )
    def test_api_key_configuration(self):
        """Test API key configuration from environment."""
        provider = UnifiedLLMProvider()
        provider._configure_api_keys()

        assert os.environ.get("OPENAI_API_KEY") == "test-key"
        assert os.environ.get("GEMINI_API_KEY") == "gemini-key"

    @patch("ai_designer.core.llm_provider.litellm.completion")
    def test_custom_temperature(self, mock_completion, mock_litellm_response):
        """Test custom temperature parameter."""
        mock_completion.return_value = mock_litellm_response

        provider = UnifiedLLMProvider()
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        provider.generate(messages=messages, temperature=0.2)

        call_args = mock_completion.call_args
        assert call_args[1]["temperature"] == 0.2

    @patch("ai_designer.core.llm_provider.litellm.completion")
    def test_max_tokens_parameter(self, mock_completion, mock_litellm_response):
        """Test max_tokens parameter."""
        mock_completion.return_value = mock_litellm_response

        provider = UnifiedLLMProvider()
        messages = [LLMMessage(role=LLMRole.USER, content="Test")]

        provider.generate(messages=messages, max_tokens=500)

        call_args = mock_completion.call_args
        assert call_args[1]["max_tokens"] == 500

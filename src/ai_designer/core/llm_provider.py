"""
Unified LLM provider using LiteLLM for multi-provider support.

This module provides a clean abstraction over multiple LLM providers:
- OpenAI (GPT-4, GPT-4o, etc.)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus, etc.)
- Google (Gemini 1.5 Pro, etc.)
- DeepSeek (via Ollama or API)

Features:
- Automatic retry with exponential backoff
- Provider fallback chains
- Rate limiting and token tracking
- Structured logging
- Type-safe responses
"""

import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import litellm

from ai_designer.core.exceptions import LLMError
from ai_designer.core.logging_config import get_logger
from ai_designer.schemas.llm_schemas import (  # noqa: F401  re-exported for backward compat
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMRole,
)

logger = get_logger(__name__)


class UnifiedLLMProvider:
    """
    Unified LLM provider using LiteLLM.

    Supports multiple providers with automatic retry and fallback.
    """

    def __init__(
        self,
        default_model: str = "gpt-4o",
        fallback_models: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: int = 60,
        enable_caching: bool = True,
    ):
        """
        Initialize the unified LLM provider.

        Args:
            default_model: Primary model to use
            fallback_models: List of fallback models if primary fails
            max_retries: Maximum retry attempts per model
            timeout: Request timeout in seconds
            enable_caching: Enable LiteLLM caching
        """
        self.default_model = default_model
        self.fallback_models = fallback_models or []
        self.max_retries = max_retries
        self.timeout = timeout

        # Configure LiteLLM
        litellm.drop_params = True  # Drop unsupported params instead of erroring
        litellm.set_verbose = False  # Disable verbose logging

        if enable_caching:
            litellm.cache = litellm.Cache()

        # API key configuration from environment
        self._configure_api_keys()

        # Usage tracking
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0

        logger.info(
            "Initialized UnifiedLLMProvider",
            default_model=default_model,
            fallback_models=fallback_models,
            max_retries=max_retries,
        )

    def _configure_api_keys(self) -> None:
        """Configure API keys from environment variables."""
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

        # Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")

        # Google
        if os.getenv("GOOGLE_API_KEY"):
            os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

        # DeepSeek
        if os.getenv("DEEPSEEK_API_KEY"):
            os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY")

        # Ollama base URL (for local models)
        if os.getenv("OLLAMA_BASE_URL"):
            os.environ["OLLAMA_API_BASE"] = os.getenv("OLLAMA_BASE_URL")

    def generate(
        self,
        messages: Union[List[LLMMessage], List[Dict[str, str]]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate completion from LLM.

        Args:
            messages: Conversation messages
            model: Override default model
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters

        Returns:
            LLMResponse with generated content

        Raises:
            LLMError: If all attempts fail
        """
        # Convert to LLMMessage if dicts provided
        if messages and isinstance(messages[0], dict):
            messages = [
                LLMMessage(role=LLMRole(m["role"]), content=m["content"])
                for m in messages
            ]

        # Prepare request
        target_model = model or self.default_model
        models_to_try = [target_model] + self.fallback_models

        last_error = None
        start_time = time.time()

        # Try each model with retries
        for model_name in models_to_try:
            for attempt in range(self.max_retries):
                try:
                    logger.debug(
                        "Attempting LLM request",
                        model=model_name,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                    )

                    # Convert messages to dict format for litellm
                    message_dicts = [
                        {"role": m.role.value, "content": m.content} for m in messages
                    ]

                    # Call LiteLLM
                    response = litellm.completion(
                        model=model_name,
                        messages=message_dicts,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=self.timeout,
                        **kwargs,
                    )

                    # Calculate latency
                    latency_ms = (time.time() - start_time) * 1000

                    # Extract response
                    content = response.choices[0].message.content
                    finish_reason = response.choices[0].finish_reason

                    # Track usage
                    usage = {}
                    if hasattr(response, "usage") and response.usage:
                        usage = {
                            "prompt_tokens": getattr(
                                response.usage, "prompt_tokens", 0
                            ),
                            "completion_tokens": getattr(
                                response.usage, "completion_tokens", 0
                            ),
                            "total_tokens": getattr(response.usage, "total_tokens", 0),
                        }
                        self.total_tokens += usage.get("total_tokens", 0)

                    self.total_requests += 1

                    # Calculate per-call cost (non-fatal if unsupported)
                    call_cost: Optional[float] = None
                    try:
                        call_cost = litellm.completion_cost(
                            completion_response=response
                        )
                        if call_cost:
                            self.total_cost += call_cost
                    except Exception:  # noqa: BLE001
                        pass

                    # Determine provider
                    provider = self._get_provider_from_model(model_name)

                    llm_response = LLMResponse(
                        content=content,
                        model=model_name,
                        provider=provider,
                        usage=usage,
                        finish_reason=finish_reason,
                        latency_ms=latency_ms,
                        cost_usd=call_cost,
                    )

                    logger.debug(
                        "LLM call cost",
                        model=model_name,
                        cost_usd=call_cost,
                        total_tokens=usage.get("total_tokens", 0),
                    )
                    logger.info(
                        "LLM request successful",
                        model=model_name,
                        provider=provider,
                        latency_ms=latency_ms,
                        total_tokens=usage.get("total_tokens", 0),
                    )

                    return llm_response

                except Exception as e:
                    last_error = e
                    logger.warning(
                        "LLM request failed",
                        model=model_name,
                        attempt=attempt + 1,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

                    # Exponential backoff before retry
                    if attempt < self.max_retries - 1:
                        backoff_time = 2**attempt
                        time.sleep(backoff_time)

            # If all retries failed for this model, try next fallback
            logger.error(
                "All retries failed for model",
                model=model_name,
                max_retries=self.max_retries,
                last_error=str(last_error),
            )

        # All models failed
        error_msg = f"All LLM requests failed. Last error: {last_error}"
        logger.error("LLM generation failed completely", error=error_msg)
        raise LLMError(
            error_msg, {"models_tried": models_to_try, "last_error": str(last_error)}
        )

    def generate_with_system_prompt(
        self,
        user_message: str,
        system_prompt: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Convenience method to generate with system prompt.

        Args:
            user_message: User's input message
            system_prompt: System instruction
            model: Override default model
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated content
        """
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content=system_prompt),
            LLMMessage(role=LLMRole.USER, content=user_message),
        ]
        return self.generate(messages=messages, model=model, **kwargs)

    def _get_provider_from_model(self, model: str) -> str:
        """Determine provider from model name."""
        model_lower = model.lower()

        if any(x in model_lower for x in ["gpt", "openai"]):
            return LLMProvider.OPENAI.value
        elif any(x in model_lower for x in ["claude", "anthropic"]):
            return LLMProvider.ANTHROPIC.value
        elif any(x in model_lower for x in ["gemini", "google"]):
            return LLMProvider.GOOGLE.value
        elif "deepseek" in model_lower:
            return LLMProvider.DEEPSEEK.value
        elif "ollama" in model_lower:
            return LLMProvider.OLLAMA.value
        else:
            return "unknown"

    async def complete_stream(self, request: "LLMRequest") -> AsyncGenerator[str, None]:
        """Yield content chunks from a streaming LLM completion.

        Uses ``litellm.acompletion`` with ``stream=True`` so the event loop is
        never blocked.  Streaming calls are **not** retried — any exception
        propagates immediately as ``LLMError``.

        Args:
            request: The ``LLMRequest`` to send.

        Yields:
            Non-empty string chunks as they arrive from the model.

        Raises:
            LLMError: Immediately on any provider or network error.
        """
        message_dicts = [
            {"role": m.role.value, "content": m.content} for m in request.messages
        ]
        try:
            response = await litellm.acompletion(
                model=request.model or self.default_model,
                messages=message_dicts,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                timeout=self.timeout,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Streaming LLM request failed: {exc}") from exc

    def get_total_cost(self) -> float:
        """Return cumulative USD cost across all calls since last reset."""
        return self.total_cost

    def reset_cost_tracking(self) -> None:
        """Reset only the cost counter (leaves request/token counts intact)."""
        self.total_cost = 0.0
        logger.info("Cost tracking reset")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }

    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        logger.info("Usage statistics reset")

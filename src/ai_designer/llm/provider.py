"""
Unified LLM provider backed by the Opper.ai platform.

This module provides a clean abstraction over Opper's task-completion API
which supports 60+ LLM providers through a single API key:

- OpenAI (GPT-4o, GPT-4.1, o3, etc.)
- Anthropic (Claude 3.5 / 4 Sonnet, Opus, Haiku)
- Google (Gemini 2.0 Flash, 2.5 Pro, etc.)
- Mistral, DeepSeek, xAI Grok, Groq, Perplexity and more

One key: ``OPPER_API_KEY``  (https://platform.opper.ai/)

Features:
- All 60+ Opper-supported models selectable per agent
- Built-in tracing, cost tracking, and task evals via Opper platform
- Per-agent tags for cost/analytics filtering
- Retry with exponential backoff on transient failures
- Same public interface as the previous LiteLLM-based provider:
  ``generate()``, ``generate_with_system_prompt()``, ``complete_stream()``
"""

import asyncio
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from opperai import Opper

from ai_designer.core.exceptions import LLMError
from ai_designer.core.logging_config import get_logger  # noqa: F401 — shared infra
from ai_designer.schemas.llm_schemas import (  # noqa: F401  re-exported for backward compat
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMRole,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level Opper singleton – initialised lazily so tests can override
# OPPER_API_KEY before the first call.
# ---------------------------------------------------------------------------
_opper_client: Optional[Opper] = None


def _get_opper() -> Opper:
    """Return (and lazily create) the module-level Opper client."""
    global _opper_client
    if _opper_client is None:
        api_key = os.getenv("OPPER_API_KEY", "")
        if not api_key:
            raise LLMError(
                "OPPER_API_KEY is not set. "
                "Get your key at https://platform.opper.ai/ and add it to .env."
            )
        _opper_client = Opper(http_bearer=api_key)
    return _opper_client


class UnifiedLLMProvider:
    """
    Unified LLM provider backed by Opper.ai.

    Supports any model available on the Opper platform with automatic retry
    and optional fallback chains.  The ``agent_name`` parameter is used as the
    Opper task name and as a tag so usage can be analysed per agent in the
    Opper platform dashboard.
    """

    def __init__(
        self,
        default_model: str = "openai/gpt-4o",
        fallback_models: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: int = 60,
        enable_caching: bool = True,  # kept for API compat, handled by Opper platform
        agent_name: str = "default",
    ):
        """
        Initialise the unified LLM provider.

        Args:
            default_model: Primary Opper model string, e.g. ``"openai/gpt-4o"``.
            fallback_models: Ordered list of fallback model strings.
            max_retries: Maximum retry attempts per model.
            timeout: Request timeout in seconds (passed through to Opper).
            enable_caching: Kept for backward compatibility (Opper handles caching).
            agent_name: Logical agent identifier used for Opper task naming and tags.
        """
        self.default_model = default_model
        self.fallback_models = fallback_models or []
        self.max_retries = max_retries
        self.timeout = timeout
        self.agent_name = agent_name

        # Usage tracking (approximate — Opper platform has authoritative cost data)
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0

        logger.info(
            "Initialized UnifiedLLMProvider (Opper)",
            agent_name=agent_name,
            default_model=default_model,
            fallback_models=fallback_models,
            max_retries=max_retries,
        )

    def _messages_to_opper_input(
        self,
        messages: List[LLMMessage],
    ) -> tuple[str, str]:
        """Split a message list into (system_prompt, user_text) for Opper.

        Opper's ``call()`` takes ``instructions`` (system role) and a plain
        ``input`` dict/string (user content).  We concatenate any assistant
        turns into the user context so no information is lost.
        """
        system_parts: List[str] = []
        user_parts: List[str] = []

        for m in messages:
            if m.role == LLMRole.SYSTEM:
                system_parts.append(m.content)
            elif m.role == LLMRole.USER:
                user_parts.append(m.content)
            elif m.role == LLMRole.ASSISTANT:
                # Prepend previous assistant turn as context
                user_parts.append(f"[Previous assistant response]: {m.content}")

        system_prompt = (
            "\n\n".join(system_parts)
            if system_parts
            else "You are a helpful assistant."
        )
        user_text = "\n\n".join(user_parts) if user_parts else ""
        return system_prompt, user_text

    def generate(
        self,
        messages: Union[List[LLMMessage], List[Dict[str, str]]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion via the Opper platform.

        Args:
            messages: Conversation messages (LLMMessage objects or plain dicts).
            model: Override the default model (Opper model string, e.g.
                ``"openai/gpt-4o"`` or ``"anthropic/claude-3-5-sonnet-20241022"``).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters (ignored; kept for API compat).

        Returns:
            LLMResponse with generated content.

        Raises:
            LLMError: If all retry/fallback attempts fail.
        """
        # Unwrap LLMRequest if passed directly (agents pass the full request object)
        if isinstance(messages, LLMRequest):
            llm_req: LLMRequest = messages
            if model is None and llm_req.model:
                model = llm_req.model
            if llm_req.temperature is not None:
                temperature = llm_req.temperature
            if llm_req.max_tokens is not None:
                max_tokens = llm_req.max_tokens
            messages = llm_req.messages

        # Normalise to LLMMessage list
        if messages and isinstance(messages[0], dict):
            messages = [
                LLMMessage(role=LLMRole(m["role"]), content=m["content"])
                for m in messages
            ]

        system_prompt, user_text = self._messages_to_opper_input(messages)
        target_model = model or self.default_model
        models_to_try = [target_model] + self.fallback_models

        last_error: Optional[Exception] = None
        start_time = time.time()
        opper = _get_opper()

        # Build Opper model param: single string or list for fallbacks
        opper_model: Any = (
            models_to_try[0]
            if len(models_to_try) == 1
            else [
                {"name": m, "options": {"temperature": temperature}}
                for m in models_to_try
            ]
        )

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    "Opper call attempt",
                    agent=self.agent_name,
                    model=target_model,
                    attempt=attempt + 1,
                )

                response = opper.call(
                    name=f"{self.agent_name}_generate",
                    instructions=system_prompt,
                    input=user_text or "Continue.",
                    model=opper_model,
                    tags={
                        "agent": self.agent_name,
                        "env": os.getenv("ENV", "development"),
                    },
                )

                latency_ms = (time.time() - start_time) * 1000
                content = response.message or ""

                self.total_requests += 1

                provider = self._get_provider_from_model(target_model)
                llm_response = LLMResponse(
                    content=content,
                    model=target_model,
                    provider=provider,
                    usage={},
                    finish_reason="stop",
                    latency_ms=latency_ms,
                    cost_usd=None,  # Authoritative cost is in Opper platform dashboard
                )

                logger.info(
                    "Opper call successful",
                    agent=self.agent_name,
                    model=target_model,
                    latency_ms=latency_ms,
                )
                return llm_response

            except Exception as e:
                last_error = e
                logger.warning(
                    "Opper call failed",
                    agent=self.agent_name,
                    model=target_model,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)

        error_msg = f"All Opper LLM requests failed for agent '{self.agent_name}'. Last error: {last_error}"
        logger.error("LLM generation failed", error=error_msg)
        raise LLMError(
            error_msg, {"models_tried": models_to_try, "last_error": str(last_error)}
        )

    async def agenerate(
        self,
        messages: "Union[List[LLMMessage], List[Dict[str, str]], LLMRequest]",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Async wrapper around generate() for use in async pipeline nodes."""
        return await asyncio.to_thread(
            self.generate, messages, model, temperature, max_tokens, **kwargs
        )

    def generate_with_system_prompt(
        self,
        user_message: str,
        system_prompt: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Convenience method: generate with explicit system prompt.

        Args:
            user_message: User's input message.
            system_prompt: System instruction.
            model: Override default model.
            **kwargs: Additional parameters.

        Returns:
            LLMResponse with generated content.
        """
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content=system_prompt),
            LLMMessage(role=LLMRole.USER, content=user_message),
        ]
        return self.generate(messages=messages, model=model, **kwargs)

    def _get_provider_from_model(self, model: str) -> str:
        """Determine provider label from Opper model string."""
        model_lower = model.lower()

        if any(x in model_lower for x in ["gpt", "openai"]):
            return LLMProvider.OPENAI.value
        elif any(x in model_lower for x in ["claude", "anthropic"]):
            return LLMProvider.ANTHROPIC.value
        elif any(x in model_lower for x in ["gemini", "google", "gcp"]):
            return LLMProvider.GOOGLE.value
        elif "deepseek" in model_lower:
            return LLMProvider.DEEPSEEK.value
        else:
            return "opper"

    async def complete_stream(self, request: "LLMRequest") -> AsyncGenerator[str, None]:
        """Yield content from an LLM completion as an async generator.

        NOTE: Opper's standard SDK does not expose a streaming endpoint.
        This implementation runs the blocking ``opper.call()`` in a thread
        executor so the event loop is not blocked, then yields the full
        response content as one chunk.  Replace with a native Opper streaming
        call when the SDK exposes one.

        Args:
            request: The LLMRequest to send.

        Yields:
            Non-empty string chunks.

        Raises:
            LLMError: On any provider or network error.
        """
        messages = request.messages
        system_prompt, user_text = self._messages_to_opper_input(messages)
        target_model = request.model or self.default_model
        opper = _get_opper()

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: opper.call(
                    name=f"{self.agent_name}_stream",
                    instructions=system_prompt,
                    input=user_text or "Continue.",
                    model=target_model,
                    tags={
                        "agent": self.agent_name,
                        "env": os.getenv("ENV", "development"),
                        "stream": "true",
                    },
                ),
            )
            content = response.message or ""
            if content:
                yield content
        except Exception as exc:
            raise LLMError(f"Opper streaming call failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Usage / cost helpers (approximate local counters; authoritative data
    # is in the Opper platform dashboard at https://platform.opper.ai/)
    # ------------------------------------------------------------------

    def get_total_cost(self) -> float:
        """Return cumulative local cost counter.

        NOTE: For authoritative per-agent cost data use the Opper platform
        dashboard where costs are tracked by agent tag.
        """
        return self.total_cost

    def reset_cost_tracking(self) -> None:
        """Reset the local cost counter."""
        self.total_cost = 0.0
        logger.info("Cost tracking reset")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get local usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }

    def reset_usage_stats(self) -> None:
        """Reset local usage statistics."""
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        logger.info("Usage statistics reset")

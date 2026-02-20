"""
Abstract base class for all AI Designer agents.

Provides common initialization, LLM call-with-retry logic, and interface
enforcement so that PlannerAgent, GeneratorAgent, ValidatorAgent, and
OrchestratorAgent all share the same structure.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from ai_designer.core.exceptions import LLMError
from ai_designer.core.llm_provider import UnifiedLLMProvider
from ai_designer.schemas.design_state import AgentType
from ai_designer.schemas.llm_schemas import LLMMessage, LLMRequest, LLMResponse, LLMRole

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all agents in the multi-agent CAD pipeline.

    Subclasses must implement ``execute()`` and set a class-level
    ``SYSTEM_PROMPT`` constant for LLM interactions.

    Attributes:
        llm_provider: Shared ``UnifiedLLMProvider`` for all LLM calls.
        agent_type: Identifies this agent in the pipeline.
        max_retries: Retry budget for ``_call_llm``.
        default_temperature: Passed to LLM when callers don't override.
    """

    def __init__(
        self,
        llm_provider: UnifiedLLMProvider,
        agent_type: AgentType,
        max_retries: int = 3,
        temperature: float = 0.7,
    ) -> None:
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(f"Temperature must be in [0.0, 1.0], got {temperature}")

        self.llm_provider = llm_provider
        self.agent_type = agent_type
        self.max_retries = max_retries
        self.default_temperature = temperature

        logger.info(
            "Initialized %s (max_retries=%d, temperature=%.2f)",
            self.name,
            max_retries,
            temperature,
        )

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Run this agent's primary operation.

        All subclasses must implement this method.
        """

    # ------------------------------------------------------------------
    # Helpers available to subclasses
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Human-readable class name, e.g. 'PlannerAgent'."""
        return self.__class__.__name__

    def _build_llm_request(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMRequest:
        """Construct a typed ``LLMRequest`` with system + user messages.

        Args:
            user_message: The user-turn content.
            system_prompt: Override the class-level ``SYSTEM_PROMPT`` if given.
            temperature: Overrides ``default_temperature`` when provided.
            max_tokens: Maximum tokens for the completion.

        Returns:
            A fully-populated ``LLMRequest`` ready to pass to ``_call_llm``.
        """
        sys_content = system_prompt or getattr(self, "SYSTEM_PROMPT", "")
        messages: List[LLMMessage] = []

        if sys_content:
            messages.append(LLMMessage(role=LLMRole.SYSTEM, content=sys_content))

        messages.append(LLMMessage(role=LLMRole.USER, content=user_message))

        return LLMRequest(
            messages=messages,
            model=self.llm_provider.default_model,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens,
        )

    async def _call_llm(
        self,
        request: LLMRequest,
        context: str = "",
    ) -> LLMResponse:
        """Call the LLM with automatic retry on transient errors.

        Args:
            request: The ``LLMRequest`` to send.
            context: Short description included in log messages (e.g. task ID).

        Returns:
            ``LLMResponse`` from the provider.

        Raises:
            LLMError: After exhausting all ``max_retries`` attempts.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.llm_provider.generate(request)
                return response

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "%s _call_llm attempt %d/%d failed%s: %s",
                    self.name,
                    attempt,
                    self.max_retries,
                    f" [{context}]" if context else "",
                    exc,
                )

                if attempt < self.max_retries:
                    # Exponential back-off: 1s, 2s, 4s …
                    await asyncio.sleep(2 ** (attempt - 1))

        raise LLMError(
            f"{self.name} failed after {self.max_retries} attempts"
            + (f" [{context}]" if context else "")
        ) from last_error

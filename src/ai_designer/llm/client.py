"""DEPRECATED – Legacy LLM client (Google Gemini via LangChain).

All generation now goes through
``ai_designer.core.llm_provider.UnifiedLLMProvider`` (Opper-backed).
This module is kept **for backward compatibility only**; new code should
not import from here.
"""

import logging
import warnings
from typing import Any, Optional

from ai_designer.core.llm_provider import UnifiedLLMProvider

logger = logging.getLogger(__name__)


class LLMClient:
    """DEPRECATED wrapper – delegates to :class:`UnifiedLLMProvider`."""

    def __init__(
        self,
        api_key: Optional[str] = None,  # ignored – Opper key comes from env
        model_name: Optional[str] = None,
        provider: str = "google",
    ):
        warnings.warn(
            "LLMClient is deprecated. Use UnifiedLLMProvider instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if model_name:
            default_model = (
                f"google/{model_name}" if provider == "google" else model_name
            )
        else:
            default_model = "gcp/gemini-2.0-flash"

        self._provider = UnifiedLLMProvider(
            default_model=default_model,
            agent_name="legacy_llm_client",
        )
        logger.warning(
            "LLMClient is deprecated – please migrate to UnifiedLLMProvider."
        )

    def generate_command(self, nl_command: str, state: Any = None) -> str:
        """Generate a FreeCAD command. Delegates to UnifiedLLMProvider."""
        system_prompt = (
            "You are an expert FreeCAD Python scripter. "
            "Given a user request, generate only valid FreeCAD Python code. "
            "No markdown, no explanations."
        )
        context = f"User request: {nl_command}"
        if state is not None:
            import json

            try:
                context += f"\nCurrent state: {json.dumps(state, indent=2)}"
            except (TypeError, ValueError):
                context += f"\nCurrent state: {state}"
        resp = self._provider.generate_with_system_prompt(
            user_message=context, system_prompt=system_prompt
        )
        return resp.content

    def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a plain text response. Delegates to UnifiedLLMProvider."""
        full_prompt = f"Context: {context}\n\nPrompt: {prompt}" if context else prompt
        resp = self._provider.generate_with_system_prompt(
            user_message=full_prompt,
            system_prompt=system_prompt or "You are a helpful assistant.",
        )
        return resp.content

    def chat(self, messages: list, **kwargs: Any) -> str:
        """Send a multi-turn message list. Delegates to UnifiedLLMProvider."""
        resp = self._provider.generate(messages=messages)
        return resp.content

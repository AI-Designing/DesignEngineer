"""DEPRECATED – Online code generation client (LiteLLM-backed).

Replaced by the Opper-backed ``UnifiedLLMProvider``.
Stubs preserved for backward-compat imports only.
"""
import warnings
from dataclasses import dataclass
from typing import Optional

from ai_designer.core.llm_provider import UnifiedLLMProvider


@dataclass
class OnlineCodeGenConfig:
    model: str = "gcp/gemini-2.0-flash"
    fallback_model: str = "openai/gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 8192
    timeout: int = 120


class OnlineCodeGenClient:
    """DEPRECATED wrapper – delegates to :class:`UnifiedLLMProvider`."""

    def __init__(self, config: Optional[OnlineCodeGenConfig] = None):
        warnings.warn(
            "OnlineCodeGenClient is deprecated. Use UnifiedLLMProvider instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.config = config or OnlineCodeGenConfig()
        self._provider = UnifiedLLMProvider(
            default_model=self.config.model,
            fallback_models=[self.config.fallback_model],
            agent_name="legacy_codegen_client",
        )

    def generate_code(self, prompt: str, system_prompt: str = "") -> str:
        resp = self._provider.generate_with_system_prompt(
            user_message=prompt,
            system_prompt=system_prompt or "You are an expert FreeCAD Python scripter.",
        )
        return resp.content

"""DEPRECATED – DeepSeek R1 via Ollama (local model).

Replaced by the Opper-backed ``UnifiedLLMProvider``.
Stubs preserved for backward-compat imports only.
"""
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DeepSeekMode(Enum):
    LOCAL = "local"
    API = "api"
    HYBRID = "hybrid"


@dataclass
class DeepSeekConfig:
    host: str = "localhost"
    port: int = 11434
    model_name: str = "deepseek-r1:14b"
    timeout: int = 600
    max_tokens: int = 8192
    temperature: float = 0.1
    top_p: float = 0.95
    reasoning_enabled: bool = True
    stream: bool = True
    fallback_to_gemini: bool = True
    mode: DeepSeekMode = DeepSeekMode.LOCAL


@dataclass
class ReasoningStep:
    step_number: int
    description: str
    code_snippet: Optional[str] = None


@dataclass
class DeepSeekResponse:
    content: str
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    model: str = "deepseek-r1:14b"
    success: bool = True
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0


class DeepSeekR1Client:
    """DEPRECATED – local Ollama client stub.

    All traffic now routes through Opper via ``UnifiedLLMProvider``.
    """

    def __init__(self, config: Optional[DeepSeekConfig] = None):
        warnings.warn(
            "DeepSeekR1Client is deprecated. Use UnifiedLLMProvider instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.config = config or DeepSeekConfig()
        self.is_available = False

    async def generate(self, prompt: str, **kwargs: Any) -> DeepSeekResponse:
        raise NotImplementedError(
            "DeepSeekR1Client is deprecated. Use UnifiedLLMProvider instead."
        )

    def health_check(self) -> bool:
        return False

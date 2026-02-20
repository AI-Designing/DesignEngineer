"""
LLM-related Pydantic schemas used across the AI Designer system.

Moved here from core/llm_provider.py to provide a single source of truth
for LLM request/response data structures.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"


class LLMRole(str, Enum):
    """Message roles in conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    """A single message in LLM conversation."""

    role: LLMRole
    content: str


class LLMRequest(BaseModel):
    """Request to LLM provider."""

    messages: List[LLMMessage]
    model: str = Field(
        ...,
        description="Model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stop: Optional[List[str]] = None


class LLMResponse(BaseModel):
    """Response from LLM provider."""

    content: str
    model: str
    provider: str
    usage: Dict[str, int] = Field(default_factory=dict)
    finish_reason: Optional[str] = None
    latency_ms: Optional[float] = None
    cost_usd: Optional[float] = None

"""
Unified LLM Provider Manager
Integrates DeepSeek R1 with existing Google Gemini and other LLM providers
Allows seamless switching between models via CLI commands

MIGRATION NOTE: New code should use ``ai_designer.core.llm_provider.UnifiedLLMProvider``
(litellm-backed).  This manager is kept for backward compatibility with ``cli.py``
and other legacy callers; internally it now delegates generation calls to
``UnifiedLLMProvider`` while preserving the old dataclass-based external interface.
"""

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .client import LLMClient  # DEPRECATED: kept for legacy init only
from .deepseek_client import (  # DEPRECATED: kept for legacy init only
    DeepSeekConfig,
    DeepSeekIntegrationManager,
    DeepSeekMode,
    DeepSeekR1Client,
    DeepSeekResponse,
)

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Available LLM providers"""

    GOOGLE_GEMINI = "google"
    DEEPSEEK_R1 = "deepseek"
    OPENAI = "openai"
    AUTO = "auto"  # Automatically select best provider


class GenerationMode(Enum):
    """Generation modes for different use cases"""

    FAST = "fast"  # Quick responses for simple tasks
    STANDARD = "standard"  # Balanced quality and speed
    COMPLEX = "complex"  # High quality for complex tasks
    CREATIVE = "creative"  # Creative/innovative solutions
    TECHNICAL = "technical"  # Precise technical implementations


@dataclass
class LLMRequest:
    """Unified request format for all LLM providers"""

    command: str
    state: Optional[Dict[str, Any]] = None
    mode: GenerationMode = GenerationMode.STANDARD
    context: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    preferred_provider: Optional[LLMProvider] = None


@dataclass
class LLMResponse:
    """Unified response format from all LLM providers"""

    status: str
    generated_code: str
    provider: LLMProvider
    execution_time: float
    confidence_score: float
    reasoning_chain: Optional[List[Dict]] = None
    optimization_suggestions: Optional[List[str]] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UnifiedLLMManager:
    """
    Unified LLM Manager that provides seamless switching between different LLM providers
    including Google Gemini, DeepSeek R1, and others.

    Internally delegates to ``ai_designer.core.llm_provider.UnifiedLLMProvider``
    (litellm-backed) for all generation calls; the legacy DeepSeek / Gemini
    client objects are still initialised for backward compatibility only.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.providers = {}
        self.active_provider = LLMProvider.AUTO
        self.fallback_chain = [
            LLMProvider.DEEPSEEK_R1,
            LLMProvider.GOOGLE_GEMINI,
        ]

        # Performance tracking
        self.generation_history = []
        self.provider_metrics = {
            provider: {
                "total_requests": 0,
                "successful_requests": 0,
                "total_time": 0.0,
                "average_confidence": 0.0,
                "last_error": None,
            }
            for provider in LLMProvider
        }

        # New litellm-backed provider: used by generate_command() internally
        try:
            from ai_designer.core.llm_provider import UnifiedLLMProvider
            from ai_designer.llm.model_config import get_agent_config

            gen_cfg = get_agent_config("generator")
            self._llm_provider = UnifiedLLMProvider(
                default_model=gen_cfg["primary"],
                fallback_models=[gen_cfg["fallback"]],
            )
            logger.info(
                "✅ litellm-backed UnifiedLLMProvider initialised for delegation"
            )
        except Exception as _e:  # noqa: BLE001
            self._llm_provider = None
            logger.warning("⚠️ Could not initialise litellm provider: %s", _e)

        # Initialize legacy providers (backward compat — DeepSeek local skipped,
        # Google Gemini still attempted if GOOGLE_API_KEY is set)
        self._initialize_providers()

        logger.info("🚀 Unified LLM Manager initialized")
        logger.info(f"   Available providers: {list(self.providers.keys())}")

    def _initialize_providers(self):
        """Initialize all available LLM providers"""

        # Initialize DeepSeek R1 – skipped; code generation is now routed through
        # OnlineCodeGenClient (litellm-backed). Mark as unavailable so the fallback
        # chain falls through to Google Gemini / litellm automatically.
        self.providers[LLMProvider.DEEPSEEK_R1] = {
            "client": None,
            "manager": None,
            "available": False,
            "type": "online",
            "note": "Replaced by OnlineCodeGenClient (google/gemini-2.0-flash)",
        }
        logger.info(
            "\u2139\ufe0f DeepSeek R1 local provider disabled; using OnlineCodeGenClient"
        )

        # Initialize Google Gemini
        try:
            google_api_key = self.config.get("google_api_key") or os.getenv(
                "GOOGLE_API_KEY"
            )
            if google_api_key:
                gemini_client = LLMClient(
                    api_key=google_api_key,
                    model_name=self.config.get("gemini_model", "gemini-1.5-flash"),
                    provider="google",
                )
                self.providers[LLMProvider.GOOGLE_GEMINI] = {
                    "client": gemini_client,
                    "available": True,
                    "type": "api",
                }
                logger.info("✅ Google Gemini provider initialized")
            else:
                raise ValueError("Google API key not found")
        except Exception as e:
            logger.warning(f"⚠️ Google Gemini initialization failed: {e}")
            self.providers[LLMProvider.GOOGLE_GEMINI] = {
                "client": None,
                "available": False,
                "type": "api",
                "error": str(e),
            }

    def set_active_provider(self, provider: LLMProvider) -> bool:
        """Set the active LLM provider"""
        if provider == LLMProvider.AUTO:
            self.active_provider = provider
            logger.info("🤖 Set to AUTO mode - will select best provider per request")
            return True

        if provider not in self.providers:
            logger.error(f"❌ Provider {provider.value} not recognized")
            return False

        if not self.providers[provider]["available"]:
            logger.error(
                f"❌ Provider {provider.value} not available: {self.providers[provider].get('error', 'Unknown error')}"
            )
            return False

        self.active_provider = provider
        logger.info(f"✅ Active LLM provider set to: {provider.value}")
        return True

    def generate_command(self, request: LLMRequest) -> LLMResponse:
        """Generate FreeCAD command using the appropriate LLM provider.

        Delegates to the litellm-backed ``UnifiedLLMProvider`` when available
        (i.e. when an API key is configured and reachable).  Falls back to the
        legacy DeepSeek / Gemini clients transparently.
        """
        start_time = time.time()

        # --- NEW: delegate to litellm-backed provider when possible ---
        if self._llm_provider is not None:
            import asyncio

            from ai_designer.schemas.llm_schemas import LLMMessage as NewLLMMessage
            from ai_designer.schemas.llm_schemas import LLMRequest as NewLLMRequest
            from ai_designer.schemas.llm_schemas import LLMRole

            new_req = NewLLMRequest(
                messages=[NewLLMMessage(role=LLMRole.USER, content=request.command)],
                model=self._llm_provider.default_model,
                temperature=0.2,
            )
            try:
                # generate() is synchronous in UnifiedLLMProvider
                new_resp = self._llm_provider.generate(
                    messages=new_req.messages,
                    model=new_req.model,
                    temperature=new_req.temperature,
                )
                execution_time = time.time() - start_time
                return LLMResponse(
                    status="success",
                    generated_code=new_resp.content,
                    provider=LLMProvider.AUTO,
                    execution_time=execution_time,
                    confidence_score=0.9,
                    metadata={"model": new_resp.model, "usage": new_resp.usage},
                )
            except Exception as _e:  # noqa: BLE001
                logger.warning(
                    "litellm delegation failed, falling back to legacy providers: %s",
                    _e,
                )
        # --- END delegation ---

        # Determine which provider to use
        selected_provider = self._select_provider(request)

        logger.info(f"🧠 Generating command with {selected_provider.value}")
        logger.info(f"   Mode: {request.mode.value}")
        logger.info(f"   Command: {request.command[:100]}...")

        try:
            # Generate using selected provider
            response = self._generate_with_provider(selected_provider, request)

            # Update metrics
            execution_time = time.time() - start_time
            self._update_metrics(selected_provider, response, execution_time)

            # Store in history
            self._store_generation_history(request, response, selected_provider)

            response.execution_time = execution_time

            logger.info(f"✅ Generation completed in {execution_time:.2f}s")
            logger.info(f"   Provider: {response.provider.value}")
            logger.info(f"   Confidence: {response.confidence_score:.2f}")

            return response

        except Exception as e:
            logger.error(f"❌ Generation failed with {selected_provider.value}: {e}")

            # Try fallback if AUTO mode and not already using fallback
            if (
                self.active_provider == LLMProvider.AUTO
                and selected_provider in self.fallback_chain
                and len(self.fallback_chain) > 1
            ):
                return self._try_fallback_providers(request, selected_provider, str(e))

            # Return error response
            return LLMResponse(
                status="error",
                generated_code="",
                provider=selected_provider,
                execution_time=time.time() - start_time,
                confidence_score=0.0,
                error_message=str(e),
            )

    def _select_provider(self, request: LLMRequest) -> LLMProvider:
        """Select the best provider for the given request"""

        # Use explicitly requested provider if specified
        if (
            request.preferred_provider
            and request.preferred_provider != LLMProvider.AUTO
        ):
            if (
                request.preferred_provider in self.providers
                and self.providers[request.preferred_provider]["available"]
            ):
                return request.preferred_provider
            else:
                logger.warning(
                    f"⚠️ Requested provider {request.preferred_provider.value} not available, using auto-selection"
                )

        # Use active provider if not AUTO
        if self.active_provider != LLMProvider.AUTO:
            if self.providers[self.active_provider]["available"]:
                return self.active_provider
            else:
                logger.warning(
                    f"⚠️ Active provider {self.active_provider.value} not available, falling back to auto-selection"
                )

        # Auto-select based on request characteristics
        return self._auto_select_provider(request)

    def _auto_select_provider(self, request: LLMRequest) -> LLMProvider:
        """Automatically select the best provider based on request characteristics"""

        command_lower = request.command.lower()

        # Criteria for DeepSeek R1 (complex, local, reasoning)
        deepseek_indicators = [
            "complex",
            "advanced",
            "intricate",
            "assembly",
            "gear",
            "mechanism",
            "optimization",
            "parametric",
            "pattern",
            "array",
            "sweep",
            "loft",
            "reasoning",
            "analysis",
            "detailed",
            "sophisticated",
        ]

        # Criteria for Gemini (fast, simple, api-based)
        gemini_indicators = [
            "simple",
            "basic",
            "quick",
            "fast",
            "cube",
            "sphere",
            "cylinder",
            "primitive",
            "basic shape",
            "straightforward",
        ]

        deepseek_score = sum(
            1 for indicator in deepseek_indicators if indicator in command_lower
        )
        gemini_score = sum(
            1 for indicator in gemini_indicators if indicator in command_lower
        )

        # Consider generation mode
        if request.mode in [GenerationMode.COMPLEX, GenerationMode.TECHNICAL]:
            deepseek_score += 2
        elif request.mode in [GenerationMode.FAST]:
            gemini_score += 2
        elif request.mode in [GenerationMode.CREATIVE]:
            deepseek_score += 1  # DeepSeek has creative mode

        # Consider request complexity (length, context, constraints)
        if len(request.command) > 100:
            deepseek_score += 1
        if request.context and len(request.context) > 0:
            deepseek_score += 1
        if request.constraints and len(request.constraints) > 0:
            deepseek_score += 1

        # Select based on scores and availability
        if deepseek_score > gemini_score:
            if self.providers[LLMProvider.DEEPSEEK_R1]["available"]:
                return LLMProvider.DEEPSEEK_R1

        if self.providers[LLMProvider.GOOGLE_GEMINI]["available"]:
            return LLMProvider.GOOGLE_GEMINI

        # Fallback to any available provider
        for provider in self.fallback_chain:
            if self.providers[provider]["available"]:
                return provider

        raise Exception("No LLM providers available")

    def _generate_with_provider(
        self, provider: LLMProvider, request: LLMRequest
    ) -> LLMResponse:
        """Generate command using specific provider"""

        if provider == LLMProvider.DEEPSEEK_R1:
            return self._generate_with_deepseek(request)
        elif provider == LLMProvider.GOOGLE_GEMINI:
            return self._generate_with_gemini(request)
        else:
            raise ValueError(f"Provider {provider.value} not implemented")

    def _generate_with_deepseek(self, request: LLMRequest) -> LLMResponse:
        """Generate using DeepSeek R1"""

        deepseek_client = self.providers[LLMProvider.DEEPSEEK_R1]["client"]

        # Map generation mode to DeepSeek mode
        mode_mapping = {
            GenerationMode.FAST: DeepSeekMode.FAST,
            GenerationMode.STANDARD: DeepSeekMode.REASONING,
            GenerationMode.COMPLEX: DeepSeekMode.REASONING,
            GenerationMode.CREATIVE: DeepSeekMode.CREATIVE,
            GenerationMode.TECHNICAL: DeepSeekMode.TECHNICAL,
        }

        deepseek_mode = mode_mapping.get(request.mode, DeepSeekMode.REASONING)

        # Generate with DeepSeek
        deepseek_response = deepseek_client.generate_complex_part(
            requirements=request.command,
            mode=deepseek_mode,
            context=request.context,
            constraints=request.constraints,
        )

        if deepseek_response.status == "success":
            return LLMResponse(
                status="success",
                generated_code=deepseek_response.generated_code,
                provider=LLMProvider.DEEPSEEK_R1,
                execution_time=deepseek_response.execution_time,
                confidence_score=deepseek_response.confidence_score,
                reasoning_chain=[
                    {
                        "step": i + 1,
                        "description": step.description,
                        "reasoning": step.reasoning,
                        "confidence": step.confidence,
                    }
                    for i, step in enumerate(deepseek_response.reasoning_chain)
                ],
                optimization_suggestions=deepseek_response.optimization_suggestions,
                metadata={
                    "complexity_analysis": deepseek_response.complexity_analysis,
                    "deepseek_mode": deepseek_mode.value,
                },
            )
        else:
            raise Exception(
                deepseek_response.error_message or "DeepSeek generation failed"
            )

    def _generate_with_gemini(self, request: LLMRequest) -> LLMResponse:
        """Generate using Google Gemini"""

        gemini_client = self.providers[LLMProvider.GOOGLE_GEMINI]["client"]

        # Generate with Gemini
        generated_code = gemini_client.generate_command(request.command, request.state)

        # Estimate confidence based on code quality
        confidence = self._estimate_gemini_confidence(generated_code)

        return LLMResponse(
            status="success",
            generated_code=generated_code,
            provider=LLMProvider.GOOGLE_GEMINI,
            execution_time=0.0,  # Will be set by caller
            confidence_score=confidence,
            metadata={
                "model": gemini_client.model_name,
                "provider_type": "api",
            },
        )

    def _estimate_gemini_confidence(self, code: str) -> float:
        """Estimate confidence score for Gemini-generated code"""
        base_confidence = 0.7

        # Check for FreeCAD patterns
        if "import FreeCAD" in code or "App." in code:
            base_confidence += 0.1
        if "doc.recompute()" in code:
            base_confidence += 0.05
        if len(code) > 100:
            base_confidence += 0.05

        return min(1.0, base_confidence)

    def _try_fallback_providers(
        self, request: LLMRequest, failed_provider: LLMProvider, error: str
    ) -> LLMResponse:
        """Try fallback providers when primary fails"""

        logger.info(f"🔄 Trying fallback providers after {failed_provider.value} failed")

        remaining_providers = [p for p in self.fallback_chain if p != failed_provider]

        for provider in remaining_providers:
            if self.providers[provider]["available"]:
                try:
                    logger.info(f"🔄 Attempting fallback with {provider.value}")
                    return self._generate_with_provider(provider, request)
                except Exception as fallback_error:
                    logger.warning(
                        f"⚠️ Fallback {provider.value} also failed: {fallback_error}"
                    )
                    continue

        # All providers failed
        return LLMResponse(
            status="error",
            generated_code="",
            provider=failed_provider,
            execution_time=0.0,
            confidence_score=0.0,
            error_message=f"All providers failed. Last error: {error}",
        )

    def _update_metrics(
        self, provider: LLMProvider, response: LLMResponse, execution_time: float
    ):
        """Update performance metrics for providers"""
        metrics = self.provider_metrics[provider]
        metrics["total_requests"] += 1

        if response.status == "success":
            metrics["successful_requests"] += 1

        metrics["total_time"] += execution_time

        if response.status == "success":
            total_successful = metrics["successful_requests"]
            metrics["average_confidence"] = (
                metrics["average_confidence"] * (total_successful - 1)
                + response.confidence_score
            ) / total_successful
        else:
            metrics["last_error"] = response.error_message

    def _store_generation_history(
        self, request: LLMRequest, response: LLMResponse, provider: LLMProvider
    ):
        """Store generation history for analysis"""
        history_entry = {
            "timestamp": time.time(),
            "provider": provider.value,
            "mode": request.mode.value,
            "command": request.command,
            "success": response.status == "success",
            "confidence": response.confidence_score,
            "execution_time": response.execution_time,
        }

        self.generation_history.append(history_entry)

        # Keep only last 100 entries
        if len(self.generation_history) > 100:
            self.generation_history = self.generation_history[-100:]

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {
            "active_provider": self.active_provider.value,
            "providers": {},
            "metrics": self.provider_metrics,
        }

        for provider, config in self.providers.items():
            status["providers"][provider.value] = {
                "available": config["available"],
                "type": config["type"],
                "error": config.get("error"),
            }

        return status

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all providers"""
        summary = {
            "total_generations": len(self.generation_history),
            "provider_usage": {},
            "success_rates": {},
            "average_times": {},
        }

        for provider in LLMProvider:
            if provider == LLMProvider.AUTO:
                continue

            metrics = self.provider_metrics[provider]
            total = metrics["total_requests"]

            if total > 0:
                summary["provider_usage"][provider.value] = total
                summary["success_rates"][provider.value] = (
                    metrics["successful_requests"] / total
                )
                summary["average_times"][provider.value] = metrics["total_time"] / total
            else:
                summary["provider_usage"][provider.value] = 0
                summary["success_rates"][provider.value] = 0.0
                summary["average_times"][provider.value] = 0.0

        return summary

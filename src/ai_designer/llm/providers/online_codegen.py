"""
llm/providers/online_codegen.py
================================
Online LLM-based FreeCAD code generator.

Drop-in replacement for ``DeepSeekR1Client`` that routes requests through
LiteLLM instead of a locally running Ollama instance.  Supports any model
reachable via LiteLLM (Gemini, OpenAI, Anthropic, …).

Default model: ``google/gemini-2.0-flash``

Usage::

    from ai_designer.llm.providers.online_codegen import (
        OnlineCodeGenClient,
        OnlineCodeGenConfig,
    )
    from ai_designer.llm.providers.deepseek import DeepSeekMode, DeepSeekResponse

    client = OnlineCodeGenClient()
    response = client.generate_complex_part(
        requirements="Create a cylinder with diameter 50 mm and height 100 mm",
        mode=DeepSeekMode.REASONING,
    )
    print(response.generated_code)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-export shared data-classes from the sibling deepseek module so callers
# that only import from here still get the canonical types.
# ---------------------------------------------------------------------------
from .deepseek import DeepSeekMode, DeepSeekResponse, ReasoningStep  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class OnlineCodeGenConfig:
    """Configuration for the online code generation client."""

    # LiteLLM model string.  Override via env var CODEGEN_MODEL.
    model: str = "google/gemini-2.0-flash"

    # Fallback model tried when the primary fails.
    fallback_model: str = "openai/gpt-4o"

    # Generation parameters
    temperature: float = 0.1
    max_tokens: int = 8192
    timeout: int = 120

    # Maximum number of retry attempts per model
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "OnlineCodeGenConfig":
        """Create a config, applying any environment-variable overrides."""
        return cls(
            model=os.getenv("CODEGEN_MODEL", cls.model),
            fallback_model=os.getenv("CODEGEN_FALLBACK_MODEL", cls.fallback_model),
            temperature=float(os.getenv("CODEGEN_TEMPERATURE", str(cls.temperature))),
            max_tokens=int(os.getenv("CODEGEN_MAX_TOKENS", str(cls.max_tokens))),
            timeout=int(os.getenv("CODEGEN_TIMEOUT", str(cls.timeout))),
        )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class OnlineCodeGenClient:
    """
    Online FreeCAD code-generation client backed by LiteLLM.

    Provides the same ``generate_complex_part()`` interface as
    ``DeepSeekR1Client`` so it can be used as a transparent drop-in
    replacement throughout the codebase.
    """

    def __init__(self, config: Optional[OnlineCodeGenConfig] = None) -> None:
        self.config = config or OnlineCodeGenConfig.from_env()

        # Lazy import so tests that mock litellm can still import this module.
        try:
            import litellm  # noqa: F401

            self._litellm_available = True
        except ImportError:
            self._litellm_available = False
            logger.warning(
                "litellm is not installed – OnlineCodeGenClient will always fail. "
                "Install it with: pip install litellm"
            )

        # Performance tracking
        self.generation_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "average_response_time": 0.0,
            "average_confidence": 0.0,
        }

        logger.info(
            "OnlineCodeGenClient ready. model=%s fallback=%s",
            self.config.model,
            self.config.fallback_model,
        )

    # ------------------------------------------------------------------
    # Public interface (mirrors DeepSeekR1Client)
    # ------------------------------------------------------------------

    def generate_complex_part(
        self,
        requirements: str,
        mode: DeepSeekMode = DeepSeekMode.REASONING,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> DeepSeekResponse:
        """
        Generate FreeCAD Python code for the given requirements.

        Args:
            requirements: Natural-language description of the part to create.
            mode: Generation mode (REASONING, FAST, CREATIVE, TECHNICAL).
            context: Optional contextual information (existing document state, …).
            constraints: Optional design constraints (dimensions, tolerances, …).

        Returns:
            ``DeepSeekResponse`` with the generated code and quality metadata.
        """
        start_time = time.time()
        self.performance_metrics["total_requests"] += 1

        if not self._litellm_available:
            return self._error_response("litellm is not installed", start_time)

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(requirements, mode, context, constraints)

        # Try primary model, then fallback
        for attempt, model in enumerate(
            [self.config.model, self.config.fallback_model], start=1
        ):
            for retry in range(1, self.config.max_retries + 1):
                try:
                    logger.info(
                        "Generating code via %s (attempt %d/%d, retry %d/%d)",
                        model,
                        attempt,
                        2,
                        retry,
                        self.config.max_retries,
                    )
                    raw_content = self._call_litellm(
                        model, system_prompt, user_prompt, mode
                    )
                    response = self._build_response(
                        raw_content, requirements, start_time
                    )
                    self._update_metrics(response, time.time() - start_time)
                    self._store_history(
                        requirements, response, time.time() - start_time
                    )
                    return response
                except Exception as exc:
                    logger.warning(
                        "model=%s retry=%d/%d failed: %s",
                        model,
                        retry,
                        self.config.max_retries,
                        exc,
                    )

        return self._error_response(
            f"All models exhausted ({self.config.model}, {self.config.fallback_model})",
            start_time,
        )

    def get_performance_metrics(self) -> Dict[str, Any]:
        total = self.performance_metrics["total_requests"]
        success_rate = (
            self.performance_metrics["successful_requests"] / total if total else 0.0
        )
        return {**self.performance_metrics, "success_rate": success_rate}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_litellm(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        mode: DeepSeekMode,
    ) -> str:
        """Make the actual LiteLLM API call and return the raw text content."""
        import litellm

        temperature = {
            DeepSeekMode.REASONING: 0.1,
            DeepSeekMode.FAST: 0.05,
            DeepSeekMode.CREATIVE: 0.3,
            DeepSeekMode.TECHNICAL: 0.05,
        }.get(mode, self.config.temperature)

        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout,
        )
        return response.choices[0].message.content or ""

    def _build_system_prompt(self) -> str:
        return (
            "You are an expert FreeCAD Python developer specialising in 3D mechanical part design. "
            "You write production-ready, executable FreeCAD Python scripts that use "
            "App.ActiveDocument (never App.newDocument) and always call doc.recompute() at the end. "
            "You use standard Python math (not FreeCAD.Math). "
            "Return ONLY the Python code inside a single ```python ... ``` block, with no extra prose "
            "outside the block."
        )

    def _build_user_prompt(
        self,
        requirements: str,
        mode: DeepSeekMode,
        context: Optional[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]],
    ) -> str:
        complexity = self._analyze_requirement_complexity(requirements)

        prompt = f"""Generate FreeCAD Python code for: {requirements}

MODE: {mode.value.upper()}
COMPLEXITY: {complexity.upper()}

STRICT RULES:
1. Use App.ActiveDocument – NEVER App.newDocument()
2. Use standard Python math: math.pi, math.sin(), etc. – NEVER FreeCAD.Math
3. Part function arguments are positional: Part.makeCylinder(radius, height)
4. Always call doc.recompute() at the end
5. Wrap complex sections with try/except
6. Print a success message: print("✅ <ObjectName> created successfully!")

AVAILABLE API:
  Part.makeBox(l, w, h)           Part.makeCylinder(r, h)
  Part.makeSphere(r)              Part.makeCone(r1, r2, h)
  Part.makeCircle(r)              shape.extrude(vector)
  shape.cut(other)                shape.fuse(other)
  shape.common(other)
  doc.addObject("Part::Feature", "Name")  → set .Shape
  PartDesign Body → Sketcher → Pad / Pocket / Revolution / Loft
  Fillet / Chamfer / LinearPattern / PolarPattern
"""

        if complexity == "complex":
            prompt += """
GUIDANCE – COMPLEX SHAPES:
- Decompose into simpler sub-components
- Use 2D wire → face → extrude for custom profiles
- For gears: simplified tooth or circular approximation is acceptable
"""
        if mode == DeepSeekMode.REASONING:
            prompt += (
                "\nProvide a brief step-by-step comment before each logical block.\n"
            )

        if context:
            try:
                prompt += f"\nCONTEXT:\n{json.dumps(context, indent=2, default=str)}\n"
            except Exception:
                prompt += f"\nCONTEXT:\n{context}\n"

        if constraints:
            try:
                prompt += f"\nCONSTRAINTS:\n{json.dumps(constraints, indent=2, default=str)}\n"
            except Exception:
                prompt += f"\nCONSTRAINTS:\n{constraints}\n"

        return prompt

    def _analyze_requirement_complexity(self, requirements: str) -> str:
        r = requirements.lower()
        complex_kw = [
            "gear",
            "spring",
            "helical",
            "thread",
            "involute",
            "spiral",
            "assembly",
            "multiple parts",
            "pattern",
            "array",
        ]
        medium_kw = [
            "hole",
            "cut",
            "fillet",
            "chamfer",
            "bracket",
            "slot",
            "groove",
            "revolve",
            "loft",
        ]
        basic_kw = ["cube", "box", "cylinder", "sphere", "cone", "simple", "basic"]

        if any(k in r for k in complex_kw):
            return "complex"
        if any(k in r for k in medium_kw):
            return "medium"
        if any(k in r for k in basic_kw):
            return "basic"
        return "medium"

    def _build_response(
        self, raw_content: str, requirements: str, start_time: float
    ) -> DeepSeekResponse:
        generated_code = self._extract_code(raw_content)
        confidence = self._estimate_confidence(generated_code)
        complexity_analysis = self._analyze_code_complexity(generated_code)
        suggestions = self._optimization_suggestions(
            generated_code, complexity_analysis
        )

        reasoning_chain = [
            ReasoningStep(
                step_id=0,
                description="Generate FreeCAD Python code via online LLM",
                code_snippet=None,
                reasoning=f"Generated by {self.config.model}",
                confidence=confidence,
                validation_status="generated",
            )
        ]

        return DeepSeekResponse(
            status="success",
            generated_code=generated_code,
            reasoning_chain=reasoning_chain,
            confidence_score=confidence,
            execution_time=time.time() - start_time,
            complexity_analysis=complexity_analysis,
            optimization_suggestions=suggestions,
        )

    def _extract_code(self, content: str) -> str:
        """Extract Python code from the model's response."""
        # Prefer ```python ... ``` block
        if "```python" in content:
            start = content.find("```python") + len("```python")
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()

        # Any fenced code block that looks like Python
        if "```" in content:
            start = content.find("```") + 3
            # skip optional language tag on first line
            newline = content.find("\n", start)
            if newline != -1:
                maybe_lang = content[start:newline].strip()
                if not maybe_lang or maybe_lang.isalpha():
                    start = newline + 1
            end = content.find("```", start)
            if end != -1:
                block = content[start:end].strip()
                if any(k in block for k in ["import", "def", "FreeCAD", "Part"]):
                    return block

        # Fallback: return everything
        return content.strip()

    def _estimate_confidence(self, code: str) -> float:
        score = 0.65
        if len(code) > 300:
            score += 0.05
        if "import FreeCAD" in code or "import App" in code:
            score += 0.10
        if "doc.recompute()" in code:
            score += 0.05
        if "try:" in code:
            score += 0.05
        if "doc.addObject" in code:
            score += 0.05
        return min(1.0, score)

    def _analyze_code_complexity(self, code: str) -> Dict[str, Any]:
        lines = [l for l in code.split("\n") if l.strip()]
        objects = code.count(".addObject(")
        booleans = sum(code.count(op) for op in (".cut(", ".fuse(", ".common("))
        advanced = sum(
            code.count(f) for f in ("Sketcher", "Pad", "Pocket", "Fillet", "Chamfer")
        )
        score = len(lines) * 0.1 + objects * 0.5 + booleans * 1.0 + advanced * 1.5
        return {
            "line_count": len(lines),
            "object_count": objects,
            "boolean_operation_count": booleans,
            "advanced_feature_count": advanced,
            "complexity_score": min(10.0, score),
        }

    def _optimization_suggestions(
        self, code: str, complexity: Dict[str, Any]
    ) -> List[str]:
        suggestions: List[str] = []
        if complexity["object_count"] > 10:
            suggestions.append(
                "Consider grouping related objects for better organisation"
            )
        if "doc.recompute()" not in code:
            suggestions.append("Add doc.recompute() to ensure proper model updates")
        if "try:" not in code:
            suggestions.append("Add error handling for robust execution")
        return suggestions

    def _error_response(self, message: str, start_time: float) -> DeepSeekResponse:
        logger.error("OnlineCodeGenClient failed: %s", message)
        return DeepSeekResponse(
            status="error",
            generated_code="",
            reasoning_chain=[],
            confidence_score=0.0,
            execution_time=time.time() - start_time,
            complexity_analysis={},
            optimization_suggestions=[],
            error_message=message,
        )

    def _update_metrics(self, response: DeepSeekResponse, elapsed: float) -> None:
        if response.status == "success":
            self.performance_metrics["successful_requests"] += 1
        total = self.performance_metrics["total_requests"]
        self.performance_metrics["average_response_time"] = (
            self.performance_metrics["average_response_time"] * (total - 1) + elapsed
        ) / total
        self.performance_metrics["average_confidence"] = (
            self.performance_metrics["average_confidence"] * (total - 1)
            + response.confidence_score
        ) / total

    def _store_history(
        self, requirements: str, response: DeepSeekResponse, elapsed: float
    ) -> None:
        self.generation_history.append(
            {
                "timestamp": time.time(),
                "requirements": requirements,
                "success": response.status == "success",
                "confidence": response.confidence_score,
                "execution_time": elapsed,
            }
        )
        self.generation_history = self.generation_history[-100:]

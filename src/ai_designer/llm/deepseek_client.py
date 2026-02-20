"""
llm/deepseek_client.py
======================
DeepSeek R1 integration layer.

The low-level ``DeepSeekR1Client`` and its dataclasses have been extracted to
``llm/providers/deepseek.py``.  This module keeps only ``DeepSeekIntegrationManager``
and backward-compatible re-exports so existing callers see no changes.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

# Re-export primitives for backward compatibility
from .providers.deepseek import (  # noqa: F401
    DeepSeekConfig,
    DeepSeekMode,
    DeepSeekR1Client,
    DeepSeekResponse,
    ReasoningStep,
)

logger = logging.getLogger(__name__)


class DeepSeekIntegrationManager:
    """
    Manager class for integrating DeepSeek R1 with the existing FreeCAD system
    Provides seamless fallback and hybrid operation modes
    """

    def __init__(self, deepseek_client: DeepSeekR1Client, fallback_client=None):
        self.deepseek_client = deepseek_client
        self.fallback_client = fallback_client
        self.integration_metrics = {
            "deepseek_requests": 0,
            "fallback_requests": 0,
            "hybrid_requests": 0,
        }

        logger.info("DeepSeek Integration Manager initialized")

    def generate_command(self, nl_command: str, state=None, mode: str = "auto") -> str:
        """
        Generate FreeCAD command with intelligent mode selection

        Args:
            nl_command: Natural language command
            state: Current FreeCAD state
            mode: "deepseek", "fallback", "hybrid", or "auto"

        Returns:
            Generated FreeCAD Python code
        """

        if mode == "auto":
            mode = self._select_optimal_mode(nl_command, state)

        try:
            if mode == "deepseek":
                return self._generate_with_deepseek(nl_command, state)
            elif mode == "hybrid":
                return self._generate_hybrid(nl_command, state)
            else:  # fallback
                return self._generate_with_fallback(nl_command, state)

        except Exception as e:
            logger.warning(f"Generation failed with mode {mode}, trying fallback: {e}")
            return self._generate_with_fallback(nl_command, state)

    def _select_optimal_mode(self, nl_command: str, state) -> str:
        """Select optimal generation mode based on command complexity"""

        # Analyze command complexity
        complexity_indicators = [
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
        ]

        command_lower = nl_command.lower()
        complexity_score = sum(
            1 for indicator in complexity_indicators if indicator in command_lower
        )

        # Check if DeepSeek is available
        try:
            self.deepseek_client._verify_connection()
            deepseek_available = True
        except:
            deepseek_available = False

        # Decision logic
        if not deepseek_available:
            return "fallback"
        elif complexity_score >= 2:
            return "deepseek"
        elif complexity_score == 1:
            return "hybrid"
        else:
            return "fallback"

    def _generate_with_deepseek(self, nl_command: str, state) -> str:
        """Generate using DeepSeek R1"""
        self.integration_metrics["deepseek_requests"] += 1

        # Determine appropriate mode based on command
        if any(
            word in nl_command.lower()
            for word in ["creative", "innovative", "artistic"]
        ):
            mode = DeepSeekMode.CREATIVE
        elif any(
            word in nl_command.lower() for word in ["precise", "accurate", "technical"]
        ):
            mode = DeepSeekMode.TECHNICAL
        elif any(word in nl_command.lower() for word in ["quick", "fast", "simple"]):
            mode = DeepSeekMode.FAST
        else:
            mode = DeepSeekMode.REASONING

        # Prepare context
        context = {"freecad_state": state} if state else None

        # Generate with DeepSeek
        response = self.deepseek_client.generate_complex_part(
            requirements=nl_command, mode=mode, context=context
        )

        if response.status == "success":
            return response.generated_code
        else:
            raise Exception(f"DeepSeek generation failed: {response.error_message}")

    def _generate_with_fallback(self, nl_command: str, state) -> str:
        """Generate using fallback client"""
        self.integration_metrics["fallback_requests"] += 1

        if self.fallback_client:
            return self.fallback_client.generate_command(nl_command, state)
        else:
            # Emergency fallback
            return f"""
# Emergency fallback for: {nl_command}
import FreeCAD as App
import Part

doc = App.ActiveDocument or App.newDocument()
box = doc.addObject('Part::Box', 'EmergencyBox')
box.Length = 10
box.Width = 10
box.Height = 10
doc.recompute()
"""

    def _generate_hybrid(self, nl_command: str, state) -> str:
        """Generate using hybrid approach (DeepSeek + fallback validation)"""
        self.integration_metrics["hybrid_requests"] += 1

        try:
            # Try DeepSeek first
            deepseek_code = self._generate_with_deepseek(nl_command, state)

            # Validate with fallback if available
            if self.fallback_client:
                fallback_code = self._generate_with_fallback(nl_command, state)

                # Compare and potentially merge approaches
                return self._merge_solutions(deepseek_code, fallback_code, nl_command)
            else:
                return deepseek_code

        except Exception as e:
            logger.warning(f"Hybrid generation failed, using fallback: {e}")
            return self._generate_with_fallback(nl_command, state)

    def _merge_solutions(
        self, deepseek_code: str, fallback_code: str, nl_command: str
    ) -> str:
        """Intelligently merge solutions from different generators"""

        # For now, prefer DeepSeek for complex operations, fallback for simple ones
        if any(
            word in nl_command.lower() for word in ["complex", "advanced", "assembly"]
        ):
            return deepseek_code
        else:
            # Use fallback for simple operations
            return fallback_code

    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get integration performance metrics"""
        total_requests = sum(self.integration_metrics.values())

        return {
            **self.integration_metrics,
            "total_requests": total_requests,
            "deepseek_usage_rate": self.integration_metrics["deepseek_requests"]
            / max(1, total_requests),
            "fallback_usage_rate": self.integration_metrics["fallback_requests"]
            / max(1, total_requests),
            "hybrid_usage_rate": self.integration_metrics["hybrid_requests"]
            / max(1, total_requests),
            "deepseek_metrics": self.deepseek_client.get_performance_metrics(),
            "reasoning_insights": self.deepseek_client.get_reasoning_insights(),
        }

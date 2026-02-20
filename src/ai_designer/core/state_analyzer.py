"""
core/state_analyzer.py
======================
Pure, stateless state-analysis helpers extracted from StateLLMIntegration.

These functions accept plain dicts/lists and return plain dicts/strings.
They have NO dependency on the LLM client, Redis, or FreeCAD — making them
trivially unit-testable.

Usage in StateLLMIntegration (after migration):
    from .state_analyzer import (
        summarize_state,
        summarize_history,
        summarize_objects,
        calculate_quality_metrics,
        extract_complexity_keywords,
        fallback_complexity_analysis,
        analyze_constraints,
        extract_generation_goals,
        define_quality_requirements,
    )
"""

from datetime import datetime
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# State summarization helpers
# ---------------------------------------------------------------------------

def summarize_state(state: Dict[str, Any]) -> str:
    """Return a compact one-line summary of the current FreeCAD document state.

    Extracted from ``StateLLMIntegration._summarize_state``.

    Args:
        state: State dict from the state service (may be empty or contain errors).

    Returns:
        Human-readable summary string.
    """
    if not state or "error" in state:
        return "No active document or state unavailable"

    parts: List[str] = [
        f"Document: {state.get('document_name', 'Unnamed')}",
        f"Objects: {state.get('object_count', 0)} total",
    ]

    objects = state.get("objects", [])
    if objects:
        obj_types: Dict[str, int] = {}
        for obj in objects[:5]:
            t = obj.get("type", "Unknown")
            obj_types[t] = obj_types.get(t, 0) + 1
        type_summary = ", ".join(f"{n} {t}" for t, n in obj_types.items())
        parts.append(f"Object types: {type_summary}")

    return " | ".join(parts)


def summarize_history(history: List[Dict[str, Any]]) -> str:
    """Return a compact summary of the last 3 commands in the history.

    Extracted from ``StateLLMIntegration._summarize_history``.

    Args:
        history: List of command history dicts with ``command`` and ``status`` keys.

    Returns:
        Human-readable summary string.
    """
    if not history:
        return "No recent commands"

    return " -> ".join(
        f"{cmd.get('command', '')[:30]}... ({cmd.get('status', 'unknown')})"
        for cmd in history[-3:]
    )


def summarize_objects(objects: List[Dict[str, Any]]) -> str:
    """Return a compact summary of up to 5 FreeCAD objects.

    Extracted from ``StateLLMIntegration._summarize_objects``.

    Args:
        objects: List of object dicts with ``name`` and ``type`` keys.

    Returns:
        Human-readable summary string.
    """
    if not objects:
        return "No objects in current document"

    parts = [
        f"{obj.get('name', 'Unnamed')} ({obj.get('type', 'Unknown')})"
        for obj in objects[:5]
    ]
    if len(objects) > 5:
        parts.append(f"... and {len(objects) - 5} more")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------

def calculate_quality_metrics(state: Dict[str, Any]) -> Dict[str, float]:
    """Compute heuristic quality metrics from a state dict.

    Extracted from ``EnhancedStateLLMIntegration._calculate_quality_metrics``.

    Args:
        state: State dict containing at least ``objects`` list.

    Returns:
        Dict of named float metrics (all in [0, 1]).
    """
    n = len(state.get("objects", []))
    return {
        "geometric_accuracy": min(1.0, n * 0.1 + 0.5),
        "design_consistency": 0.8 if n > 1 else 1.0,
        "complexity_score": min(1.0, n * 0.15),
        "manufacturability": max(0.0, 0.9 - n * 0.05),
        "performance_score": max(0.1, 1.0 - n * 0.08),
    }


# ---------------------------------------------------------------------------
# Complexity analysis
# ---------------------------------------------------------------------------

_COMPLEXITY_KEYWORDS = [
    "complex", "advanced", "intricate", "detailed", "parametric",
    "tower", "building", "assembly", "multiple", "combined",
]


def extract_complexity_keywords(user_input: str) -> List[str]:
    """Return complexity-signalling keywords present in *user_input*.

    Extracted from ``EnhancedStateLLMIntegration._extract_complexity_keywords``.
    """
    lower = user_input.lower()
    return [kw for kw in _COMPLEXITY_KEYWORDS if kw in lower]


def fallback_complexity_analysis(user_input: str) -> Dict[str, Any]:
    """Heuristic complexity analysis used when the LLM is unavailable.

    Extracted from ``EnhancedStateLLMIntegration._fallback_complexity_analysis``.

    Args:
        user_input: Raw user text.

    Returns:
        Dict compatible with the ``_analyze_complexity_requirements`` return value.
    """
    keywords = extract_complexity_keywords(user_input)
    score = min(10, len(keywords) * 2 + 3)

    return {
        "geometric_complexity": score,
        "operation_complexity": max(3, score - 1),
        "overall_complexity": "advanced" if score >= 7 else "intermediate",
        "decomposition_recommended": score >= 6,
        "estimated_steps": max(3, score),
        "keywords": keywords,
        "analysis_timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Constraint / goal / quality requirement helpers
# ---------------------------------------------------------------------------

def analyze_constraints(
    current_state: Dict[str, Any],
    complexity_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute execution constraints from state and complexity.

    Extracted from ``EnhancedStateLLMIntegration._analyze_constraints``.
    """
    n_objects = current_state.get("object_count", 0)
    complexity = complexity_analysis.get("geometric_complexity", 5)

    return {
        "max_objects": max(10, 50 - n_objects),
        "memory_usage": f"{n_objects * 10}MB estimated",
        "execution_time_limit": min(300, complexity * 30),
        "quality_threshold": 0.8,
        "performance_threshold": 0.7,
    }


def extract_generation_goals(
    user_input: str,
    complexity_analysis: Dict[str, Any],  # noqa: ARG001  (reserved for future use)
) -> List[str]:
    """Derive high-level generation goals from user input text.

    Extracted from ``EnhancedStateLLMIntegration._extract_generation_goals``.
    """
    lower = user_input.lower()
    goals: List[str] = []

    if any(w in lower for w in ("create", "make", "build", "design")):
        goals.append("Create primary shape")
    if any(w in lower for w in ("complex", "detailed", "intricate")):
        goals.append("Add complexity and detail")
    if any(w in lower for w in ("combine", "together", "assembly")):
        goals.append("Combine multiple components")

    return goals or ["Fulfill user requirements"]


def define_quality_requirements(
    complexity_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Map complexity score to quality thresholds.

    Extracted from ``EnhancedStateLLMIntegration._define_quality_requirements``.
    """
    c = complexity_analysis.get("geometric_complexity", 5)
    return {
        "minimum_accuracy": max(0.7, 1.0 - c * 0.05),
        "geometric_tolerance": min(0.1, c * 0.01),
        "surface_quality": max(0.8, 1.0 - c * 0.03),
        "structural_integrity": 0.9,
        "manufacturability": max(0.6, 1.0 - c * 0.04),
    }

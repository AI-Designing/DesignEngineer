"""
freecad/workflow_templates.py
==============================
Pure workflow-analysis helpers extracted from StateAwareCommandProcessor.

These functions are stateless (no instance state needed), making them
easily unit-testable in isolation.
"""

from typing import Any, Dict

# Keyword categories (shared between functions)
_SKETCH_OPERATIONS = ["cylinder", "extrude", "pad", "revolve", "sweep", "loft"]
_HOLE_OPERATIONS = ["hole", "drill", "bore", "pocket", "cut"]
_COMPLEX_INDICATORS = [
    "bracket",
    "housing",
    "assembly",
    "pattern",
    "array",
    "grid",
    "fillet",
    "chamfer",
    "shell",
    "multiple",
    "mounting",
    "features",
    "complex",
    "gear",
    "mechanical",
    "cover",
    "lid",
]
_PATTERN_INDICATORS = [
    "pattern",
    "array",
    "grid",
    "circular",
    "linear",
    "matrix",
    "repeat",
    "multiple holes",
    "series of",
    "row of",
    "circle of",
]
_FEATURE_INDICATORS = [
    "fillet",
    "chamfer",
    "round",
    "bevel",
    "shell",
    "hollow",
    "rounded corners",
    "smooth edges",
    "draft angle",
]
_BASE_STEPS = {
    "simple": 1,
    "sketch_then_operate": 3,
    "face_selection": 2,
    "multi_step": 4,
    "complex_workflow": 6,
}


def analyze_workflow_requirements(
    nl_command: str, current_state: Dict[str, Any]
) -> Dict[str, Any]:
    """Decide which workflow strategy to use for *nl_command*.

    Extracted from ``StateAwareCommandProcessor._analyze_workflow_requirements``.

    Args:
        nl_command: Raw natural-language user request.
        current_state: Combined state dict from ``_get_current_state()``.

    Returns:
        Dict describing the chosen strategy and associated flags.
    """
    nl_lower = nl_command.lower()

    requires_sketch = any(
        op in nl_lower for op in _SKETCH_OPERATIONS + _HOLE_OPERATIONS
    )
    requires_face_selection = any(
        op in nl_lower for op in _HOLE_OPERATIONS + ["on face", "on surface"]
    )
    is_geometric_primitive = any(
        term in nl_lower for term in ["cube", "box", "sphere", "cone"]
    )
    has_complex_indicators = any(ind in nl_lower for ind in _COMPLEX_INDICATORS)
    has_pattern_indicators = any(ind in nl_lower for ind in _PATTERN_INDICATORS)
    has_feature_indicators = any(ind in nl_lower for ind in _FEATURE_INDICATORS)

    complexity_factors = sum(
        [
            has_complex_indicators,
            has_pattern_indicators,
            has_feature_indicators,
            "and" in nl_lower,
            len(nl_lower.split()) > 8,
            "with" in nl_lower,
        ]
    )

    has_active_body = current_state.get("live_state", {}).get("active_body", False)
    object_count = current_state.get("object_count", 0)

    strategy = "simple"
    if complexity_factors >= 2 or has_complex_indicators:
        strategy = "complex_workflow"
    elif requires_sketch and not is_geometric_primitive:
        strategy = "sketch_then_operate"
    elif requires_face_selection and object_count > 0:
        strategy = "face_selection"
    elif object_count > 0 and ("add" in nl_lower or "attach" in nl_lower):
        strategy = "multi_step"

    # Override for hole/pocket on existing geometry
    if (
        object_count > 0
        and any(op in nl_lower for op in _HOLE_OPERATIONS)
        and not has_complex_indicators
    ):
        strategy = "face_selection"

    return {
        "strategy": strategy,
        "requires_sketch_then_operate": strategy == "sketch_then_operate",
        "requires_face_selection": strategy == "face_selection",
        "is_multi_step": strategy == "multi_step",
        "is_complex_workflow": strategy == "complex_workflow",
        "has_pattern_indicators": has_pattern_indicators,
        "has_feature_indicators": has_feature_indicators,
        "complexity_factors": complexity_factors,
        "needs_active_body": requires_sketch and not has_active_body,
        "estimated_steps": estimate_step_count(nl_command, strategy),
        "complexity_score": calculate_complexity_score(nl_command, current_state),
    }


def estimate_step_count(nl_command: str, strategy: str) -> int:
    """Return a rough estimate of execution steps for *nl_command*.

    Extracted from ``StateAwareCommandProcessor._estimate_step_count``.
    """
    nl_lower = nl_command.lower()
    modifier = 1

    if "diameter" in nl_command and "height" in nl_command:
        modifier += 1
    if "mounting" in nl_command or "bracket" in nl_command:
        modifier += 2
    if any(t in nl_lower for t in ["pattern", "array", "grid"]):
        modifier += 2
    if any(t in nl_lower for t in ["fillet", "chamfer", "round"]):
        modifier += 1
    if "assembly" in nl_lower or "multiple parts" in nl_lower:
        modifier += 3
    modifier += nl_lower.count("and")

    return _BASE_STEPS.get(strategy, 1) * modifier


def calculate_complexity_score(nl_command: str, current_state: Dict[str, Any]) -> float:
    """Return a complexity score in [0, 1] for *nl_command*.

    Extracted from ``StateAwareCommandProcessor._calculate_complexity_score``.
    """
    score = 0.0
    nl_lower = nl_command.lower()

    if len(nl_command.split()) > 10:
        score += 0.2
    if any(t in nl_lower for t in ["bracket", "assembly", "gear", "housing"]):
        score += 0.3
    if current_state.get("object_count", 0) > 0:
        score += 0.2

    advanced = ["fillet", "chamfer", "pattern", "array", "mirror"]
    score += 0.1 * sum(1 for t in advanced if t in nl_lower)

    complex_terms = [
        "complex",
        "assembly",
        "multiple",
        "housing",
        "mechanical",
        "cover",
    ]
    score += 0.15 * sum(1 for t in complex_terms if t in nl_lower)

    pattern_terms = ["grid", "matrix", "circular", "linear", "pattern"]
    score += 0.1 * sum(1 for t in pattern_terms if t in nl_lower)

    score += 0.1 * nl_lower.count("and")

    if any(t in nl_lower for t in ["with", "including", "plus", "also"]):
        score += 0.1

    return min(score, 1.0)

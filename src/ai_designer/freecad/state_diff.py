"""
freecad/state_diff.py
=====================
Stateless state-diffing & validation helpers extracted from StateAwareCommandProcessor.

All functions accept plain dicts and return plain dicts.  No FreeCAD or
Redis calls are made here — callers provide all required data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def compute_state_diff(
    before: Dict[str, Any], after: Dict[str, Any]
) -> Dict[str, Any]:
    """Return a structured diff between two FreeCAD state snapshots.

    Args:
        before: State dict captured before an operation.
        after: State dict captured after an operation.

    Returns:
        Dict with keys:
            - ``objects_added`` (list of names)
            - ``objects_removed`` (list of names)
            - ``object_count_delta`` (int)
            - ``had_errors_before`` (bool)
            - ``had_errors_after`` (bool)
            - ``error_introduced`` (bool)
    """
    before_names = {o.get("name") for o in before.get("objects", [])}
    after_names = {o.get("name") for o in after.get("objects", [])}

    return {
        "objects_added": sorted(after_names - before_names),
        "objects_removed": sorted(before_names - after_names),
        "object_count_delta": after.get("object_count", 0) - before.get("object_count", 0),
        "had_errors_before": before.get("live_state", {}).get("has_errors", False),
        "had_errors_after": after.get("live_state", {}).get("has_errors", False),
        "error_introduced": (
            not before.get("live_state", {}).get("has_errors", False)
            and after.get("live_state", {}).get("has_errors", False)
        ),
    }


def validate_final_state(
    final_state: Dict[str, Any], geometry_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Check whether *final_state* satisfies the expectations set by *geometry_analysis*.

    Extracted from ``StateAwareCommandProcessor._validate_final_state``.

    Args:
        final_state: The combined state dict after all operations.
        geometry_analysis: Output from ``analyze_geometry_requirements()``.

    Returns:
        Dict with keys: ``valid`` (bool), ``issues`` (list[str]), ``quality_score`` (float).
    """
    validation: Dict[str, Any] = {"valid": True, "issues": [], "quality_score": 1.0}

    live_state = final_state.get("live_state", {})

    if live_state.get("has_errors", False):
        validation["valid"] = False
        validation["issues"].append("Document contains errors")
        validation["quality_score"] -= 0.3

    if final_state.get("object_count", 0) == 0:
        validation["valid"] = False
        validation["issues"].append("No objects created")
        validation["quality_score"] -= 0.5

    operation = geometry_analysis.get("operation", "unknown")
    if operation == "pad" and not live_state.get("has_pad", False):
        validation["issues"].append("Pad operation may have failed")
        validation["quality_score"] -= 0.2

    return validation


def preflight_checks(
    current_state: Dict[str, Any],
    workflow_analysis: Dict[str, Any],
    api_client_available: bool = True,
) -> Dict[str, Any]:
    """Run pre-flight checks before starting a workflow.

    Extracted from ``StateAwareCommandProcessor._preflight_state_check``.

    Args:
        current_state: Output from ``_get_current_state()``.
        workflow_analysis: Output from ``analyze_workflow_requirements()``.
        api_client_available: Whether the FreeCAD API client is connected.

    Returns:
        Dict with ``ready`` (bool) and optional ``reason`` / ``suggestion`` keys.
    """
    live = current_state.get("live_state", {})
    checks = {
        "freecad_connected": api_client_available,
        "document_available": live.get("document_name") is not None,
        "no_critical_errors": live.get("has_errors", True) is False,
    }

    if workflow_analysis.get("needs_active_body"):
        checks["body_ready"] = True  # Will be created if missing

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        return {
            "ready": False,
            "reason": f"Failed checks: {', '.join(failed)}",
            "suggestion": "Check FreeCAD connection and document state",
        }

    return {"ready": True}


def build_checkpoint_key(session_id: str, checkpoint_name: str) -> str:
    """Return a Redis cache key for a state checkpoint.

    Args:
        session_id: The current session identifier.
        checkpoint_name: A descriptive name for the checkpoint.

    Returns:
        String key of the form ``"{session_id}_{checkpoint_name}_{epoch_ms}"``.
    """
    return f"{session_id}_{checkpoint_name}_{int(datetime.now().timestamp())}"

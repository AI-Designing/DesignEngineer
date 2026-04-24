"""
Structured assertions for FreeCADExecutor benchmark results.

Track 5 follow-up: extend assert_execution_meets_criteria to use top-level
total_volume / bounding_box on the execution dict when executor exposes them
(validator already expects those keys).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def assert_execution_meets_criteria(
    result: Dict[str, Any],
    *,
    expect_success: bool,
    criteria: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Assert benchmark outcomes beyond bare process success.

    Args:
        result: Dict returned by FreeCADExecutor.execute().
        expect_success: Whether the run should succeed.
        criteria: Optional thresholds (min_object_count, max_recompute_errors,
            min_constraint_total). Ignored when expect_success is False except
            for future Track 5 keys.
    """
    criteria = criteria or {}

    assert result["success"] is expect_success, (
        f"expected success={expect_success}, got {result.get('success')}, "
        f"errors={result.get('errors')}"
    )

    if not expect_success:
        assert result.get("errors") or not result.get("success")
        return

    assert result.get("document_path"), "expected document_path on success"
    state = result.get("state") or {}
    assert state.get("success") is not False, f"state extraction failed: {state}"

    min_oc = criteria.get("min_object_count")
    if min_oc is not None:
        actual = int(state.get("object_count", 0))
        assert actual >= min_oc, f"object_count {actual} < min {min_oc}"

    max_re = criteria.get("max_recompute_errors")
    if max_re is not None:
        errs = state.get("recompute_errors") or []
        assert (
            len(errs) <= max_re
        ), f"recompute_errors {len(errs)} > max {max_re}: {errs}"

    min_ct = criteria.get("min_constraint_total")
    if min_ct is not None:
        cons = state.get("constraints") or {}
        total = int(cons.get("total", 0))
        assert total >= min_ct, f"constraint total {total} < min {min_ct}"

    # Track 5: when executor merges geometry summary onto result, assert here, e.g.:
    # vol = result.get("total_volume")
    # if criteria.get("volume_mm3_min") is not None:
    #     assert vol is not None and vol >= criteria["volume_mm3_min"]

"""Track 9: legacy keyword heuristics — geometry, workflow routing, intent."""

import importlib.util
from pathlib import Path

from ai_designer.core.intent_processor import IntentProcessor

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"


def _load_module(name: str, relative_path: str):
    path = _SRC / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_geometry = _load_module(
    "track9_geometry_helpers", "ai_designer/freecad/geometry_helpers.py"
)
_workflow = _load_module(
    "track9_workflow_templates", "ai_designer/freecad/workflow_templates.py"
)

analyze_geometry_requirements = _geometry.analyze_geometry_requirements
analyze_workflow_requirements = _workflow.analyze_workflow_requirements


def test_geometry_unknown_no_bare_mm_fabrication():
    g = analyze_geometry_requirements("mounting pattern 10mm and 20mm spacing")
    assert g["shape"] == "unknown"
    assert g["parse_confidence"] == "none"
    assert g["needs_llm_geometry"] is True
    assert g["dimensions"] == {}


def test_geometry_cylinder_explicit_unchanged():
    g = analyze_geometry_requirements(
        "Create a 50mm diameter cylinder that is 100mm tall"
    )
    assert g["shape"] == "circle"
    assert g["needs_llm_geometry"] is False
    assert g["parse_confidence"] == "high"
    assert g["dimensions"]["diameter"] == 50.0
    assert g["dimensions"]["height"] == 100.0


def test_geometry_bare_mm_fallback_only_when_shape_known():
    g = analyze_geometry_requirements("box 30mm 40mm")
    assert g["shape"] == "rectangle"
    assert g["dimensions"]["width"] == 30.0
    assert g["dimensions"]["height"] == 40.0
    assert g["needs_llm_geometry"] is False


def test_geometry_diameter_without_cylinder_or_hole_keyword():
    g = analyze_geometry_requirements("Extrude a 40mm diameter boss 12mm tall")
    assert g["shape"] == "circle"
    assert g["operation"] == "pad"
    assert g["dimensions"]["diameter"] == 40.0
    assert g["dimensions"]["height"] == 12.0


def test_workflow_ambiguous_primitive_with_fillet():
    state = {"object_count": 0, "live_state": {}}
    a = analyze_workflow_requirements("create a box with fillet corners", state)
    assert a["ambiguous_routing"] is True
    assert a["strategy"] == "simple"
    assert a["recommended_escalation"] == "standard_llm"
    assert a["requires_sketch_then_operate"] is False


def test_workflow_weak_signals_only_forces_simple():
    state = {"object_count": 0, "live_state": {}}
    nl = "one two three four five six seven eight nine and with extras"
    a = analyze_workflow_requirements(nl, state)
    assert a["ambiguous_routing"] is True
    assert a["strategy"] == "simple"


def test_workflow_clear_complex_still_complex():
    state = {"object_count": 0, "live_state": {}}
    a = analyze_workflow_requirements("design a mounting bracket with ribs", state)
    assert a["ambiguous_routing"] is False
    assert a["strategy"] == "complex_workflow"


def test_intent_create_and_query_collision_requires_llm():
    proc = IntentProcessor(state_service=None, llm_client=None)
    out = proc.process_intent("how do I create a box for export", session_id=None)
    assert out["ambiguous_intent"] is True
    assert out["action_plan"]["requires_llm"] is True


def test_intent_create_only_still_sensible():
    proc = IntentProcessor(state_service=None, llm_client=None)
    out = proc.process_intent("create a box 10mm 20mm 30mm", session_id=None)
    assert out["ambiguous_intent"] is False
    assert out["intent_type"] == "create_object"

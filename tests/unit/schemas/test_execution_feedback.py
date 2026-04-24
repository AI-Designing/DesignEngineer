"""Track 5: GeometrySummary and geometry_summary_from_state."""

from ai_designer.freecad.state_extractor import geometry_summary_from_state
from ai_designer.schemas.execution_feedback import GeometrySummary


def test_geometry_summary_from_state_with_geometry_summary_block():
    state = {
        "success": True,
        "object_count": 2,
        "geometry_summary": {
            "solid_object_count": 1,
            "total_volume_mm3": 8000.0,
            "document_bbox": {
                "xmin": 0.0,
                "ymin": 0.0,
                "zmin": 0.0,
                "xmax": 20.0,
                "ymax": 10.0,
                "zmax": 40.0,
            },
            "is_manifold": True,
            "has_invalid_faces": False,
            "has_self_intersections": None,
        },
    }
    g = geometry_summary_from_state(state)
    assert g is not None
    assert g.object_count == 2
    assert g.total_volume_mm3 == 8000.0
    assert g.bounding_box == {"length": 20.0, "width": 10.0, "height": 40.0}
    assert g.is_manifold is True
    assert g.has_invalid_faces is False
    assert g.has_self_intersections is None


def test_geometry_summary_from_state_failure_returns_none():
    assert geometry_summary_from_state({"success": False, "error": "x"}) is None
    assert geometry_summary_from_state(None) is None


def test_geometry_summary_to_legacy_flat():
    g = GeometrySummary(
        object_count=1,
        total_volume_mm3=1000.0,
        bounding_box={"length": 10.0, "width": 10.0, "height": 10.0},
        is_manifold=True,
        has_invalid_faces=False,
        has_self_intersections=False,
    )
    flat = g.to_legacy_flat()
    assert flat["object_count"] == 1
    assert flat["total_volume"] == 1000.0
    assert flat["bounding_box"]["length"] == 10.0

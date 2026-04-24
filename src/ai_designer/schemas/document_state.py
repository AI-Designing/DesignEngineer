"""
Stable JSON keys and types for FreeCAD document state extraction (Track 7).

Orchestration (Track 5) should map ``geometry_summary`` and related fields into
``execution_result`` for the validator; do not rename these keys without
coordinating with Track 5/6.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict

from typing_extensions import NotRequired

# Bump when adding/removing top-level contract fields consumed by other tracks.
STATE_SCHEMA_VERSION: int = 1

DetailLevel = Literal["minimal", "standard", "full"]

DETAIL_LEVELS: tuple[str, ...] = ("minimal", "standard", "full")
DEFAULT_DETAIL_LEVEL: DetailLevel = "standard"


class BBoxDict(TypedDict):
    xmin: float
    ymin: float
    zmin: float
    xmax: float
    ymax: float
    zmax: float


class CenterOfMassDict(TypedDict):
    x: float
    y: float
    z: float


class TopologyDict(TypedDict):
    face_count: int
    edge_count: int
    vertex_count: int


class LargestSolidDict(TypedDict):
    name: str
    volume_mm3: float


class GeometrySummaryDict(TypedDict, total=False):
    """Document-level aggregates; Track 5 maps into ``GeometrySummary`` for the validator."""

    solid_object_count: int
    total_volume_mm3: float
    document_bbox: Optional[BBoxDict]
    largest_solid_by_volume: Optional[LargestSolidDict]
    is_manifold: NotRequired[Optional[bool]]
    has_invalid_faces: NotRequired[Optional[bool]]
    has_self_intersections: NotRequired[Optional[bool]]


class SketchConstraintRowDict(TypedDict, total=False):
    type: Optional[int]
    type_name: Optional[str]
    id: Optional[str]
    first: Any
    second: Any
    third: Any


class SketchStateDict(TypedDict, total=False):
    sketch_name: str
    sketch_label: str
    constraints: List[SketchConstraintRowDict]
    fully_constrained: Optional[bool]
    dof_unknown: bool


class RecomputeIssueDict(TypedDict):
    name: str
    label: str
    state: int
    message: str


class DocumentStatePayload(TypedDict, total=False):
    """
    Payload shape emitted by ``StateExtractor`` / freecadcmd script.

    Legacy keys (object_count, objects, feature_tree, constraints,
    recompute_errors, metadata) are always present on success.
    """

    success: bool
    state_schema_version: int
    detail_level: str
    document_name: str
    document_path: str
    object_count: int
    objects: List[Dict[str, Any]]
    feature_tree: Dict[str, Any]
    recompute_errors: List[str]
    recompute_issues: List[RecomputeIssueDict]
    constraints: Dict[str, Any]
    sketches: List[SketchStateDict]
    geometry_summary: Optional[GeometrySummaryDict]
    sketch_constraints_truncated: bool
    metadata: Dict[str, Any]
    error: str

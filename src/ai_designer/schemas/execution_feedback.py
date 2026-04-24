"""
Execution feedback and geometry metrics shared by executor, pipeline nodes, and validator.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class GeometrySummary(BaseModel):
    """Machine-usable geometry metrics from FreeCAD (executor → validator)."""

    feedback_version: Literal["1"] = Field(
        default="1", description="Bump when fields change for downstream parsers"
    )
    object_count: int = Field(default=0, ge=0, description="Document object count")
    total_volume_mm3: Optional[float] = Field(
        default=None,
        description="Sum of solid volumes in mm³; null if not measured",
    )
    bounding_box: Optional[Dict[str, float]] = Field(
        default=None,
        description="Overall axis-aligned size as length, width, height (mm)",
    )
    is_manifold: Optional[bool] = Field(
        default=None,
        description="True if all measured solids appear watertight/valid; null if unknown",
    )
    has_invalid_faces: Optional[bool] = Field(
        default=None, description="True if any invalid shape; null if unknown"
    )
    has_self_intersections: Optional[bool] = Field(
        default=None, description="True if self-intersections detected; null if unknown"
    )

    def to_legacy_flat(self) -> Dict[str, Any]:
        """Top-level keys expected by older callers and LLM context."""
        out: Dict[str, Any] = {
            "object_count": self.object_count,
        }
        if self.total_volume_mm3 is not None:
            out["total_volume"] = self.total_volume_mm3
        if self.bounding_box is not None:
            out["bounding_box"] = self.bounding_box
        if self.is_manifold is not None:
            out["is_manifold"] = self.is_manifold
        if self.has_invalid_faces is not None:
            out["has_invalid_faces"] = self.has_invalid_faces
        if self.has_self_intersections is not None:
            out["has_self_intersections"] = self.has_self_intersections
        return out


class ExecutionFeedback(BaseModel):
    """Typed view of executor output; pipeline may still use dict for LangGraph state."""

    success: bool = Field(default=False)
    errors: List[str] = Field(default_factory=list)
    execution_time: float = Field(default=0.0)
    document_path: Optional[str] = None
    created_objects: List[str] = Field(default_factory=list)
    geometry: Optional[GeometrySummary] = None
    geometry_unavailable_reason: Optional[str] = Field(
        default=None,
        description="Set when execution succeeded but metrics could not be produced",
    )
    skipped: bool = Field(default=False, description="Executor was not run")
    skip_reason: Optional[str] = None

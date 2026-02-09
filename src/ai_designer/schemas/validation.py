"""
Validation schemas for design quality assessment.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity level of validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class GeometricValidation(BaseModel):
    """Geometric validation results from FreeCAD analysis."""

    is_valid: bool = Field(..., description="Overall geometric validity")
    has_solid_bodies: bool = Field(
        default=False, description="Contains valid solid bodies"
    )
    body_count: int = Field(default=0, ge=0, description="Number of solid bodies")

    # Geometric checks
    is_manifold: bool = Field(
        default=True, description="All bodies are manifold (watertight)"
    )
    has_invalid_faces: bool = Field(
        default=False, description="Contains invalid/degenerate faces"
    )
    has_self_intersections: bool = Field(
        default=False, description="Contains self-intersecting geometry"
    )

    # Measurements
    total_volume: Optional[float] = Field(
        default=None, description="Total volume in mm³"
    )
    bounding_box: Optional[Dict[str, float]] = Field(
        default=None, description="Bounding box dimensions (length, width, height)"
    )

    # Issues
    issues: List[str] = Field(
        default_factory=list, description="List of geometric issues found"
    )


class SemanticValidation(BaseModel):
    """Semantic validation of design against user requirements."""

    is_valid: bool = Field(..., description="Semantically matches user intent")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in semantic match (0-1)"
    )

    # Requirement checking
    requirements_met: List[str] = Field(
        default_factory=list, description="Requirements successfully met"
    )
    requirements_missing: List[str] = Field(
        default_factory=list, description="Requirements not met"
    )

    # Design characteristics
    detected_features: List[str] = Field(
        default_factory=list, description="CAD features detected in design"
    )
    expected_features: List[str] = Field(
        default_factory=list, description="Features expected from prompt"
    )

    # Issues
    issues: List[str] = Field(
        default_factory=list, description="Semantic validation issues"
    )


class LLMReviewResult(BaseModel):
    """LLM-based design review results."""

    overall_assessment: str = Field(
        ..., description="High-level assessment of design quality"
    )
    quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall quality score (0-1)"
    )

    # Detailed feedback
    strengths: List[str] = Field(
        default_factory=list, description="Design strengths identified"
    )
    weaknesses: List[str] = Field(
        default_factory=list, description="Design weaknesses identified"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Improvement suggestions"
    )

    # Code quality
    script_quality_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Quality of generated FreeCAD script"
    )
    code_issues: List[str] = Field(
        default_factory=list, description="Issues in generated code"
    )


class ValidationResult(BaseModel):
    """Complete validation result for a design."""

    request_id: str = Field(..., description="Links to DesignRequest/DesignState")
    is_valid: bool = Field(..., description="Overall validation status")
    validation_time: datetime = Field(
        default_factory=datetime.utcnow, description="Validation timestamp"
    )

    # Component validations
    geometric: Optional[GeometricValidation] = Field(
        default=None, description="Geometric validation results"
    )
    semantic: Optional[SemanticValidation] = Field(
        default=None, description="Semantic validation results"
    )
    llm_review: Optional[LLMReviewResult] = Field(
        default=None, description="LLM review results"
    )

    # Aggregated issues
    all_issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All issues with severity levels",
    )

    # Overall scores
    geometric_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Geometric quality (0-1)"
    )
    semantic_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Semantic match (0-1)"
    )
    overall_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Combined quality score (0-1)"
    )

    # Recommendations
    should_refine: bool = Field(
        default=False, description="Should trigger refinement iteration"
    )
    refinement_suggestions: List[str] = Field(
        default_factory=list, description="Specific suggestions for refinement"
    )

    def add_issue(
        self, severity: ValidationSeverity, message: str, source: str
    ) -> None:
        """Add a validation issue."""
        self.all_issues.append(
            {
                "severity": severity.value,
                "message": message,
                "source": source,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def calculate_overall_score(self) -> float:
        """Calculate weighted overall score from component scores."""
        scores = []
        weights = []

        if self.geometric_score is not None:
            scores.append(self.geometric_score)
            weights.append(0.4)  # Geometric is critical

        if self.semantic_score is not None:
            scores.append(self.semantic_score)
            weights.append(0.4)  # Semantic match is critical

        if self.llm_review and self.llm_review.quality_score is not None:
            scores.append(self.llm_review.quality_score)
            weights.append(0.2)  # LLM review is supplementary

        if not scores:
            return 0.0

        # Weighted average
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)
        self.overall_score = weighted_sum / total_weight
        return self.overall_score

    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(
            issue["severity"] == ValidationSeverity.CRITICAL.value
            for issue in self.all_issues
        )

    def get_issues_by_severity(
        self, severity: ValidationSeverity
    ) -> List[Dict[str, Any]]:
        """Get issues filtered by severity."""
        return [
            issue for issue in self.all_issues if issue["severity"] == severity.value
        ]

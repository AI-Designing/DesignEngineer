"""
Validator Agent for design quality assessment.

This agent performs multi-faceted validation of generated FreeCAD designs,
combining geometric analysis, semantic checking, and LLM-based review.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from ai_designer.agents.base import BaseAgent
from ai_designer.core.exceptions import LLMError
from ai_designer.core.logging_config import get_logger
from ai_designer.freecad.state_extractor import geometry_summary_from_state
from ai_designer.llm.provider import LLMMessage, LLMRequest, LLMRole, UnifiedLLMProvider
from ai_designer.schemas.design_state import AgentType, DesignRequest
from ai_designer.schemas.execution_feedback import GeometrySummary
from ai_designer.schemas.task_graph import TaskGraph
from ai_designer.schemas.validation import (
    GeometricValidation,
    LLMReviewResult,
    SemanticValidation,
    ValidationResult,
    ValidationSeverity,
)

logger = get_logger(__name__)

# FreeCAD object TypeId -> planner operation_type used in TaskGraph
_FC_TYPE_TO_PLANNER_OP: Dict[str, str] = {
    "Part::Box": "create_box",
    "Part::Cylinder": "create_cylinder",
    "Part::Sphere": "create_sphere",
    "Part::Cone": "create_cone",
    "Part::Torus": "create_torus",
    "Part::Cut": "boolean_cut",
    "Part::Fuse": "boolean_fuse",
    "Part::MultiFuse": "boolean_fuse",
    "Part::Fillet": "fillet",
    "Part::Chamfer": "chamfer",
}

_PROMPT_THREE_DIMS = re.compile(
    r"(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)",
    re.IGNORECASE,
)


@dataclass
class DesignIntentSpec:
    """Structured design intent derived from the task graph (and optional prompt)."""

    required_operations: List[str]
    box_length: Optional[float] = None
    box_width: Optional[float] = None
    box_height: Optional[float] = None
    prompt_mentions_hole: bool = False
    prompt_mentions_fillet: bool = False


class ValidatorAgent(BaseAgent):
    """
    Multi-faceted validation agent for FreeCAD designs.

    The ValidatorAgent assesses design quality through three dimensions:
    1. Geometric validation - checks geometry validity, measurements, and structure
    2. Semantic validation - verifies design matches user requirements
    3. LLM review - provides qualitative assessment and suggestions

    Attributes:
        llm_provider: Unified LLM provider for semantic review
        agent_type: Fixed to AgentType.VALIDATOR
        default_temperature: Temperature for review generation (default: 0.3)
        pass_threshold: Score threshold for automatic pass (default: 0.8)
        refine_threshold: Minimum score for refinement attempt (default: 0.4)
    """

    # System prompt for design review
    REVIEW_PROMPT = """You are an expert FreeCAD design reviewer specializing in CAD quality assessment.

Your role is to evaluate generated FreeCAD designs against user requirements and engineering best practices.

EVALUATION CRITERIA:
1. **Design Intent Match**: Does the design fulfill the user's stated requirements?
2. **Geometric Quality**: Are shapes properly formed, dimensioned, and constructed?
3. **Code Quality**: Is the FreeCAD Python code correct, efficient, and maintainable?
4. **Practical Feasibility**: Is the design manufacturable and physically sound?
5. **Completeness**: Are all requested features present and properly integrated?

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
  "overall_assessment": "Brief 1-2 sentence summary of design quality",
  "quality_score": 0.85,
  "strengths": [
    "Correctly implements box with specified dimensions",
    "Clean boolean operation with proper object references"
  ],
  "weaknesses": [
    "Cylinder positioning may not be centered",
    "Missing fillet operations mentioned in prompt"
  ],
  "suggestions": [
    "Add position parameters to center the hole",
    "Include 2mm fillets on box edges as requested"
  ],
  "code_issues": [
    "Could use more descriptive variable names",
    "Missing error handling for getObject calls"
  ],
  "script_quality_score": 0.75
}

SCORING GUIDE:
- 0.9-1.0: Excellent - fully meets requirements with high quality
- 0.7-0.89: Good - meets requirements with minor issues
- 0.5-0.69: Fair - partially meets requirements, needs refinement
- 0.3-0.49: Poor - significant gaps or errors
- 0.0-0.29: Failed - does not meet basic requirements

Review the following FreeCAD design:"""

    def __init__(
        self,
        llm_provider: UnifiedLLMProvider,
        temperature: float = 0.3,
        pass_threshold: float = 0.8,
        refine_threshold: float = 0.4,
    ):
        """Initialize the Validator Agent."""
        super().__init__(
            llm_provider=llm_provider,
            agent_type=AgentType.VALIDATOR,
            max_retries=3,
            temperature=temperature,
        )
        if not 0.0 <= pass_threshold <= 1.0:
            raise ValueError(
                f"Pass threshold must be in [0.0, 1.0], got {pass_threshold}"
            )
        if not 0.0 <= refine_threshold <= 1.0:
            raise ValueError(
                f"Refine threshold must be in [0.0, 1.0], got {refine_threshold}"
            )
        if refine_threshold > pass_threshold:
            raise ValueError(
                f"Refine threshold ({refine_threshold}) must be <= "
                f"pass threshold ({pass_threshold})"
            )
        self.pass_threshold = pass_threshold
        self.refine_threshold = refine_threshold

    async def execute(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D102
        """Delegate to validate() to satisfy BaseAgent contract."""
        return await self.validate(*args, **kwargs)

    async def validate(
        self,
        design_request: DesignRequest,
        task_graph: TaskGraph,
        generated_scripts: Dict[str, str],
        execution_result: Optional[Dict[str, any]] = None,
    ) -> ValidationResult:
        """Validate a generated design.

        Performs comprehensive validation including geometric checks,
        semantic matching, and LLM-based review.

        Args:
            design_request: Original design request with user prompt
            task_graph: The task graph that was executed
            generated_scripts: Dictionary of task_id -> generated Python code
            execution_result: Optional execution results from FreeCAD

        Returns:
            Complete validation result with scores and recommendations
        """
        logger.info(
            f"Validating design for request {design_request.request_id} "
            f"with {len(generated_scripts)} scripts"
        )

        # Initialize validation result
        result = ValidationResult(
            request_id=str(design_request.request_id), is_valid=False
        )

        # 1. Geometric validation (if execution results available; skip when executor absent)
        if execution_result and not execution_result.get("skipped"):
            result.geometric = self._validate_geometry(execution_result, task_graph)
            result.geometric_score = self._calculate_geometric_score(result.geometric)

        # 2. Semantic validation
        result.semantic = self._validate_semantics(
            design_request,
            task_graph,
            generated_scripts,
            execution_result,
        )
        result.semantic_score = result.semantic.confidence_score

        # 3. LLM-based review
        result.llm_review = await self._perform_llm_review(
            design_request, task_graph, generated_scripts, execution_result
        )

        # 4. Calculate overall score
        result.calculate_overall_score()

        # 5. Make validation decision
        result.is_valid = self._make_validation_decision(result)

        # 6. Add refinement suggestions if needed
        if not result.is_valid and result.overall_score >= self.refine_threshold:
            result.should_refine = True
            result.refinement_suggestions = self._generate_refinement_suggestions(
                result
            )

        logger.info(
            f"Validation complete: overall_score={result.overall_score:.2f}, "
            f"is_valid={result.is_valid}, should_refine={result.should_refine}"
        )

        return result

    def _execution_error_message(
        self, execution_result: Dict[str, Any]
    ) -> Optional[str]:
        err = execution_result.get("error")
        if err is None:
            return None
        if isinstance(err, (list, tuple)):
            parts = [str(x) for x in err if x]
            return "; ".join(parts) if parts else None
        return str(err)

    def _resolve_geometry_summary(
        self, execution_result: Dict[str, Any]
    ) -> Optional[GeometrySummary]:
        raw = execution_result.get("geometry")
        if isinstance(raw, dict):
            try:
                return GeometrySummary.model_validate(raw)
            except Exception:
                logger.warning("Invalid geometry payload; falling back to state/legacy")
        state = execution_result.get("state")
        if isinstance(state, dict):
            g = geometry_summary_from_state(state)
            if g is not None:
                return g
        if any(
            k in execution_result
            for k in ("object_count", "total_volume", "bounding_box")
        ):
            return GeometrySummary(
                object_count=int(execution_result.get("object_count", 0)),
                total_volume_mm3=execution_result.get("total_volume"),
                bounding_box=execution_result.get("bounding_box"),
                is_manifold=execution_result.get("is_manifold"),
                has_invalid_faces=execution_result.get("has_invalid_faces"),
                has_self_intersections=execution_result.get("has_self_intersections"),
            )
        return None

    def _validate_geometry(
        self, execution_result: Dict[str, any], task_graph: TaskGraph
    ) -> GeometricValidation:
        """Perform geometric validation on execution results.

        Args:
            execution_result: Results from FreeCAD execution
            task_graph: The task graph for expected object count

        Returns:
            Geometric validation results
        """
        logger.info("Performing geometric validation")

        validation = GeometricValidation(is_valid=True)
        issues: List[str] = []

        err = self._execution_error_message(execution_result)
        if err:
            validation.is_valid = False
            issues.append(f"Execution error: {err}")
            validation.issues = issues
            return validation

        geom = self._resolve_geometry_summary(execution_result)
        exec_ok = execution_result.get("success") is True
        unavailable = execution_result.get("geometry_unavailable_reason")

        object_count = (
            geom.object_count if geom else int(execution_result.get("object_count", 0))
        )
        expected_count = len([t for t in task_graph.nodes.values()])

        validation.body_count = object_count
        validation.has_solid_bodies = object_count > 0

        if object_count == 0:
            validation.is_valid = False
            issues.append("No solid bodies created")
        elif object_count < expected_count:
            issues.append(
                f"Object count mismatch: expected ~{expected_count}, got {object_count}"
            )

        total_volume: Optional[float] = None
        if geom and geom.total_volume_mm3 is not None:
            total_volume = float(geom.total_volume_mm3)
        elif execution_result.get("total_volume") is not None:
            total_volume = float(execution_result["total_volume"])

        validation.total_volume = total_volume

        volume_known = total_volume is not None
        if volume_known:
            if total_volume <= 0 and object_count > 0:
                validation.is_valid = False
                issues.append(
                    "Invalid volume: volume must be positive for non-empty model"
                )
            elif total_volume is not None and total_volume > 1e9:
                issues.append(f"Unusually large volume: {total_volume} mm³")
        elif exec_ok and object_count > 0:
            if unavailable:
                issues.append(f"Geometry metrics unavailable: {unavailable}")
            else:
                issues.append(
                    "Geometry volume not measured; cannot confirm solid volume"
                )

        bbox = geom.bounding_box if geom else execution_result.get("bounding_box")
        if bbox:
            validation.bounding_box = dict(bbox)
            for dim, value in bbox.items():
                if value <= 0:
                    issues.append(f"Invalid {dim}: {value} (must be positive)")
                elif value > 10000:
                    issues.append(f"Unusually large {dim}: {value} mm")

        if geom:
            validation.is_manifold = (
                geom.is_manifold
                if geom.is_manifold is not None
                else execution_result.get("is_manifold")
            )
            validation.has_invalid_faces = (
                geom.has_invalid_faces
                if geom.has_invalid_faces is not None
                else execution_result.get("has_invalid_faces")
            )
            validation.has_self_intersections = (
                geom.has_self_intersections
                if geom.has_self_intersections is not None
                else execution_result.get("has_self_intersections")
            )
        else:
            validation.is_manifold = execution_result.get("is_manifold")
            validation.has_invalid_faces = execution_result.get("has_invalid_faces")
            validation.has_self_intersections = execution_result.get(
                "has_self_intersections"
            )

        if validation.is_manifold is False:
            issues.append("Geometry is not manifold (not watertight)")

        if validation.has_invalid_faces is True:
            issues.append("Contains invalid or degenerate faces")

        if validation.has_self_intersections is True:
            issues.append("Contains self-intersecting geometry")

        validation.issues = issues

        if issues:
            logger.warning("Geometric validation found %s issues", len(issues))

        return validation

    def _calculate_geometric_score(self, geo_validation: GeometricValidation) -> float:
        """Calculate a numeric score from geometric validation.

        Args:
            geo_validation: Geometric validation results

        Returns:
            Score between 0.0 and 1.0
        """
        if not geo_validation.is_valid:
            return 0.0

        score = 1.0
        penalty_per_issue = 0.15

        # Deduct for each issue
        score -= len(geo_validation.issues) * penalty_per_issue

        # Bonus for having solid bodies
        if not geo_validation.has_solid_bodies:
            score -= 0.5

        if geo_validation.is_manifold is False:
            score -= 0.2

        if geo_validation.has_invalid_faces is True:
            score -= 0.2

        if geo_validation.has_self_intersections is True:
            score -= 0.3

        return max(0.0, min(1.0, score))

    def _task_ids_in_order(self, task_graph: TaskGraph) -> List[str]:
        """Topological task order; append any nodes missing from ordering."""
        ordered: List[str] = []
        for level in task_graph.get_execution_order():
            ordered.extend(level)
        for tid in task_graph.nodes:
            if tid not in ordered:
                ordered.append(tid)
        return ordered

    def _build_intent_spec(
        self, design_request: DesignRequest, task_graph: TaskGraph
    ) -> DesignIntentSpec:
        """Derive structured intent from the task graph and optional prompt numerics."""
        ordered = self._task_ids_in_order(task_graph)
        required_operations = [
            task_graph.nodes[tid].operation_type
            for tid in ordered
            if tid in task_graph.nodes
        ]

        bl = bw = bh = None
        for tid in ordered:
            if tid not in task_graph.nodes:
                continue
            node = task_graph.nodes[tid]
            if node.operation_type != "create_box":
                continue
            params = node.parameters or {}
            try:
                if params.get("length") is not None:
                    bl = float(params["length"])
                if params.get("width") is not None:
                    bw = float(params["width"])
                if params.get("height") is not None:
                    bh = float(params["height"])
            except (TypeError, ValueError):
                continue

        if bl is None and bw is None and bh is None:
            m = _PROMPT_THREE_DIMS.search(design_request.user_prompt)
            if m:
                try:
                    bl, bw, bh = float(m.group(1)), float(m.group(2)), float(m.group(3))
                except ValueError:
                    pass

        pl = design_request.user_prompt.lower()
        return DesignIntentSpec(
            required_operations=required_operations,
            box_length=bl,
            box_width=bw,
            box_height=bh,
            prompt_mentions_hole=("hole" in pl or "cut" in pl),
            prompt_mentions_fillet=("round" in pl or "fillet" in pl),
        )

    def _detect_features_from_scripts(
        self, generated_scripts: Dict[str, str]
    ) -> Set[str]:
        """Weak evidence: substring patterns in generated code (fallback only)."""
        detected: Set[str] = set()
        blob = "\n".join(generated_scripts.values())
        if "Box" in blob or "makeBox" in blob:
            detected.add("create_box")
        if "Cylinder" in blob or "makeCylinder" in blob:
            detected.add("create_cylinder")
        if "Sphere" in blob or "makeSphere" in blob:
            detected.add("create_sphere")
        if "Cut" in blob or ".cut(" in blob:
            detected.add("boolean_cut")
        if "Fuse" in blob or ".fuse(" in blob:
            detected.add("boolean_fuse")
        if "Fillet" in blob or "makeFillet" in blob:
            detected.add("fillet")
        if "Chamfer" in blob or "makeChamfer" in blob:
            detected.add("chamfer")
        return detected

    def _detect_features_from_state(
        self, execution_result: Optional[Dict[str, Any]]
    ) -> Set[str]:
        """Map FreeCAD document objects to planner-level operation tags."""
        out: Set[str] = set()
        if not execution_result:
            return out
        state = execution_result.get("state")
        if not isinstance(state, dict) or not state.get("success"):
            return out
        for obj in state.get("objects") or []:
            tid = str(obj.get("type") or "")
            mapped = _FC_TYPE_TO_PLANNER_OP.get(tid)
            if mapped:
                out.add(mapped)
            elif "Cut" in tid:
                out.add("boolean_cut")
            elif "Fuse" in tid or "MultiFuse" in tid:
                out.add("boolean_fuse")
        return out

    def _dimension_check_vs_bbox(
        self, intent: DesignIntentSpec, execution_result: Optional[Dict[str, Any]]
    ) -> Tuple[str, List[str], List[str]]:
        """
        Returns:
            status: 'pass' | 'fail' | 'unknown'
            issues, data_gaps
        """
        issues: List[str] = []
        gaps: List[str] = []
        dims = [intent.box_length, intent.box_width, intent.box_height]
        if all(d is None for d in dims):
            return "pass", issues, gaps

        if not execution_result or not execution_result.get("bounding_box"):
            gaps.append(
                "cannot verify dimensions (no bounding box in execution result)"
            )
            return "unknown", issues, gaps

        bbox = execution_result["bounding_box"]
        try:
            b_dims = sorted(
                [
                    float(bbox["length"]),
                    float(bbox["width"]),
                    float(bbox["height"]),
                ],
                reverse=True,
            )
        except (KeyError, TypeError, ValueError):
            gaps.append("cannot verify dimensions (bounding box malformed)")
            return "unknown", issues, gaps

        spec_dims = sorted([float(d) for d in dims if d is not None], reverse=True)
        if len(spec_dims) < 3:
            gaps.append(
                "partial box dimensions in plan; skipped strict bbox comparison"
            )
            return "unknown", issues, gaps

        tol_rel = 0.10
        tol_abs = 0.5
        for sd, bd in zip(spec_dims, b_dims):
            limit = max(tol_abs, tol_rel * max(abs(sd), 1e-6))
            if abs(sd - bd) > limit:
                issues.append(
                    f"Bounding box size mismatch: expected ~{spec_dims} mm "
                    f"(sorted L/W/H), got {b_dims} mm from geometry"
                )
                return "fail", issues, gaps

        return "pass", issues, gaps

    def _operations_match_score(
        self,
        intent: DesignIntentSpec,
        from_state: Set[str],
        from_scripts: Set[str],
        structured_notes: List[str],
    ) -> Tuple[float, List[str], List[str], List[str], List[str]]:
        """
        Returns:
            ops_score 0..1, requirements_met, requirements_missing,
            detected_features (ordered list for schema), data_gaps
        """
        expected = intent.required_operations
        if not expected:
            return 1.0, [], [], sorted(from_state or from_scripts), []

        gaps: List[str] = []
        use_state = bool(from_state)
        detected = set(from_state) if use_state else set(from_scripts)
        if use_state:
            structured_notes.append("operation_evidence=document_state")
        else:
            structured_notes.append(
                "operation_evidence=script_heuristics_weak_cap_applied"
            )
            gaps.append(
                "document state unavailable; operation match uses script keywords only"
            )

        met: List[str] = []
        missing: List[str] = []
        for feat in expected:
            if feat in detected:
                met.append(feat)
            else:
                missing.append(feat)

        if not expected:
            ratio = 1.0
        else:
            ratio = len(met) / len(expected)

        if use_state:
            score = ratio
        else:
            score = min(0.85, ratio * 0.9)

        return (
            score,
            met,
            missing,
            sorted(detected),
            gaps,
        )

    def _validate_semantics(
        self,
        design_request: DesignRequest,
        task_graph: TaskGraph,
        generated_scripts: Dict[str, str],
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> SemanticValidation:
        """Perform semantic validation against user requirements.

        Uses task parameters and execution metrics/state when available; falls back
        to script keyword heuristics with explicit data gaps when information is missing.
        """
        logger.info("Performing semantic validation")

        intent = self._build_intent_spec(design_request, task_graph)
        expected_features = intent.required_operations

        from_state = self._detect_features_from_state(execution_result)
        from_scripts = self._detect_features_from_scripts(generated_scripts)

        structured_notes: List[str] = []
        data_gaps: List[str] = []

        (
            ops_score,
            requirements_met,
            requirements_missing,
            detected_sorted,
            op_gaps,
        ) = self._operations_match_score(
            intent, from_state, from_scripts, structured_notes
        )
        data_gaps.extend(op_gaps)

        dim_status, dim_issues, dim_gaps = self._dimension_check_vs_bbox(
            intent, execution_result
        )
        issues: List[str] = list(dim_issues)
        data_gaps.extend(dim_gaps)
        if dim_status == "pass":
            structured_notes.append("dimensions_vs_bbox=pass")
        elif dim_status == "fail":
            structured_notes.append("dimensions_vs_bbox=fail")
        else:
            structured_notes.append("dimensions_vs_bbox=unknown")

        confidence_score = ops_score
        if dim_status == "fail":
            confidence_score *= 0.4
        elif dim_status == "unknown":
            confidence_score *= 0.92

        # Keyword alignment: prefer state evidence, union scripts for prompt hints
        detected_for_keywords = set(detected_sorted) | from_scripts
        prompt_lower = design_request.user_prompt.lower()
        if (
            intent.prompt_mentions_hole
            or "hole" in prompt_lower
            or "cut" in prompt_lower
        ):
            if "boolean_cut" not in detected_for_keywords:
                issues.append("Prompt mentions hole/cut but no boolean cut detected")
                confidence_score *= 0.82

        if intent.prompt_mentions_fillet:
            if "fillet" not in detected_for_keywords:
                issues.append("Prompt mentions rounding but no fillet detected")
                confidence_score *= 0.9

        confidence_score = min(1.0, max(0.0, confidence_score))

        is_valid = confidence_score >= 0.6

        return SemanticValidation(
            is_valid=is_valid,
            confidence_score=confidence_score,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            detected_features=detected_sorted,
            expected_features=expected_features,
            issues=issues,
            data_gaps=data_gaps,
            structured_notes=structured_notes,
        )

    async def _perform_llm_review(
        self,
        design_request: DesignRequest,
        task_graph: TaskGraph,
        generated_scripts: Dict[str, str],
        execution_result: Optional[Dict[str, any]],
    ) -> LLMReviewResult:
        """Perform LLM-based design review.

        Args:
            design_request: Original design request
            task_graph: Task graph structure
            generated_scripts: Generated FreeCAD scripts
            execution_result: Optional execution results

        Returns:
            LLM review results
        """
        logger.info("Performing LLM-based design review")

        # Build review context
        review_context = self._build_review_context(
            design_request, task_graph, generated_scripts, execution_result
        )

        # Prepare LLM request
        llm_request = LLMRequest(
            messages=[
                LLMMessage(role=LLMRole.SYSTEM, content=self.REVIEW_PROMPT),
                LLMMessage(role=LLMRole.USER, content=review_context),
            ],
            model=self.llm_provider.default_model,
            temperature=self.default_temperature,
            max_tokens=2048,
        )

        try:
            response = await self.llm_provider.agenerate(llm_request)
            review_data = self._parse_review_response(response.content)

            return LLMReviewResult(
                overall_assessment=review_data.get(
                    "overall_assessment", "No assessment provided"
                ),
                quality_score=review_data.get("quality_score", 0.5),
                strengths=review_data.get("strengths", []),
                weaknesses=review_data.get("weaknesses", []),
                suggestions=review_data.get("suggestions", []),
                script_quality_score=review_data.get("script_quality_score"),
                code_issues=review_data.get("code_issues", []),
            )

        except Exception as e:
            logger.error(f"LLM review failed: {e}")
            # Return fallback review on error
            return LLMReviewResult(
                overall_assessment="LLM review unavailable due to error",
                quality_score=0.5,
                strengths=[],
                weaknesses=[f"LLM review failed: {str(e)}"],
                suggestions=[],
            )

    def _build_review_context(
        self,
        design_request: DesignRequest,
        task_graph: TaskGraph,
        generated_scripts: Dict[str, str],
        execution_result: Optional[Dict[str, any]],
    ) -> str:
        """Build context for LLM review.

        Args:
            design_request: Original request
            task_graph: Task graph
            generated_scripts: Generated code
            execution_result: Execution results

        Returns:
            Formatted review context string
        """
        context_parts = [
            "USER PROMPT:",
            design_request.user_prompt,
            "",
            "TASK BREAKDOWN:",
            f"Total tasks: {len(task_graph.nodes)}",
        ]

        # Add task details
        for task in task_graph.nodes.values():
            context_parts.append(
                f"- {task.task_id}: {task.operation_type} - {task.description}"
            )

        context_parts.append("")
        context_parts.append("GENERATED CODE:")

        # Add scripts
        for task_id, script in generated_scripts.items():
            context_parts.append(f"\n--- {task_id} ---")
            context_parts.append(script)

        # Add execution results if available
        if execution_result:
            context_parts.append("")
            context_parts.append("EXECUTION RESULTS:")
            err = self._execution_error_message(execution_result)
            context_parts.append(f"Success: {execution_result.get('success', False)}")
            if err:
                context_parts.append(f"Error: {err}")
            raw_g = execution_result.get("geometry")
            if isinstance(raw_g, dict):
                context_parts.append(
                    f"Geometry summary (JSON): {json.dumps(raw_g, indent=2)}"
                )
            else:
                context_parts.append(
                    f"Objects (legacy count): {execution_result.get('object_count', 0)}"
                )
                tv = execution_result.get("total_volume")
                if tv is not None:
                    context_parts.append(f"Total volume: {tv} mm³")
            if execution_result.get("geometry_unavailable_reason"):
                context_parts.append(
                    "Note: " + str(execution_result["geometry_unavailable_reason"])
                )

        return "\n".join(context_parts)

    def _parse_review_response(self, response_content: str) -> Dict[str, any]:
        """Parse LLM review response.

        Args:
            response_content: Raw LLM response

        Returns:
            Parsed review data dictionary
        """
        # Try to extract JSON from response
        content = response_content.strip()

        # Remove markdown code fences if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse review JSON: {e}")
            # Return minimal valid structure
            return {
                "overall_assessment": "Failed to parse review",
                "quality_score": 0.5,
                "strengths": [],
                "weaknesses": ["Review parsing failed"],
                "suggestions": [],
            }

    def _make_validation_decision(self, result: ValidationResult) -> bool:
        """Make overall validation decision.

        Args:
            result: Validation result with scores

        Returns:
            True if design passes validation
        """
        # Fail if critical issues exist
        if result.has_critical_issues():
            logger.info("Validation failed: critical issues detected")
            return False

        # Fail if no overall score could be calculated
        if result.overall_score is None:
            logger.info("Validation failed: no score available")
            return False

        # Pass if score meets threshold
        passes = result.overall_score >= self.pass_threshold

        logger.info(
            f"Validation decision: {'PASS' if passes else 'FAIL'} "
            f"(score {result.overall_score:.2f} vs threshold {self.pass_threshold})"
        )

        return passes

    def _generate_refinement_suggestions(self, result: ValidationResult) -> List[str]:
        """Generate specific refinement suggestions.

        Args:
            result: Validation result

        Returns:
            List of actionable refinement suggestions
        """
        suggestions = []

        # Add geometric issues
        if result.geometric and result.geometric.issues:
            suggestions.extend(
                [f"Geometric: {issue}" for issue in result.geometric.issues[:3]]
            )

        # Add semantic issues
        if result.semantic and result.semantic.issues:
            suggestions.extend(
                [f"Semantic: {issue}" for issue in result.semantic.issues[:3]]
            )

        # Add missing requirements
        if result.semantic and result.semantic.requirements_missing:
            missing = ", ".join(result.semantic.requirements_missing[:3])
            suggestions.append(f"Missing features: {missing}")

        # Add LLM suggestions
        if result.llm_review and result.llm_review.suggestions:
            suggestions.extend(result.llm_review.suggestions[:3])

        return suggestions[:5]  # Limit to top 5 suggestions

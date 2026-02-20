"""
Validator Agent for design quality assessment.

This agent performs multi-faceted validation of generated FreeCAD designs,
combining geometric analysis, semantic checking, and LLM-based review.
"""

import json
from typing import Any, Dict, List, Optional

from ai_designer.agents.base import BaseAgent
from ai_designer.core.exceptions import LLMError
from ai_designer.core.llm_provider import (
    LLMMessage,
    LLMRequest,
    LLMRole,
    UnifiedLLMProvider,
)
from ai_designer.core.logging_config import get_logger
from ai_designer.schemas.design_state import AgentType, DesignRequest
from ai_designer.schemas.task_graph import TaskGraph
from ai_designer.schemas.validation import (
    GeometricValidation,
    LLMReviewResult,
    SemanticValidation,
    ValidationResult,
    ValidationSeverity,
)

logger = get_logger(__name__)


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

        # 1. Geometric validation (if execution results available)
        if execution_result:
            result.geometric = self._validate_geometry(execution_result, task_graph)
            result.geometric_score = self._calculate_geometric_score(result.geometric)

        # 2. Semantic validation
        result.semantic = self._validate_semantics(
            design_request, task_graph, generated_scripts
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
        issues = []

        # Check if FreeCAD recompute succeeded
        if execution_result.get("error"):
            validation.is_valid = False
            issues.append(f"Execution error: {execution_result['error']}")
            validation.issues = issues
            return validation

        # Check object count
        object_count = execution_result.get("object_count", 0)
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

        # Check volume
        total_volume = execution_result.get("total_volume", 0)
        validation.total_volume = total_volume

        if total_volume <= 0:
            validation.is_valid = False
            issues.append("Invalid volume: volume must be positive")
        elif total_volume > 1e9:  # Sanity check: > 1 cubic meter
            issues.append(f"Unusually large volume: {total_volume} mm³")

        # Check bounding box
        bbox = execution_result.get("bounding_box")
        if bbox:
            validation.bounding_box = bbox
            # Sanity checks on dimensions
            for dim, value in bbox.items():
                if value <= 0:
                    issues.append(f"Invalid {dim}: {value} (must be positive)")
                elif value > 10000:  # > 10 meters
                    issues.append(f"Unusually large {dim}: {value} mm")

        # Check for invalid geometry flags
        validation.is_manifold = execution_result.get("is_manifold", True)
        validation.has_invalid_faces = execution_result.get("has_invalid_faces", False)
        validation.has_self_intersections = execution_result.get(
            "has_self_intersections", False
        )

        if not validation.is_manifold:
            issues.append("Geometry is not manifold (not watertight)")

        if validation.has_invalid_faces:
            issues.append("Contains invalid or degenerate faces")

        if validation.has_self_intersections:
            issues.append("Contains self-intersecting geometry")

        validation.issues = issues

        if issues:
            logger.warning(f"Geometric validation found {len(issues)} issues")

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

        # Penalty for invalid geometry
        if not geo_validation.is_manifold:
            score -= 0.2

        if geo_validation.has_invalid_faces:
            score -= 0.2

        if geo_validation.has_self_intersections:
            score -= 0.3

        return max(0.0, min(1.0, score))

    def _validate_semantics(
        self,
        design_request: DesignRequest,
        task_graph: TaskGraph,
        generated_scripts: Dict[str, str],
    ) -> SemanticValidation:
        """Perform semantic validation against user requirements.

        Args:
            design_request: Original design request
            task_graph: Task graph structure
            generated_scripts: Generated code

        Returns:
            Semantic validation results
        """
        logger.info("Performing semantic validation")

        # Extract expected features from task graph
        expected_features = [task.operation_type for task in task_graph.nodes.values()]

        # Detect features in generated scripts
        detected_features = []
        for script in generated_scripts.values():
            if "Box" in script or "makeBox" in script:
                detected_features.append("create_box")
            if "Cylinder" in script or "makeCylinder" in script:
                detected_features.append("create_cylinder")
            if "Sphere" in script or "makeSphere" in script:
                detected_features.append("create_sphere")
            if "Cut" in script or ".cut(" in script:
                detected_features.append("boolean_cut")
            if "Fuse" in script or ".fuse(" in script:
                detected_features.append("boolean_fuse")
            if "Fillet" in script or "makeFillet" in script:
                detected_features.append("fillet")

        detected_features = list(set(detected_features))  # Remove duplicates

        # Check requirements matching
        requirements_met = [f for f in expected_features if f in detected_features]
        requirements_missing = [
            f for f in expected_features if f not in detected_features
        ]

        # Calculate confidence score based on feature matching
        if expected_features:
            match_ratio = len(requirements_met) / len(expected_features)
        else:
            match_ratio = 1.0

        confidence_score = match_ratio

        # Check for keyword alignment with prompt
        prompt_lower = design_request.user_prompt.lower()
        issues = []

        # Basic keyword checks
        if "hole" in prompt_lower or "cut" in prompt_lower:
            if "boolean_cut" not in detected_features:
                issues.append("Prompt mentions hole/cut but no boolean cut detected")
                confidence_score *= 0.8

        if "round" in prompt_lower or "fillet" in prompt_lower:
            if "fillet" not in detected_features:
                issues.append("Prompt mentions rounding but no fillet detected")
                confidence_score *= 0.9

        is_valid = confidence_score >= 0.6  # 60% threshold for semantic validity

        return SemanticValidation(
            is_valid=is_valid,
            confidence_score=min(1.0, confidence_score),
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            detected_features=detected_features,
            expected_features=expected_features,
            issues=issues,
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
            response = await self.llm_provider.generate(llm_request)
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
            context_parts.append(f"Success: {not execution_result.get('error')}")
            if execution_result.get("error"):
                context_parts.append(f"Error: {execution_result['error']}")
            else:
                context_parts.append(
                    f"Objects created: {execution_result.get('object_count', 0)}"
                )
                context_parts.append(
                    f"Total volume: {execution_result.get('total_volume', 0)} mm³"
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

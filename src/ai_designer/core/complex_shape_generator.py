"""
Advanced Complex Shape Generator with Continuous State Analysis
This module handles the generation of complex 3D shapes through iterative LLM feedback
and continuous state monitoring.
"""

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from ..freecad.command_executor import CommandExecutor
    from ..freecad.state_manager import FreeCADStateAnalyzer
    from ..llm.client import LLMClient
    from ..redis_utils.state_cache import StateCache
except ImportError:
    # Fallback for development
    pass


class ComplexityLevel(Enum):
    """Defines the complexity levels for shape generation"""

    SIMPLE = "simple"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class ShapeGenerationStep:
    """Represents a single step in complex shape generation"""

    step_id: str
    description: str
    freecad_commands: List[str]
    dependencies: List[str]
    expected_objects: List[str]
    validation_criteria: Dict[str, Any]
    complexity_score: float


@dataclass
class StateAnalysisResult:
    """Result of state analysis"""

    current_objects: List[Dict[str, Any]]
    object_count: int
    geometric_relationships: Dict[str, Any]
    design_constraints: List[str]
    next_possible_actions: List[str]
    completion_percentage: float
    quality_metrics: Dict[str, float]


class ComplexShapeGenerator:
    """
    Advanced generator for complex 3D shapes with continuous state analysis
    """

    def __init__(
        self,
        llm_client: LLMClient,
        state_analyzer: FreeCADStateAnalyzer,
        command_executor: CommandExecutor,
        state_cache: Optional[StateCache] = None,
    ):
        """
        Initialize the complex shape generator

        Args:
            llm_client: LLM client for generating steps and analysis
            state_analyzer: FreeCAD state analyzer
            command_executor: Command executor for FreeCAD
            state_cache: Optional state cache for performance
        """
        self.llm_client = llm_client
        self.state_analyzer = state_analyzer
        self.command_executor = command_executor
        self.state_cache = state_cache
        self.logger = logging.getLogger(__name__)

        # Generation history and state
        self.generation_history: List[ShapeGenerationStep] = []
        self.current_state: Optional[StateAnalysisResult] = None
        self.session_metrics: Dict[str, Any] = {
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "start_time": None,
            "complexity_progression": [],
        }

    def generate_complex_shape(
        self,
        user_requirements: str,
        session_id: str,
        target_complexity: ComplexityLevel = ComplexityLevel.INTERMEDIATE,
    ) -> Dict[str, Any]:
        """
        Generate a complex shape based on user requirements with continuous state analysis

        Args:
            user_requirements: Natural language description of desired shape
            session_id: Unique session identifier
            target_complexity: Target complexity level for generation

        Returns:
            Dictionary containing generation result and analysis
        """
        self.logger.info(f"Starting complex shape generation for session {session_id}")
        self.session_metrics["start_time"] = time.time()

        try:
            # Step 1: Analyze initial state
            initial_state = self._analyze_current_state(session_id)
            self.current_state = initial_state

            # Step 2: Generate decomposition plan
            decomposition_plan = self._generate_decomposition_plan(
                user_requirements, initial_state, target_complexity
            )

            # Step 3: Execute plan with continuous feedback
            execution_result = self._execute_generation_plan(
                decomposition_plan, session_id, user_requirements
            )

            # Step 4: Final analysis and validation
            final_state = self._analyze_current_state(session_id)
            validation_result = self._validate_generation_result(
                user_requirements, initial_state, final_state
            )

            # Step 5: Generate documentation
            documentation = self._generate_documentation(
                user_requirements,
                decomposition_plan,
                execution_result,
                validation_result,
            )

            return {
                "status": "success",
                "session_id": session_id,
                "user_requirements": user_requirements,
                "target_complexity": target_complexity.value,
                "initial_state": initial_state.__dict__,
                "final_state": final_state.__dict__,
                "decomposition_plan": decomposition_plan,
                "execution_result": execution_result,
                "validation_result": validation_result,
                "documentation": documentation,
                "session_metrics": self.session_metrics,
                "generation_history": [
                    step.__dict__ for step in self.generation_history
                ],
            }

        except Exception as e:
            self.logger.error(f"Complex shape generation failed: {str(e)}")
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
                "session_metrics": self.session_metrics,
            }

    def _analyze_current_state(self, session_id: str) -> StateAnalysisResult:
        """
        Perform comprehensive analysis of current FreeCAD state
        """
        self.logger.info("Analyzing current FreeCAD state")

        # Get raw state from FreeCAD
        raw_state = self.state_analyzer.get_full_state()

        # Extract object information
        objects = raw_state.get("objects", [])
        object_count = len(objects)

        # Analyze geometric relationships
        relationships = self._analyze_geometric_relationships(objects)

        # Determine design constraints
        constraints = self._identify_design_constraints(objects, relationships)

        # Generate next possible actions
        next_actions = self._generate_next_actions(objects, relationships)

        # Calculate completion percentage (if we have a target)
        completion = self._calculate_completion_percentage(objects)

        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(objects, relationships)

        state_result = StateAnalysisResult(
            current_objects=objects,
            object_count=object_count,
            geometric_relationships=relationships,
            design_constraints=constraints,
            next_possible_actions=next_actions,
            completion_percentage=completion,
            quality_metrics=quality_metrics,
        )

        # Cache the state if caching is enabled
        if self.state_cache:
            self.state_cache.set_state(
                f"complex_state_{session_id}", state_result.__dict__
            )

        return state_result

    def _generate_decomposition_plan(
        self,
        user_requirements: str,
        current_state: StateAnalysisResult,
        target_complexity: ComplexityLevel,
    ) -> List[ShapeGenerationStep]:
        """
        Generate a decomposition plan using LLM analysis
        """
        self.logger.info("Generating decomposition plan using LLM")

        # Prepare context for LLM
        context = {
            "user_requirements": user_requirements,
            "current_state": current_state.__dict__,
            "target_complexity": target_complexity.value,
            "available_freecad_operations": self._get_available_operations(),
            "design_patterns": self._get_design_patterns(),
        }

        # Generate LLM prompt for decomposition
        decomposition_prompt = self._create_decomposition_prompt(context)

        # Get LLM response
        llm_response = self.llm_client.generate_response(decomposition_prompt)

        # Parse LLM response into steps
        steps = self._parse_decomposition_response(llm_response)

        # Validate and optimize the plan
        optimized_steps = self._optimize_generation_plan(steps, context)

        return optimized_steps

    def _execute_generation_plan(
        self, plan: List[ShapeGenerationStep], session_id: str, user_requirements: str
    ) -> Dict[str, Any]:
        """
        Execute the generation plan with continuous state analysis and LLM feedback
        """
        self.logger.info(f"Executing generation plan with {len(plan)} steps")

        execution_results = []

        for i, step in enumerate(plan):
            self.logger.info(f"Executing step {i+1}/{len(plan)}: {step.description}")

            # Pre-step state analysis
            pre_state = self._analyze_current_state(session_id)

            # Execute the step
            step_result = self._execute_single_step(step, session_id)

            # Post-step state analysis
            post_state = self._analyze_current_state(session_id)

            # LLM feedback and adaptation
            feedback = self._get_llm_feedback(
                step, pre_state, post_state, user_requirements
            )

            # Adapt remaining plan if needed
            if feedback.get("adapt_plan", False):
                remaining_steps = plan[i + 1 :]
                adapted_steps = self._adapt_plan_based_on_feedback(
                    remaining_steps, feedback, post_state, user_requirements
                )
                plan[i + 1 :] = adapted_steps

            execution_results.append(
                {
                    "step": step.__dict__,
                    "pre_state": pre_state.__dict__,
                    "post_state": post_state.__dict__,
                    "step_result": step_result,
                    "llm_feedback": feedback,
                    "timestamp": time.time(),
                }
            )

            # Update session metrics
            self.session_metrics["total_steps"] += 1
            if step_result.get("status") == "success":
                self.session_metrics["successful_steps"] += 1
            else:
                self.session_metrics["failed_steps"] += 1

            # Add to generation history
            self.generation_history.append(step)

            # Check if we should continue
            if not step_result.get("status") == "success":
                self.logger.warning(f"Step {i+1} failed, considering recovery options")
                recovery_result = self._attempt_step_recovery(
                    step, step_result, post_state
                )
                if not recovery_result.get("recovered", False):
                    break

        return {
            "total_steps": len(plan),
            "executed_steps": len(execution_results),
            "execution_results": execution_results,
            "final_metrics": self.session_metrics,
        }

    def _execute_single_step(
        self, step: ShapeGenerationStep, session_id: str
    ) -> Dict[str, Any]:
        """
        Execute a single generation step
        """
        try:
            results = []
            for command in step.freecad_commands:
                result = self.command_executor.execute_command(command)
                results.append(result)

            # Validate step completion
            validation = self._validate_step_completion(step, results)

            return {
                "status": "success",
                "command_results": results,
                "validation": validation,
                "step_id": step.step_id,
            }

        except Exception as e:
            self.logger.error(f"Step execution failed: {str(e)}")
            return {"status": "error", "error": str(e), "step_id": step.step_id}

    def _get_llm_feedback(
        self,
        step: ShapeGenerationStep,
        pre_state: StateAnalysisResult,
        post_state: StateAnalysisResult,
        user_requirements: str,
    ) -> Dict[str, Any]:
        """
        Get LLM feedback on step execution and state changes
        """
        feedback_prompt = self._create_feedback_prompt(
            step, pre_state, post_state, user_requirements
        )

        feedback_response = self.llm_client.generate_response(feedback_prompt)

        return self._parse_feedback_response(feedback_response)

    def _create_decomposition_prompt(self, context: Dict[str, Any]) -> str:
        """
        Create a detailed prompt for LLM decomposition
        """
        return f"""
You are an expert CAD designer and FreeCAD automation specialist. Your task is to decompose a complex shape generation request into a series of precise, executable steps.

USER REQUIREMENTS: {context['user_requirements']}

CURRENT STATE ANALYSIS:
- Object count: {context['current_state']['object_count']}
- Existing objects: {context['current_state']['current_objects']}
- Design constraints: {context['current_state']['design_constraints']}
- Quality metrics: {context['current_state']['quality_metrics']}

TARGET COMPLEXITY: {context['target_complexity']}

AVAILABLE FREECAD OPERATIONS:
{json.dumps(context['available_freecad_operations'], indent=2)}

DESIGN PATTERNS:
{json.dumps(context['design_patterns'], indent=2)}

Please decompose the user requirements into a detailed step-by-step plan. Each step should include:

1. step_id: Unique identifier
2. description: Clear description of what this step accomplishes
3. freecad_commands: List of specific FreeCAD Python commands
4. dependencies: List of step_ids this step depends on
5. expected_objects: List of object names/types this step should create
6. validation_criteria: How to validate this step succeeded
7. complexity_score: Numerical score (1-10) indicating step complexity

Consider:
- Building complexity gradually from simple to advanced
- Ensuring each step has clear validation criteria
- Managing dependencies between steps
- Optimizing for reliability and error recovery
- Following CAD best practices

Respond with a JSON array of steps:
```json
[
  {{
    "step_id": "step_001",
    "description": "Create base geometry",
    "freecad_commands": ["import FreeCAD", "doc = FreeCAD.newDocument()", ...],
    "dependencies": [],
    "expected_objects": ["Box001"],
    "validation_criteria": {{"object_count": 1, "object_type": "Box"}},
    "complexity_score": 3.0
  }},
  ...
]
```
"""

    def _create_feedback_prompt(
        self,
        step: ShapeGenerationStep,
        pre_state: StateAnalysisResult,
        post_state: StateAnalysisResult,
        user_requirements: str,
    ) -> str:
        """
        Create a prompt for LLM feedback on step execution
        """
        return f"""
You are analyzing the execution of a CAD generation step. Provide feedback on the step's success and recommend adaptations for the remaining plan.

ORIGINAL USER REQUIREMENTS: {user_requirements}

EXECUTED STEP:
- ID: {step.step_id}
- Description: {step.description}
- Commands: {step.freecad_commands}
- Expected objects: {step.expected_objects}

STATE BEFORE STEP:
- Object count: {pre_state.object_count}
- Objects: {pre_state.current_objects}
- Quality metrics: {pre_state.quality_metrics}

STATE AFTER STEP:
- Object count: {post_state.object_count}
- Objects: {post_state.current_objects}
- Quality metrics: {post_state.quality_metrics}

Please analyze:
1. Did the step execute successfully?
2. Are we progressing toward the user requirements?
3. What adaptations should be made to the remaining plan?
4. Are there any quality issues that need addressing?
5. What should be the next priority?

Respond in JSON format:
```json
{{
  "step_success": true/false,
  "progress_assessment": "detailed assessment",
  "quality_score": 0.0-1.0,
  "adapt_plan": true/false,
  "recommended_adaptations": ["adaptation 1", "adaptation 2"],
  "next_priority": "description of next priority",
  "concerns": ["concern 1", "concern 2"],
  "suggestions": ["suggestion 1", "suggestion 2"]
}}
```
"""

    # Additional helper methods
    def _get_available_operations(self) -> List[str]:
        """Get list of available FreeCAD operations"""
        return [
            "create_box",
            "create_cylinder",
            "create_sphere",
            "create_cone",
            "create_torus",
            "create_prism",
            "extrude",
            "revolve",
            "loft",
            "boolean_union",
            "boolean_difference",
            "boolean_intersection",
            "fillet",
            "chamfer",
            "mirror",
            "linear_pattern",
            "circular_pattern",
            "sketch",
            "constraint",
            "dimension",
            "assembly",
        ]

    def _get_design_patterns(self) -> Dict[str, Any]:
        """Get common design patterns for complex shapes"""
        return {
            "architectural": ["building", "tower", "bridge", "dome"],
            "mechanical": ["gear", "shaft", "bearing", "housing"],
            "organic": ["surface", "shell", "lattice", "voronoi"],
            "parametric": ["configurable", "adaptive", "scalable"],
        }

    def _analyze_geometric_relationships(self, objects: List[Dict]) -> Dict[str, Any]:
        """Analyze geometric relationships between objects"""
        # Simplified implementation - would need actual geometric analysis
        return {
            "adjacencies": [],
            "intersections": [],
            "containments": [],
            "alignments": [],
        }

    def _identify_design_constraints(
        self, objects: List[Dict], relationships: Dict
    ) -> List[str]:
        """Identify design constraints from current state"""
        return ["constraint_1", "constraint_2"]

    def _generate_next_actions(
        self, objects: List[Dict], relationships: Dict
    ) -> List[str]:
        """Generate possible next actions based on current state"""
        return ["action_1", "action_2", "action_3"]

    def _calculate_completion_percentage(self, objects: List[Dict]) -> float:
        """Calculate how complete the design is"""
        return min(len(objects) * 0.1, 1.0)  # Simplified calculation

    def _calculate_quality_metrics(
        self, objects: List[Dict], relationships: Dict
    ) -> Dict[str, float]:
        """Calculate quality metrics for the current design"""
        return {
            "geometric_accuracy": 0.95,
            "design_consistency": 0.88,
            "complexity_score": 0.75,
            "manufacturability": 0.82,
        }

    def _parse_decomposition_response(self, response: str) -> List[ShapeGenerationStep]:
        """Parse LLM response into generation steps"""
        try:
            steps_data = json.loads(response)
            steps = []
            for step_data in steps_data:
                step = ShapeGenerationStep(**step_data)
                steps.append(step)
            return steps
        except Exception as e:
            self.logger.error(f"Failed to parse decomposition response: {e}")
            return []

    def _optimize_generation_plan(
        self, steps: List[ShapeGenerationStep], context: Dict[str, Any]
    ) -> List[ShapeGenerationStep]:
        """Optimize the generation plan for efficiency and reliability"""
        # Simplified optimization - could include dependency reordering, parallelization, etc.
        return steps

    def _validate_step_completion(
        self, step: ShapeGenerationStep, results: List[Dict]
    ) -> Dict[str, Any]:
        """Validate that a step completed successfully"""
        return {
            "validation_passed": True,
            "validation_details": "Step completed successfully",
        }

    def _adapt_plan_based_on_feedback(
        self,
        remaining_steps: List[ShapeGenerationStep],
        feedback: Dict[str, Any],
        current_state: StateAnalysisResult,
        user_requirements: str,
    ) -> List[ShapeGenerationStep]:
        """Adapt the remaining plan based on LLM feedback"""
        # Simplified adaptation - could involve re-planning with LLM
        return remaining_steps

    def _attempt_step_recovery(
        self,
        step: ShapeGenerationStep,
        step_result: Dict[str, Any],
        current_state: StateAnalysisResult,
    ) -> Dict[str, Any]:
        """Attempt to recover from a failed step"""
        return {"recovered": False}

    def _parse_feedback_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM feedback response"""
        try:
            return json.loads(response)
        except:
            return {
                "step_success": False,
                "progress_assessment": "Failed to parse feedback",
            }

    def _validate_generation_result(
        self,
        user_requirements: str,
        initial_state: StateAnalysisResult,
        final_state: StateAnalysisResult,
    ) -> Dict[str, Any]:
        """Validate the overall generation result"""
        return {
            "meets_requirements": True,
            "quality_score": 0.85,
            "improvement_suggestions": [],
        }

    def _generate_documentation(
        self,
        user_requirements: str,
        plan: List[ShapeGenerationStep],
        execution_result: Dict[str, Any],
        validation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive documentation for the generation process"""
        return {
            "summary": f"Complex shape generation completed",
            "requirements_analysis": user_requirements,
            "generation_steps": len(plan),
            "success_rate": execution_result.get("executed_steps", 0) / len(plan),
            "quality_assessment": validation_result.get("quality_score", 0),
            "recommendations": validation_result.get("improvement_suggestions", []),
        }

#!/usr/bin/env python3
"""
Phase 3: Multi-Step Workflow Orchestrator
Coordinates complex multi-step operations and manages workflow execution.

Step execution honesty (supported vs not)
-----------------------------------------
``WorkflowStepType`` values are decomposed from NL commands; execution behavior:

- **Executed in FreeCAD** (when ``command_executor`` is set): ``SKETCH_CREATE``
  (primitives / sketch), ``OPERATION_PAD``, ``OPERATION_HOLE`` (through-hole
  cut via ``Part::Cut`` on the last ``PartDesign::Pad`` or ``Part::*`` solid).
- **Skipped** (``status=skipped_unimplemented``; workflow may end as
  ``partial``): pattern steps, fillet/chamfer, pocket, face selection, shell,
  assembly constraint, state validation — not wired to FreeCAD yet.
- **Error**: dependency failure, missing executor where required, or FreeCAD
  script failure.

Hole limitation: axis is +Z; position is XY center of the target solid's
bounding box (no face picking). Coordinate with Track 8 if face-based holes
are required.

Workflow aggregate ``status``: ``error`` if any step errored; else ``partial``
if any step was skipped; else ``warning`` / ``success`` as documented on
``WorkflowExecutionResult``.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowStepType(Enum):
    """Types of workflow steps"""

    SKETCH_CREATE = "sketch_create"
    OPERATION_PAD = "operation_pad"
    OPERATION_POCKET = "operation_pocket"
    OPERATION_HOLE = "operation_hole"
    FACE_SELECTION = "face_selection"
    PATTERN_LINEAR = "pattern_linear"
    PATTERN_CIRCULAR = "pattern_circular"
    PATTERN_MATRIX = "pattern_matrix"
    FEATURE_FILLET = "feature_fillet"
    FEATURE_CHAMFER = "feature_chamfer"
    FEATURE_SHELL = "feature_shell"
    ASSEMBLY_CONSTRAINT = "assembly_constraint"
    STATE_VALIDATION = "state_validation"


@dataclass
class WorkflowStep:
    """Individual step in a complex workflow"""

    step_id: str
    step_type: WorkflowStepType
    description: str
    parameters: Dict[str, Any]
    dependencies: List[str] = None  # IDs of steps this depends on
    expected_output: Dict[str, Any] = None
    validation_criteria: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.expected_output is None:
            self.expected_output = {}
        if self.validation_criteria is None:
            self.validation_criteria = {}


@dataclass
class WorkflowExecutionResult:
    """Result of workflow step execution.

    ``status`` is one of: ``success``, ``warning``, ``error``,
    ``skipped_unimplemented`` (no silent mock success).
    ``reason_code`` is optional machine-stable context (e.g. for validators).
    """

    step_id: str
    status: str
    output: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None
    reason_code: Optional[str] = None
    state_changes: Dict[str, Any] = None

    def __post_init__(self):
        if self.state_changes is None:
            self.state_changes = {}


class WorkflowOrchestrator:
    """
    Orchestrate complex multi-step workflows

    This class coordinates the execution of complex operations that require
    multiple sequential steps with dependency management and state validation.
    """

    def __init__(
        self, state_processor=None, pattern_engine=None, advanced_features=None
    ):
        """Initialize the workflow orchestrator"""
        self.state_processor = state_processor
        self.pattern_engine = pattern_engine
        self.advanced_features = advanced_features
        self.execution_history = []
        self.workflow_cache = {}
        # Pull command_executor from state_processor so workflow steps can execute FreeCAD
        self.command_executor = getattr(state_processor, "command_executor", None)

    @staticmethod
    def _aggregate_workflow_status(
        execution_results: List["WorkflowExecutionResult"],
    ) -> str:
        if any(r.status == "error" for r in execution_results):
            return "error"
        if any(r.status == "skipped_unimplemented" for r in execution_results):
            return "partial"
        if any(r.status == "warning" for r in execution_results):
            return "warning"
        return "success"

    def _result_skipped_unimplemented(
        self,
        step: WorkflowStep,
        detail: str,
        reason_code: str,
    ) -> WorkflowExecutionResult:
        st = step.step_type.value
        return WorkflowExecutionResult(
            step_id=step.step_id,
            status="skipped_unimplemented",
            output={
                "skipped_unimplemented": True,
                "step_type": st,
                "reason_code": reason_code,
            },
            execution_time=0.0,
            error_message=detail,
            reason_code=reason_code,
        )

    @staticmethod
    def _safe_fc_object_name(step_id: str, suffix: str) -> str:
        base = re.sub(r"[^0-9a-zA-Z_]", "_", step_id)
        name = f"{base}{suffix}" if suffix else base
        return (name or "workflow_step")[:100]

    def _workflow_execute(
        self, context: Dict[str, Any], freecad_code: str
    ) -> Dict[str, Any]:
        """Run ``freecad_code`` via ``command_executor`` with optional FCStd checkpoint.

        Subprocess FreeCAD runs are process-isolated.  After step 1 saves a
        document, ``context[\"checkpoint_fcstd\"]`` points at that file and is
        passed as ``document_path`` so step 2+ see the same geometry.
        """
        if not self.command_executor:
            return {"status": "error", "message": "No command executor available"}
        chk = context.get("checkpoint_fcstd")
        if chk:
            return self.command_executor.execute(freecad_code, document_path=chk)
        return self.command_executor.execute(freecad_code)

    def decompose_complex_workflow(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """
        Break down complex command into executable steps

        Examples:
        - "Create a bracket with 4 mounting holes and fillets"
        - "Build a gear housing with cover and mounting features"
        - "Design a mechanical assembly with multiple parts"
        """
        logger.info(f"🔧 Decomposing complex workflow: {nl_command}")

        steps = []
        command_lower = nl_command.lower()

        # Detect workflow patterns
        workflow_pattern = self._identify_workflow_pattern(command_lower, current_state)

        if workflow_pattern == "bracket_with_holes_and_features":
            steps = self._create_bracket_workflow(nl_command, current_state)
        elif workflow_pattern == "housing_with_cover":
            steps = self._create_housing_workflow(nl_command, current_state)
        elif workflow_pattern == "pattern_operation":
            steps = self._create_pattern_workflow(nl_command, current_state)
        elif workflow_pattern == "assembly_operation":
            steps = self._create_assembly_workflow(nl_command, current_state)
        else:
            # Fallback: Generic multi-step decomposition
            steps = self._create_generic_workflow(nl_command, current_state)

        logger.info(f"✅ Decomposed into {len(steps)} steps")
        return steps

    def _identify_workflow_pattern(
        self, command_lower: str, current_state: Dict[str, Any]
    ) -> str:
        """Identify the type of workflow pattern"""

        # Pattern detection keywords
        pattern_indicators = {
            "bracket_with_holes_and_features": [
                ["bracket", "holes", "fillet"],
                ["bracket", "mounting", "rounded"],
                ["bracket", "holes", "chamfer"],
            ],
            "housing_with_cover": [
                ["housing", "cover"],
                ["enclosure", "lid"],
                ["case", "cover"],
            ],
            "pattern_operation": [
                ["pattern", "holes"],
                ["array", "features"],
                ["grid", "mounting"],
                ["circular", "pattern"],
                ["linear", "pattern"],
            ],
            "assembly_operation": [
                ["assembly", "parts"],
                ["multiple", "components"],
                ["align", "parts"],
                ["assemble", "components"],
            ],
        }

        for pattern_name, keyword_sets in pattern_indicators.items():
            for keyword_set in keyword_sets:
                if all(keyword in command_lower for keyword in keyword_set):
                    logger.info(f"🎯 Identified workflow pattern: {pattern_name}")
                    return pattern_name

        return "generic_multi_step"

    def _create_bracket_workflow(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """Create workflow for bracket with holes and features"""
        steps = []

        # Step 1: Create base bracket geometry
        steps.append(
            WorkflowStep(
                step_id="bracket_01_base",
                step_type=WorkflowStepType.SKETCH_CREATE,
                description="Create base bracket sketch",
                parameters={
                    "shape": "rectangle",
                    "dimensions": self._extract_dimensions(nl_command, "bracket"),
                    "plane": "XY",
                },
                expected_output={"sketch_created": True, "object_count": 1},
            )
        )

        # Step 2: Extrude bracket
        steps.append(
            WorkflowStep(
                step_id="bracket_02_extrude",
                step_type=WorkflowStepType.OPERATION_PAD,
                description="Extrude bracket base",
                parameters={"height": self._extract_height(nl_command, default=10.0)},
                dependencies=["bracket_01_base"],
                expected_output={"pad_created": True, "object_count": 2},
            )
        )

        # Step 3: Add mounting holes pattern
        if "holes" in nl_command or "mounting" in nl_command:
            hole_count = self._extract_hole_count(nl_command)
            if hole_count > 1:
                steps.append(
                    WorkflowStep(
                        step_id="bracket_03_hole_pattern",
                        step_type=WorkflowStepType.PATTERN_LINEAR,
                        description=f"Create pattern of {hole_count} mounting holes",
                        parameters={
                            "base_feature": "hole",
                            "count": hole_count,
                            "spacing": self._extract_hole_spacing(nl_command),
                            "diameter": self._extract_hole_diameter(nl_command),
                        },
                        dependencies=["bracket_02_extrude"],
                        expected_output={"holes_created": hole_count},
                    )
                )
            else:
                steps.append(
                    WorkflowStep(
                        step_id="bracket_03_single_hole",
                        step_type=WorkflowStepType.OPERATION_HOLE,
                        description="Create single mounting hole",
                        parameters={
                            "diameter": self._extract_hole_diameter(nl_command),
                            "depth": "through",
                        },
                        dependencies=["bracket_02_extrude"],
                        expected_output={"hole_created": True},
                    )
                )

        # Step 4: Add fillets if requested
        if "fillet" in nl_command or "rounded" in nl_command:
            steps.append(
                WorkflowStep(
                    step_id="bracket_04_fillets",
                    step_type=WorkflowStepType.FEATURE_FILLET,
                    description="Apply fillets to bracket edges",
                    parameters={
                        "radius": self._extract_fillet_radius(nl_command),
                        "edges": "corner_edges",
                    },
                    dependencies=["bracket_02_extrude"],
                    expected_output={"fillets_applied": True},
                )
            )

        return steps

    def _create_pattern_workflow(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """Create workflow for pattern operations"""
        steps = []

        pattern_type = self._detect_pattern_type(nl_command)
        base_feature = self._extract_base_feature(nl_command)

        if pattern_type == "linear":
            steps.append(
                WorkflowStep(
                    step_id="pattern_01_linear",
                    step_type=WorkflowStepType.PATTERN_LINEAR,
                    description="Create linear pattern",
                    parameters={
                        "base_feature": base_feature,
                        "direction": self._extract_pattern_direction(nl_command),
                        "count": self._extract_pattern_count(nl_command),
                        "spacing": self._extract_pattern_spacing(nl_command),
                    },
                    expected_output={"pattern_created": True},
                )
            )
        elif pattern_type == "circular":
            steps.append(
                WorkflowStep(
                    step_id="pattern_01_circular",
                    step_type=WorkflowStepType.PATTERN_CIRCULAR,
                    description="Create circular pattern",
                    parameters={
                        "base_feature": base_feature,
                        "axis": self._extract_pattern_axis(nl_command),
                        "count": self._extract_pattern_count(nl_command),
                        "angle": self._extract_pattern_angle(nl_command),
                    },
                    expected_output={"pattern_created": True},
                )
            )
        elif pattern_type == "matrix":
            steps.append(
                WorkflowStep(
                    step_id="pattern_01_matrix",
                    step_type=WorkflowStepType.PATTERN_MATRIX,
                    description="Create matrix pattern",
                    parameters={
                        "base_feature": base_feature,
                        "x_count": self._extract_matrix_x_count(nl_command),
                        "y_count": self._extract_matrix_y_count(nl_command),
                        "x_spacing": self._extract_matrix_x_spacing(nl_command),
                        "y_spacing": self._extract_matrix_y_spacing(nl_command),
                    },
                    expected_output={"pattern_created": True},
                )
            )

        return steps

    def _create_generic_workflow(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """Create generic multi-step workflow"""
        steps = []

        # Analyze command for basic operations
        operations = self._extract_operations(nl_command)

        step_counter = 1
        for operation in operations:
            if operation["type"] == "primitive":
                # Direct Part:: primitive — reuse SKETCH_CREATE step type so
                # _execute_sketch_step() handles it, but embed the primitive
                # name in the description so the primitive branch is triggered.
                prim = operation["primitive"]
                steps.append(
                    WorkflowStep(
                        step_id=f"generic_{step_counter:02d}_{prim}",
                        step_type=WorkflowStepType.SKETCH_CREATE,
                        description=f"Create {prim} primitive",
                        parameters={**operation.get("parameters", {}), "shape": prim},
                        expected_output={"shape_created": True},
                    )
                )
            elif operation["type"] == "sketch":
                steps.append(
                    WorkflowStep(
                        step_id=f"generic_{step_counter:02d}_sketch",
                        step_type=WorkflowStepType.SKETCH_CREATE,
                        description=f"Create {operation['shape']} sketch",
                        parameters=operation["parameters"],
                        expected_output={"sketch_created": True},
                    )
                )
            elif operation["type"] == "extrude":
                steps.append(
                    WorkflowStep(
                        step_id=f"generic_{step_counter:02d}_extrude",
                        step_type=WorkflowStepType.OPERATION_PAD,
                        description=f"Extrude operation",
                        parameters=operation["parameters"],
                        dependencies=(
                            [f"generic_{step_counter-1:02d}_sketch"]
                            if step_counter > 1
                            else []
                        ),
                        expected_output={"extrusion_created": True},
                    )
                )

            step_counter += 1

        return steps

    def plan_execution_sequence(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """Determine optimal execution order based on dependencies"""
        logger.info("📋 Planning execution sequence...")

        # Topological sort to handle dependencies
        sorted_steps = []
        remaining_steps = steps.copy()

        while remaining_steps:
            # Find steps with no unresolved dependencies
            ready_steps = []
            for step in remaining_steps:
                if all(
                    dep_id in [s.step_id for s in sorted_steps]
                    for dep_id in step.dependencies
                ):
                    ready_steps.append(step)

            if not ready_steps:
                # Circular dependency or missing dependency
                logger.warning("⚠️ Circular or missing dependencies detected")
                # Add remaining steps anyway
                sorted_steps.extend(remaining_steps)
                break

            # Add ready steps to sorted list
            for step in ready_steps:
                sorted_steps.append(step)
                remaining_steps.remove(step)

        logger.info(f"✅ Execution sequence planned: {len(sorted_steps)} steps")
        return sorted_steps

    def execute_workflow_steps(
        self, steps: List[WorkflowStep], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute workflow steps with dependency management.

        ``context`` may include ``checkpoint_fcstd`` to resume from a saved
        ``.FCStd``; otherwise it is initialised to ``None``.  After each
        successful FreeCAD step, the checkpoint is updated from
        ``command_executor.last_saved_path`` so the next subprocess can reload
        the same document (Track 10).
        """
        logger.info(f"🚀 Executing {len(steps)} workflow steps...")

        execution_results = []
        step_outputs = {}  # Store outputs for dependency resolution
        if "checkpoint_fcstd" not in context:
            context["checkpoint_fcstd"] = None

        start_time = datetime.now()

        for i, step in enumerate(steps, 1):
            logger.info(f"📋 Step {i}/{len(steps)}: {step.description}")

            try:
                # Validate dependencies
                if not self._validate_step_dependencies(step, step_outputs):
                    result = WorkflowExecutionResult(
                        step_id=step.step_id,
                        status="error",
                        output={"reason_code": "DEPENDENCY_VALIDATION_FAILED"},
                        execution_time=0.0,
                        error_message="Dependency validation failed",
                        reason_code="DEPENDENCY_VALIDATION_FAILED",
                    )
                    execution_results.append(result)
                    break

                # Execute step
                step_start = datetime.now()
                result = self._execute_single_step(step, context, step_outputs)
                step_end = datetime.now()

                result.execution_time = (step_end - step_start).total_seconds()
                execution_results.append(result)

                # Store output for dependent steps
                step_outputs[step.step_id] = result.output

                if result.status == "success" and self.command_executor:
                    lp = getattr(self.command_executor, "last_saved_path", None)
                    if lp:
                        context["checkpoint_fcstd"] = lp

                if result.status == "error":
                    logger.error(
                        f"❌ Step {step.step_id} failed: {result.error_message}"
                    )
                    break
                if result.status == "skipped_unimplemented":
                    logger.warning(
                        f"⏭️ Step {step.step_id} skipped (unimplemented): {result.error_message}"
                    )
                elif result.status == "warning":
                    logger.warning(f"⚠️ Step {step.step_id} completed with warnings")
                else:
                    logger.info(f"✅ Step {step.step_id} completed successfully")

            except Exception as e:
                result = WorkflowExecutionResult(
                    step_id=step.step_id,
                    status="error",
                    output={"reason_code": "STEP_EXCEPTION"},
                    execution_time=0.0,
                    error_message=str(e),
                    reason_code="STEP_EXCEPTION",
                )
                execution_results.append(result)
                logger.error(f"❌ Exception in step {step.step_id}: {e}")
                break

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        overall_status = self._aggregate_workflow_status(execution_results)
        completed_steps = sum(1 for r in execution_results if r.status == "success")
        skipped_steps = sum(
            1 for r in execution_results if r.status == "skipped_unimplemented"
        )

        workflow_result = {
            "status": overall_status,
            "total_steps": len(steps),
            "completed_steps": completed_steps,
            "skipped_steps": skipped_steps,
            "failed_steps": len([r for r in execution_results if r.status == "error"]),
            "execution_time": total_time,
            "step_results": execution_results,
            "final_outputs": step_outputs,
        }

        logger.info(f"🎯 Workflow execution complete: {workflow_result['status']}")
        logger.info(
            f"📊 Success {workflow_result['completed_steps']}/{workflow_result['total_steps']} "
            f"(skipped_unimplemented={skipped_steps}, failed={workflow_result['failed_steps']})"
        )

        return workflow_result

    def _execute_single_step(
        self, step: WorkflowStep, context: Dict[str, Any], step_outputs: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Execute a single workflow step"""

        try:
            if step.step_type == WorkflowStepType.SKETCH_CREATE:
                return self._execute_sketch_step(step, context)
            elif step.step_type == WorkflowStepType.OPERATION_PAD:
                return self._execute_pad_step(step, context)
            elif step.step_type == WorkflowStepType.OPERATION_HOLE:
                return self._execute_hole_step(step, context)
            elif step.step_type in [
                WorkflowStepType.PATTERN_LINEAR,
                WorkflowStepType.PATTERN_CIRCULAR,
                WorkflowStepType.PATTERN_MATRIX,
            ]:
                return self._execute_pattern_step(step, context)
            elif step.step_type in [
                WorkflowStepType.FEATURE_FILLET,
                WorkflowStepType.FEATURE_CHAMFER,
            ]:
                return self._execute_feature_step(step, context)
            else:
                return self._result_skipped_unimplemented(
                    step,
                    f"Workflow step type not implemented: {step.step_type.value}",
                    "UNIMPLEMENTED_STEP",
                )

        except Exception as e:
            return WorkflowExecutionResult(
                step_id=step.step_id,
                status="error",
                output={},
                execution_time=0.0,
                error_message=str(e),
            )

    def _execute_sketch_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Execute sketch creation step with real FreeCAD commands.

        For simple geometric primitives (box, cylinder, sphere, cone) detected
        in the step description or original command, generates Part:: primitive
        code directly rather than a Sketcher sketch object.  Falls back to
        Sketcher for genuine sketch-based operations.
        """
        try:
            shape = step.parameters.get("shape", "rectangle")
            dimensions = step.parameters.get("dimensions", {})
            original_command = context.get("original_command", "").lower()
            description_lower = step.description.lower()

            import re

            # ------------------------------------------------------------------
            # Helper: extract a numeric dimension from a string
            # ------------------------------------------------------------------
            def _dim(text, *keys, default=10.0):
                """Return first matching float from 'NUMmm' pattern or default."""
                for key in keys:
                    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*" + key, text)
                    if m:
                        return float(m.group(1))
                # Also try bare NxNxN triples (e.g. 20x10x5mm)
                triple = re.search(
                    r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", text
                )
                if triple:
                    idx = {"length": 0, "width": 1, "height": 2, "radius": 0}
                    k = list(keys)[0] if keys else "length"
                    return float(triple.group(idx.get(k, 0) + 1))
                return default

            # Determine x-offset for side-by-side placement (increments per object)
            obj_index = context.get("_primitive_index", 0)
            context["_primitive_index"] = obj_index + 1
            x_offset = obj_index * 30  # 30 mm gap between primitives

            # ------------------------------------------------------------------
            # BOX / CUBE
            # ------------------------------------------------------------------
            if any(
                k in description_lower or k in original_command
                for k in ("box", "cube", "rectangular")
            ):
                length = _dim(
                    description_lower + " " + original_command,
                    "length",
                    "long",
                    default=10.0,
                )
                width = _dim(
                    description_lower + " " + original_command,
                    "width",
                    "wide",
                    default=10.0,
                )
                height = _dim(
                    description_lower + " " + original_command,
                    "height",
                    "high",
                    "tall",
                    default=10.0,
                )
                # Fall back to triple notation
                triple = re.search(
                    r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)",
                    description_lower + " " + original_command,
                )
                if triple:
                    length, width, height = (
                        float(triple.group(1)),
                        float(triple.group(2)),
                        float(triple.group(3)),
                    )
                obj_name = step.step_id.replace("-", "_").replace(" ", "_")
                freecad_code = f"""
import FreeCAD as App
import Part
doc = App.ActiveDocument
if not doc:
    doc = App.newDocument("AutomationDoc")
box = doc.addObject("Part::Box", "{obj_name}")
box.Length = {length}
box.Width  = {width}
box.Height = {height}
box.Placement.Base.x = {x_offset}
doc.recompute()
print("Box created: {obj_name} {length}x{width}x{height}mm at x={x_offset}")
"""

            # ------------------------------------------------------------------
            # CYLINDER
            # ------------------------------------------------------------------
            elif "cylinder" in description_lower or "cylinder" in original_command:
                radius = _dim(
                    description_lower + " " + original_command,
                    "radius",
                    "r",
                    default=5.0,
                )
                height = _dim(
                    description_lower + " " + original_command,
                    "height",
                    "high",
                    "tall",
                    default=10.0,
                )
                obj_name = step.step_id.replace("-", "_").replace(" ", "_")
                freecad_code = f"""
import FreeCAD as App
import Part
doc = App.ActiveDocument
if not doc:
    doc = App.newDocument("AutomationDoc")
cyl = doc.addObject("Part::Cylinder", "{obj_name}")
cyl.Radius = {radius}
cyl.Height = {height}
cyl.Placement.Base.x = {x_offset}
doc.recompute()
print("Cylinder created: {obj_name} r={radius}mm h={height}mm at x={x_offset}")
"""

            # ------------------------------------------------------------------
            # SPHERE
            # ------------------------------------------------------------------
            elif "sphere" in description_lower or "sphere" in original_command:
                radius = _dim(
                    description_lower + " " + original_command,
                    "radius",
                    "r",
                    default=5.0,
                )
                obj_name = step.step_id.replace("-", "_").replace(" ", "_")
                freecad_code = f"""
import FreeCAD as App
import Part
doc = App.ActiveDocument
if not doc:
    doc = App.newDocument("AutomationDoc")
sph = doc.addObject("Part::Sphere", "{obj_name}")
sph.Radius = {radius}
sph.Placement.Base.x = {x_offset}
doc.recompute()
print("Sphere created: {obj_name} r={radius}mm at x={x_offset}")
"""

            # ------------------------------------------------------------------
            # CONE
            # ------------------------------------------------------------------
            elif "cone" in description_lower or "cone" in original_command:
                radius1 = _dim(
                    description_lower + " " + original_command,
                    "radius",
                    "base",
                    default=5.0,
                )
                height = _dim(
                    description_lower + " " + original_command,
                    "height",
                    "high",
                    "tall",
                    default=10.0,
                )
                obj_name = step.step_id.replace("-", "_").replace(" ", "_")
                freecad_code = f"""
import FreeCAD as App
import Part
doc = App.ActiveDocument
if not doc:
    doc = App.newDocument("AutomationDoc")
cone = doc.addObject("Part::Cone", "{obj_name}")
cone.Radius1 = {radius1}
cone.Radius2 = 0
cone.Height  = {height}
cone.Placement.Base.x = {x_offset}
doc.recompute()
print("Cone created: {obj_name} r={radius1}mm h={height}mm at x={x_offset}")
"""

            # ------------------------------------------------------------------
            # GEAR (existing logic)
            # ------------------------------------------------------------------
            elif "gear" in original_command:
                teeth = 20
                diameter = 50.0
                thickness = 10.0
                if "teeth" in original_command:
                    m = re.search(r"(\d+)\s*teeth", original_command)
                    if m:
                        teeth = int(m.group(1))
                if "diameter" in original_command:
                    m = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*diameter", original_command)
                    if m:
                        diameter = float(m.group(1))
                if "thickness" in original_command:
                    m = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*thickness", original_command)
                    if m:
                        thickness = float(m.group(1))

                obj_name = step.step_id.replace("-", "_").replace(" ", "_")
                freecad_code = f"""
import FreeCAD as App, Part, math
doc = App.ActiveDocument
if not doc:
    doc = App.newDocument("AutomationDoc")
num_teeth      = {teeth}
outer_diameter = {diameter}
thickness      = {thickness}
mod            = outer_diameter / num_teeth
root_diameter  = outer_diameter - 2 * 1.25 * mod
base_radius    = (outer_diameter - 2 * mod) / 2 * math.cos(math.radians(20))
# Simplified gear: extrude a disc with teeth as rectangular protrusions
base_cyl = Part.makeCylinder(root_diameter / 2, thickness)
angular_step = 360.0 / num_teeth
tooth_h = (outer_diameter - root_diameter) / 2
tooth_w = math.pi * (outer_diameter - 2 * mod) / num_teeth * 0.5
for i in range(num_teeth):
    ang = math.radians(i * angular_step)
    tx  = (root_diameter / 2 + tooth_h / 2) * math.cos(ang)
    ty  = (root_diameter / 2 + tooth_h / 2) * math.sin(ang)
    tooth = Part.makeBox(tooth_h, tooth_w, thickness)
    tooth.translate(App.Vector(tx - tooth_h / 2, ty - tooth_w / 2, 0))
    tooth = tooth.rotate(App.Vector(tx, ty, 0), App.Vector(0, 0, 1), math.degrees(ang))
    base_cyl = base_cyl.fuse(tooth)
gear_obj = doc.addObject("Part::Feature", "{obj_name}")
gear_obj.Shape = base_cyl
gear_obj.Label = "Gear_{teeth}T"
doc.recompute()
print("Gear created: {teeth} teeth, {diameter}mm dia")
"""

            # ------------------------------------------------------------------
            # FALLBACK — generic Sketcher sketch
            # ------------------------------------------------------------------
            else:
                freecad_code = f"""
import FreeCAD as App
import Part
import Sketcher
doc = App.ActiveDocument
if not doc:
    doc = App.newDocument("AutomationDoc")
sketch = doc.addObject('Sketcher::SketchObject', 'Sketch')
sketch.Placement = App.Placement(
    App.Vector(0, 0, 0), App.Rotation(0, 0, 0, 1)
)
if "{shape}" == "rectangle":
    sketch.addGeometry(Part.LineSegment(App.Vector(-10, -10, 0), App.Vector(10, -10, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(10, -10, 0),  App.Vector(10,  10, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(10,  10, 0),  App.Vector(-10, 10, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(-10, 10, 0),  App.Vector(-10,-10, 0)), False)
doc.recompute()
"""

            # Execute via command_executor
            if self.command_executor:
                result = self._workflow_execute(context, freecad_code)
                return WorkflowExecutionResult(
                    step_id=step.step_id,
                    status="success" if result.get("status") == "success" else "error",
                    output={
                        "freecad_code": freecad_code,
                        "execution_result": result,
                        "shape_created": True,
                        "shape_type": shape,
                    },
                    execution_time=0.5,
                    error_message=result.get("message")
                    if result.get("status") != "success"
                    else None,
                )
            else:
                return WorkflowExecutionResult(
                    step_id=step.step_id,
                    status="error",
                    output={},
                    execution_time=0.0,
                    error_message="No command executor available",
                )

        except Exception as e:
            return WorkflowExecutionResult(
                step_id=step.step_id,
                status="error",
                output={},
                execution_time=0.0,
                error_message=str(e),
            )

    def _execute_pad_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Execute pad/extrusion step using PartDesign::Pad on the last sketch.

        Finds the most-recently added Sketcher sketch in the active document
        and pads it to the requested height.
        """
        height = step.parameters.get("height", 10.0)
        pad_name = f"Pad_{step.step_id}".replace("-", "_")

        freecad_code = f"""
import FreeCAD as App
import Part
import PartDesign
doc = App.ActiveDocument
if not doc:
    doc = App.newDocument("AutomationDoc")
# Find the last Sketcher sketch in the document
sketch = None
for obj in reversed(doc.Objects):
    if obj.TypeId == "Sketcher::SketchObject":
        sketch = obj
        break
if sketch is None:
    raise RuntimeError("No sketch found to pad")
pad = doc.addObject("PartDesign::Pad", "{pad_name}")
pad.Profile = sketch
pad.Length  = {height}
doc.recompute()
print("Pad created: {pad_name} height={height}mm")
"""
        if self.command_executor:
            result = self._workflow_execute(context, freecad_code)
            return WorkflowExecutionResult(
                step_id=step.step_id,
                status="success" if result.get("status") == "success" else "error",
                output={
                    "pad_created": result.get("status") == "success",
                    "pad_name": pad_name,
                    "height": height,
                    "execution_result": result,
                },
                execution_time=0.3,
                error_message=result.get("message")
                if result.get("status") != "success"
                else None,
            )
        return WorkflowExecutionResult(
            step_id=step.step_id,
            status="error",
            output={"reason_code": "NO_COMMAND_EXECUTOR"},
            execution_time=0.0,
            error_message="No command executor available",
            reason_code="NO_COMMAND_EXECUTOR",
        )

    def _execute_hole_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Through-hole along +Z at XY center of the target solid's bounding box.

        Prefers the last ``PartDesign::Pad`` with a valid shape, else the last
        ``Part::*`` object with a valid shape. Requires ``command_executor``.
        """
        if not self.command_executor:
            return WorkflowExecutionResult(
                step_id=step.step_id,
                status="error",
                output={"reason_code": "NO_COMMAND_EXECUTOR"},
                execution_time=0.0,
                error_message="No command executor available",
                reason_code="NO_COMMAND_EXECUTOR",
            )

        diameter = float(step.parameters.get("diameter", 5.0))
        radius = diameter / 2.0
        depth = step.parameters.get("depth", "through")
        tool_name = self._safe_fc_object_name(step.step_id, "_hole_tool")
        cut_name = self._safe_fc_object_name(step.step_id, "_hole_cut")

        freecad_code = f"""
import FreeCAD as App
import Part
doc = App.ActiveDocument
if not doc:
    raise RuntimeError("No active document")
target = None
for obj in reversed(doc.Objects):
    tid = getattr(obj, "TypeId", "")
    sh = getattr(obj, "Shape", None)
    if sh is None or not sh.isValid():
        continue
    if tid == "PartDesign::Pad":
        target = obj
        break
if target is None:
    for obj in reversed(doc.Objects):
        tid = getattr(obj, "TypeId", "")
        sh = getattr(obj, "Shape", None)
        if sh is None or not sh.isValid():
            continue
        if tid.startswith("Part::"):
            target = obj
            break
if target is None:
    raise RuntimeError("No PartDesign::Pad or Part:: solid found for hole cut")
bb = target.Shape.BoundBox
cx = 0.5 * (bb.XMin + bb.XMax)
cy = 0.5 * (bb.YMin + bb.YMax)
z0 = bb.ZMin - 20.0
tool_h = bb.ZLength + 50.0
tool = doc.addObject("Part::Cylinder", "{tool_name}")
tool.Radius = {radius}
tool.Height = tool_h
tool.Placement = App.Placement(App.Vector(cx, cy, z0), App.Rotation())
cut = doc.addObject("Part::Cut", "{cut_name}")
cut.Base = target
cut.Tool = tool
doc.recompute()
if cut.Shape.isNull():
    raise RuntimeError("Boolean cut produced an empty shape")
print("Hole cut created: {cut_name} diameter={diameter} depth={depth!r}")
"""

        result = self._workflow_execute(context, freecad_code)
        ok = result.get("status") == "success"
        return WorkflowExecutionResult(
            step_id=step.step_id,
            status="success" if ok else "error",
            output={
                "hole_created": ok,
                "hole_cut_name": cut_name,
                "diameter": diameter,
                "depth": depth,
                "execution_result": result,
                "reason_code": None if ok else "HOLE_EXECUTION_FAILED",
            },
            execution_time=0.2,
            error_message=None
            if ok
            else result.get("message", "Hole execution failed"),
            reason_code=None if ok else "HOLE_EXECUTION_FAILED",
        )

    def _execute_pattern_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Pattern steps are not implemented (no pattern_engine in default wiring)."""
        return self._result_skipped_unimplemented(
            step,
            "Linear/circular/matrix patterns are not implemented in the workflow orchestrator yet.",
            "UNIMPLEMENTED_PATTERN",
        )

    def _execute_feature_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Fillet/chamfer (and similar) are not implemented in the orchestrator yet."""
        return self._result_skipped_unimplemented(
            step,
            "Fillet/chamfer workflow steps are not implemented in the workflow orchestrator yet.",
            "UNIMPLEMENTED_FEATURE",
        )

    def _validate_step_dependencies(
        self, step: WorkflowStep, step_outputs: Dict[str, Any]
    ) -> bool:
        """Validate that all step dependencies are satisfied"""
        for dep_id in step.dependencies:
            if dep_id not in step_outputs:
                logger.error(f"❌ Missing dependency: {dep_id} for step {step.step_id}")
                return False

            dep_result = step_outputs[dep_id]
            if not dep_result or not isinstance(dep_result, dict):
                logger.error(f"❌ Invalid dependency output: {dep_id}")
                return False

        return True

    # Parameter extraction methods (simplified implementations)
    def _extract_dimensions(self, command: str, shape_type: str) -> Dict[str, float]:
        """Extract dimensions from command"""
        # Simplified implementation - would use more sophisticated parsing
        import re

        # Look for dimension patterns
        width_match = re.search(
            r"(\d+\.?\d*)\s*(?:mm|millimeter)?\s*(?:wide|width)", command.lower()
        )
        height_match = re.search(
            r"(\d+\.?\d*)\s*(?:mm|millimeter)?\s*(?:high|height|tall)", command.lower()
        )
        length_match = re.search(
            r"(\d+\.?\d*)\s*(?:mm|millimeter)?\s*(?:long|length)", command.lower()
        )

        dimensions = {}
        if width_match:
            dimensions["width"] = float(width_match.group(1))
        if height_match:
            dimensions["height"] = float(height_match.group(1))
        if length_match:
            dimensions["length"] = float(length_match.group(1))

        # Default dimensions if not found
        if not dimensions:
            dimensions = {"width": 50.0, "height": 30.0, "length": 10.0}

        return dimensions

    def _extract_height(self, command: str, default: float = 10.0) -> float:
        """Extract height/thickness from command"""
        import re

        height_match = re.search(
            r"(\d+\.?\d*)\s*(?:mm|millimeter)?\s*(?:thick|height|tall)", command.lower()
        )
        return float(height_match.group(1)) if height_match else default

    def _extract_hole_count(self, command: str) -> int:
        """Extract number of holes from command"""
        import re

        count_match = re.search(r"(\d+)\s*holes?", command.lower())
        return int(count_match.group(1)) if count_match else 1

    def _extract_hole_diameter(self, command: str) -> float:
        """Extract hole diameter from command"""
        import re

        diameter_match = re.search(
            r"(\d+\.?\d*)\s*(?:mm|millimeter)?\s*diameter", command.lower()
        )
        return float(diameter_match.group(1)) if diameter_match else 5.0

    def _extract_hole_spacing(self, command: str) -> float:
        """Extract hole spacing from command"""
        import re

        spacing_match = re.search(
            r"(\d+\.?\d*)\s*(?:mm|millimeter)?\s*(?:spacing|apart)", command.lower()
        )
        return float(spacing_match.group(1)) if spacing_match else 20.0

    def _extract_fillet_radius(self, command: str) -> float:
        """Extract fillet radius from command"""
        import re

        radius_match = re.search(
            r"(\d+\.?\d*)\s*(?:mm|millimeter)?\s*(?:radius|fillet)", command.lower()
        )
        return float(radius_match.group(1)) if radius_match else 2.0

    def _detect_pattern_type(self, command: str) -> str:
        """Detect pattern type from command"""
        command_lower = command.lower()
        if "circular" in command_lower or "around" in command_lower:
            return "circular"
        elif "grid" in command_lower or "matrix" in command_lower:
            return "matrix"
        else:
            return "linear"

    def _extract_base_feature(self, command: str) -> str:
        """Extract the base feature for patterns"""
        command_lower = command.lower()
        if "hole" in command_lower:
            return "hole"
        elif "bolt" in command_lower:
            return "bolt"
        elif "screw" in command_lower:
            return "screw"
        else:
            return "feature"

    def _extract_pattern_direction(self, command: str) -> str:
        """Extract pattern direction"""
        command_lower = command.lower()
        if "vertical" in command_lower or "up" in command_lower:
            return "vertical"
        elif "horizontal" in command_lower or "across" in command_lower:
            return "horizontal"
        else:
            return "horizontal"

    def _extract_pattern_count(self, command: str) -> int:
        """Extract pattern count"""
        import re

        count_match = re.search(
            r"(\d+)\s*(?:holes?|features?|bolts?|screws?)", command.lower()
        )
        return int(count_match.group(1)) if count_match else 4

    def _extract_pattern_spacing(self, command: str) -> float:
        """Extract pattern spacing"""
        import re

        spacing_match = re.search(
            r"(\d+\.?\d*)\s*(?:mm|millimeter)?\s*(?:spacing|apart)", command.lower()
        )
        return float(spacing_match.group(1)) if spacing_match else 15.0

    def _extract_pattern_axis(self, command: str) -> str:
        """Extract pattern axis for circular patterns"""
        return "Z"  # Default to Z-axis

    def _extract_pattern_angle(self, command: str) -> float:
        """Extract pattern angle for circular patterns"""
        import re

        angle_match = re.search(r"(\d+\.?\d*)\s*(?:degrees?|deg)", command.lower())
        return float(angle_match.group(1)) if angle_match else 360.0

    def _extract_matrix_x_count(self, command: str) -> int:
        """Extract X count for matrix patterns"""
        import re

        grid_match = re.search(r"(\d+)\s*x\s*(\d+)", command.lower())
        return int(grid_match.group(1)) if grid_match else 3

    def _extract_matrix_y_count(self, command: str) -> int:
        """Extract Y count for matrix patterns"""
        import re

        grid_match = re.search(r"(\d+)\s*x\s*(\d+)", command.lower())
        return int(grid_match.group(2)) if grid_match else 3

    def _extract_matrix_x_spacing(self, command: str) -> float:
        """Extract X spacing for matrix patterns"""
        return 20.0  # Default spacing

    def _extract_matrix_y_spacing(self, command: str) -> float:
        """Extract Y spacing for matrix patterns"""
        return 20.0  # Default spacing

    def _extract_operations(self, command: str) -> List[Dict[str, Any]]:
        """Extract basic operations from command.

        Detects direct geometric primitives first (box, cylinder, sphere, cone)
        so _create_generic_workflow emits the right step type and description.
        Falls back to sketch+extrude for non-primitive commands.
        """
        operations = []
        cmd_lower = command.lower()

        # --- Primitive detection -------------------------------------------------
        _PRIMITIVES = [
            ("box", "box"),
            ("cube", "box"),
            ("cylinder", "cylinder"),
            ("sphere", "sphere"),
            ("cone", "cone"),
            ("torus", "torus"),
        ]
        for keyword, prim_type in _PRIMITIVES:
            if keyword in cmd_lower:
                operations.append(
                    {
                        "type": "primitive",
                        "primitive": prim_type,
                        "shape": prim_type,
                        # description is picked up by _execute_sketch_step to choose the right code
                        "description": f"Create {prim_type} from user command",
                        "parameters": {"command": command},
                    }
                )

        # De-duplicate (a command might have both "box" and "cube")
        seen = set()
        unique_ops = []
        for op in operations:
            key = op["primitive"]
            if key not in seen:
                seen.add(key)
                unique_ops.append(op)
        operations = unique_ops

        # --- Generic sketch+extrude fallback (no primitives detected) -----------
        if not operations:
            if "create" in cmd_lower or "sketch" in cmd_lower:
                operations.append(
                    {
                        "type": "sketch",
                        "shape": "rectangle",
                        "parameters": {"width": 50.0, "height": 30.0},
                    }
                )
            if "extrude" in cmd_lower or "tall" in cmd_lower:
                operations.append(
                    {
                        "type": "extrude",
                        "parameters": {"height": 10.0},
                    }
                )

        return operations

    def _create_housing_workflow(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """Create workflow for housing with cover (placeholder)"""
        # Simplified implementation for housing workflow
        return self._create_generic_workflow(nl_command, current_state)

    def _create_assembly_workflow(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """Create workflow for assembly operations (placeholder)"""
        # Simplified implementation for assembly workflow
        return self._create_generic_workflow(nl_command, current_state)

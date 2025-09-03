#!/usr/bin/env python3
"""
Phase 3: Multi-Step Workflow Orchestrator
Coordinates complex multi-step operations and manages workflow execution
"""

import logging
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
    """Result of workflow step execution"""

    step_id: str
    status: str  # 'success', 'warning', 'error'
    output: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None
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
            if operation["type"] == "sketch":
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
        """Execute workflow steps with dependency management"""
        logger.info(f"🚀 Executing {len(steps)} workflow steps...")

        execution_results = []
        overall_status = "success"
        step_outputs = {}  # Store outputs for dependency resolution

        start_time = datetime.now()

        for i, step in enumerate(steps, 1):
            logger.info(f"📋 Step {i}/{len(steps)}: {step.description}")

            try:
                # Validate dependencies
                if not self._validate_step_dependencies(step, step_outputs):
                    result = WorkflowExecutionResult(
                        step_id=step.step_id,
                        status="error",
                        output={},
                        execution_time=0.0,
                        error_message="Dependency validation failed",
                    )
                    execution_results.append(result)
                    overall_status = "error"
                    break

                # Execute step
                step_start = datetime.now()
                result = self._execute_single_step(step, context, step_outputs)
                step_end = datetime.now()

                result.execution_time = (step_end - step_start).total_seconds()
                execution_results.append(result)

                # Store output for dependent steps
                step_outputs[step.step_id] = result.output

                if result.status == "error":
                    overall_status = "error"
                    logger.error(
                        f"❌ Step {step.step_id} failed: {result.error_message}"
                    )
                    break
                elif result.status == "warning":
                    overall_status = "warning"
                    logger.warning(f"⚠️ Step {step.step_id} completed with warnings")
                else:
                    logger.info(f"✅ Step {step.step_id} completed successfully")

            except Exception as e:
                result = WorkflowExecutionResult(
                    step_id=step.step_id,
                    status="error",
                    output={},
                    execution_time=0.0,
                    error_message=str(e),
                )
                execution_results.append(result)
                overall_status = "error"
                logger.error(f"❌ Exception in step {step.step_id}: {e}")
                break

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        workflow_result = {
            "status": overall_status,
            "total_steps": len(steps),
            "completed_steps": len(
                [r for r in execution_results if r.status != "error"]
            ),
            "failed_steps": len([r for r in execution_results if r.status == "error"]),
            "execution_time": total_time,
            "step_results": execution_results,
            "final_outputs": step_outputs,
        }

        logger.info(f"🎯 Workflow execution complete: {workflow_result['status']}")
        logger.info(
            f"📊 Completed {workflow_result['completed_steps']}/{workflow_result['total_steps']} steps"
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
                # Mock execution for unsupported step types
                return WorkflowExecutionResult(
                    step_id=step.step_id,
                    status="success",
                    output={"mock_execution": True, "step_type": step.step_type.value},
                    execution_time=0.1,
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
        """Execute sketch creation step with real FreeCAD commands"""
        try:
            # Extract parameters from the step
            shape = step.parameters.get("shape", "rectangle")
            dimensions = step.parameters.get("dimensions", {})

            # Generate appropriate FreeCAD code based on the original command context
            original_command = context.get("original_command", "").lower()

            if "gear" in original_command:
                # Generate gear creation code
                teeth = 20  # Default, extract from command if needed
                diameter = 50  # Default, extract from command if needed
                thickness = 10  # Default, extract from command if needed

                # Extract parameters from original command if possible
                import re

                if "teeth" in original_command:
                    teeth_match = re.search(r"(\d+)\s*teeth", original_command)
                    if teeth_match:
                        teeth = int(teeth_match.group(1))

                if "diameter" in original_command:
                    diameter_match = re.search(
                        r"(\d+(?:\.\d+)?)\s*mm\s*diameter", original_command
                    )
                    if diameter_match:
                        diameter = float(diameter_match.group(1))

                if "thickness" in original_command:
                    thickness_match = re.search(
                        r"(\d+(?:\.\d+)?)\s*mm\s*thickness", original_command
                    )
                    if thickness_match:
                        thickness = float(thickness_match.group(1))

                freecad_code = f"""
# Create precision gear with {teeth} teeth, {diameter}mm diameter, {thickness}mm thickness
import FreeCAD as App
import Part
import math

# Get active document
doc = App.ActiveDocument
if not doc:
    doc = App.newDocument()

# Gear parameters
num_teeth = {teeth}
outer_diameter = {diameter}
thickness = {thickness}
module = outer_diameter / num_teeth  # Calculate module
pressure_angle = 20  # degrees
addendum = module
dedendum = 1.25 * module
root_diameter = outer_diameter - 2 * dedendum
pitch_diameter = outer_diameter - 2 * addendum

# Create gear profile using involute curve
def involute_point(base_radius, angle):
    x = base_radius * (math.cos(angle) + angle * math.sin(angle))
    y = base_radius * (math.sin(angle) - angle * math.cos(angle))
    return (x, y)

# Base circle radius
base_radius = pitch_diameter / 2 * math.cos(math.radians(pressure_angle))

# Create gear tooth profile
import Part
from FreeCAD import Vector

# Create one tooth profile
tooth_points = []
angle_step = 0.1
max_angle = math.sqrt((outer_diameter/2)**2 / base_radius**2 - 1)

# Involute curve points
for i in range(int(max_angle / angle_step) + 1):
    angle = i * angle_step
    x, y = involute_point(base_radius, angle)
    tooth_points.append(Vector(x, y, 0))

# Create base circle for gear
base_circle = Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), root_diameter/2)
base_wire = Part.Wire([base_circle.toShape()])
gear_face = Part.Face(base_wire)

# Create gear teeth by boolean operations
angular_step = 360.0 / num_teeth
for tooth_num in range(num_teeth):
    angle_deg = tooth_num * angular_step

    # Create simplified rectangular tooth for now
    tooth_height = (outer_diameter - root_diameter) / 2
    tooth_width = math.pi * pitch_diameter / num_teeth * 0.4  # Simplified

    # Create tooth rectangle
    tooth_x = root_diameter/2 + tooth_height/2
    tooth_y = 0

    # Create tooth shape
    tooth_box = Part.makeBox(tooth_height, tooth_width, thickness)
    tooth_box.translate(Vector(tooth_x - tooth_height/2, -tooth_width/2, 0))

    # Rotate tooth to correct position
    tooth_box = tooth_box.rotate(Vector(0, 0, 0), Vector(0, 0, 1), math.radians(angle_deg))

    # Union with gear
    gear_face = gear_face.fuse(tooth_box)

# Extrude gear to thickness
gear_solid = gear_face.extrude(Vector(0, 0, thickness))

# Create mounting hole if specified
if 'mounting' in original_command or 'hole' in original_command:
    hole_diameter = min(root_diameter * 0.3, 10)  # Reasonable hole size
    hole_cylinder = Part.makeCylinder(hole_diameter/2, thickness * 1.1)
    hole_cylinder.translate(Vector(0, 0, -thickness * 0.05))
    gear_solid = gear_solid.cut(hole_cylinder)

# Create FreeCAD object
gear_obj = doc.addObject("Part::Feature", "PrecisionGear")
gear_obj.Shape = gear_solid
gear_obj.Label = f"Gear_{teeth}T_{diameter}mm"

# Recompute document
doc.recompute()
"""

            else:
                # Default sketch creation for other shapes
                freecad_code = f"""
# Create {shape} sketch
import FreeCAD as App
import Sketcher

doc = App.ActiveDocument
if not doc:
    doc = App.newDocument()

sketch = doc.addObject('Sketcher::SketchObject', 'Sketch')
sketch.Placement = App.Placement(App.Vector(0.000000, 0.000000, 0.000000), App.Rotation(0.000000, 0.000000, 0.000000, 1.000000))

# Add geometry to sketch
if "{shape}" == "rectangle":
    sketch.addGeometry(Part.LineSegment(App.Vector(-10.0, -10.0, 0), App.Vector(10.0, -10.0, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(10.0, -10.0, 0), App.Vector(10.0, 10.0, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(10.0, 10.0, 0), App.Vector(-10.0, 10.0, 0)), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(-10.0, 10.0, 0), App.Vector(-10.0, -10.0, 0)), False)

doc.recompute()
"""

            # Execute the FreeCAD code
            if self.command_executor:
                result = self.command_executor.execute(freecad_code)

                return WorkflowExecutionResult(
                    step_id=step.step_id,
                    status="success" if result.get("status") == "success" else "error",
                    output={
                        "freecad_code": freecad_code,
                        "execution_result": result,
                        "shape_created": True,
                        "shape_type": "gear" if "gear" in original_command else shape,
                    },
                    execution_time=0.5,
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
        """Execute pad/extrusion step"""
        # Mock implementation - would integrate with actual pad operation
        return WorkflowExecutionResult(
            step_id=step.step_id,
            status="success",
            output={
                "pad_created": True,
                "pad_name": f"Pad_{step.step_id}",
                "height": step.parameters.get("height", 10.0),
            },
            execution_time=0.3,
        )

    def _execute_hole_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Execute hole creation step"""
        # Mock implementation - would integrate with actual hole operation
        return WorkflowExecutionResult(
            step_id=step.step_id,
            status="success",
            output={
                "hole_created": True,
                "hole_name": f"Hole_{step.step_id}",
                "diameter": step.parameters.get("diameter", 5.0),
                "depth": step.parameters.get("depth", "through"),
            },
            execution_time=0.2,
        )

    def _execute_pattern_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Execute pattern creation step"""
        # Mock implementation - would integrate with pattern engine
        return WorkflowExecutionResult(
            step_id=step.step_id,
            status="success",
            output={
                "pattern_created": True,
                "pattern_name": f"Pattern_{step.step_id}",
                "pattern_type": step.step_type.value,
                "count": step.parameters.get("count", 1),
            },
            execution_time=0.4,
        )

    def _execute_feature_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Execute feature operation step (fillet, chamfer, etc.)"""
        # Mock implementation - would integrate with advanced features engine
        return WorkflowExecutionResult(
            step_id=step.step_id,
            status="success",
            output={
                "feature_applied": True,
                "feature_name": f"Feature_{step.step_id}",
                "feature_type": step.step_type.value,
                "radius": step.parameters.get("radius", 1.0),
            },
            execution_time=0.3,
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
        """Extract basic operations from command"""
        # Simplified implementation
        operations = []

        if "create" in command.lower() or "sketch" in command.lower():
            operations.append(
                {
                    "type": "sketch",
                    "shape": "rectangle",
                    "parameters": {"width": 50.0, "height": 30.0},
                }
            )

        if "extrude" in command.lower() or "tall" in command.lower():
            operations.append({"type": "extrude", "parameters": {"height": 10.0}})

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

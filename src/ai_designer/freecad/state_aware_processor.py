"""
State-Driven Command Processor
Handles complex natural language commands by breaking them down into steps
and using Redis state for intelligent decision making.
"""

import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .geometry_helpers import (  # noqa: E402
    analyze_geometry_requirements,
    build_circle_sketch_script,
    build_rectangle_sketch_script,
)
from .state_diff import (  # noqa: E402
    build_checkpoint_key,
    preflight_checks,
    validate_final_state,
)
from .workflow_templates import (  # noqa: E402
    analyze_workflow_requirements,
    calculate_complexity_score,
    estimate_step_count,
)


class StateAwareCommandProcessor:
    """
    Enhanced command processor that uses Redis state to break down complex
    natural language commands into multiple executable steps.
    """

    def __init__(self, llm_client, state_cache, api_client, command_executor):
        self.llm_client = llm_client
        self.state_cache = state_cache
        self.api_client = api_client
        self.command_executor = command_executor
        self.session_id = f"session_{int(time.time())}"

        # Initialize face selection engine for Phase 2
        try:
            from .face_selection_engine import FaceDetectionEngine, FaceSelector

            self.face_detector = FaceDetectionEngine(api_client)
            self.face_selector = FaceSelector(self.face_detector)
            self.face_selection_available = True
        except ImportError:
            self.face_detector = None
            self.face_selector = None
            self.face_selection_available = False

        # Initialize workflow orchestrator for Phase 3
        try:
            from .workflow_orchestrator import WorkflowOrchestrator

            self.workflow_orchestrator = WorkflowOrchestrator(
                state_processor=self,
                pattern_engine=None,  # Will be initialized when pattern engine is implemented
                advanced_features=None,  # Will be initialized when advanced features are implemented
            )
            self.multi_step_workflows_available = True
        except ImportError:
            self.workflow_orchestrator = None
            self.multi_step_workflows_available = False
            print("✅ Face selection engine initialized")
        except ImportError as e:
            print(f"⚠️ Face selection engine not available: {e}")
            self.face_selection_available = False

    def process_complex_command(self, nl_command: str) -> Dict[str, Any]:
        """
        Main entry point: Process complex natural language command using state-driven approach

        Enhanced Flow:
        1. Analyze workflow requirements (sketch-then-operate vs simple)
        2. Get current state from Redis
        3. Use appropriate processing strategy
        4. Execute with continuous state validation
        """
        print(f"🧠 Processing complex command: {nl_command}")

        try:
            # Step 1: Get current state from Redis
            current_state = self._get_current_state()
            print(
                f"📊 Current state retrieved: {len(current_state.get('objects', []))} objects"
            )

            # Step 2: Analyze workflow requirements
            workflow_analysis = self._analyze_workflow_requirements(
                nl_command, current_state
            )
            print(
                f"🔍 Workflow analysis: {workflow_analysis.get('strategy', 'unknown')}"
            )

            # Step 3: Use appropriate processing strategy
            if workflow_analysis.get("is_complex_workflow", False):
                return self._process_complex_workflow(
                    nl_command, current_state, workflow_analysis
                )
            elif workflow_analysis.get("requires_sketch_then_operate", False):
                return self._process_sketch_then_operate_workflow(
                    nl_command, current_state, workflow_analysis
                )
            elif workflow_analysis.get("requires_face_selection", False):
                return self._process_face_selection_workflow(
                    nl_command, current_state, workflow_analysis
                )
            elif workflow_analysis.get("is_multi_step", False):
                return self._process_multi_step_workflow(
                    nl_command, current_state, workflow_analysis
                )
            else:
                return self._process_standard_workflow(nl_command, current_state)

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "suggestion": "Check FreeCAD connection and try a simpler command",
            }
            return self._execute_step_sequence(task_breakdown, nl_command)

        except Exception as e:
            print(f"❌ Error in complex command processing: {e}")
            return {"status": "error", "message": str(e)}

    def _get_current_state(self) -> Dict[str, Any]:
        """Get the current FreeCAD document state and any cached state from Redis"""
        try:
            # Get live state from FreeCAD
            live_state = self.api_client.get_document_state()

            # Get cached state from Redis
            cached_states = self.state_cache.list_states(session_id=self.session_id)
            latest_cached_state = {}

            if cached_states:
                # Get the most recent state
                latest_key = max(cached_states)
                latest_cached_state = self.state_cache.retrieve_state(latest_key) or {}

            # Combine live and cached state
            combined_state = {
                "live_state": live_state,
                "cached_state": latest_cached_state,
                "objects": live_state.get("objects", []),
                "object_count": live_state.get("object_count", 0),
                "document_name": live_state.get("document_name", "Unknown"),
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
            }

            return combined_state

        except Exception as e:
            print(f"⚠️ Error getting current state: {e}")
            return {"objects": [], "object_count": 0, "error": str(e)}

    def _analyze_workflow_requirements(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze what type of workflow is required. Delegates to workflow_templates."""
        return analyze_workflow_requirements(nl_command, current_state)

    def _estimate_step_count(self, nl_command: str, strategy: str) -> int:
        """Estimate number of steps. Delegates to workflow_templates."""
        return estimate_step_count(nl_command, strategy)

    def _calculate_complexity_score(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> float:
        """Calculate complexity score (0-1). Delegates to workflow_templates."""
        return calculate_complexity_score(nl_command, current_state)

    def _process_sketch_then_operate_workflow(
        self,
        nl_command: str,
        current_state: Dict[str, Any],
        workflow_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle the core 'Sketch-Then-Operate' workflow

        Example: "Create a 50mm diameter cylinder that is 100mm tall"
        Steps:
        1. Pre-flight state check
        2. Create/activate PartDesign Body (if needed)
        3. Create sketch on appropriate plane
        4. Define sketch geometry with constraints
        5. Perform operation (Pad, Pocket, etc.)
        6. Validate final state
        """
        print(f"🎯 Starting Sketch-Then-Operate workflow for: {nl_command}")

        execution_results = []

        try:
            # Step 1: Pre-flight state analysis
            preflight_check = self._preflight_state_check(
                current_state, workflow_analysis
            )
            if not preflight_check["ready"]:
                return {
                    "status": "error",
                    "error": f"Pre-flight check failed: {preflight_check['reason']}",
                    "suggestion": preflight_check["suggestion"],
                }

            # Step 2: Ensure PartDesign Body exists and is active
            if workflow_analysis.get("needs_active_body", False):
                body_result = self._ensure_active_body()
                execution_results.append(body_result)
                if body_result["status"] != "success":
                    return body_result

                # Update state after body creation
                current_state = self._get_current_state()

            # Step 3: Analyze geometry requirements
            geometry_analysis = self._analyze_geometry_requirements(nl_command)

            # Step 4: Create sketch on appropriate plane
            sketch_result = self._create_parametric_sketch(
                geometry_analysis, current_state
            )
            execution_results.append(sketch_result)
            if sketch_result["status"] != "success":
                return sketch_result

            # Update state after sketch creation
            current_state = self._get_current_state()

            # Step 5: Perform the operation (Pad, Pocket, etc.)
            operation_result = self._execute_sketch_operation(
                geometry_analysis, current_state
            )
            execution_results.append(operation_result)

            # Step 6: Final state validation
            final_state = self._get_current_state()
            validation_result = self._validate_final_state(
                final_state, geometry_analysis
            )

            return {
                "status": "success" if validation_result["valid"] else "warning",
                "workflow": "sketch_then_operate",
                "steps_executed": len(execution_results),
                "execution_results": execution_results,
                "final_state": final_state,
                "validation": validation_result,
                "objects_created": final_state.get("object_count", 0)
                - current_state.get("object_count", 0),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Sketch-Then-Operate workflow failed: {str(e)}",
                "steps_completed": len(execution_results),
                "execution_results": execution_results,
            }

    def _process_face_selection_workflow(
        self,
        nl_command: str,
        current_state: Dict[str, Any],
        workflow_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle the 'Face Selection & Operations' workflow

        Example: "Add a 10mm diameter hole on the top face"
        Steps:
        1. Check face selection availability
        2. Analyze operation requirements
        3. Detect and select appropriate face
        4. Create operation geometry
        5. Execute operation on selected face
        6. Validate final state
        """
        print(f"🎯 Starting Face Selection workflow for: {nl_command}")

        execution_results = []

        try:
            # Step 1: Check if face selection is available
            if not self.face_selection_available:
                return {
                    "status": "error",
                    "error": "Face selection engine not available",
                    "suggestion": "Face selection features require Phase 2 components",
                }

            # Step 2: Analyze operation requirements
            operation_analysis = self._analyze_face_operation_requirements(nl_command)
            execution_results.append(
                {
                    "step": "operation_analysis",
                    "status": "success",
                    "analysis": operation_analysis,
                }
            )

            # Step 3: Get existing objects for face detection
            existing_objects = [
                obj.get("name", "") for obj in current_state.get("objects", [])
            ]
            if not existing_objects:
                return {
                    "status": "error",
                    "error": "No existing objects found for face selection",
                    "suggestion": "Create some geometry first before adding holes or pockets",
                }

            # Step 4: Select appropriate face
            face_selection_result = self._select_operation_face(
                existing_objects,
                operation_analysis["operation_type"],
                operation_analysis.get("face_criteria", ""),
            )
            execution_results.append(face_selection_result)

            if face_selection_result["status"] != "success":
                return face_selection_result

            # Step 5: Create operation geometry
            geometry_result = self._create_face_operation_geometry(
                operation_analysis, face_selection_result["selected_face"]
            )
            execution_results.append(geometry_result)

            if geometry_result["status"] != "success":
                return geometry_result

            # Step 6: Execute operation
            operation_result = self._execute_face_operation(
                operation_analysis,
                face_selection_result["selected_face"],
                geometry_result["geometry"],
            )
            execution_results.append(operation_result)

            # Step 7: Final state validation
            final_state = self._get_current_state()
            validation_result = self._validate_face_operation_result(
                final_state, operation_analysis
            )

            return {
                "status": "success" if validation_result["valid"] else "warning",
                "workflow": "face_selection",
                "steps_executed": len(execution_results),
                "execution_results": execution_results,
                "selected_face": face_selection_result.get("selected_face"),
                "operation_type": operation_analysis["operation_type"],
                "final_state": final_state,
                "validation": validation_result,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Face selection workflow failed: {str(e)}",
                "steps_completed": len(execution_results),
                "execution_results": execution_results,
            }

    def _analyze_face_operation_requirements(self, nl_command: str) -> Dict[str, Any]:
        """
        Analyze face-specific operation requirements

        Examples:
        - "Add a 10mm hole on the top face"
        - "Create a pocket in the center"
        - "Drill 4 holes in a square pattern"
        """
        operation = {
            "operation_type": "hole",  # Default
            "dimensions": {},
            "face_criteria": "",
            "positioning": "center",
            "count": 1,
            "pattern_type": None,
        }

        nl_lower = nl_command.lower()

        # Determine operation type
        if any(word in nl_lower for word in ["hole", "drill", "bore"]):
            operation["operation_type"] = "hole"
        elif any(word in nl_lower for word in ["pocket", "cut", "remove"]):
            operation["operation_type"] = "pocket"
        elif any(word in nl_lower for word in ["pattern", "array"]):
            operation["operation_type"] = "pattern"

        # Extract dimensions
        diameter_match = re.search(
            r"(\d+(?:\.\d+)?)\s*mm\s+(?:diameter|hole)", nl_command
        )
        if diameter_match:
            operation["dimensions"]["diameter"] = float(diameter_match.group(1))
            operation["dimensions"]["radius"] = float(diameter_match.group(1)) / 2

        depth_match = re.search(r"(\d+(?:\.\d+)?)\s*mm\s+(?:deep|depth)", nl_command)
        if depth_match:
            operation["dimensions"]["depth"] = float(depth_match.group(1))

        # Extract face criteria
        face_keywords = [
            "top",
            "bottom",
            "front",
            "back",
            "left",
            "right",
            "center",
            "large",
            "flat",
        ]
        for keyword in face_keywords:
            if keyword in nl_lower:
                operation["face_criteria"] += f"{keyword} "

        operation["face_criteria"] = operation["face_criteria"].strip()

        # Extract count and pattern info
        count_match = re.search(r"(\d+)\s+holes?", nl_command)
        if count_match:
            operation["count"] = int(count_match.group(1))
            if operation["count"] > 1:
                operation["pattern_type"] = "linear"  # Default pattern

        return operation

    def _select_operation_face(
        self, objects: List[str], operation_type: str, face_criteria: str
    ) -> Dict[str, Any]:
        """Select the best face for the operation"""
        try:
            selected_face = self.face_selector.select_optimal_face(
                objects, operation_type, face_criteria
            )

            if selected_face:
                return {
                    "status": "success",
                    "step": "face_selection",
                    "selected_face": {
                        "object_name": selected_face.object_name,
                        "face_id": selected_face.face_id,
                        "face_type": selected_face.face_type.value,
                        "area": selected_face.area,
                        "center": selected_face.center,
                        "normal": selected_face.normal,
                        "suitability_score": selected_face.suitability_score,
                    },
                }
            else:
                return {
                    "status": "error",
                    "step": "face_selection",
                    "error": "No suitable face found for operation",
                }
        except Exception as e:
            return {
                "status": "error",
                "step": "face_selection",
                "error": f"Face selection failed: {str(e)}",
            }

    def _create_face_operation_geometry(
        self, operation_analysis: Dict, selected_face: Dict
    ) -> Dict[str, Any]:
        """Create geometry for the face operation"""
        try:
            geometry = {
                "operation_type": operation_analysis["operation_type"],
                "dimensions": operation_analysis["dimensions"],
                "position": selected_face["center"],
                "normal": selected_face["normal"],
            }

            # Add operation-specific geometry
            if operation_analysis["operation_type"] == "hole":
                geometry["profile"] = "circle"
                geometry["radius"] = operation_analysis["dimensions"].get(
                    "radius", 2.5
                )  # Default 5mm diameter
                geometry["depth"] = operation_analysis["dimensions"].get(
                    "depth", 10.0
                )  # Default 10mm deep

            elif operation_analysis["operation_type"] == "pocket":
                geometry["profile"] = "rectangle"
                geometry["width"] = operation_analysis["dimensions"].get("width", 20.0)
                geometry["height"] = operation_analysis["dimensions"].get(
                    "height", 20.0
                )
                geometry["depth"] = operation_analysis["dimensions"].get("depth", 5.0)

            return {
                "status": "success",
                "step": "geometry_creation",
                "geometry": geometry,
            }

        except Exception as e:
            return {
                "status": "error",
                "step": "geometry_creation",
                "error": f"Geometry creation failed: {str(e)}",
            }

    def _execute_face_operation(
        self, operation_analysis: Dict, selected_face: Dict, geometry: Dict
    ) -> Dict[str, Any]:
        """Execute the operation on the selected face"""
        try:
            if geometry["operation_type"] == "hole":
                return self._execute_hole_on_face(selected_face, geometry)
            elif geometry["operation_type"] == "pocket":
                return self._execute_pocket_on_face(selected_face, geometry)
            else:
                return {
                    "status": "error",
                    "step": "operation_execution",
                    "error": f"Unsupported operation type: {geometry['operation_type']}",
                }
        except Exception as e:
            return {
                "status": "error",
                "step": "operation_execution",
                "error": f"Operation execution failed: {str(e)}",
            }

    def _execute_hole_on_face(
        self, selected_face: Dict, geometry: Dict
    ) -> Dict[str, Any]:
        """Execute hole drilling on selected face"""
        radius = geometry.get("radius", 2.5)
        depth = geometry.get("depth", 10.0)
        position = geometry.get("position", [0, 0, 0])

        hole_script = f"""
import FreeCAD
import PartDesign
import Sketcher
import Part

doc = FreeCAD.ActiveDocument

# Get the target object
target_obj = doc.getObject('{selected_face['object_name']}')
if not target_obj:
    raise Exception("Target object not found")

# Get active body or create one
activeBody = None
for obj in doc.Objects:
    if hasattr(obj, 'TypeId') and obj.TypeId == 'PartDesign::Body':
        activeBody = obj
        break

if not activeBody:
    activeBody = doc.addObject('PartDesign::Body', 'Body')

# Create sketch for hole on the selected face
sketch = activeBody.newObject('Sketcher::SketchObject', 'HoleSketch')

# Map sketch to the selected face
# Note: In real implementation, we'd use the actual face reference
sketch.MapMode = 'FlatFace'

# Create circle for hole
circle = sketch.addGeometry(Part.Circle(FreeCAD.Vector({position[0]}, {position[1]}, 0), FreeCAD.Vector(0, 0, 1), {radius}), False)

# Add radius constraint
sketch.addConstraint(Sketcher.Constraint('Radius', circle, {radius}))

# Create pocket (hole) feature
pocket = activeBody.newObject('PartDesign::Pocket', 'Hole')
pocket.Profile = sketch
pocket.Length = {depth}
pocket.Type = 0  # Length type

# Recompute
doc.recompute()
print(f"SUCCESS: Hole created - radius {radius}mm, depth {depth}mm")
"""

        try:
            result = self.api_client.execute_command(hole_script)
            return {
                "status": "success",
                "step": "hole_execution",
                "operation": "hole",
                "parameters": {"radius": radius, "depth": depth},
                "result": result,
            }
        except Exception as e:
            return {"status": "error", "step": "hole_execution", "error": str(e)}

    def _execute_pocket_on_face(
        self, selected_face: Dict, geometry: Dict
    ) -> Dict[str, Any]:
        """Execute pocket creation on selected face"""
        width = geometry.get("width", 20.0)
        height = geometry.get("height", 20.0)
        depth = geometry.get("depth", 5.0)

        # Use existing pocket operation but with face-specific positioning
        return self._execute_pocket_operation(
            {"depth": depth, "width": width, "height": height}
        )

    def _validate_face_operation_result(
        self, final_state: Dict, operation_analysis: Dict
    ) -> Dict[str, Any]:
        """Validate the result of face operation"""
        validation = {"valid": True, "issues": [], "quality_score": 1.0}

        # Check basic state validity
        live_state = final_state.get("live_state", {})

        if live_state.get("has_errors", False):
            validation["valid"] = False
            validation["issues"].append("Document contains errors after operation")
            validation["quality_score"] -= 0.3

        # Check operation-specific results
        operation_type = operation_analysis.get("operation_type", "unknown")
        if operation_type == "hole":
            # Check if pocket/hole was created
            if not live_state.get("has_pocket", False):
                validation["issues"].append("Hole operation may not have completed")
                validation["quality_score"] -= 0.2

        return validation

    def _process_complex_workflow(
        self,
        nl_command: str,
        current_state: Dict[str, Any],
        workflow_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle Phase 3 complex multi-step workflows

        Examples:
        - "Create a bracket with 4 mounting holes and fillets"
        - "Build a gear housing with cover and mounting features"
        - "Design a mechanical assembly with multiple parts"
        """
        print(f"🎯 Starting Complex Workflow for: {nl_command}")

        if not self.multi_step_workflows_available:
            return {
                "status": "error",
                "error": "Complex workflow engine not available",
                "suggestion": "Complex workflows require Phase 3 components",
            }

        try:
            # Step 1: Decompose complex workflow
            workflow_steps = self.workflow_orchestrator.decompose_complex_workflow(
                nl_command, current_state
            )
            print(f"🔧 Decomposed into {len(workflow_steps)} workflow steps")

            # Step 2: Plan execution sequence
            sorted_steps = self.workflow_orchestrator.plan_execution_sequence(
                workflow_steps
            )
            print(f"📋 Execution sequence planned for {len(sorted_steps)} steps")

            # Step 3: Execute workflow
            execution_context = {
                "session_id": self.session_id,
                "current_state": current_state,
                "workflow_analysis": workflow_analysis,
                "original_command": nl_command,  # Add original command for proper context
            }

            execution_result = self.workflow_orchestrator.execute_workflow_steps(
                sorted_steps, execution_context
            )

            # Step 4: Final state validation
            final_state = self._get_current_state()

            return {
                "status": execution_result["status"],
                "workflow": "complex_workflow",
                "total_steps": execution_result["total_steps"],
                "completed_steps": execution_result["completed_steps"],
                "failed_steps": execution_result["failed_steps"],
                "execution_time": execution_result["execution_time"],
                "step_results": execution_result["step_results"],
                "final_state": final_state,
                "complexity_score": workflow_analysis.get("complexity_score", 0.0),
                "workflow_pattern": workflow_analysis.get("strategy", "unknown"),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Complex workflow failed: {str(e)}",
                "suggestion": "Try breaking the command into simpler parts",
            }

    def _process_multi_step_workflow(
        self,
        nl_command: str,
        current_state: Dict[str, Any],
        workflow_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle traditional multi-step workflows (Phase 1 extension)

        Examples:
        - "Add multiple features to existing object"
        - "Create and position additional components"
        """
        print(f"🎯 Starting Multi-Step Workflow for: {nl_command}")

        try:
            # Use existing task breakdown logic
            task_breakdown = self._decompose_task(nl_command, current_state)

            if not task_breakdown or "error" in task_breakdown:
                return {
                    "status": "error",
                    "message": "Failed to decompose multi-step task",
                }

            print(f"📋 Task broken down into {len(task_breakdown['steps'])} steps")

            # Execute each step with state updates
            execution_result = self._execute_step_sequence(task_breakdown, nl_command)

            return {
                "status": execution_result.get("status", "unknown"),
                "workflow": "multi_step",
                "steps_executed": execution_result.get("completed_steps", 0),
                "execution_results": execution_result.get("step_results", []),
                "final_state": self._get_current_state(),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Multi-step workflow failed: {str(e)}",
                "suggestion": "Try using simpler commands",
            }

    def _process_standard_workflow(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process commands using standard decomposition workflow"""
        # Use existing decomposition logic for non-sketch-based commands
        task_breakdown = self._decompose_task(nl_command, current_state)

        if not task_breakdown or "error" in task_breakdown:
            return {"status": "error", "message": "Failed to decompose task"}

        print(f"📋 Task broken down into {len(task_breakdown['steps'])} steps")

        # Execute each step with state updates
        return self._execute_steps_with_state_updates(
            task_breakdown["steps"], current_state
        )

    def _preflight_state_check(
        self, current_state: Dict[str, Any], workflow_analysis: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Run pre-flight checks. Delegates to state_diff."""
        return preflight_checks(
            current_state,
            workflow_analysis,
            api_client_available=self.api_client is not None,
        )

    def _ensure_active_body(self) -> Dict[str, Any]:
        """
        Ensure an active PartDesign Body exists, create if necessary
        """
        print("🏗️ Ensuring active PartDesign Body exists...")

        body_creation_script = """
import FreeCAD
import PartDesign

doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutoCAD")

# Check if there's already an active body
activeBody = None
for obj in doc.Objects:
    if hasattr(obj, 'TypeId') and obj.TypeId == 'PartDesign::Body':
        activeBody = obj
        break

if not activeBody:
    # Create new PartDesign Body
    activeBody = doc.addObject('PartDesign::Body', 'Body')
    print(f"Created new PartDesign Body: {activeBody.Name}")
else:
    print(f"Using existing PartDesign Body: {activeBody.Name}")

# Set as active body
if hasattr(FreeCAD, 'setActiveDocument'):
    FreeCAD.setActiveDocument(doc.Name)

# Recompute document
doc.recompute()
print("SUCCESS: Active Body ready")
"""

        try:
            result = self.api_client.execute_command(body_creation_script)
            return {
                "status": "success",
                "operation": "ensure_active_body",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "operation": "ensure_active_body",
                "error": str(e),
            }

    def _analyze_geometry_requirements(self, nl_command: str) -> Dict[str, Any]:
        """Extract geometry requirements. Delegates to geometry_helpers."""
        return analyze_geometry_requirements(nl_command)

    def _create_parametric_sketch(
        self, geometry_analysis: Dict[str, Any], current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a parametric sketch based on geometry requirements
        """
        print(f"✏️ Creating parametric sketch: {geometry_analysis['shape']}")

        shape = geometry_analysis["shape"]
        dimensions = geometry_analysis["dimensions"]
        plane = geometry_analysis["plane"]

        if shape == "circle":
            return self._create_circle_sketch(dimensions, plane)
        elif shape == "rectangle":
            return self._create_rectangle_sketch(dimensions, plane)
        else:
            return {
                "status": "error",
                "error": f"Unsupported shape for sketching: {shape}",
            }

    def _create_circle_sketch(
        self, dimensions: Dict[str, float], plane: str = "XY"
    ) -> Dict[str, Any]:
        """Create a parametric circle sketch. Delegates script building to geometry_helpers."""
        script = build_circle_sketch_script(dimensions, plane)
        try:
            result = self.api_client.execute_command(script)
            return {
                "status": "success",
                "operation": "create_circle_sketch",
                "dimensions": dimensions,
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "operation": "create_circle_sketch",
                "error": str(e),
            }

    def _create_rectangle_sketch(
        self, dimensions: Dict[str, float], plane: str = "XY"
    ) -> Dict[str, Any]:
        """Create a parametric rectangle sketch. Delegates script building to geometry_helpers."""
        script = build_rectangle_sketch_script(dimensions, plane)
        try:
            result = self.api_client.execute_command(script)
            return {
                "status": "success",
                "operation": "create_rectangle_sketch",
                "dimensions": dimensions,
                "result": result,
            }
        except Exception as e:
            return {
                "status": "error",
                "operation": "create_rectangle_sketch",
                "error": str(e),
            }

    def _execute_sketch_operation(
        self, geometry_analysis: Dict[str, Any], current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the operation on the created sketch (Pad, Pocket, etc.)
        """
        operation = geometry_analysis["operation"]
        dimensions = geometry_analysis["dimensions"]

        if operation == "pad":
            return self._execute_pad_operation(dimensions)
        elif operation == "pocket":
            return self._execute_pocket_operation(dimensions)
        else:
            return {"status": "error", "error": f"Unsupported operation: {operation}"}

    def _execute_pad_operation(self, dimensions: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Pad operation on the latest sketch"""
        height = dimensions.get("height", 10.0)  # Default 10mm height

        pad_script = f"""
import FreeCAD
import PartDesign

doc = FreeCAD.ActiveDocument

# Get active body
activeBody = None
for obj in doc.Objects:
    if hasattr(obj, 'TypeId') and obj.TypeId == 'PartDesign::Body':
        activeBody = obj
        break

if not activeBody:
    raise Exception("No active PartDesign Body found")

# Find the latest sketch
latest_sketch = None
for obj in activeBody.Group:
    if hasattr(obj, 'TypeId') and obj.TypeId == 'Sketcher::SketchObject':
        latest_sketch = obj

if not latest_sketch:
    raise Exception("No sketch found for Pad operation")

# Create Pad feature
pad = activeBody.newObject('PartDesign::Pad', 'Pad')
pad.Profile = latest_sketch
pad.Length = {height}
pad.Type = 0  # Length type

# Recompute
doc.recompute()
print(f"SUCCESS: Pad created with height {{height}}mm")
"""

        try:
            result = self.api_client.execute_command(pad_script)
            return {
                "status": "success",
                "operation": "pad",
                "height": height,
                "result": result,
            }
        except Exception as e:
            return {"status": "error", "operation": "pad", "error": str(e)}

    def _execute_pocket_operation(self, dimensions: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Pocket operation on the latest sketch"""
        depth = dimensions.get(
            "depth", dimensions.get("height", 5.0)
        )  # Default 5mm depth

        pocket_script = f"""
import FreeCAD
import PartDesign

doc = FreeCAD.ActiveDocument

# Get active body
activeBody = None
for obj in doc.Objects:
    if hasattr(obj, 'TypeId') and obj.TypeId == 'PartDesign::Body':
        activeBody = obj
        break

if not activeBody:
    raise Exception("No active PartDesign Body found")

# Find the latest sketch
latest_sketch = None
for obj in activeBody.Group:
    if hasattr(obj, 'TypeId') and obj.TypeId == 'Sketcher::SketchObject':
        latest_sketch = obj

if not latest_sketch:
    raise Exception("No sketch found for Pocket operation")

# Create Pocket feature
pocket = activeBody.newObject('PartDesign::Pocket', 'Pocket')
pocket.Profile = latest_sketch
pocket.Length = {depth}
pocket.Type = 0  # Length type

# Recompute
doc.recompute()
print(f"SUCCESS: Pocket created with depth {{depth}}mm")
"""

        try:
            result = self.api_client.execute_command(pocket_script)
            return {
                "status": "success",
                "operation": "pocket",
                "depth": depth,
                "result": result,
            }
        except Exception as e:
            return {"status": "error", "operation": "pocket", "error": str(e)}

    def _validate_final_state(
        self, final_state: Dict[str, Any], geometry_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate final state. Delegates to state_diff."""
        return validate_final_state(final_state, geometry_analysis)

    def _decompose_task(
        self, nl_command: str, current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to break down complex natural language command into executable steps
        """
        print("🔧 Decomposing task with LLM...")

        try:
            # Create a detailed prompt for task decomposition
            decomposition_prompt = f"""
You are a FreeCAD automation expert. Break down the following user request into a sequence of executable steps.

User Request: "{nl_command}"

Current FreeCAD State:
- Objects in document: {current_state.get('object_count', 0)}
- Object list: {[obj.get('name', 'Unknown') for obj in current_state.get('objects', [])]}
- Document: {current_state.get('document_name', 'Unknown')}

Instructions:
1. Analyze the user request and current state
2. Break the request into logical, sequential steps
3. Each step should be a single, specific FreeCAD operation
4. Consider object positioning, sizing, and relationships
5. If objects need to be combined, plan the positioning first
6. Use ONLY numeric values in JSON - NO mathematical expressions or formulas
7. Use only standard FreeCAD object types: Part::Box, Part::Cylinder, Part::Cone, Part::Sphere, Part::Torus
8. For gears, use cylinders as simplified representations
9. Return ONLY a JSON object with this exact structure:

{{
    "total_steps": <number>,
    "analysis": "<brief analysis of what needs to be done>",
    "steps": [
        {{
            "step_number": 1,
            "description": "<what this step does>",
            "action_type": "<create|modify|position|combine>",
            "target_object": "<object name or type>",
            "details": {{
                "object_type": "<Part::Box|Part::Cylinder|Part::Cone|Part::Sphere|Part::Torus|etc>",
                "parameters": {{"param1": "value1", "param2": "value2"}},
                "positioning": {{"x": 0, "y": 0, "z": 0, "explanation": "why positioned here"}}
            }}
        }}
    ]
}}

Example for "create a cone and cylinder together":
{{
    "total_steps": 3,
    "analysis": "Create a cylinder as base, create a cone positioned on top, then optionally combine them",
    "steps": [
        {{
            "step_number": 1,
            "description": "Create a base cylinder",
            "action_type": "create",
            "target_object": "Cylinder",
            "details": {{
                "object_type": "Part::Cylinder",
                "parameters": {{"radius": 5, "height": 10}},
                "positioning": {{"x": 0, "y": 0, "z": 0, "explanation": "base position"}}
            }}
        }},
        {{
            "step_number": 2,
            "description": "Create a cone on top of cylinder",
            "action_type": "create",
            "target_object": "Cone",
            "details": {{
                "object_type": "Part::Cone",
                "parameters": {{"radius1": 5, "radius2": 0, "height": 8}},
                "positioning": {{"x": 0, "y": 0, "z": 10, "explanation": "positioned on top of cylinder"}}
            }}
        }},
        {{
            "step_number": 3,
            "description": "Combine cylinder and cone",
            "action_type": "combine",
            "target_object": "Fusion",
            "details": {{
                "object_type": "Part::MultiFuse",
                "parameters": {{"shapes": ["Cylinder", "Cone"]}},
                "positioning": {{"x": 0, "y": 0, "z": 0, "explanation": "fusion combines at original positions"}}
            }}
        }}
    ]
}}
"""

            # Use LLM to decompose the task
            response = self.llm_client.llm.invoke(decomposition_prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            print(f"🤖 LLM decomposition response: {response_text[:200]}...")

            # Try to parse JSON response
            try:
                # Clean the response - remove any markdown formatting
                clean_response = response_text.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                elif clean_response.startswith("```"):
                    clean_response = clean_response[3:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]

                # Additional cleaning for mathematical expressions in JSON
                clean_response = clean_response.strip()

                # Try to find JSON between curly braces
                import re

                json_match = re.search(r"\{.*\}", clean_response, re.DOTALL)
                if json_match:
                    clean_response = json_match.group(0)

                task_breakdown = json.loads(clean_response)

                # Validate the structure
                if not all(
                    key in task_breakdown
                    for key in ["total_steps", "analysis", "steps"]
                ):
                    raise ValueError("Invalid task breakdown structure")

                print(f"✅ Task successfully decomposed: {task_breakdown['analysis']}")
                return task_breakdown

            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse LLM response as JSON: {e}")
                print(f"Character position: line {e.lineno}, column {e.colno}")

                # Try to extract just the problematic area for debugging
                lines = response_text.split("\n")
                if len(lines) >= e.lineno:
                    problematic_line = lines[e.lineno - 1] if e.lineno > 0 else ""
                    print(f"Problematic line: {problematic_line}")
                    print(
                        f"Error near: {problematic_line[max(0, e.colno-10):e.colno+10]}"
                    )

                print(f"Raw response: {response_text}")

                # Try fallback: create a simplified task breakdown
                print("🔄 Attempting to create simplified task breakdown...")
                return self._create_fallback_task_breakdown(nl_command)

            except Exception as e:
                print(f"❌ Other parsing error: {e}")
                return {"error": "Invalid JSON response from LLM"}

        except Exception as e:
            print(f"❌ Error in task decomposition: {e}")
            return {"error": str(e)}

    def _execute_step_sequence(
        self, task_breakdown: Dict[str, Any], original_command: str
    ) -> Dict[str, Any]:
        """
        Execute the sequence of steps, updating state after each step
        """
        print(f"🚀 Executing {task_breakdown['total_steps']} steps...")

        results = []
        execution_state = {
            "original_command": original_command,
            "task_analysis": task_breakdown["analysis"],
            "total_steps": task_breakdown["total_steps"],
            "completed_steps": 0,
            "failed_steps": 0,
            "created_objects": [],
            "start_time": datetime.now().isoformat(),
        }

        for step in task_breakdown["steps"]:
            step_number = step["step_number"]
            step_description = step["description"]

            print(
                f"\n🔄 Step {step_number}/{task_breakdown['total_steps']}: {step_description}"
            )

            try:
                # Get current state before this step
                current_state = self._get_current_state()

                # Generate FreeCAD command for this step
                freecad_command = self._generate_step_command(step, current_state)

                if freecad_command:
                    print(f"📝 Generated command: {freecad_command[:100]}...")

                    # Execute the command
                    execution_result = self.command_executor.execute(freecad_command)

                    if execution_result.get("status") == "success":
                        print(f"✅ Step {step_number} completed successfully")
                        execution_state["completed_steps"] += 1

                        # Update state in Redis
                        updated_state = self._get_current_state()
                        state_key = self.state_cache.cache_state(
                            updated_state,
                            session_id=self.session_id,
                            document_name=updated_state.get("document_name"),
                        )

                        # Track created objects
                        if step["action_type"] == "create":
                            target_object = step["target_object"]
                            execution_state["created_objects"].append(
                                {
                                    "name": target_object,
                                    "step": step_number,
                                    "type": step["details"].get(
                                        "object_type", "Unknown"
                                    ),
                                }
                            )

                        results.append(
                            {
                                "step": step_number,
                                "status": "success",
                                "description": step_description,
                                "command": freecad_command,
                                "state_key": state_key,
                            }
                        )

                    else:
                        print(
                            f"❌ Step {step_number} failed: {execution_result.get('message', 'Unknown error')}"
                        )
                        execution_state["failed_steps"] += 1
                        results.append(
                            {
                                "step": step_number,
                                "status": "failed",
                                "description": step_description,
                                "error": execution_result.get(
                                    "message", "Unknown error"
                                ),
                            }
                        )

                else:
                    print(f"❌ Step {step_number} failed: Could not generate command")
                    execution_state["failed_steps"] += 1
                    results.append(
                        {
                            "step": step_number,
                            "status": "failed",
                            "description": step_description,
                            "error": "Could not generate FreeCAD command",
                        }
                    )

            except Exception as e:
                print(f"❌ Step {step_number} failed with exception: {e}")
                execution_state["failed_steps"] += 1
                results.append(
                    {
                        "step": step_number,
                        "status": "failed",
                        "description": step_description,
                        "error": str(e),
                    }
                )

        # Final summary
        execution_state["end_time"] = datetime.now().isoformat()
        execution_state["overall_status"] = (
            "success" if execution_state["failed_steps"] == 0 else "partial"
        )

        print(f"\n🎯 Execution Summary:")
        print(
            f"   ✅ Completed: {execution_state['completed_steps']}/{execution_state['total_steps']}"
        )
        print(f"   ❌ Failed: {execution_state['failed_steps']}")
        print(f"   📦 Objects created: {len(execution_state['created_objects'])}")

        return {
            "status": execution_state["overall_status"],
            "execution_state": execution_state,
            "step_results": results,
            "summary": f"Completed {execution_state['completed_steps']}/{execution_state['total_steps']} steps",
        }

    def _generate_step_command(
        self, step: Dict[str, Any], current_state: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate a specific FreeCAD command for a single step using current state context
        """
        try:
            action_type = step["action_type"]
            target_object = step["target_object"]
            details = step["details"]

            print(
                f"🔨 Generating command for step: {step.get('description', 'Unknown')}"
            )
            print(f"   Action: {action_type}, Target: {target_object}")
            print(f"   Details: {details}")

            # Create a simple, direct command based on action type
            if action_type == "create":
                object_type = details.get("object_type", "")
                parameters = details.get("parameters", {})
                positioning = details.get("positioning", {})

                # Generate direct FreeCAD command based on object type
                if "Cylinder" in object_type:
                    radius = parameters.get("radius", 5)
                    height = parameters.get("height", 10)
                    command = f"""cylinder = doc.addObject('Part::Cylinder', '{target_object}')
cylinder.Radius = {radius}
cylinder.Height = {height}"""

                elif "Cone" in object_type:
                    radius1 = parameters.get("radius1", 5)
                    radius2 = parameters.get("radius2", 0)
                    height = parameters.get("height", 8)
                    command = f"""cone = doc.addObject('Part::Cone', '{target_object}')
cone.Radius1 = {radius1}
cone.Radius2 = {radius2}
cone.Height = {height}"""

                elif "Box" in object_type:
                    length = parameters.get("length", 10)
                    width = parameters.get("width", 10)
                    height = parameters.get("height", 10)
                    command = f"""box = doc.addObject('Part::Box', '{target_object}')
box.Length = {length}
box.Width = {width}
box.Height = {height}"""

                elif "Sphere" in object_type:
                    radius = parameters.get("radius", 10)
                    command = f"""sphere = doc.addObject('Part::Sphere', '{target_object}')
sphere.Radius = {radius}"""

                else:
                    # Fallback to LLM generation
                    print(f"⚠️ Unknown object type {object_type}, using LLM fallback")
                    return self._llm_generate_fallback(step, current_state)

                # Add positioning if specified
                if (
                    positioning.get("x", 0) != 0
                    or positioning.get("y", 0) != 0
                    or positioning.get("z", 0) != 0
                ):
                    x, y, z = (
                        positioning.get("x", 0),
                        positioning.get("y", 0),
                        positioning.get("z", 0),
                    )
                    var_name = target_object.lower()
                    command += f"""
{var_name}.Placement = App.Placement(App.Vector({x},{y},{z}), App.Rotation())"""

                # Always end with recompute
                command += "\ndoc.recompute()"

                return command

            elif action_type == "combine":
                # Handle fusion/combination
                parameters = details.get("parameters", {})
                shapes = parameters.get("shapes", [])
                if len(shapes) >= 2:
                    shapes_str = ", ".join(
                        [f"doc.getObject('{shape}')" for shape in shapes]
                    )
                    command = f"""fusion = doc.addObject('Part::MultiFuse', '{target_object}')
fusion.Shapes = [{shapes_str}]
doc.recompute()"""
                    return command
                else:
                    print(f"⚠️ Insufficient shapes for combination: {shapes}")
                    return None

            else:
                # Fallback to LLM for complex operations
                print(f"⚠️ Unsupported action type {action_type}, using LLM fallback")
                return self._llm_generate_fallback(step, current_state)

        except Exception as e:
            print(f"❌ Error generating step command: {e}")
            print(f"   Step data: {step}")
            return None

    def _llm_generate_fallback(
        self, step: Dict[str, Any], current_state: Dict[str, Any]
    ) -> Optional[str]:
        """Fallback to LLM generation with simpler prompt"""
        try:
            simple_prompt = f"Create FreeCAD Python code to: {step.get('description', 'unknown task')}"
            return self.llm_client.generate_command(simple_prompt, current_state)
        except Exception as e:
            print(f"❌ LLM fallback failed: {e}")
            return None

    def _create_fallback_task_breakdown(self, nl_command: str) -> Dict[str, Any]:
        """Create a simple fallback task breakdown when JSON parsing fails"""
        return {
            "total_steps": 1,
            "analysis": f"Simplified execution of: {nl_command}",
            "steps": [
                {
                    "step_number": 1,
                    "description": nl_command,
                    "action_type": "create",
                    "target_object": "GeneratedObject",
                    "details": {
                        "object_type": "generated",
                        "parameters": {"command": nl_command},
                        "positioning": {
                            "x": 0,
                            "y": 0,
                            "z": 0,
                            "explanation": "Default position",
                        },
                    },
                }
            ],
        }

    def _execute_steps_with_state_updates(
        self, steps: list, initial_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a list of steps with state updates between each step
        This is the original workflow execution method
        """
        execution_results = []
        current_state = initial_state
        successful_operations = 0

        print(f"🔄 Executing {len(steps)} steps with state updates...")

        for i, step in enumerate(steps, 1):
            print(
                f"\n🎯 Step {i}/{len(steps)}: {step.get('description', 'Unknown step')}"
            )

            try:
                # Execute the step
                if self.command_executor:
                    # Try using the command executor
                    result = self.command_executor.execute_natural_language(
                        step.get("description", "")
                    )
                else:
                    # Fallback to direct LLM generation
                    result = self._execute_step_with_llm(step, current_state)

                if result and result.get("success", False):
                    successful_operations += 1
                    print(f"✅ Step {i} completed successfully")
                else:
                    print(
                        f"⚠️ Step {i} completed with issues: {result.get('error', 'Unknown error')}"
                    )

                execution_results.append(
                    {
                        "step": i,
                        "description": step.get("description", ""),
                        "result": result,
                        "status": (
                            "success"
                            if result and result.get("success", False)
                            else "error"
                        ),
                    }
                )

                # Update state after each step
                try:
                    current_state = self._get_current_state()
                    self._cache_state_update(current_state, f"after_step_{i}")
                except Exception as state_error:
                    print(
                        f"⚠️ Warning: Could not update state after step {i}: {state_error}"
                    )

            except Exception as e:
                print(f"❌ Step {i} failed: {str(e)}")
                execution_results.append(
                    {
                        "step": i,
                        "description": step.get("description", ""),
                        "result": {"error": str(e), "success": False},
                        "status": "error",
                    }
                )

        # Final state update
        final_state = self._get_current_state()

        return {
            "status": "success" if successful_operations > 0 else "error",
            "workflow": "standard_decomposition",
            "total_steps": len(steps),
            "successful_operations": successful_operations,
            "execution_results": execution_results,
            "initial_state": initial_state,
            "final_state": final_state,
            "objects_created": final_state.get("object_count", 0)
            - initial_state.get("object_count", 0),
        }

    def _execute_step_with_llm(
        self, step: Dict[str, Any], current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single step using LLM command generation"""
        try:
            description = step.get("description", "Unknown task")

            # Generate FreeCAD code using LLM
            llm_result = self.llm_client.generate_command(
                prompt=f"Create FreeCAD Python code to: {description}",
                current_state=current_state,
            )

            if llm_result and "command" in llm_result:
                # Execute the generated command
                api_result = self.api_client.execute_command(llm_result["command"])
                return {
                    "success": True,
                    "llm_result": llm_result,
                    "api_result": api_result,
                    "step_description": description,
                }
            else:
                return {
                    "success": False,
                    "error": "LLM failed to generate command",
                    "step_description": description,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step_description": step.get("description", "Unknown task"),
            }

    def _cache_state_update(self, state: Dict[str, Any], checkpoint_name: str):
        """Cache state update with checkpoint name. Uses state_diff.build_checkpoint_key."""
        try:
            if self.state_cache:
                cache_key = build_checkpoint_key(self.session_id, checkpoint_name)
                self.state_cache.store_state(cache_key, state)
                print(f"📦 State cached at checkpoint: {checkpoint_name}")
        except Exception as e:
            print(f"⚠️ Warning: Failed to cache state at {checkpoint_name}: {e}")

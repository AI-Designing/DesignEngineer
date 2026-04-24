"""
Generator Agent for FreeCAD Python script generation.

This agent takes a task graph and generates executable FreeCAD Python code
for each task, ensuring proper syntax, safety, and API compliance.
"""

import ast
import json
from typing import Any, Dict, List, Optional

from ai_designer.agents.base import BaseAgent
from ai_designer.core.llm_provider import (
    LLMMessage,
    LLMRequest,
    LLMRole,
    UnifiedLLMProvider,
)
from ai_designer.core.logging_config import get_logger
from ai_designer.schemas.design_state import AgentType
from ai_designer.schemas.planner_plan import (
    EXECUTABLE_PLANNER_OPS,
    OPERATION_API_HINTS,
    UnsupportedGeneratorOperation,
    assert_generator_can_emit,
)
from ai_designer.schemas.task_graph import TaskGraph, TaskNode, TaskStatus

logger = get_logger(__name__)

_ALLOWED_OPS_LINE = "ALLOWED_OPERATION_TYPES (this software build): " + ", ".join(
    sorted(EXECUTABLE_PLANNER_OPS)
)


class ScriptValidationError(Exception):
    """Raised when generated script fails validation."""

    pass


class GeneratorAgent(BaseAgent):
    """
    LLM-based code generator for FreeCAD Python scripts.

    The GeneratorAgent converts task graph nodes into executable FreeCAD Python code.
    It iterates through tasks in topological order, generating scripts that reference
    previous task outputs when needed.

    Attributes:
        llm_provider: Unified LLM provider for multi-model support
        agent_type: Fixed to AgentType.GENERATOR
        default_temperature: Temperature for code generation (default: 0.2 for consistency)
        max_retries: Maximum retry attempts for generation failures (default: 3)
    """

    # System prompt for FreeCAD code generation (task blocks; see HeadlessRunner + executor)
    SYSTEM_PROMPT = (
        "You are an expert FreeCAD Python code generator specialized in Part and "
        "PartDesign (body → sketch → pad/pocket-style features) workbenches.\n\n"
        + _ALLOWED_OPS_LINE
        + """

FREECAD API REFERENCE (use doc.addObject; Part booleans on shapes are optional — prefer Part workbench objects below):
- Part primitives: doc.addObject("Part::Box"|"Part::Cylinder"|"Part::Sphere"|"Part::Cone"|"Part::Torus", name) with Length/Width/Height/Radius fields as applicable
- Booleans: doc.addObject("Part::Cut"|"Part::Fuse"|"Part::Common", name); set .Base and .Tool to prior task variables
- Dress-up: doc.addObject("Part::Fillet"|"Part::Chamfer", name); set .Base and .Edges per FreeCAD API
- PartDesign: doc.addObject("PartDesign::Body", name); doc.addObject("Sketcher::SketchObject", name); attach sketch to body with body_var.addObject(sketch); doc.addObject("PartDesign::Pad", name); body.addObject(pad); pad.Profile = sketch_var; pad.Length = distance_mm

PARTDESIGN / SKETCHER (body-first):
- Always anchor new sketches on an existing PartDesign::Body from dependencies when the task is sketch/pad; use MapMode = "FlatFace" and Support = (doc.XY_Plane, [""]) for a datum sketch, or attach to a face when the spec says so
- Use sketch.addGeometry(Part.LineSegment(App.Vector(...), App.Vector(...))) for wires; sketch.addConstraint(Sketcher.Constraint("Distance", edge_index, value_mm)) etc.
- Close sketch geometry before pads when the design intent requires a closed profile
- App (FreeCAD as App), Part, PartDesign, and Sketcher are already available in the runner — do NOT add import lines for them

CRITICAL EXECUTION MODEL — READ CAREFULLY:
All task scripts are concatenated and executed as ONE combined Python script.
The framework automatically injects `doc.recompute()` between each task block.
This means:
- Variables defined in earlier tasks are ALREADY IN SCOPE — reference them directly by their Python variable name
- NEVER use doc.getObject() to look up objects from dependency tasks — use the variable name directly
- Do NOT add 'import FreeCAD', 'import Part', 'import App', or 'doc = FreeCAD.ActiveDocument' — these are already set up
- Do NOT call doc.recompute() yourself — the framework injects it between every task automatically
- When your task accesses .Shape.Edges, .Shape.Faces, .Shape.Wires of a dependency object, those shapes
  ARE already computed (because doc.recompute() ran between the dependency task and yours)
- Every addObject() call MUST use a unique Name string that includes the task_id (e.g. "Box_task_1", "Cylinder_task_2") to avoid FreeCAD auto-renaming collisions

CODING RULES:
1. No imports, no doc setup — just the object creation/operation code
2. Use unique, task-specific addObject names: addObject("Part::Box", "Box_{task_id}")
3. For dependency tasks: use the Python variable name shown in PREVIOUS TASK OUTPUTS directly
4. Store results in descriptive variable names unique per task: box_t1, cyl_t2, cut_t4, body_t1, sketch_t2, pad_t3
5. End with a comment: # RESULT: variable_name
6. Handle units in millimeters
7. Position objects at origin unless specified
8. QUANTITY ARITHMETIC — CRITICAL: Properties like .Length, .Width, .Height, .Radius on
   FreeCAD objects return Quantity objects (e.g. "10 mm"), NOT plain floats. When you use
   them in arithmetic or assign to Placement.Base.x/y/z, always call .Value to get the
   raw float first. Examples:
     WRONG:  cyl.Placement.Base.x = box.Length - 15.0        # ArithmeticError
     CORRECT: cyl.Placement.Base.x = box.Length.Value - 15.0  # OK
     WRONG:  pos = box.Width / 2                             # ArithmeticError
     CORRECT: pos = box.Width.Value / 2                       # OK
   Placement.Base.x/y/z always expects a plain float — NEVER assign a Quantity to it.
   Integer and float literals (15.0, 5.0) are always safe on their own — only properties
   of existing objects need .Value when used in arithmetic.

RESPONSE FORMAT:
Return ONLY valid Python code with no markdown formatting, explanations, or code fences.

Example for create_box (task_1):
box_t1 = doc.addObject("Part::Box", "Box_task_1")
box_t1.Length = 10.0
box_t1.Width = 10.0
box_t1.Height = 10.0
# RESULT: box_t1

Example for create_body (task_1):
body_t1 = doc.addObject("PartDesign::Body", "Body_task_1")
# RESULT: body_t1

Example for create_sketch (task_2) after body_t1 from task_1:
sketch_t2 = doc.addObject("Sketcher::SketchObject", "Sketch_task_2")
body_t1.addObject(sketch_t2)
sketch_t2.MapMode = "FlatFace"
sketch_t2.Support = (doc.XY_Plane, [""])
sketch_t2.addGeometry(Part.LineSegment(App.Vector(-50, -25, 0), App.Vector(50, -25, 0)))
sketch_t2.addGeometry(Part.LineSegment(App.Vector(50, -25, 0), App.Vector(50, 25, 0)))
sketch_t2.addGeometry(Part.LineSegment(App.Vector(50, 25, 0), App.Vector(-50, 25, 0)))
sketch_t2.addGeometry(Part.LineSegment(App.Vector(-50, 25, 0), App.Vector(-50, -25, 0)))
sketch_t2.addConstraint(Sketcher.Constraint("Horizontal", 0))
sketch_t2.addConstraint(Sketcher.Constraint("Vertical", 1))
sketch_t2.addConstraint(Sketcher.Constraint("Distance", 0, 100.0))
sketch_t2.addConstraint(Sketcher.Constraint("Distance", 1, 50.0))
# RESULT: sketch_t2

Example for pad (task_3) after body_t1 and sketch_t2:
pad_t3 = doc.addObject("PartDesign::Pad", "Pad_task_3")
body_t1.addObject(pad_t3)
pad_t3.Profile = sketch_t2
pad_t3.Length = 30.0
# RESULT: pad_t3

Example for create_cylinder (task_2, positioned at 15mm from origin — plain float literal, no .Value needed):
cyl_t2 = doc.addObject("Part::Cylinder", "Cylinder_task_2")
cyl_t2.Radius = 5.0
cyl_t2.Height = 15.0
cyl_t2.Placement.Base.x = 15.0
# RESULT: cyl_t2

Example for create_cylinder (task_3, positioned relative to an existing object's property — .Value REQUIRED):
cyl_t3 = doc.addObject("Part::Cylinder", "Cylinder_task_3")
cyl_t3.Radius = 5.0
cyl_t3.Height = 15.0
cyl_t3.Placement.Base.x = box_t1.Length.Value - 15.0
# RESULT: cyl_t3

Example for boolean_cut (task_3) where task_1=box_t1, task_2=cyl_t2:
cut_t3 = doc.addObject("Part::Cut", "Cut_task_3")
cut_t3.Base = box_t1
cut_t3.Tool = cyl_t2
# RESULT: cut_t3

Example for fillet (task_4) where task_3=cut_t3:
# NOTE: the framework already ran doc.recompute() before this task block executes,
# so cut_t3.Shape.Edges is fully populated — len() will return a real non-zero count.
fillet_t4 = doc.addObject("Part::Fillet", "Fillet_task_4")
fillet_t4.Base = cut_t3
__edges = [(i, 2.0, 2.0) for i in range(1, len(cut_t3.Shape.Edges) + 1)]
fillet_t4.Edges = __edges
# RESULT: fillet_t4

Generate FreeCAD Python code for the following task:"""
    )

    def __init__(
        self,
        llm_provider: UnifiedLLMProvider,
        temperature: float = 0.2,
        max_retries: int = 3,
    ):
        """Initialize the Generator Agent."""
        super().__init__(
            llm_provider=llm_provider,
            agent_type=AgentType.GENERATOR,
            max_retries=max_retries,
            temperature=temperature,
        )

    async def execute(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D102
        """Delegate to generate() to satisfy BaseAgent contract."""
        return await self.generate(*args, **kwargs)

    async def generate(
        self,
        task_graph: TaskGraph,
        temperature: Optional[float] = None,
    ) -> Dict[str, str]:
        """Generate FreeCAD Python scripts for all tasks in the graph.

        Processes tasks in topological order, generating code for each task
        and validating syntax before proceeding to dependent tasks.

        Args:
            task_graph: The task graph with operations to generate code for
            temperature: Override default temperature for this generation call

        Returns:
            Dictionary mapping task_id to generated Python code

        Raises:
            ValueError: If task graph has cycles or invalid structure
            RuntimeError: If code generation fails after max retries
        """
        temp = temperature if temperature is not None else self.default_temperature

        logger.info(
            f"Generating code for task graph {task_graph.graph_id} "
            f"with {len(task_graph.nodes)} tasks"
        )

        # Get execution order (topological sort with levels)
        execution_levels = task_graph.get_execution_order()
        scripts: Dict[str, str] = {}

        # Generate code level by level
        for level_idx, level_tasks in enumerate(execution_levels):
            logger.info(
                f"Generating code for level {level_idx + 1}/{len(execution_levels)} "
                f"({len(level_tasks)} tasks)"
            )

            for task_id in level_tasks:
                task = task_graph.nodes[task_id]

                # Generate code for this task (includes validation)
                script = await self._generate_task_script(
                    task=task, previous_scripts=scripts, temperature=temp
                )

                scripts[task_id] = script
                logger.info(f"Successfully generated code for task {task_id}")

        logger.info(
            f"Completed code generation for all {len(scripts)} tasks in graph "
            f"{task_graph.graph_id}"
        )

        return scripts

    async def _generate_task_script(
        self,
        task: TaskNode,
        previous_scripts: Dict[str, str],
        temperature: float,
    ) -> str:
        """Generate Python code for a single task.

        Args:
            task: The task node to generate code for
            previous_scripts: Scripts generated for dependency tasks
            temperature: LLM temperature for sampling

        Returns:
            Generated Python code as a string

        Raises:
            UnsupportedGeneratorOperation: If ``task.operation_type`` is not executable.
            RuntimeError: If generation fails after max retries
        """
        assert_generator_can_emit(task.operation_type)

        # Build task description with context
        task_description = self._build_task_description(task, previous_scripts)

        logger.info(f"Generating code for task {task.task_id} ({task.operation_type})")

        # Prepare LLM request
        llm_request = LLMRequest(
            messages=[
                LLMMessage(role=LLMRole.SYSTEM, content=self.SYSTEM_PROMPT),
                LLMMessage(role=LLMRole.USER, content=task_description),
            ],
            model=self.llm_provider.default_model,
            temperature=temperature,
            max_tokens=2048,
        )

        # Retry loop for generation
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.llm_provider.agenerate(llm_request)
                script = self._clean_script(response.content)

                # Validate the script
                self._validate_script(script, task.task_id)

                logger.info(
                    f"Generated {len(script)} chars of code for {task.task_id} "
                    f"(attempt {attempt})"
                )

                return script

            except (ScriptValidationError, Exception) as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed for {task.task_id}: {e}"
                )

                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed to generate code for task {task.task_id} after "
                        f"{self.max_retries} attempts: {e}"
                    ) from e

        # Should never reach here due to exception in loop
        raise RuntimeError(
            f"Unexpected error generating code for {task.task_id}"
        ) from last_error

    def _build_task_description(
        self, task: TaskNode, previous_scripts: Dict[str, str]
    ) -> str:
        """Build detailed task description for code generation.

        Args:
            task: The task to describe
            previous_scripts: Previously generated scripts for context

        Returns:
            Formatted task description string
        """
        # Start with operation and parameters
        desc_parts = [
            f"TASK: {task.task_id}",
            f"OPERATION: {task.operation_type}",
            f"DESCRIPTION: {task.description}",
            f"PARAMETERS: {json.dumps(task.parameters, indent=2)}",
        ]

        # Add dependency information with full script context so the LLM
        # knows exactly which variable names are in scope
        if task.depends_on:
            desc_parts.append(f"DEPENDS_ON: {', '.join(task.depends_on)}")
            desc_parts.append("\nPREVIOUS TASK OUTPUTS (variables already in scope):")
            for dep_id in task.depends_on:
                if dep_id in previous_scripts:
                    result_var = self._extract_result_variable(previous_scripts[dep_id])
                    dep_script = previous_scripts[dep_id]
                    if result_var:
                        desc_parts.append(
                            f"- {dep_id}: Python variable = {result_var}  "
                            f"(use this variable directly, do NOT call doc.getObject)"
                        )
                    desc_parts.append(
                        f"  [Code for {dep_id}:]\n"
                        + "\n".join(f"  {ln}" for ln in dep_script.splitlines())
                    )

        hint = self._operation_hints(task.operation_type)
        if hint:
            desc_parts.append(f"OPERATION_API_HINT:\n{hint}")

        return "\n".join(desc_parts)

    @staticmethod
    def _operation_hints(operation_type: str) -> str:
        """Stable FreeCAD API notes for the LLM (from planner_plan registry)."""
        return OPERATION_API_HINTS.get(operation_type, "")

    def _clean_script(self, raw_script: str) -> str:
        """Clean LLM output to extract pure Python code.

        Removes markdown code fences, explanatory text, and normalizes whitespace.

        Args:
            raw_script: Raw LLM output

        Returns:
            Cleaned Python code
        """
        script = raw_script.strip()

        # Remove markdown code fences
        if script.startswith("```python"):
            script = script[9:]
        elif script.startswith("```"):
            script = script[3:]

        if script.endswith("```"):
            script = script[:-3]

        script = script.strip()

        # Remove common LLM preambles
        lines = script.split("\n")
        cleaned_lines = []

        for line in lines:
            # Skip explanatory lines that don't look like Python
            if line.strip() and not line.strip().startswith(
                ("Here", "This", "Note:", "Explanation:")
            ):
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _validate_script(self, script: str, task_id: str) -> None:
        """Validate generated Python script for syntax and safety.

        Args:
            script: The Python code to validate
            task_id: Task ID for error reporting

        Raises:
            ScriptValidationError: If validation fails
        """
        # 1. AST parse check (syntax validation)
        try:
            ast.parse(script)
        except SyntaxError as e:
            raise ScriptValidationError(
                f"Task {task_id}: Syntax error at line {e.lineno}: {e.msg}"
            ) from e

        # 2. Import whitelist check
        forbidden_imports = {"os", "sys", "subprocess", "shutil", "pathlib"}
        allowed_imports = {"FreeCAD", "Part", "math", "Draft", "PartDesign", "Sketcher"}

        try:
            tree = ast.parse(script)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in forbidden_imports:
                            raise ScriptValidationError(
                                f"Task {task_id}: Forbidden import '{alias.name}'"
                            )
                        if alias.name not in allowed_imports:
                            logger.warning(
                                f"Task {task_id}: Unusual import '{alias.name}' "
                                "(not in standard whitelist)"
                            )

                elif isinstance(node, ast.ImportFrom):
                    if node.module in forbidden_imports:
                        raise ScriptValidationError(
                            f"Task {task_id}: Forbidden import from '{node.module}'"
                        )

        except ScriptValidationError:
            raise
        except Exception as e:
            logger.warning(f"Task {task_id}: Import check failed: {e}")

        # 3. Dangerous pattern check
        dangerous_patterns = ["exec", "eval", "__import__"]
        script_lower = script.lower()

        for pattern in dangerous_patterns:
            if pattern in script_lower:
                raise ScriptValidationError(
                    f"Task {task_id}: Dangerous pattern '{pattern}' detected"
                )

        # 4. FreeCAD Quantity arithmetic check — detect obj.Length/Width/Height/Radius
        #    used directly in arithmetic or assigned to Placement.Base without .Value
        _quantity_props = {"Length", "Width", "Height", "Radius", "Size", "Diameter"}
        try:
            tree2 = ast.parse(script)
            for node in ast.walk(tree2):
                # Flag: someobj.Prop used as operand in BinOp without .Value
                if isinstance(node, ast.BinOp):
                    for operand in (node.left, node.right):
                        if (
                            isinstance(operand, ast.Attribute)
                            and operand.attr in _quantity_props
                        ):
                            raise ScriptValidationError(
                                f"Task {task_id}: Quantity arithmetic detected — "
                                f"use '.Value' when doing math with .{operand.attr} "
                                f"(e.g. obj.{operand.attr}.Value - 15.0)"
                            )
        except ScriptValidationError:
            raise
        except Exception:
            pass  # AST walk errors are non-fatal for this check

        logger.info(f"Script validation passed for task {task_id}")

    def _extract_result_variable(self, script: str) -> Optional[str]:
        """Extract the result variable name from a script's RESULT comment.

        Args:
            script: Python script with # RESULT: varname comment

        Returns:
            Variable name or None if not found
        """
        for line in script.split("\n"):
            line = line.strip()
            if line.startswith("# RESULT:"):
                # Extract variable name after "# RESULT:"
                result = line[9:].strip()
                return result if result else None

        return None

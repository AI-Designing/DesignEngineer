"""
Generator Agent for FreeCAD Python script generation.

This agent takes a task graph and generates executable FreeCAD Python code
for each task, ensuring proper syntax, safety, and API compliance.
"""

import ast
import json
from typing import Dict, List, Optional

from ai_designer.core.exceptions import LLMError
from ai_designer.core.llm_provider import (
    LLMMessage,
    LLMRequest,
    LLMRole,
    UnifiedLLMProvider,
)
from ai_designer.core.logging_config import get_logger
from ai_designer.schemas.design_state import AgentType
from ai_designer.schemas.task_graph import TaskGraph, TaskNode, TaskStatus

logger = get_logger(__name__)


class ScriptValidationError(Exception):
    """Raised when generated script fails validation."""

    pass


class GeneratorAgent:
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

    # System prompt for FreeCAD code generation
    SYSTEM_PROMPT = """You are an expert FreeCAD Python code generator specialized in Part and PartDesign workbenches.

FREECAD API REFERENCE:
- Create primitives: Part.makeBox(l,w,h), Part.makeCylinder(r,h), Part.makeSphere(r), Part.makeCone(r1,r2,h), Part.makeTorus(r1,r2)
- Boolean operations: obj1.cut(obj2), obj1.fuse(obj2), obj1.common(obj2)
- Transformations: Part.makeFilletedBox(l,w,h,r), obj.makeFillet(radius, edges)
- Document operations: FreeCAD.ActiveDocument.addObject("Part::Feature", "name")
- Recompute: FreeCAD.ActiveDocument.recompute()

CODING RULES:
1. Import only: FreeCAD, Part, math (no os, sys, subprocess)
2. Use ActiveDocument for all operations
3. Store results in descriptive variable names (e.g., box, cylinder, cut_result)
4. Always call doc.recompute() at the end
5. Return the final object name in a comment: # RESULT: object_name
6. Handle units in millimeters
7. Position objects at origin unless specified
8. Use clear, descriptive variable names matching task descriptions

RESPONSE FORMAT:
Return ONLY valid Python code with no markdown formatting, explanations, or code fences.
The code must be executable as-is in FreeCAD's Python console.

Example for create_box:
import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument()

box = doc.addObject("Part::Box", "Box")
box.Length = 10.0
box.Width = 10.0
box.Height = 10.0
doc.recompute()
# RESULT: box

Example for boolean_cut:
import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
base = doc.getObject("box")
tool = doc.getObject("cylinder")

cut_result = doc.addObject("Part::Cut", "Cut")
cut_result.Base = base
cut_result.Tool = tool
doc.recompute()
# RESULT: cut_result

Generate FreeCAD Python code for the following task:"""

    def __init__(
        self,
        llm_provider: UnifiedLLMProvider,
        temperature: float = 0.2,
        max_retries: int = 3,
    ):
        """Initialize the Generator Agent.

        Args:
            llm_provider: Unified LLM provider for model interactions
            temperature: LLM temperature for sampling (0.0-1.0, lower = more deterministic)
            max_retries: Maximum retry attempts for generation failures

        Raises:
            ValueError: If temperature is not in [0.0, 1.0] range
        """
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(f"Temperature must be in [0.0, 1.0], got {temperature}")

        self.llm_provider = llm_provider
        self.agent_type = AgentType.GENERATOR
        self.default_temperature = temperature
        self.max_retries = max_retries

        logger.info(
            f"Initialized GeneratorAgent with temperature={temperature}, "
            f"max_retries={max_retries}"
        )

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
            RuntimeError: If generation fails after max retries
        """
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
                response = await self.llm_provider.generate(llm_request)
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

        # Add dependency information
        if task.depends_on:
            desc_parts.append(f"DEPENDS_ON: {', '.join(task.depends_on)}")
            desc_parts.append("\nPREVIOUS TASK OUTPUTS:")
            for dep_id in task.depends_on:
                if dep_id in previous_scripts:
                    result_var = self._extract_result_variable(previous_scripts[dep_id])
                    if result_var:
                        desc_parts.append(f"- {dep_id}: object name = {result_var}")

        return "\n".join(desc_parts)

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

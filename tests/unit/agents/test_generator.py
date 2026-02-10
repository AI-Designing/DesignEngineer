"""Tests for the Generator Agent."""

import json
from typing import Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_designer.agents.generator import GeneratorAgent, ScriptValidationError
from ai_designer.core.llm_provider import LLMResponse, UnifiedLLMProvider
from ai_designer.schemas.design_state import AgentType
from ai_designer.schemas.task_graph import TaskGraph, TaskNode, TaskStatus


class TestGeneratorAgentInit:
    """Test GeneratorAgent initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        generator = GeneratorAgent(llm_provider=mock_provider)

        assert generator.llm_provider == mock_provider
        assert generator.agent_type == AgentType.GENERATOR
        assert generator.default_temperature == 0.2
        assert generator.max_retries == 3

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        generator = GeneratorAgent(
            llm_provider=mock_provider, temperature=0.5, max_retries=5
        )

        assert generator.default_temperature == 0.5
        assert generator.max_retries == 5

    def test_init_invalid_temperature(self):
        """Test initialization with invalid temperature."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        with pytest.raises(ValueError, match="Temperature must be in"):
            GeneratorAgent(llm_provider=mock_provider, temperature=1.5)


class TestGeneratorAgentGeneration:
    """Test GeneratorAgent code generation."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        mock = MagicMock(spec=UnifiedLLMProvider)
        mock.default_model = "gpt-4o"
        return mock

    @pytest.fixture
    def generator(self, mock_provider):
        """Create a generator instance."""
        return GeneratorAgent(llm_provider=mock_provider)

    @pytest.fixture
    def simple_task_graph(self):
        """Create a simple task graph with one task."""
        request_id = uuid4()
        graph = TaskGraph(request_id=request_id)

        task = TaskNode(
            task_id="task_1",
            operation_type="create_box",
            description="Create a box 10x10x10mm",
            parameters={"length": 10.0, "width": 10.0, "height": 10.0},
        )
        graph.add_task(task)

        return graph

    @pytest.fixture
    def complex_task_graph(self):
        """Create a task graph with dependencies."""
        request_id = uuid4()
        graph = TaskGraph(request_id=request_id)

        task_1 = TaskNode(
            task_id="task_1",
            operation_type="create_box",
            description="Create base box",
            parameters={"length": 10.0, "width": 10.0, "height": 10.0},
        )
        task_2 = TaskNode(
            task_id="task_2",
            operation_type="create_cylinder",
            description="Create hole cylinder",
            parameters={"radius": 2.0, "height": 12.0},
        )
        task_3 = TaskNode(
            task_id="task_3",
            operation_type="boolean_cut",
            description="Cut hole from box",
            parameters={"base_task_id": "task_1", "tool_task_id": "task_2"},
        )

        graph.add_task(task_1)
        graph.add_task(task_2)
        graph.add_task(task_3)

        graph.add_dependency("task_1", "task_3")
        graph.add_dependency("task_2", "task_3")

        return graph

    @pytest.fixture
    def valid_box_script(self):
        """Sample valid box script."""
        return """import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument()

box = doc.addObject("Part::Box", "Box")
box.Length = 10.0
box.Width = 10.0
box.Height = 10.0
doc.recompute()
# RESULT: box"""

    @pytest.fixture
    def valid_cylinder_script(self):
        """Sample valid cylinder script."""
        return """import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
cylinder = doc.addObject("Part::Cylinder", "Cylinder")
cylinder.Radius = 2.0
cylinder.Height = 12.0
doc.recompute()
# RESULT: cylinder"""

    @pytest.fixture
    def valid_cut_script(self):
        """Sample valid cut script."""
        return """import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
base = doc.getObject("box")
tool = doc.getObject("cylinder")

cut_result = doc.addObject("Part::Cut", "Cut")
cut_result.Base = base
cut_result.Tool = tool
doc.recompute()
# RESULT: cut_result"""

    @pytest.mark.asyncio
    async def test_generate_simple_task(
        self, generator, mock_provider, simple_task_graph, valid_box_script
    ):
        """Test generating code for a single task."""
        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(
                content=valid_box_script, model="gpt-4o", provider="openai"
            )
        )

        scripts = await generator.generate(simple_task_graph)

        assert len(scripts) == 1
        assert "task_1" in scripts
        assert "import FreeCAD" in scripts["task_1"]
        assert "box.Length = 10.0" in scripts["task_1"]
        mock_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_dependencies(
        self,
        generator,
        mock_provider,
        complex_task_graph,
        valid_box_script,
        valid_cylinder_script,
        valid_cut_script,
    ):
        """Test generating code for tasks with dependencies."""
        # Mock provider returns different scripts for each task
        mock_provider.generate = AsyncMock(
            side_effect=[
                LLMResponse(
                    content=valid_box_script, model="gpt-4o", provider="openai"
                ),
                LLMResponse(
                    content=valid_cylinder_script, model="gpt-4o", provider="openai"
                ),
                LLMResponse(
                    content=valid_cut_script, model="gpt-4o", provider="openai"
                ),
            ]
        )

        scripts = await generator.generate(complex_task_graph)

        assert len(scripts) == 3
        assert "task_1" in scripts
        assert "task_2" in scripts
        assert "task_3" in scripts
        assert "box.Length" in scripts["task_1"]
        assert "cylinder.Radius" in scripts["task_2"]
        assert "Part::Cut" in scripts["task_3"]
        assert mock_provider.generate.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_with_custom_temperature(
        self, generator, mock_provider, simple_task_graph, valid_box_script
    ):
        """Test generation with custom temperature."""
        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(
                content=valid_box_script, model="gpt-4o", provider="openai"
            )
        )

        await generator.generate(simple_task_graph, temperature=0.8)

        # Verify temperature was passed to LLM request
        call_args = mock_provider.generate.call_args[0][0]
        assert call_args.temperature == 0.8

    @pytest.mark.asyncio
    async def test_generate_with_markdown_wrapped_code(
        self, generator, mock_provider, simple_task_graph, valid_box_script
    ):
        """Test handling of markdown-wrapped code."""
        markdown_wrapped = f"```python\n{valid_box_script}\n```"

        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(
                content=markdown_wrapped, model="gpt-4o", provider="openai"
            )
        )

        scripts = await generator.generate(simple_task_graph)

        # Should clean markdown and still parse
        assert "```" not in scripts["task_1"]
        assert "import FreeCAD" in scripts["task_1"]

    @pytest.mark.asyncio
    async def test_generate_syntax_error_script(
        self, generator, mock_provider, simple_task_graph
    ):
        """Test handling of script with syntax errors."""
        invalid_script = """import FreeCAD
this is not valid python syntax!!!
doc.recompute()"""

        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(
                content=invalid_script, model="gpt-4o", provider="openai"
            )
        )

        with pytest.raises(RuntimeError, match="Failed to generate code"):
            await generator.generate(simple_task_graph)

    @pytest.mark.asyncio
    async def test_generate_forbidden_import(
        self, generator, mock_provider, simple_task_graph
    ):
        """Test detection of forbidden imports."""
        dangerous_script = """import os
import FreeCAD

os.system('rm -rf /')
doc = FreeCAD.ActiveDocument
# RESULT: doc"""

        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(
                content=dangerous_script, model="gpt-4o", provider="openai"
            )
        )

        with pytest.raises(RuntimeError, match="Failed to generate code"):
            await generator.generate(simple_task_graph)


class TestGeneratorAgentHelpers:
    """Test GeneratorAgent helper methods."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)
        return GeneratorAgent(llm_provider=mock_provider)

    def test_clean_script_with_markdown(self, generator):
        """Test cleaning script with markdown fences."""
        raw = "```python\nimport FreeCAD\ndoc.recompute()\n```"
        cleaned = generator._clean_script(raw)

        assert "```" not in cleaned
        assert "import FreeCAD" in cleaned

    def test_clean_script_plain_code(self, generator):
        """Test cleaning plain code without markdown."""
        raw = "import FreeCAD\ndoc.recompute()"
        cleaned = generator._clean_script(raw)

        assert cleaned == raw.strip()

    def test_validate_script_valid(self, generator):
        """Test validation of valid script."""
        valid_script = """import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
box = doc.addObject("Part::Box", "Box")
doc.recompute()"""

        # Should not raise
        generator._validate_script(valid_script, "task_1")

    def test_validate_script_syntax_error(self, generator):
        """Test validation catches syntax errors."""
        invalid_script = "this is not valid python!!!"

        with pytest.raises(ScriptValidationError, match="Syntax error"):
            generator._validate_script(invalid_script, "task_1")

    def test_validate_script_forbidden_import(self, generator):
        """Test validation catches forbidden imports."""
        dangerous_script = """import os
import FreeCAD

os.system('bad command')"""

        with pytest.raises(ScriptValidationError, match="Forbidden import"):
            generator._validate_script(dangerous_script, "task_1")

    def test_validate_script_dangerous_eval(self, generator):
        """Test validation catches dangerous eval/exec."""
        dangerous_script = """import FreeCAD

eval(user_input)
doc.recompute()"""

        with pytest.raises(ScriptValidationError, match="Dangerous pattern"):
            generator._validate_script(dangerous_script, "task_1")

    def test_extract_result_variable(self, generator):
        """Test extracting result variable from script."""
        script = """import FreeCAD
box = doc.addObject("Part::Box", "Box")
doc.recompute()
# RESULT: box"""

        result = generator._extract_result_variable(script)
        assert result == "box"

    def test_extract_result_variable_no_comment(self, generator):
        """Test extraction returns None when no RESULT comment."""
        script = """import FreeCAD
box = doc.addObject("Part::Box", "Box")
doc.recompute()"""

        result = generator._extract_result_variable(script)
        assert result is None

    def test_build_task_description_simple(self, generator):
        """Test building task description without dependencies."""
        task = TaskNode(
            task_id="task_1",
            operation_type="create_box",
            description="Create a box",
            parameters={"length": 10.0, "width": 10.0, "height": 10.0},
        )

        description = generator._build_task_description(task, {})

        assert "TASK: task_1" in description
        assert "OPERATION: create_box" in description
        assert "Create a box" in description
        assert "10.0" in description

    def test_build_task_description_with_dependencies(self, generator):
        """Test building task description with dependencies."""
        task = TaskNode(
            task_id="task_3",
            operation_type="boolean_cut",
            description="Cut hole",
            parameters={"base_task_id": "task_1", "tool_task_id": "task_2"},
            depends_on=["task_1", "task_2"],
        )

        previous_scripts = {
            "task_1": "import FreeCAD\nbox = doc.addObject('Part::Box', 'Box')\n# RESULT: box",
            "task_2": "import FreeCAD\ncyl = doc.addObject('Part::Cylinder', 'Cyl')\n# RESULT: cyl",
        }

        description = generator._build_task_description(task, previous_scripts)

        assert "DEPENDS_ON: task_1, task_2" in description
        assert "PREVIOUS TASK OUTPUTS:" in description
        assert "box" in description
        assert "cyl" in description

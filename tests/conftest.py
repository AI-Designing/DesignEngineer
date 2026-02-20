"""
Shared pytest fixtures and configuration for the test suite.

Provides:
- Mock LLM provider with canned responses
- Mock Redis using fakeredis
- Mock FreeCAD module for unit tests
- Common test data and utilities
- Async test support
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fakeredis import FakeRedis

# Add src directory to path for imports
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require infrastructure)",
    )
    config.addinivalue_line("markers", "slow: marks tests as slow running (>1s)")
    config.addinivalue_line(
        "markers", "requires_freecad: marks tests that require FreeCAD installation"
    )


# ============================================================================
# Event Loop Fixture
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Directory Fixtures
# ============================================================================


@pytest.fixture
def temp_dir(tmp_path):
    """Provide temporary directory for test files."""
    return tmp_path


@pytest.fixture
def temp_outputs_dir(tmp_path):
    """Provide temporary outputs directory."""
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    return outputs


@pytest.fixture
def test_fixtures_dir():
    """Provide path to test fixtures directory."""
    return TEST_DIR / "fixtures"


# ============================================================================
# Mock FreeCAD Module
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def mock_freecad():
    """
    Mock FreeCAD module for unit tests.

    FreeCAD has complex C++ bindings that aren't available in test environments.
    This fixture stubs the module with basic functionality for testing.
    """
    # Create mock FreeCAD module
    freecad_mock = MagicMock()

    # Mock App (FreeCAD.Application)
    app_mock = MagicMock()
    app_mock.newDocument = MagicMock(return_value=MagicMock())
    app_mock.openDocument = MagicMock(return_value=MagicMock())
    app_mock.ActiveDocument = MagicMock()
    app_mock.Vector = lambda x, y, z: {"x": x, "y": y, "z": z}

    freecad_mock.App = app_mock
    freecad_mock.Application = app_mock

    # Mock Part module
    part_mock = MagicMock()
    part_mock.makeBox = MagicMock(return_value=MagicMock())
    part_mock.makeCylinder = MagicMock(return_value=MagicMock())
    part_mock.Circle = MagicMock()
    part_mock.LineSegment = MagicMock()

    freecad_mock.Part = part_mock

    # Mock PartDesign module
    partdesign_mock = MagicMock()
    freecad_mock.PartDesign = partdesign_mock

    # Mock Sketcher module
    sketcher_mock = MagicMock()
    freecad_mock.Sketcher = sketcher_mock

    # Inject into sys.modules
    sys.modules["FreeCAD"] = freecad_mock
    sys.modules["Part"] = part_mock
    sys.modules["PartDesign"] = partdesign_mock
    sys.modules["Sketcher"] = sketcher_mock

    yield freecad_mock

    # Cleanup
    for module in ["FreeCAD", "Part", "PartDesign", "Sketcher"]:
        if module in sys.modules:
            del sys.modules[module]


# ============================================================================
# Mock Redis
# ============================================================================


@pytest.fixture
def mock_redis():
    """
    Provide in-memory Redis using fakeredis.

    Fast, no infrastructure required, perfect for unit tests.
    """
    redis_client = FakeRedis(decode_responses=False)
    yield redis_client
    redis_client.flushall()


@pytest.fixture
def redis_client(mock_redis):
    """Alias for mock_redis for compatibility."""
    return mock_redis


# ============================================================================
# Mock LLM Provider
# ============================================================================


class MockLLMProvider:
    """
    Mock LLM provider that returns canned responses.

    Avoids actual API calls during testing while maintaining the same interface.
    """

    def __init__(self):
        self.call_count = 0
        self.last_prompt = None
        self.response_override = None

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate a canned response based on prompt content."""
        self.call_count += 1
        self.last_prompt = prompt

        # Use override if set
        if self.response_override:
            return self.response_override

        # Return canned responses based on prompt content
        if "plan" in prompt.lower() or "task" in prompt.lower():
            return self._get_planner_response()
        elif "generate" in prompt.lower() or "freecad" in prompt.lower():
            return self._get_generator_response()
        elif "validate" in prompt.lower() or "check" in prompt.lower():
            return self._get_validator_response()
        else:
            return self._get_default_response()

    def _get_planner_response(self) -> str:
        """Return mock planner response."""
        return json.dumps(
            {
                "task_graph_id": "tg_mock_001",
                "tasks": [
                    {
                        "id": "task_1",
                        "type": "create_sketch",
                        "description": "Create base sketch",
                        "dependencies": [],
                        "parameters": {"shape": "rectangle", "width": 10, "height": 10},
                    },
                    {
                        "id": "task_2",
                        "type": "extrude",
                        "description": "Extrude sketch to create 3D solid",
                        "dependencies": ["task_1"],
                        "parameters": {"length": 10},
                    },
                ],
                "reasoning": "Mock reasoning for task decomposition",
            }
        )

    def _get_generator_response(self) -> str:
        """Return mock generator response (FreeCAD script)."""
        return """import FreeCAD as App
import Part
import PartDesign

# Create document
doc = App.newDocument("MockDesign")

# Create body
body = doc.addObject("PartDesign::Body", "Body")

# Create sketch
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"

# Add rectangle geometry
sketch.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(10, 0, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(10, 0, 0), App.Vector(10, 10, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(10, 10, 0), App.Vector(0, 10, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(0, 10, 0), App.Vector(0, 0, 0)))

# Create pad
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = 10

doc.recompute()
print("CREATED_OBJECT: Body")
print("CREATED_OBJECT: Sketch")
print("CREATED_OBJECT: Pad")
"""

    def _get_validator_response(self) -> str:
        """Return mock validator response."""
        return json.dumps(
            {
                "is_valid": True,
                "overall_score": 0.85,
                "scores": {
                    "geometric_validity": 0.9,
                    "intent_match": 0.8,
                    "completeness": 0.85,
                    "best_practices": 0.85,
                },
                "issues": [],
                "suggestions": ["Consider adding fillets for smoother edges"],
                "reasoning": "Mock validation reasoning",
            }
        )

    def _get_default_response(self) -> str:
        """Return default mock response."""
        return "Mock LLM response"

    def set_response(self, response: str):
        """Override response for next call."""
        self.response_override = response

    def reset(self):
        """Reset provider state."""
        self.call_count = 0
        self.last_prompt = None
        self.response_override = None


@pytest.fixture
def mock_llm_provider():
    """Provide mock LLM provider for testing."""
    provider = MockLLMProvider()
    yield provider
    provider.reset()


@pytest.fixture
def mock_unified_llm_provider(mock_llm_provider):
    """
    Mock UnifiedLLMProvider for testing.

    Wraps MockLLMProvider to match UnifiedLLMProvider interface.
    """
    from ai_designer.core.llm_provider import UnifiedLLMProvider

    mock_provider = Mock(spec=UnifiedLLMProvider)
    mock_provider.generate = mock_llm_provider.generate
    mock_provider.call_count = 0

    return mock_provider


# ============================================================================
# Sample Test Data
# ============================================================================


@pytest.fixture
def sample_prompts(test_fixtures_dir):
    """Load sample user prompts from fixtures."""
    prompts_file = test_fixtures_dir / "sample_prompts.json"
    if prompts_file.exists():
        with open(prompts_file) as f:
            return json.load(f)

    # Fallback if file doesn't exist
    return {
        "simple": [
            "Create a 10x10x10mm cube",
            "Design a cylinder with diameter 20mm and height 30mm",
            "Make a rectangular box 50x30x20mm",
        ],
        "intermediate": [
            "Create an L-bracket 50x50mm with 10mm thickness",
            "Design a mounting bracket with 4 holes",
            "Build a washer with outer diameter 20mm, inner diameter 10mm, thickness 2mm",
        ],
        "complex": [
            "Create a gear wheel with 20 teeth and 50mm diameter",
            "Design a flange with 6 mounting holes arranged in a circle",
            "Build a threaded bolt M10x30",
        ],
    }


@pytest.fixture
def sample_scripts(test_fixtures_dir):
    """Load sample FreeCAD scripts from fixtures."""
    scripts_file = test_fixtures_dir / "sample_scripts.py"
    if scripts_file.exists():
        with open(scripts_file) as f:
            return f.read()

    # Fallback
    return """
# Sample box script
import FreeCAD as App
import Part

doc = App.newDocument("Box")
box = Part.makeBox(10, 10, 10)
Part.show(box)
doc.recompute()
"""


@pytest.fixture
def sample_validation_result():
    """Provide sample validation result."""
    return {
        "is_valid": True,
        "overall_score": 0.85,
        "scores": {
            "geometric_validity": 0.9,
            "intent_match": 0.8,
            "completeness": 0.85,
            "best_practices": 0.85,
        },
        "issues": [],
        "suggestions": ["Add fillets"],
        "reasoning": "Design meets requirements",
    }


# ============================================================================
# UUID Fixtures
# ============================================================================


@pytest.fixture
def mock_request_id():
    """Provide consistent UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_request_id():
    """Provide sample request ID string."""
    return "12345678-1234-5678-1234-567812345678"


# ============================================================================
# Agent Fixtures
# ============================================================================


@pytest.fixture
def mock_planner_agent(mock_llm_provider):
    """Mock PlannerAgent for testing."""
    from ai_designer.agents.planner import PlannerAgent

    # Create mock that uses our mock LLM provider
    mock_agent = Mock(spec=PlannerAgent)
    mock_agent.generate_plan = AsyncMock(
        return_value={"task_graph_id": "tg_001", "tasks": [], "reasoning": "Mock plan"}
    )

    return mock_agent


@pytest.fixture
def mock_generator_agent(mock_llm_provider):
    """Mock GeneratorAgent for testing."""
    from ai_designer.agents.generator import GeneratorAgent

    mock_agent = Mock(spec=GeneratorAgent)
    mock_agent.generate_script = AsyncMock(return_value="# Mock script")

    return mock_agent


@pytest.fixture
def mock_validator_agent(mock_llm_provider):
    """Mock ValidatorAgent for testing."""
    from ai_designer.agents.validator import ValidatorAgent

    mock_agent = Mock(spec=ValidatorAgent)
    mock_agent.validate = AsyncMock(
        return_value={
            "is_valid": True,
            "overall_score": 0.85,
            "scores": {},
            "issues": [],
            "suggestions": [],
        }
    )

    return mock_agent


# ============================================================================
# Executor Fixtures
# ============================================================================


@pytest.fixture
def mock_freecad_executor():
    """Mock FreeCADExecutor for testing."""
    from ai_designer.agents.executor import FreeCADExecutor
    from ai_designer.sandbox.result import ExecutionResult, ExecutionStatus

    mock_executor = Mock(spec=FreeCADExecutor)
    mock_executor.execute = AsyncMock(
        return_value=ExecutionResult(
            success=True,
            status=ExecutionStatus.SUCCESS,
            created_objects=["Body", "Sketch", "Pad"],
            output="Execution successful",
            execution_time=1.5,
        )
    )

    return mock_executor


# ============================================================================
# Pipeline Fixtures
# ============================================================================


@pytest.fixture
def mock_pipeline_executor(
    mock_planner_agent,
    mock_generator_agent,
    mock_validator_agent,
    mock_freecad_executor,
):
    """Mock PipelineExecutor with all dependencies."""
    from ai_designer.orchestration.pipeline import PipelineExecutor

    mock_pipeline = Mock(spec=PipelineExecutor)
    mock_pipeline.execute = AsyncMock()

    return mock_pipeline


# ============================================================================
# Cleanup
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test(tmp_path):
    """Cleanup after each test."""
    yield
    # Cleanup is automatic with tmp_path

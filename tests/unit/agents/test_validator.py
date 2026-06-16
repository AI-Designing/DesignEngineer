"""Tests for the Validator Agent."""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_designer.agents.validator import ValidatorAgent
from ai_designer.llm.provider import LLMResponse, UnifiedLLMProvider
from ai_designer.schemas.design_state import AgentType, DesignRequest
from ai_designer.schemas.task_graph import TaskGraph, TaskNode
from ai_designer.schemas.validation import (
    GeometricValidation,
    LLMReviewResult,
    SemanticValidation,
    ValidationResult,
)


class TestValidatorAgentInit:
    """Test ValidatorAgent initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        validator = ValidatorAgent(llm_provider=mock_provider)

        assert validator.llm_provider == mock_provider
        assert validator.agent_type == AgentType.VALIDATOR
        assert validator.default_temperature == 0.3
        assert validator.pass_threshold == 0.8
        assert validator.refine_threshold == 0.4

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        validator = ValidatorAgent(
            llm_provider=mock_provider,
            temperature=0.5,
            pass_threshold=0.85,
            refine_threshold=0.5,
        )

        assert validator.default_temperature == 0.5
        assert validator.pass_threshold == 0.85
        assert validator.refine_threshold == 0.5

    def test_init_invalid_temperature(self):
        """Test initialization with invalid temperature."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        with pytest.raises(ValueError, match="Temperature must be in"):
            ValidatorAgent(llm_provider=mock_provider, temperature=1.5)

    def test_init_invalid_thresholds(self):
        """Test initialization with invalid threshold order."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        with pytest.raises(ValueError, match="Refine threshold.*must be <="):
            ValidatorAgent(
                llm_provider=mock_provider, pass_threshold=0.6, refine_threshold=0.8
            )


class TestValidatorAgentValidation:
    """Test ValidatorAgent validation logic."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        mock = MagicMock(spec=UnifiedLLMProvider)
        mock.default_model = "gpt-4o"
        return mock

    @pytest.fixture
    def validator(self, mock_provider):
        """Create a validator instance."""
        return ValidatorAgent(llm_provider=mock_provider)

    @pytest.fixture
    def design_request(self):
        """Create a sample design request."""
        return DesignRequest(user_prompt="Create a box 10x10x10mm with a 2mm hole")

    @pytest.fixture
    def simple_task_graph(self):
        """Create a simple task graph."""
        request_id = uuid4()
        graph = TaskGraph(request_id=request_id)

        task_1 = TaskNode(
            task_id="task_1",
            operation_type="create_box",
            description="Create box",
            parameters={"length": 10.0, "width": 10.0, "height": 10.0},
        )
        task_2 = TaskNode(
            task_id="task_2",
            operation_type="create_cylinder",
            description="Create hole",
            parameters={"radius": 1.0, "height": 12.0},
        )
        task_3 = TaskNode(
            task_id="task_3",
            operation_type="boolean_cut",
            description="Cut hole",
            parameters={},
        )

        graph.add_task(task_1)
        graph.add_task(task_2)
        graph.add_task(task_3)

        return graph

    @pytest.fixture
    def generated_scripts(self):
        """Sample generated scripts."""
        return {
            "task_1": """import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
box = doc.addObject("Part::Box", "Box")
box.Length = 10.0
box.Width = 10.0
box.Height = 10.0
doc.recompute()
# RESULT: box""",
            "task_2": """import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
cylinder = doc.addObject("Part::Cylinder", "Cylinder")
cylinder.Radius = 1.0
cylinder.Height = 12.0
doc.recompute()
# RESULT: cylinder""",
            "task_3": """import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
base = doc.getObject("box")
tool = doc.getObject("cylinder")
cut_result = doc.addObject("Part::Cut", "Cut")
cut_result.Base = base
cut_result.Tool = tool
doc.recompute()
# RESULT: cut_result""",
        }

    @pytest.fixture
    def successful_execution(self):
        """Sample successful execution result."""
        return {
            "object_count": 3,
            "total_volume": 900.0,  # 10^3 - π*1^2*10 ≈ 900
            "bounding_box": {"length": 10.0, "width": 10.0, "height": 10.0},
            "is_manifold": True,
            "has_invalid_faces": False,
            "has_self_intersections": False,
            "state": {
                "success": True,
                "objects": [
                    {"type": "Part::Box", "name": "Box"},
                    {"type": "Part::Cylinder", "name": "Cylinder"},
                    {"type": "Part::Cut", "name": "Cut"},
                ],
            },
        }

    @pytest.fixture
    def llm_review_response(self):
        """Sample LLM review response."""
        return {
            "overall_assessment": "Good quality design matching requirements",
            "quality_score": 0.85,
            "strengths": [
                "Correctly implements box dimensions",
                "Boolean cut properly configured",
            ],
            "weaknesses": ["Cylinder could be better centered"],
            "suggestions": ["Add positioning parameters for hole centering"],
            "script_quality_score": 0.8,
            "code_issues": [],
        }

    @pytest.mark.asyncio
    async def test_validate_successful_design(
        self,
        validator,
        mock_provider,
        design_request,
        simple_task_graph,
        generated_scripts,
        successful_execution,
        llm_review_response,
    ):
        """Test validation of a successful design."""
        mock_provider.agenerate = AsyncMock(
            return_value=LLMResponse(
                content=json.dumps(llm_review_response),
                model="gpt-4o",
                provider="openai",
            )
        )

        result = await validator.validate(
            design_request, simple_task_graph, generated_scripts, successful_execution
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert result.geometric_score is not None
        assert result.semantic_score is not None
        assert result.overall_score is not None
        assert result.overall_score >= validator.pass_threshold
        assert not result.should_refine

    @pytest.mark.asyncio
    async def test_validate_needs_refinement(
        self,
        validator,
        mock_provider,
        design_request,
        simple_task_graph,
        generated_scripts,
    ):
        """Test validation that suggests refinement."""
        # Use imperfect execution result to lower geometric score
        mediocre_execution = {
            "object_count": 3,
            "total_volume": 900.0,
            "bounding_box": {"length": 10.0, "width": 10.0, "height": 10.0},
            "is_manifold": True,
            "has_invalid_faces": True,  # Has some geometric issues
            "has_self_intersections": False,
            "state": {
                "success": True,
                "objects": [
                    {"type": "Part::Box", "name": "Box"},
                    {"type": "Part::Cylinder", "name": "Cylinder"},
                    {"type": "Part::Cut", "name": "Cut"},
                ],
            },
        }

        # Lower quality review
        poor_review = {
            "overall_assessment": "Fair quality, needs improvement",
            "quality_score": 0.6,
            "strengths": ["Basic structure correct"],
            "weaknesses": ["Missing features", "Dimensions off"],
            "suggestions": ["Add missing fillet", "Fix dimensions"],
            "script_quality_score": 0.5,
            "code_issues": ["Poor variable names"],
        }

        mock_provider.agenerate = AsyncMock(
            return_value=LLMResponse(
                content=json.dumps(poor_review), model="gpt-4o", provider="openai"
            )
        )

        result = await validator.validate(
            design_request, simple_task_graph, generated_scripts, mediocre_execution
        )

        # Should not pass but should suggest refinement
        assert not result.is_valid
        assert result.should_refine
        assert result.overall_score >= validator.refine_threshold
        assert result.overall_score < validator.pass_threshold
        assert len(result.refinement_suggestions) > 0

    @pytest.mark.asyncio
    async def test_validate_execution_error(
        self,
        validator,
        mock_provider,
        design_request,
        simple_task_graph,
        generated_scripts,
        llm_review_response,
    ):
        """Test validation with execution error."""
        failed_execution = {"error": "RuntimeError: Invalid object reference"}

        mock_provider.agenerate = AsyncMock(
            return_value=LLMResponse(
                content=json.dumps(llm_review_response),
                model="gpt-4o",
                provider="openai",
            )
        )

        result = await validator.validate(
            design_request, simple_task_graph, generated_scripts, failed_execution
        )

        assert not result.is_valid
        assert result.geometric is not None
        assert not result.geometric.is_valid
        assert len(result.geometric.issues) > 0

    @pytest.mark.asyncio
    async def test_validate_without_execution_result(
        self,
        validator,
        mock_provider,
        design_request,
        simple_task_graph,
        generated_scripts,
        llm_review_response,
    ):
        """Test validation without execution results."""
        mock_provider.agenerate = AsyncMock(
            return_value=LLMResponse(
                content=json.dumps(llm_review_response),
                model="gpt-4o",
                provider="openai",
            )
        )

        result = await validator.validate(
            design_request, simple_task_graph, generated_scripts, None
        )

        assert result.geometric is None
        assert result.geometric_score is None
        assert result.semantic is not None
        assert result.llm_review is not None


class TestValidatorAgentGeometric:
    """Test geometric validation logic."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)
        return ValidatorAgent(llm_provider=mock_provider)

    @pytest.fixture
    def simple_task_graph(self):
        """Create a simple task graph."""
        graph = TaskGraph(request_id=uuid4())
        graph.add_task(
            TaskNode(
                task_id="task_1",
                operation_type="create_box",
                description="Box",
                parameters={},
            )
        )
        return graph

    def test_validate_geometry_success(self, validator, simple_task_graph):
        """Test successful geometric validation."""
        execution_result = {
            "object_count": 1,
            "total_volume": 1000.0,
            "bounding_box": {"length": 10.0, "width": 10.0, "height": 10.0},
            "is_manifold": True,
            "has_invalid_faces": False,
            "has_self_intersections": False,
        }

        geo_validation = validator._validate_geometry(
            execution_result, simple_task_graph
        )

        assert geo_validation.is_valid
        assert geo_validation.has_solid_bodies
        assert geo_validation.body_count == 1
        assert geo_validation.total_volume == 1000.0

    def test_validate_geometry_no_objects(self, validator, simple_task_graph):
        """Test geometric validation with no objects."""
        execution_result = {
            "object_count": 0,
            "total_volume": 0.0,
        }

        geo_validation = validator._validate_geometry(
            execution_result, simple_task_graph
        )

        assert not geo_validation.is_valid
        assert not geo_validation.has_solid_bodies
        assert any("No solid bodies" in issue for issue in geo_validation.issues)

    def test_validate_geometry_invalid_volume(self, validator, simple_task_graph):
        """Test geometric validation with invalid volume."""
        execution_result = {
            "object_count": 1,
            "total_volume": -10.0,  # Negative volume
        }

        geo_validation = validator._validate_geometry(
            execution_result, simple_task_graph
        )

        assert not geo_validation.is_valid
        assert "Invalid volume" in str(geo_validation.issues)

    def test_validate_geometry_nested_geometry_key(self, validator, simple_task_graph):
        """Validator reads canonical ``geometry`` from execution_result."""
        execution_result = {
            "success": True,
            "geometry": {
                "feedback_version": "1",
                "object_count": 1,
                "total_volume_mm3": 125.0,
                "bounding_box": {"length": 5.0, "width": 5.0, "height": 5.0},
                "is_manifold": True,
                "has_invalid_faces": False,
                "has_self_intersections": False,
            },
        }
        geo = validator._validate_geometry(execution_result, simple_task_graph)
        assert geo.is_valid
        assert geo.body_count == 1
        assert geo.total_volume == 125.0
        assert geo.bounding_box["length"] == 5.0

    def test_validate_geometry_success_missing_volume_info(
        self, validator, simple_task_graph
    ):
        """Successful run without measured volume should not assume volume is zero."""
        execution_result = {
            "success": True,
            "object_count": 1,
            "geometry_unavailable_reason": "sandbox execution",
        }
        geo = validator._validate_geometry(execution_result, simple_task_graph)
        assert geo.total_volume is None
        assert any("Geometry metrics unavailable" in i for i in geo.issues)

    def test_execution_error_message_joins_list(self, validator):
        assert validator._execution_error_message({"error": ["a", "b"]}) == "a; b"

    def test_calculate_geometric_score(self, validator):
        """Test geometric score calculation."""
        # Perfect geometry
        perfect = GeometricValidation(
            is_valid=True,
            has_solid_bodies=True,
            is_manifold=True,
            has_invalid_faces=False,
            has_self_intersections=False,
        )
        assert validator._calculate_geometric_score(perfect) == 1.0

        # Invalid geometry
        invalid = GeometricValidation(is_valid=False, has_solid_bodies=False)
        assert validator._calculate_geometric_score(invalid) == 0.0


class TestValidatorAgentSemantic:
    """Test semantic validation logic."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)
        return ValidatorAgent(llm_provider=mock_provider)

    def test_validate_semantics_full_match(self, validator):
        """Test semantic validation with perfect feature match."""
        request = DesignRequest(user_prompt="Create a box with a hole")

        graph = TaskGraph(request_id=uuid4())
        graph.add_task(
            TaskNode(
                task_id="t1",
                operation_type="create_box",
                description="Box",
                parameters={},
            )
        )
        graph.add_task(
            TaskNode(
                task_id="t2",
                operation_type="create_cylinder",
                description="Hole",
                parameters={},
            )
        )
        graph.add_task(
            TaskNode(
                task_id="t3",
                operation_type="boolean_cut",
                description="Cut",
                parameters={},
            )
        )

        scripts = {
            "t1": "box = doc.addObject('Part::Box', 'Box')",
            "t2": "cyl = doc.addObject('Part::Cylinder', 'Cyl')",
            "t3": "cut = doc.addObject('Part::Cut', 'Cut')",
        }

        execution = {
            "success": True,
            "bounding_box": {"length": 10.0, "width": 10.0, "height": 10.0},
            "state": {
                "success": True,
                "objects": [
                    {"type": "Part::Box", "name": "Box"},
                    {"type": "Part::Cylinder", "name": "Cyl"},
                    {"type": "Part::Cut", "name": "Cut"},
                ],
            },
        }
        semantic = validator._validate_semantics(request, graph, scripts, execution)

        assert semantic.is_valid
        assert semantic.confidence_score >= 0.9
        assert "create_box" in semantic.detected_features
        assert "create_cylinder" in semantic.detected_features
        assert "boolean_cut" in semantic.detected_features

    def test_validate_semantics_missing_features(self, validator):
        """Test semantic validation with missing features."""
        request = DesignRequest(user_prompt="Create a box with rounded edges")

        graph = TaskGraph(request_id=uuid4())
        graph.add_task(
            TaskNode(
                task_id="t1",
                operation_type="create_box",
                description="Box",
                parameters={},
            )
        )
        graph.add_task(
            TaskNode(
                task_id="t2",
                operation_type="fillet",
                description="Fillet",
                parameters={},
            )
        )

        scripts = {
            "t1": "box = doc.addObject('Part::Box', 'Box')",
            "t2": "# No fillet code generated",  # Missing fillet
        }

        semantic = validator._validate_semantics(request, graph, scripts, None)

        # Should detect the issue
        assert len(semantic.issues) > 0
        assert semantic.confidence_score < 1.0

    def test_semantic_wrong_bbox_vs_planned_dimensions(self, validator):
        """Planned box 10mm but geometry bbox much larger should fail dimension check."""
        request = DesignRequest(user_prompt="Create a box")
        graph = TaskGraph(request_id=uuid4())
        graph.add_task(
            TaskNode(
                task_id="t1",
                operation_type="create_box",
                description="Box",
                parameters={"length": 10.0, "width": 10.0, "height": 10.0},
            )
        )
        scripts = {"t1": "box = doc.addObject('Part::Box', 'Box')"}
        execution = {
            "success": True,
            "bounding_box": {"length": 100.0, "width": 100.0, "height": 100.0},
            "state": {
                "success": True,
                "objects": [{"type": "Part::Box", "name": "Box"}],
            },
        }
        semantic = validator._validate_semantics(request, graph, scripts, execution)
        assert any("mismatch" in i.lower() for i in semantic.issues)
        assert semantic.confidence_score < 0.6

    def test_semantic_missing_boolean_ignores_script_only_when_state_present(
        self, validator
    ):
        """State without Part::Cut should fail boolean requirement despite 'Cut' in code."""
        request = DesignRequest(user_prompt="Cut a hole")
        graph = TaskGraph(request_id=uuid4())
        graph.add_task(
            TaskNode(
                task_id="t1",
                operation_type="create_box",
                description="Base",
                parameters={},
            )
        )
        graph.add_task(
            TaskNode(
                task_id="t2",
                operation_type="boolean_cut",
                description="Hole",
                parameters={},
            )
        )
        scripts = {
            "t1": "box = doc.addObject('Part::Box', 'Box')",
            "t2": "# fake: doc.addObject('Part::Cut' in comment only",
        }
        execution = {
            "success": True,
            "state": {
                "success": True,
                "objects": [{"type": "Part::Box", "name": "Box"}],
            },
        }
        semantic = validator._validate_semantics(request, graph, scripts, execution)
        assert "boolean_cut" in semantic.requirements_missing
        assert semantic.confidence_score < 0.6

    def test_semantic_data_gap_when_no_bbox_but_dimensions_planned(self, validator):
        """Explicit box dims without bbox must not claim dimensional pass."""
        request = DesignRequest(user_prompt="10x10x10 mm cube")
        graph = TaskGraph(request_id=uuid4())
        graph.add_task(
            TaskNode(
                task_id="t1",
                operation_type="create_box",
                description="Box",
                parameters={"length": 10.0, "width": 10.0, "height": 10.0},
            )
        )
        scripts = {"t1": "Part.makeBox(10,10,10)"}
        execution = {
            "success": True,
            "state": {"success": True, "objects": [{"type": "Part::Box", "name": "B"}]},
        }
        semantic = validator._validate_semantics(request, graph, scripts, execution)
        assert any("bounding box" in g.lower() for g in semantic.data_gaps)
        assert any("unknown" in n for n in semantic.structured_notes)


class TestValidatorAgentHelpers:
    """Test ValidatorAgent helper methods."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)
        return ValidatorAgent(llm_provider=mock_provider)

    def test_parse_review_response_valid_json(self, validator):
        """Test parsing valid JSON review."""
        response = json.dumps(
            {
                "overall_assessment": "Good design",
                "quality_score": 0.85,
                "strengths": ["Well structured"],
                "weaknesses": [],
                "suggestions": [],
            }
        )

        parsed = validator._parse_review_response(response)

        assert parsed["quality_score"] == 0.85
        assert parsed["overall_assessment"] == "Good design"

    def test_parse_review_response_with_markdown(self, validator):
        """Test parsing JSON wrapped in markdown."""
        response = (
            '```json\n{"quality_score": 0.9, "overall_assessment": "Excellent"}\n```'
        )

        parsed = validator._parse_review_response(response)

        assert parsed["quality_score"] == 0.9

    def test_parse_review_response_invalid_json(self, validator):
        """Test parsing invalid JSON returns fallback."""
        response = "This is not JSON at all!"

        parsed = validator._parse_review_response(response)

        assert "overall_assessment" in parsed
        assert parsed["quality_score"] == 0.5  # Fallback value

    def test_make_validation_decision_pass(self, validator):
        """Test validation decision for passing design."""
        result = ValidationResult(request_id="test", is_valid=False)
        result.overall_score = 0.85

        decision = validator._make_validation_decision(result)

        assert decision is True

    def test_make_validation_decision_fail(self, validator):
        """Test validation decision for failing design."""
        result = ValidationResult(request_id="test", is_valid=False)
        result.overall_score = 0.5

        decision = validator._make_validation_decision(result)

        assert decision is False

    def test_generate_refinement_suggestions(self, validator):
        """Test generating refinement suggestions."""
        result = ValidationResult(request_id="test", is_valid=False)

        result.geometric = GeometricValidation(
            is_valid=False, issues=["Issue 1", "Issue 2"]
        )
        result.semantic = SemanticValidation(
            is_valid=False,
            confidence_score=0.6,
            issues=["Semantic issue"],
            requirements_met=[],
            requirements_missing=["fillet"],
            detected_features=[],
            expected_features=[],
        )
        result.llm_review = LLMReviewResult(
            overall_assessment="Needs work",
            quality_score=0.6,
            suggestions=["Improve X", "Fix Y"],
        )

        suggestions = validator._generate_refinement_suggestions(result)

        assert len(suggestions) > 0
        assert len(suggestions) <= 5  # Should be limited

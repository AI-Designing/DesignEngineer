"""
Unit tests for HeadlessRunner.

Tests headless FreeCAD execution with mocked subprocess calls.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from ai_designer.freecad.headless_runner import HeadlessRunner, get_execution_semaphore
from ai_designer.sandbox.result import ExecutionStatus


@pytest.fixture
def temp_outputs_dir(tmp_path):
    """Create temporary outputs directory."""
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    return outputs


@pytest.fixture
def mock_freecad_cmd():
    """Mock FreeCAD command path."""
    return "/usr/bin/freecadcmd"


@pytest.fixture
def headless_runner(mock_freecad_cmd, temp_outputs_dir):
    """Create HeadlessRunner instance with mocked command."""
    with patch.object(
        HeadlessRunner, "_detect_freecad_cmd", return_value=mock_freecad_cmd
    ):
        with patch.object(
            HeadlessRunner, "_detect_freecad_version", return_value="0.21"
        ):
            runner = HeadlessRunner(
                freecad_cmd=mock_freecad_cmd, outputs_dir=temp_outputs_dir
            )
            return runner


class TestHeadlessRunner:
    """Test cases for HeadlessRunner."""

    def test_initialization(self, headless_runner, mock_freecad_cmd, temp_outputs_dir):
        """Test HeadlessRunner initialization."""
        assert headless_runner.freecad_cmd == mock_freecad_cmd
        assert headless_runner.outputs_dir == temp_outputs_dir
        assert headless_runner.freecad_version == "0.21"
        assert temp_outputs_dir.exists()

    def test_semaphore_creation(self):
        """Test global semaphore creation."""
        semaphore = get_execution_semaphore(max_concurrent=4)
        assert isinstance(semaphore, asyncio.Semaphore)
        assert semaphore._value == 4

    @pytest.mark.asyncio
    async def test_execute_script_success(self, headless_runner):
        """Test successful script execution."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """
CREATED_OBJECT: Box
CREATED_OBJECT: Cylinder
Execution completed successfully
"""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = await headless_runner.execute_script(
                script="box = Part.makeBox(10, 10, 10)",
                prompt="Create a box",
                request_id="test-123",
            )

        assert result.success is True
        assert result.status == ExecutionStatus.SUCCESS
        assert len(result.created_objects) == 2
        assert "Box" in result.created_objects
        assert "Cylinder" in result.created_objects
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_execute_script_with_error(self, headless_runner):
        """Test script execution with errors."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Syntax error in script"

        with patch("subprocess.run", return_value=mock_result):
            result = await headless_runner.execute_script(
                script="invalid python code",
                prompt="Test error",
                request_id="test-error",
            )

        assert result.success is False
        assert result.status == ExecutionStatus.ERROR
        assert "Syntax error" in result.error

    @pytest.mark.asyncio
    async def test_execute_script_with_warnings(self, headless_runner):
        """Test script execution with warnings."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """
CREATED_OBJECT: Box
WARNING: Object may have constraints issues
Execution completed
"""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = await headless_runner.execute_script(
                script="box = Part.makeBox(10, 10, 10)",
                prompt="Create box with warnings",
                request_id="test-warning",
            )

        assert result.success is True
        assert len(result.warnings) > 0
        assert any("constraints" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_retry_logic_with_recompute_error(self, headless_runner):
        """Test retry logic for recompute errors."""
        # First attempt: recompute error
        error_result = Mock()
        error_result.returncode = 1
        error_result.stdout = ""
        error_result.stderr = "ERROR: Recompute failed for object Box"

        # Second attempt: success
        success_result = Mock()
        success_result.returncode = 0
        success_result.stdout = "CREATED_OBJECT: Box\nRECOMPUTE_SUCCESS"
        success_result.stderr = ""

        with patch("subprocess.run", side_effect=[error_result, success_result]):
            with patch("asyncio.sleep"):  # Mock sleep to speed up test
                result = await headless_runner.execute_script(
                    script="box = Part.makeBox(10, 10, 10)",
                    prompt="Test retry",
                    request_id="test-retry",
                    max_retries=3,
                )

        assert result.success is True
        assert "Box" in result.created_objects

    @pytest.mark.asyncio
    async def test_timeout_handling(self, headless_runner):
        """Test timeout handling."""
        import subprocess

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="freecadcmd", timeout=30),
        ):
            result = await headless_runner.execute_script(
                script="# Long running script",
                prompt="Test timeout",
                request_id="test-timeout",
                timeout=30,
            )

        assert result.success is False
        assert result.status == ExecutionStatus.TIMEOUT
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_output_parsing(self, headless_runner):
        """Test output parsing for objects and errors."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """
CREATED_OBJECT: Box001
CREATED_OBJECT: Cylinder001
WARNING: Mesh quality may be low
RECOMPUTE_SUCCESS
"""
        mock_result.stderr = "ERROR: Minor issue detected"

        with patch("subprocess.run", return_value=mock_result):
            result = await headless_runner.execute_script(
                script="test",
                prompt="Test parsing",
                request_id="test-parse",
            )

        assert len(result.created_objects) == 2
        assert "Box001" in result.created_objects
        assert "Cylinder001" in result.created_objects
        assert len(result.warnings) > 0
        assert any("Mesh quality" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_metadata_saving(self, headless_runner, temp_outputs_dir):
        """Test metadata JSON saving."""
        request_id = str(uuid4())
        prompt = "Create test object"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "CREATED_OBJECT: Box"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = await headless_runner.execute_script(
                script="box = Part.makeBox(10, 10, 10)",
                prompt=prompt,
                request_id=request_id,
            )

        # Check metadata file exists
        metadata_files = list(temp_outputs_dir.glob("*_metadata.json"))
        assert len(metadata_files) > 0

        # Verify metadata content
        metadata = json.loads(metadata_files[0].read_text())
        assert metadata["request_id"] == request_id
        assert metadata["prompt"] == prompt
        assert "Box" in metadata["created_objects"]
        assert "timestamp" in metadata
        assert "freecad_version" in metadata

    @pytest.mark.asyncio
    async def test_script_template_generation(self, headless_runner):
        """Test script template generation."""
        script = "box = Part.makeBox(10, 10, 10)"
        template = headless_runner._create_script_template(script)

        assert "import FreeCAD" in template
        assert "import Part" in template
        assert script in template
        assert "CREATED_OBJECT:" in template
        assert "ERROR:" in template
        assert "doc.recompute()" in template

    def test_version_detection(self):
        """Test FreeCAD version detection."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "FreeCAD 0.21.2, Libs: 0.21.2\n"

        with patch("subprocess.run", return_value=mock_result):
            runner = HeadlessRunner(freecad_cmd="freecadcmd")
            assert runner.freecad_version == "0.21.2"

    def test_command_detection_fallback(self):
        """Test FreeCAD command detection fallback."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            runner = HeadlessRunner()
            assert runner.freecad_cmd == "freecadcmd"


class TestStateExtractor:
    """Test cases for StateExtractor."""

    @pytest.fixture
    def state_extractor(self, mock_freecad_cmd):
        """Create StateExtractor instance."""
        from ai_designer.freecad.state_extractor import StateExtractor

        return StateExtractor(freecad_cmd=mock_freecad_cmd)

    @pytest.mark.asyncio
    async def test_extract_state_success(self, state_extractor, tmp_path):
        """Test successful state extraction."""
        doc_path = tmp_path / "test.FCStd"
        doc_path.touch()

        state_data = {
            "success": True,
            "document_name": "test",
            "object_count": 2,
            "objects": [
                {"name": "Box", "type": "Part::Box", "label": "Box"},
                {"name": "Cylinder", "type": "Part::Cylinder", "label": "Cylinder"},
            ],
            "feature_tree": {},
            "recompute_errors": [],
        }

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            f"STATE_JSON_START\n{json.dumps(state_data)}\nSTATE_JSON_END"
        )
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            state = state_extractor.extract_state(doc_path)

        assert state["success"] is True
        assert state["object_count"] == 2
        assert len(state["objects"]) == 2

    @pytest.mark.asyncio
    async def test_extract_state_missing_file(self, state_extractor, tmp_path):
        """Test state extraction with missing file."""
        doc_path = tmp_path / "nonexistent.FCStd"

        state = state_extractor.extract_state(doc_path)

        assert state["success"] is False
        assert "not found" in state["error"].lower()

    @pytest.mark.asyncio
    async def test_extract_state_timeout(self, state_extractor, tmp_path):
        """Test state extraction timeout."""
        import subprocess

        doc_path = tmp_path / "test.FCStd"
        doc_path.touch()

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="freecadcmd", timeout=30),
        ):
            state = state_extractor.extract_state(doc_path, timeout=30)

        assert state["success"] is False
        assert "timeout" in state["error"].lower()

    def test_feature_tree_hierarchy(self, state_extractor):
        """Test feature tree hierarchy building."""
        feature_tree = {
            "Box": {
                "label": "Box",
                "type": "Part::Box",
                "parents": [],
                "children": ["Fillet"],
            },
            "Fillet": {
                "label": "Fillet",
                "type": "Part::Fillet",
                "parents": ["Box"],
                "children": [],
            },
        }

        hierarchy = state_extractor.get_feature_tree_hierarchy(feature_tree)

        assert hierarchy["total_objects"] == 2
        assert hierarchy["root_count"] == 1
        assert len(hierarchy["roots"]) == 1
        assert hierarchy["roots"][0]["name"] == "Box"
        assert len(hierarchy["roots"][0]["children"]) == 1

    def test_extract_object_dimensions(self, state_extractor):
        """Test object dimensions extraction."""
        objects = [
            {
                "name": "Box",
                "type": "Part::Box",
                "bbox": {
                    "xmin": 0,
                    "ymin": 0,
                    "zmin": 0,
                    "xmax": 10,
                    "ymax": 10,
                    "zmax": 10,
                },
            },
            {
                "name": "Cylinder",
                "type": "Part::Cylinder",
                "bbox": {
                    "xmin": -5,
                    "ymin": -5,
                    "zmin": 0,
                    "xmax": 5,
                    "ymax": 5,
                    "zmax": 20,
                },
            },
        ]

        dimensions = state_extractor.extract_object_dimensions(objects)

        assert dimensions["total_objects"] == 2
        assert dimensions["objects_with_bbox"] == 2
        assert dimensions["overall_bbox"]["xmin"] == -5
        assert dimensions["overall_bbox"]["xmax"] == 10
        assert dimensions["overall_bbox"]["zmax"] == 20
        assert "Part::Box" in dimensions["by_type"]
        assert dimensions["by_type"]["Part::Box"] == 1


class TestExportMethods:
    """Test cases for export methods."""

    @pytest.fixture
    def headless_runner_with_mocks(self, headless_runner):
        """HeadlessRunner with export mocks."""
        return headless_runner

    @pytest.mark.asyncio
    async def test_export_step(self, headless_runner_with_mocks, tmp_path):
        """Test STEP export."""
        doc_path = tmp_path / "test.FCStd"
        doc_path.touch()
        output_path = tmp_path / "test.step"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = f"EXPORT_SUCCESS: {output_path}"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists", return_value=True):
                result_path = await headless_runner_with_mocks.export_step(
                    doc_path, output_path
                )

        assert result_path == output_path

    @pytest.mark.asyncio
    async def test_export_stl(self, headless_runner_with_mocks, tmp_path):
        """Test STL export with resolution."""
        doc_path = tmp_path / "test.FCStd"
        doc_path.touch()
        output_path = tmp_path / "test.stl"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = f"EXPORT_SUCCESS: {output_path}"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists", return_value=True):
                result_path = await headless_runner_with_mocks.export_stl(
                    doc_path, output_path, resolution=0.05
                )

        assert result_path == output_path

    @pytest.mark.asyncio
    async def test_export_fcstd(self, headless_runner_with_mocks, tmp_path):
        """Test FCStd copy."""
        doc_path = tmp_path / "test.FCStd"
        doc_path.write_text("test content")
        output_path = tmp_path / "output" / "test.FCStd"

        result_path = await headless_runner_with_mocks.export_fcstd(
            doc_path, output_path
        )

        assert result_path == output_path
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_export_all_formats(self, headless_runner_with_mocks, tmp_path):
        """Test multi-format export."""
        doc_path = tmp_path / "test.FCStd"
        doc_path.write_text("test content")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "EXPORT_SUCCESS"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists", return_value=True):
                results = await headless_runner_with_mocks.export_all_formats(
                    doc_path=doc_path,
                    output_dir=tmp_path / "exports",
                    formats=["step", "stl", "fcstd"],
                )

        assert "step" in results
        assert "stl" in results
        assert "fcstd" in results
        assert results["fcstd"] is not None  # FCStd copy should succeed

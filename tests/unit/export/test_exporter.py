"""
Unit tests for CADExporter.

Tests export functionality with metadata tracking, caching, and multi-format support.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from ai_designer.export.exporter import CADExporter, ExportMetadata, ExportResult
from ai_designer.freecad.headless_runner import HeadlessRunner


@pytest.fixture
def temp_outputs_dir(tmp_path):
    """Create temporary outputs directory."""
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    return outputs


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture
def mock_headless_runner():
    """Create mock HeadlessRunner."""
    runner = Mock(spec=HeadlessRunner)
    runner.freecad_version = "0.21"
    runner.outputs_dir = Path("outputs")

    # Mock export methods as async
    runner.export_step = AsyncMock(return_value=Path("outputs/test.step"))
    runner.export_stl = AsyncMock(return_value=Path("outputs/test.stl"))
    runner.export_fcstd = AsyncMock(return_value=Path("outputs/test.FCStd"))

    return runner


@pytest.fixture
def cad_exporter(mock_headless_runner, temp_outputs_dir, temp_cache_dir):
    """Create CADExporter instance."""
    exporter = CADExporter(
        headless_runner=mock_headless_runner,
        outputs_dir=str(temp_outputs_dir),
        enable_cache=True,
        cache_dir=str(temp_cache_dir),
    )
    return exporter


class TestCADExporter:
    """Test cases for CADExporter."""

    def test_initialization(self, cad_exporter, temp_outputs_dir, temp_cache_dir):
        """Test CADExporter initialization."""
        assert cad_exporter.outputs_dir == temp_outputs_dir
        assert cad_exporter.cache_dir == temp_cache_dir
        assert cad_exporter.enable_cache is True
        assert temp_cache_dir.exists()
        assert cad_exporter.cache_index_path.exists()

    def test_compute_prompt_hash(self):
        """Test prompt hash computation."""
        prompt = "Create a box 10x10x10mm"
        hash1 = CADExporter.compute_prompt_hash(prompt)
        hash2 = CADExporter.compute_prompt_hash(prompt)

        # Same prompt should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 16  # First 16 chars of SHA-256

        # Different prompts should produce different hashes
        hash3 = CADExporter.compute_prompt_hash("Different prompt")
        assert hash1 != hash3

    def test_cache_index_persistence(self, cad_exporter, temp_cache_dir):
        """Test cache index save/load."""
        # Update cache
        prompt_hash = "abcd1234"
        file_path = Path("outputs/test.step")
        cad_exporter._update_cache(prompt_hash, "step", file_path)

        # Verify saved
        assert prompt_hash in cad_exporter._cache_index
        assert cad_exporter._cache_index[prompt_hash]["step"] == str(file_path)

        # Create new exporter and verify index loaded
        new_exporter = CADExporter(
            outputs_dir=str(cad_exporter.outputs_dir),
            cache_dir=str(temp_cache_dir),
        )
        assert prompt_hash in new_exporter._cache_index

    def test_check_cache_miss(self, cad_exporter):
        """Test cache miss."""
        cached = cad_exporter._check_cache("nonexistent_hash", "step")
        assert cached is None

    def test_check_cache_hit(self, cad_exporter, temp_outputs_dir):
        """Test cache hit."""
        # Create a test file
        test_file = temp_outputs_dir / "cached.step"
        test_file.write_text("test content")

        # Add to cache
        prompt_hash = "test_hash_123"
        cad_exporter._update_cache(prompt_hash, "step", test_file)

        # Check cache
        cached = cad_exporter._check_cache(prompt_hash, "step")
        assert cached == test_file
        assert cached.exists()

    def test_check_cache_stale(self, cad_exporter):
        """Test stale cache entry removal."""
        # Add non-existent file to cache
        prompt_hash = "stale_hash"
        fake_path = Path("outputs/nonexistent.step")
        cad_exporter._cache_index[prompt_hash] = {"step": str(fake_path)}

        # Should return None and clean up
        cached = cad_exporter._check_cache(prompt_hash, "step")
        assert cached is None
        assert "step" not in cad_exporter._cache_index.get(prompt_hash, {})

    def test_generate_metadata(self, cad_exporter, temp_outputs_dir):
        """Test metadata generation."""
        # Create test file
        test_file = temp_outputs_dir / "test.step"
        test_file.write_text("test" * 1000)

        metadata = cad_exporter._generate_metadata(
            prompt="Create a box",
            prompt_hash="abc123",
            request_id="req-001",
            format="step",
            file_path=test_file,
            export_settings={"resolution": 0.1},
            cache_hit=False,
        )

        assert metadata.prompt == "Create a box"
        assert metadata.prompt_hash == "abc123"
        assert metadata.request_id == "req-001"
        assert metadata.format == "step"
        assert metadata.file_size_bytes == 4000  # "test" * 1000
        assert metadata.freecad_version == "0.21"
        assert metadata.export_settings == {"resolution": 0.1}
        assert metadata.cache_hit is False

    def test_save_metadata_sidecar(self, cad_exporter, temp_outputs_dir):
        """Test metadata sidecar file creation."""
        # Create test file
        test_file = temp_outputs_dir / "test.step"
        test_file.write_text("content")

        metadata = ExportMetadata(
            prompt="Create a box",
            prompt_hash="abc123",
            request_id="req-001",
            format="step",
            file_path=str(test_file),
            file_size_bytes=100,
            created_at="2024-01-01T00:00:00",
            freecad_version="0.21",
            export_settings={},
            cache_hit=False,
        )

        cad_exporter._save_metadata_sidecar(test_file, metadata)

        # Verify sidecar file
        sidecar_path = test_file.with_suffix(".step.json")
        assert sidecar_path.exists()

        with open(sidecar_path) as f:
            loaded = json.load(f)

        assert loaded["prompt"] == "Create a box"
        assert loaded["prompt_hash"] == "abc123"
        assert loaded["format"] == "step"
        assert loaded["file_size_bytes"] == 100

    @pytest.mark.asyncio
    async def test_export_format_step_success(
        self, cad_exporter, temp_outputs_dir, mock_headless_runner
    ):
        """Test successful STEP export."""
        # Create mock document
        doc_path = temp_outputs_dir / "test.FCStd"
        doc_path.write_text("fake fcstd")

        # Create expected output file
        output_file = temp_outputs_dir / "output.step"
        output_file.write_text("step content")
        mock_headless_runner.export_step.return_value = output_file

        result = await cad_exporter.export_format(
            doc_path=doc_path,
            format="step",
            prompt="Create a box",
            request_id=uuid4(),
        )

        assert result.success is True
        assert result.format == "step"
        assert result.file_path == output_file
        assert result.metadata is not None
        assert result.cache_hit is False
        mock_headless_runner.export_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_format_cache_hit(
        self, cad_exporter, temp_outputs_dir, mock_headless_runner
    ):
        """Test export with cache hit."""
        # Create cached file
        cached_file = temp_outputs_dir / "cached.step"
        cached_file.write_text("cached content")

        prompt = "Create a box"
        prompt_hash = CADExporter.compute_prompt_hash(prompt)
        cad_exporter._update_cache(prompt_hash, "step", cached_file)

        # Create mock document (won't be used due to cache)
        doc_path = temp_outputs_dir / "test.FCStd"
        doc_path.write_text("fake fcstd")

        result = await cad_exporter.export_format(
            doc_path=doc_path,
            format="step",
            prompt=prompt,
            request_id=uuid4(),
        )

        assert result.success is True
        assert result.cache_hit is True
        assert result.file_path == cached_file
        # Should not call export method
        mock_headless_runner.export_step.assert_not_called()

    @pytest.mark.asyncio
    async def test_export_format_invalid_format(self, cad_exporter, temp_outputs_dir):
        """Test export with invalid format."""
        doc_path = temp_outputs_dir / "test.FCStd"
        doc_path.write_text("fake")

        result = await cad_exporter.export_format(
            doc_path=doc_path,
            format="invalid",
            prompt="test",
            request_id=uuid4(),
        )

        assert result.success is False
        assert "Unsupported format" in result.error

    @pytest.mark.asyncio
    async def test_export_format_export_failure(
        self, cad_exporter, temp_outputs_dir, mock_headless_runner
    ):
        """Test export failure handling."""
        doc_path = temp_outputs_dir / "test.FCStd"
        doc_path.write_text("fake")

        # Mock export failure
        mock_headless_runner.export_step.return_value = None

        result = await cad_exporter.export_format(
            doc_path=doc_path,
            format="step",
            prompt="test",
            request_id=uuid4(),
        )

        assert result.success is False
        assert "Export failed" in result.error

    @pytest.mark.asyncio
    async def test_export_multiple_formats(
        self, cad_exporter, temp_outputs_dir, mock_headless_runner
    ):
        """Test multi-format export."""
        doc_path = temp_outputs_dir / "test.FCStd"
        doc_path.write_text("fake")

        # Create output files
        step_file = temp_outputs_dir / "out.step"
        stl_file = temp_outputs_dir / "out.stl"
        step_file.write_text("step")
        stl_file.write_text("stl")

        mock_headless_runner.export_step.return_value = step_file
        mock_headless_runner.export_stl.return_value = stl_file

        results = await cad_exporter.export_multiple_formats(
            doc_path=doc_path,
            formats=["step", "stl"],
            prompt="Create a box",
            request_id=uuid4(),
        )

        assert "step" in results
        assert "stl" in results
        assert results["step"].success is True
        assert results["stl"].success is True
        assert results["step"].file_path == step_file
        assert results["stl"].file_path == stl_file

    @pytest.mark.asyncio
    async def test_export_multiple_formats_partial_failure(
        self, cad_exporter, temp_outputs_dir, mock_headless_runner
    ):
        """Test multi-format export with partial failure."""
        doc_path = temp_outputs_dir / "test.FCStd"
        doc_path.write_text("fake")

        step_file = temp_outputs_dir / "out.step"
        step_file.write_text("step")

        mock_headless_runner.export_step.return_value = step_file
        mock_headless_runner.export_stl.return_value = None  # Fail STL

        results = await cad_exporter.export_multiple_formats(
            doc_path=doc_path,
            formats=["step", "stl"],
            prompt="Create a box",
            request_id=uuid4(),
        )

        assert results["step"].success is True
        assert results["stl"].success is False

    def test_get_export_path(self, cad_exporter):
        """Test export path generation."""
        request_id = uuid4()
        prompt_hash = "abc123"

        # With hash
        path = cad_exporter.get_export_path(request_id, "step", prompt_hash)
        assert str(request_id) in str(path)
        assert prompt_hash in str(path)
        assert path.suffix == ".step"

        # Without hash
        path_no_hash = cad_exporter.get_export_path(request_id, "stl")
        assert str(request_id) in str(path_no_hash)
        assert path_no_hash.suffix == ".stl"

    def test_list_exports(self, cad_exporter, temp_outputs_dir):
        """Test listing exports."""
        # Create test files
        request_id = uuid4()
        files = [
            temp_outputs_dir / f"{request_id}_abc.step",
            temp_outputs_dir / f"{request_id}_def.stl",
            temp_outputs_dir / f"other_file.FCStd",
        ]
        for f in files:
            f.write_text("test")

        # List all
        all_exports = cad_exporter.list_exports()
        assert len(all_exports) == 3

        # List by request_id
        filtered = cad_exporter.list_exports(request_id=request_id)
        assert len(filtered) == 2
        assert all(str(request_id) in f.name for f in filtered)

    def test_cache_disabled(self, mock_headless_runner, temp_outputs_dir):
        """Test exporter with cache disabled."""
        exporter = CADExporter(
            headless_runner=mock_headless_runner,
            outputs_dir=str(temp_outputs_dir),
            enable_cache=False,
        )

        assert exporter.enable_cache is False

        # Cache operations should be no-ops
        exporter._update_cache("hash", "step", Path("test.step"))
        cached = exporter._check_cache("hash", "step")
        assert cached is None


class TestExportMetadata:
    """Test ExportMetadata dataclass."""

    def test_metadata_creation(self):
        """Test metadata creation."""
        metadata = ExportMetadata(
            prompt="Test prompt",
            prompt_hash="abc123",
            request_id="req-001",
            format="step",
            file_path="/path/to/file.step",
            file_size_bytes=1024,
            created_at="2024-01-01T00:00:00",
        )

        assert metadata.prompt == "Test prompt"
        assert metadata.format == "step"
        assert metadata.file_size_bytes == 1024


class TestExportResult:
    """Test ExportResult dataclass."""

    def test_result_creation(self):
        """Test result creation."""
        result = ExportResult(
            success=True,
            format="step",
            file_path=Path("test.step"),
            cache_hit=False,
        )

        assert result.success is True
        assert result.format == "step"
        assert result.cache_hit is False
        assert result.error is None

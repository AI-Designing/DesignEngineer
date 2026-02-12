"""
Integration tests for export API endpoints.

Tests FastAPI endpoints for design export with multi-format support.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ai_designer.api.app import create_app
from ai_designer.export.exporter import ExportMetadata, ExportResult
from ai_designer.schemas.design_state import DesignState, ExecutionStatus


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_design_state():
    """Create mock design state."""
    state = DesignState(
        request_id=uuid4(),
        user_prompt="Create a box 10x10x10mm",
        max_iterations=5,
    )
    state.status = ExecutionStatus.COMPLETED
    state.fcstd_path = "outputs/test.FCStd"
    return state


@pytest.fixture
def mock_export_result():
    """Create mock export result."""
    return ExportResult(
        success=True,
        format="step",
        file_path=Path("outputs/test.step"),
        metadata=ExportMetadata(
            prompt="Create a box",
            prompt_hash="abc123",
            request_id="req-001",
            format="step",
            file_path="outputs/test.step",
            file_size_bytes=1024,
            created_at="2024-01-01T00:00:00",
        ),
        cache_hit=False,
    )


class TestExportEndpoint:
    """Test cases for /design/{request_id}/export endpoint."""

    @pytest.mark.asyncio
    async def test_export_design_not_found(self, test_client):
        """Test export for non-existent design."""
        response = test_client.get(
            "/api/v1/design/nonexistent-id/export?formats=step"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_export_design_not_completed(self, test_client, mock_design_state):
        """Test export for incomplete design."""
        from ai_designer.api.routes.design import _designs

        # Set design to pending
        mock_design_state.status = ExecutionStatus.PENDING
        _designs[str(mock_design_state.request_id)] = mock_design_state

        response = test_client.get(
            f"/api/v1/design/{mock_design_state.request_id}/export?formats=step"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be completed" in response.json()["detail"].lower()

        # Cleanup
        del _designs[str(mock_design_state.request_id)]

    @pytest.mark.asyncio
    async def test_export_design_invalid_format(self, test_client, mock_design_state):
        """Test export with invalid format."""
        from ai_designer.api.routes.design import _designs

        _designs[str(mock_design_state.request_id)] = mock_design_state

        response = test_client.get(
            f"/api/v1/design/{mock_design_state.request_id}/export?formats=invalid"
        )
        # Should fail validation due to regex pattern
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

        # Cleanup
        del _designs[str(mock_design_state.request_id)]

    @pytest.mark.asyncio
    async def test_export_design_success_single_format(
        self, test_client, mock_design_state, mock_export_result, tmp_path
    ):
        """Test successful export with single format."""
        from ai_designer.api.routes.design import _designs

        # Create test files
        fcstd_file = tmp_path / "test.FCStd"
        fcstd_file.write_text("fake fcstd")
        step_file = tmp_path / "test.step"
        step_file.write_text("fake step")

        mock_design_state.fcstd_path = str(fcstd_file)
        _designs[str(mock_design_state.request_id)] = mock_design_state

        # Mock exporter
        mock_export_result.file_path = step_file

        with patch(
            "ai_designer.api.routes.design.get_cad_exporter"
        ) as mock_get_exporter:
            mock_exporter = Mock()
            mock_exporter.outputs_dir = tmp_path
            mock_exporter.export_multiple_formats = AsyncMock(
                return_value={"step": mock_export_result}
            )
            mock_get_exporter.return_value = mock_exporter

            response = test_client.get(
                f"/api/v1/design/{mock_design_state.request_id}/export?formats=step"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "step" in data
        assert data["step"]["success"] is True
        assert data["step"]["format"] == "step"
        assert data["step"]["cache_hit"] is False

        # Cleanup
        del _designs[str(mock_design_state.request_id)]

    @pytest.mark.asyncio
    async def test_export_design_multi_format(
        self, test_client, mock_design_state, tmp_path
    ):
        """Test export with multiple formats."""
        from ai_designer.api.routes.design import _designs

        # Create test files
        fcstd_file = tmp_path / "test.FCStd"
        fcstd_file.write_text("fake")
        step_file = tmp_path / "test.step"
        step_file.write_text("fake")
        stl_file = tmp_path / "test.stl"
        stl_file.write_text("fake")

        mock_design_state.fcstd_path = str(fcstd_file)
        _designs[str(mock_design_state.request_id)] = mock_design_state

        # Mock results
        step_result = ExportResult(
            success=True,
            format="step",
            file_path=step_file,
            metadata=ExportMetadata(
                prompt="test",
                prompt_hash="abc",
                request_id="req",
                format="step",
                file_path=str(step_file),
                file_size_bytes=100,
                created_at="2024-01-01",
            ),
        )
        stl_result = ExportResult(
            success=True,
            format="stl",
            file_path=stl_file,
            metadata=ExportMetadata(
                prompt="test",
                prompt_hash="abc",
                request_id="req",
                format="stl",
                file_path=str(stl_file),
                file_size_bytes=200,
                created_at="2024-01-01",
            ),
        )

        with patch(
            "ai_designer.api.routes.design.get_cad_exporter"
        ) as mock_get_exporter:
            mock_exporter = Mock()
            mock_exporter.outputs_dir = tmp_path
            mock_exporter.export_multiple_formats = AsyncMock(
                return_value={"step": step_result, "stl": stl_result}
            )
            mock_get_exporter.return_value = mock_exporter

            response = test_client.get(
                f"/api/v1/design/{mock_design_state.request_id}/export?formats=step,stl"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "step" in data
        assert "stl" in data
        assert data["step"]["success"] is True
        assert data["stl"]["success"] is True

        # Cleanup
        del _designs[str(mock_design_state.request_id)]

    @pytest.mark.asyncio
    async def test_export_design_cache_hit(
        self, test_client, mock_design_state, tmp_path
    ):
        """Test export with cache hit."""
        from ai_designer.api.routes.design import _designs

        fcstd_file = tmp_path / "test.FCStd"
        fcstd_file.write_text("fake")
        cached_file = tmp_path / "cached.step"
        cached_file.write_text("cached")

        mock_design_state.fcstd_path = str(fcstd_file)
        _designs[str(mock_design_state.request_id)] = mock_design_state

        # Mock cache hit result
        cache_result = ExportResult(
            success=True,
            format="step",
            file_path=cached_file,
            metadata=ExportMetadata(
                prompt="test",
                prompt_hash="abc",
                request_id="req",
                format="step",
                file_path=str(cached_file),
                file_size_bytes=100,
                created_at="2024-01-01",
                cache_hit=True,
            ),
            cache_hit=True,
        )

        with patch(
            "ai_designer.api.routes.design.get_cad_exporter"
        ) as mock_get_exporter:
            mock_exporter = Mock()
            mock_exporter.outputs_dir = tmp_path
            mock_exporter.export_multiple_formats = AsyncMock(
                return_value={"step": cache_result}
            )
            mock_get_exporter.return_value = mock_exporter

            response = test_client.get(
                f"/api/v1/design/{mock_design_state.request_id}/export?formats=step"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["step"]["cache_hit"] is True

        # Cleanup
        del _designs[str(mock_design_state.request_id)]


class TestDownloadEndpoint:
    """Test cases for /design/{request_id}/download/{format} endpoint."""

    @pytest.mark.asyncio
    async def test_download_invalid_format(self, test_client):
        """Test download with invalid format."""
        response = test_client.get("/api/v1/design/some-id/download/invalid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_download_success(self, test_client, mock_design_state, tmp_path):
        """Test successful file download."""
        from ai_designer.api.routes.design import _designs

        # Create test files
        fcstd_file = tmp_path / "test.FCStd"
        fcstd_file.write_text("fake fcstd")
        step_file = tmp_path / "test.step"
        step_file.write_text("fake step content")

        mock_design_state.fcstd_path = str(fcstd_file)
        _designs[str(mock_design_state.request_id)] = mock_design_state

        # Mock export result
        export_result = ExportResult(
            success=True,
            format="step",
            file_path=step_file,
            metadata=ExportMetadata(
                prompt="test",
                prompt_hash="abc",
                request_id="req",
                format="step",
                file_path=str(step_file),
                file_size_bytes=100,
                created_at="2024-01-01",
            ),
        )

        with patch(
            "ai_designer.api.routes.design.get_cad_exporter"
        ) as mock_get_exporter:
            mock_exporter = Mock()
            mock_exporter.outputs_dir = tmp_path
            mock_exporter.export_multiple_formats = AsyncMock(
                return_value={"step": export_result}
            )
            mock_get_exporter.return_value = mock_exporter

            response = test_client.get(
                f"/api/v1/design/{mock_design_state.request_id}/download/step"
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/step"
        assert b"fake step content" in response.content

        # Cleanup
        del _designs[str(mock_design_state.request_id)]

    @pytest.mark.asyncio
    async def test_download_export_failure(
        self, test_client, mock_design_state, tmp_path
    ):
        """Test download when export fails."""
        from ai_designer.api.routes.design import _designs

        fcstd_file = tmp_path / "test.FCStd"
        fcstd_file.write_text("fake")
        mock_design_state.fcstd_path = str(fcstd_file)
        _designs[str(mock_design_state.request_id)] = mock_design_state

        # Mock export failure
        fail_result = ExportResult(
            success=False, format="step", error="Export failed"
        )

        with patch(
            "ai_designer.api.routes.design.get_cad_exporter"
        ) as mock_get_exporter:
            mock_exporter = Mock()
            mock_exporter.outputs_dir = tmp_path
            mock_exporter.export_multiple_formats = AsyncMock(
                return_value={"step": fail_result}
            )
            mock_get_exporter.return_value = mock_exporter

            response = test_client.get(
                f"/api/v1/design/{mock_design_state.request_id}/download/step"
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Cleanup
        del _designs[str(mock_design_state.request_id)]


class TestAuditLogging:
    """Test audit logging integration."""

    @pytest.mark.asyncio
    async def test_export_logs_audit_event(
        self, test_client, mock_design_state, tmp_path
    ):
        """Test that successful exports log audit events."""
        from ai_designer.api.routes.design import _designs

        fcstd_file = tmp_path / "test.FCStd"
        fcstd_file.write_text("fake")
        step_file = tmp_path / "test.step"
        step_file.write_text("fake")

        mock_design_state.fcstd_path = str(fcstd_file)
        _designs[str(mock_design_state.request_id)] = mock_design_state

        export_result = ExportResult(
            success=True,
            format="step",
            file_path=step_file,
            metadata=ExportMetadata(
                prompt="test",
                prompt_hash="abc",
                request_id="req",
                format="step",
                file_path=str(step_file),
                file_size_bytes=100,
                created_at="2024-01-01",
            ),
        )

        with patch(
            "ai_designer.api.routes.design.get_cad_exporter"
        ) as mock_get_exporter:
            with patch(
                "ai_designer.api.routes.design._log_export_audit_event"
            ) as mock_audit:
                mock_exporter = Mock()
                mock_exporter.outputs_dir = tmp_path
                mock_exporter.export_multiple_formats = AsyncMock(
                    return_value={"step": export_result}
                )
                mock_get_exporter.return_value = mock_exporter

                response = test_client.get(
                    f"/api/v1/design/{mock_design_state.request_id}/export?formats=step"
                )

                assert response.status_code == status.HTTP_200_OK
                # Verify audit logging was called
                mock_audit.assert_called_once()

        # Cleanup
        del _designs[str(mock_design_state.request_id)]

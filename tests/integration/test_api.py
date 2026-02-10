"""
Integration tests for FastAPI REST API.

Tests the complete API endpoints with mocked agents.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import AsyncClient

from ai_designer.api.app import create_app
from ai_designer.api.deps import reset_dependencies
from ai_designer.schemas.design_state import DesignState, ExecutionStatus
from ai_designer.schemas.validation import ValidationResult


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def reset_deps():
    """Reset dependencies before each test."""
    reset_dependencies()
    yield
    reset_dependencies()


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "freecad-ai-designer"
        assert "version" in data
    
    def test_readiness_check(self, client):
        """Test readiness check."""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data


class TestDesignEndpoints:
    """Tests for design creation and management endpoints."""
    
    @patch("ai_designer.api.routes.design._process_design")
    def test_create_design(self, mock_process, client):
        """Test creating a new design request."""
        request_data = {
            "prompt": "Create a 10x10x10mm cube",
            "max_iterations": 3,
            "enable_execution": True,
        }
        
        response = client.post("/api/v1/design", json=request_data)
        
        assert response.status_code == 202
        data = response.json()
        assert "request_id" in data
        assert data["status"] == "pending"
        assert "created_at" in data
        
        # Verify background task was scheduled
        mock_process.assert_called_once()
    
    def test_create_design_validation_error(self, client):
        """Test design creation with invalid input."""
        request_data = {
            "prompt": "Too short",  # Less than 10 chars
            "max_iterations": 3,
        }
        
        response = client.post("/api/v1/design", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
    
    @patch("ai_designer.api.routes.design._designs")
    def test_get_design_status(self, mock_designs, client):
        """Test retrieving design status."""
        request_id = str(uuid4())
        now = datetime.utcnow()
        
        # Mock stored design state
        mock_state = DesignState(
            request_id=request_id,
            user_prompt="Create a cube",
            status=ExecutionStatus.COMPLETED,
            iteration=1,
            max_iterations=5,
            created_at=now,
            updated_at=now,
            generated_script="# FreeCAD script",
        )
        mock_designs.get.return_value = mock_state
        
        response = client.get(f"/api/v1/design/{request_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == request_id
        assert data["status"] == "completed"
        assert data["prompt"] == "Create a cube"
        assert data["current_iteration"] == 1
        assert data["max_iterations"] == 5
    
    def test_get_design_status_not_found(self, client):
        """Test retrieving non-existent design."""
        response = client.get("/api/v1/design/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch("ai_designer.api.routes.design._process_design")
    @patch("ai_designer.api.routes.design._designs")
    def test_refine_design(self, mock_designs, mock_process, client):
        """Test submitting refinement feedback."""
        request_id = str(uuid4())
        now = datetime.utcnow()
        
        # Mock completed design
        mock_state = DesignState(
            request_id=request_id,
            user_prompt="Create a cube",
            status=ExecutionStatus.COMPLETED,
            iteration=1,
            max_iterations=5,
            created_at=now,
            updated_at=now,
        )
        mock_designs.get.return_value = mock_state
        
        refinement_data = {
            "feedback": "Make it larger, 20x20x20mm instead",
        }
        
        response = client.post(
            f"/api/v1/design/{request_id}/refine",
            json=refinement_data,
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["request_id"] == request_id
        assert "refinement request accepted" in data["message"].lower()
        
        # Verify background task was scheduled
        mock_process.assert_called_once()
    
    @patch("ai_designer.api.routes.design._designs")
    def test_refine_design_invalid_status(self, mock_designs, client):
        """Test refinement on design that's not completed."""
        request_id = str(uuid4())
        now = datetime.utcnow()
        
        # Mock design still in progress
        mock_state = DesignState(
            request_id=request_id,
            user_prompt="Create a cube",
            status=ExecutionStatus.GENERATING,
            iteration=0,
            max_iterations=5,
            created_at=now,
            updated_at=now,
        )
        mock_designs.get.return_value = mock_state
        
        refinement_data = {
            "feedback": "Make it larger",
        }
        
        response = client.post(
            f"/api/v1/design/{request_id}/refine",
            json=refinement_data,
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "must be completed" in data["detail"].lower()
    
    @patch("ai_designer.api.routes.design._designs")
    def test_delete_design(self, mock_designs, client):
        """Test deleting a design request."""
        request_id = str(uuid4())
        
        # Mock design exists
        mock_designs.__contains__.return_value = True
        mock_designs.__delitem__ = MagicMock()
        
        response = client.delete(f"/api/v1/design/{request_id}")
        
        assert response.status_code == 204
    
    def test_delete_design_not_found(self, client):
        """Test deleting non-existent design."""
        response = client.delete("/api/v1/design/nonexistent-id")
        
        assert response.status_code == 404


class TestProcessDesignIntegration:
    """Tests for the background processing pipeline."""
    
    @pytest.mark.asyncio
    async def test_process_design_success(self):
        """Test successful design processing with mocked orchestrator."""
        from ai_designer.api.routes.design import _process_design, _designs
        
        request_id = str(uuid4())
        now = datetime.utcnow()
        
        # Create initial state
        initial_state = DesignState(
            request_id=request_id,
            user_prompt="Create a 10x10x10mm cube",
            status=ExecutionStatus.PENDING,
            iteration=0,
            max_iterations=5,
            created_at=now,
            updated_at=now,
        )
        _designs[request_id] = initial_state
        
        # Mock orchestrator
        mock_orchestrator = AsyncMock()
        completed_state = DesignState(
            request_id=request_id,
            user_prompt="Create a 10x10x10mm cube",
            status=ExecutionStatus.COMPLETED,
            iteration=1,
            max_iterations=5,
            created_at=now,
            updated_at=now,
            generated_script="# Generated script",
            validation_result=ValidationResult(
                request_id=request_id,
                is_valid=True,
                overall_score=0.95,
                feedback="Design looks good",
            ),
        )
        mock_orchestrator.execute.return_value = completed_state
        
        # Mock executor
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {
            "success": True,
            "executed_count": 1,
            "created_objects": ["Cube001"],
            "errors": [],
        }
        
        # Run processing
        await _process_design(
            request_id=request_id,
            enable_execution=True,
            orchestrator=mock_orchestrator,
            executor=mock_executor,
        )
        
        # Verify orchestrator was called
        mock_orchestrator.execute.assert_called_once()
        
        # Verify state was updated
        final_state = _designs[request_id]
        assert final_state.status == ExecutionStatus.COMPLETED
        assert final_state.generated_script == "# Generated script"
        
        # Cleanup
        del _designs[request_id]
    
    @pytest.mark.asyncio
    async def test_process_design_failure(self):
        """Test design processing with orchestrator failure."""
        from ai_designer.api.routes.design import _process_design, _designs
        
        request_id = str(uuid4())
        now = datetime.utcnow()
        
        # Create initial state
        initial_state = DesignState(
            request_id=request_id,
            user_prompt="Create invalid design",
            status=ExecutionStatus.PENDING,
            iteration=0,
            max_iterations=5,
            created_at=now,
            updated_at=now,
        )
        _designs[request_id] = initial_state
        
        # Mock orchestrator to raise exception
        mock_orchestrator = AsyncMock()
        mock_orchestrator.execute.side_effect = Exception("Orchestrator error")
        
        mock_executor = AsyncMock()
        
        # Run processing
        await _process_design(
            request_id=request_id,
            enable_execution=True,
            orchestrator=mock_orchestrator,
            executor=mock_executor,
        )
        
        # Verify state was updated with error
        final_state = _designs[request_id]
        assert final_state.status == ExecutionStatus.FAILED
        assert "Orchestrator error" in final_state.error_message
        
        # Cleanup
        del _designs[request_id]


class TestWebSocketEndpoint:
    """Tests for WebSocket real-time updates."""
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection and disconnection."""
        request_id = str(uuid4())
        
        with client.websocket_connect(f"/ws/{request_id}") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["request_id"] == request_id
            
            # Send a test message
            websocket.send_text("ping")
            
            # Should receive acknowledgment
            response = websocket.receive_json()
            assert response["type"] == "ack"
            assert response["request_id"] == request_id


class TestErrorHandling:
    """Tests for error handling and exception responses."""
    
    def test_validation_error_response(self, client):
        """Test response format for validation errors."""
        # Send invalid data (missing required field)
        response = client.post("/api/v1/design", json={})
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"] == "Validation Error"
        assert "detail" in data
        assert "request_id" in data
    
    def test_request_id_header(self, client):
        """Test that request ID is added to responses."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

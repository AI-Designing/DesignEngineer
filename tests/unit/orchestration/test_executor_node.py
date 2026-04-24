"""Executor node passes full FreeCADExecutor payload including geometry."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from ai_designer.orchestration.nodes import PipelineNodes
from ai_designer.orchestration.state import PipelineState
from ai_designer.schemas.design_state import DesignState, ExecutionStatus


def test_executor_node_preserves_geometry_payload():
    geom_dict = {
        "feedback_version": "1",
        "object_count": 3,
        "total_volume_mm3": 500.0,
        "bounding_box": {"length": 10.0, "width": 5.0, "height": 10.0},
        "is_manifold": True,
        "has_invalid_faces": False,
        "has_self_intersections": False,
    }
    mock_executor = MagicMock()
    mock_executor.execute = AsyncMock(
        return_value={
            "success": True,
            "executed_count": 1,
            "failed_count": 0,
            "created_objects": ["Box"],
            "errors": [],
            "execution_time": 1.5,
            "document_path": "/tmp/test.FCStd",
            "geometry": geom_dict,
            "geometry_unavailable_reason": None,
            "state": {"success": True, "object_count": 3},
        }
    )

    planner = MagicMock()
    generator = MagicMock()
    validator = MagicMock()

    nodes = PipelineNodes(
        planner=planner,
        generator=generator,
        validator=validator,
        executor=mock_executor,
    )

    design = DesignState(
        request_id=uuid4(),
        user_prompt="build a simple test part for unit tests",
        status=ExecutionStatus.GENERATING,
    )
    state = PipelineState(
        design_state=design,
        generated_scripts={"task_1": "doc = App.newDocument()"},
    )

    out = asyncio.run(nodes.executor_node(state))

    assert out.execution_result is not None
    assert out.execution_result["geometry"] == geom_dict
    assert out.execution_result["state"]["object_count"] == 3
    assert out.execution_result["document_path"] == "/tmp/test.FCStd"
    assert out.execution_result["error"] is None
    mock_executor.execute.assert_awaited_once()

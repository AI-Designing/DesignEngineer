"""Unit tests for workflow orchestrator honesty (Track 4)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[3] / "src"
_WF_PATH = _SRC / "ai_designer" / "freecad" / "workflow_orchestrator.py"
_spec = importlib.util.spec_from_file_location(
    "_workflow_orchestrator_under_test",
    _WF_PATH,
    submodule_search_locations=[str(_SRC)],
)
_wf = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _wf
assert _spec.loader is not None
_spec.loader.exec_module(_wf)

WorkflowExecutionResult = _wf.WorkflowExecutionResult
WorkflowOrchestrator = _wf.WorkflowOrchestrator
WorkflowStep = _wf.WorkflowStep
WorkflowStepType = _wf.WorkflowStepType


class MockCommandExecutor:
    def __init__(self, status: str = "success", message: str = ""):
        self.status = status
        self.message = message
        self.scripts: list[str] = []

    def execute(self, command: str, document_path=None, **kwargs):
        self.scripts.append(command)
        return {"status": self.status, "message": self.message}


class DummyStateProcessor:
    def __init__(self, executor=None):
        self.command_executor = executor


def test_pad_without_executor_returns_error():
    orch = WorkflowOrchestrator(state_processor=DummyStateProcessor(None))
    step = WorkflowStep(
        step_id="p1",
        step_type=WorkflowStepType.OPERATION_PAD,
        description="Pad",
        parameters={"height": 5.0},
    )
    out = orch._execute_pad_step(step, {})
    assert out.status == "error"
    assert out.reason_code == "NO_COMMAND_EXECUTOR"


def test_pattern_step_skipped_unimplemented():
    orch = WorkflowOrchestrator(
        state_processor=DummyStateProcessor(MockCommandExecutor())
    )
    step = WorkflowStep(
        step_id="pat1",
        step_type=WorkflowStepType.PATTERN_LINEAR,
        description="Pattern",
        parameters={"count": 4},
    )
    out = orch._execute_pattern_step(step, {})
    assert out.status == "skipped_unimplemented"
    assert out.output.get("skipped_unimplemented") is True
    assert out.reason_code == "UNIMPLEMENTED_PATTERN"


def test_unsupported_step_type_skipped():
    orch = WorkflowOrchestrator(
        state_processor=DummyStateProcessor(MockCommandExecutor())
    )
    step = WorkflowStep(
        step_id="pk1",
        step_type=WorkflowStepType.OPERATION_POCKET,
        description="Pocket",
        parameters={},
    )
    out = orch._execute_single_step(step, {}, {})
    assert out.status == "skipped_unimplemented"
    assert out.reason_code == "UNIMPLEMENTED_STEP"


def test_execute_workflow_partial_when_pattern_skipped_after_sketch():
    """Sketch succeeds (mock executor); pattern step is skipped -> partial."""
    mock_ex = MockCommandExecutor()
    orch = WorkflowOrchestrator(state_processor=DummyStateProcessor(mock_ex))
    steps = [
        WorkflowStep(
            step_id="s1",
            step_type=WorkflowStepType.SKETCH_CREATE,
            description="Create box primitive",
            parameters={"shape": "box"},
        ),
        WorkflowStep(
            step_id="p2",
            step_type=WorkflowStepType.PATTERN_LINEAR,
            description="Pattern",
            parameters={"count": 2},
            dependencies=["s1"],
        ),
    ]
    ctx = {"original_command": "create a box 10mm"}
    res = orch.execute_workflow_steps(steps, ctx)
    assert res["status"] == "partial"
    assert res["skipped_steps"] == 1
    assert res["completed_steps"] == 1
    assert res["failed_steps"] == 0
    assert res["step_results"][0].status == "success"
    assert res["step_results"][1].status == "skipped_unimplemented"


def test_execute_workflow_error_stops_on_first_error():
    orch = WorkflowOrchestrator(state_processor=DummyStateProcessor(None))
    steps = [
        WorkflowStep(
            step_id="h1",
            step_type=WorkflowStepType.OPERATION_HOLE,
            description="Hole requires executor",
            parameters={"diameter": 4.0},
        ),
    ]
    res = orch.execute_workflow_steps(steps, {})
    assert res["status"] == "error"
    assert res["completed_steps"] == 0
    assert res["failed_steps"] == 1


def test_hole_step_calls_executor_and_maps_success():
    mock_ex = MockCommandExecutor()
    orch = WorkflowOrchestrator(state_processor=DummyStateProcessor(mock_ex))
    step = WorkflowStep(
        step_id="h1",
        step_type=WorkflowStepType.OPERATION_HOLE,
        description="Hole",
        parameters={"diameter": 6.0, "depth": "through"},
    )
    out = orch._execute_hole_step(step, {})
    assert out.status == "success"
    assert out.output.get("hole_created") is True
    assert len(mock_ex.scripts) == 1
    assert "Part::Cut" in mock_ex.scripts[0]
    assert "6.0" in mock_ex.scripts[0] or "3.0" in mock_ex.scripts[0]


def test_hole_step_maps_executor_failure():
    mock_ex = MockCommandExecutor(status="error", message="FC failed")
    orch = WorkflowOrchestrator(state_processor=DummyStateProcessor(mock_ex))
    step = WorkflowStep(
        step_id="h1",
        step_type=WorkflowStepType.OPERATION_HOLE,
        description="Hole",
        parameters={"diameter": 4.0},
    )
    out = orch._execute_hole_step(step, {})
    assert out.status == "error"
    assert out.reason_code == "HOLE_EXECUTION_FAILED"
    assert out.error_message == "FC failed"


def test_aggregate_workflow_status():
    assert (
        WorkflowOrchestrator._aggregate_workflow_status(
            [
                WorkflowExecutionResult(
                    "a",
                    "success",
                    {},
                    0.0,
                ),
            ]
        )
        == "success"
    )
    assert (
        WorkflowOrchestrator._aggregate_workflow_status(
            [
                WorkflowExecutionResult(
                    "a",
                    "success",
                    {},
                    0.0,
                ),
                WorkflowExecutionResult(
                    "b",
                    "skipped_unimplemented",
                    {"skipped_unimplemented": True},
                    0.0,
                ),
            ]
        )
        == "partial"
    )
    assert (
        WorkflowOrchestrator._aggregate_workflow_status(
            [
                WorkflowExecutionResult("a", "error", {}, 0.0),
                WorkflowExecutionResult(
                    "b",
                    "skipped_unimplemented",
                    {"skipped_unimplemented": True},
                    0.0,
                ),
            ]
        )
        == "error"
    )

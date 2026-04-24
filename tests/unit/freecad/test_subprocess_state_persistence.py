"""
Track 10: multi-step subprocess state — merged scripts, checkpoint open, tests.

Acceptance: subprocess wrapper must open checkpoint ``.FCStd`` when given
``document_path`` so a follow-up step sees prior geometry; merged multi-step
must not fan out to one ``execute()`` per LLM step.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_execute_via_subprocess_script_opens_checkpoint(tmp_path):
    """Wrapper script includes FreeCAD.openDocument when document_path is set."""
    from ai_designer.freecad.api_client import FreeCADAPIClient

    fcstd = tmp_path / "step1.FCStd"
    fcstd.write_bytes(b"PK\x03\x04fake")  # exists on disk; FreeCAD not invoked

    client = FreeCADAPIClient(use_headless=True)
    captured_scripts: list = []

    def fake_run(cmd, **kwargs):
        script_path = cmd[-1]
        captured_scripts.append(Path(script_path).read_text())
        text = captured_scripts[-1]
        m = re.search(r'open\("(/tmp/freecad_ok_[a-f0-9]+)"', text)
        if m:
            Path(m.group(1)).write_text("ok", encoding="ascii")
        return MagicMock(returncode=0, stdout="SAVED_TO: /tmp/x\n", stderr="")

    with patch.object(client, "freecad_executable", "/usr/bin/true"):
        with patch("subprocess.run", side_effect=fake_run):
            out = client._execute_via_subprocess(
                "doc.recompute()",
                save_path=str(tmp_path / "out.FCStd"),
                document_path=str(fcstd),
            )

    assert out["status"] == "success"
    assert "saved_path" in out
    body = captured_scripts[0]
    assert "openDocument" in body
    assert str(fcstd) in body


def test_execute_via_subprocess_new_doc_without_checkpoint(tmp_path):
    """Without document_path, wrapper uses newDocument path (no openDocument)."""
    from ai_designer.freecad.api_client import FreeCADAPIClient

    client = FreeCADAPIClient(use_headless=True)
    captured: list = []

    def fake_run(cmd, **kwargs):
        captured.append(Path(cmd[-1]).read_text())
        m = re.search(r'open\("(/tmp/freecad_ok_[a-f0-9]+)"', captured[0])
        if m:
            Path(m.group(1)).write_text("ok", encoding="ascii")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(client, "freecad_executable", "/usr/bin/true"):
        with patch("subprocess.run", side_effect=fake_run):
            client._execute_via_subprocess("pass", save_path=None, document_path=None)

    assert "openDocument" not in captured[0]
    assert "newDocument" in captured[0]


def test_get_document_state_reads_stdout_state_line(tmp_path):
    """STATE lines must be parsed from captured stdout (subprocess success)."""
    from ai_designer.freecad.api_client import FreeCADAPIClient

    client = FreeCADAPIClient(use_headless=True)

    def fake_run(cmd, **kwargs):
        text = Path(cmd[-1]).read_text()
        m = re.search(r'open\("(/tmp/freecad_ok_[a-f0-9]+)"', text)
        if m:
            Path(m.group(1)).write_text("ok", encoding="ascii")
        return MagicMock(
            returncode=0,
            stdout='STATE: {"active_document":"D","objects":[],"object_count":0}\n',
            stderr="",
        )

    with patch.object(client, "freecad_executable", "/usr/bin/true"):
        with patch("subprocess.run", side_effect=fake_run):
            st = client.get_document_state()

    assert st.get("active_document") == "D"
    assert st.get("object_count") == 0


def test_workflow_execute_passes_checkpoint_kwarg():
    """Orchestrator threads ``checkpoint_fcstd`` as ``document_path``."""
    from ai_designer.freecad.workflow_orchestrator import WorkflowOrchestrator

    ex = MagicMock()
    ex.execute = MagicMock(return_value={"status": "success"})
    proc = MagicMock(command_executor=ex)
    orch = WorkflowOrchestrator(state_processor=proc)

    ctx: dict = {}
    orch._workflow_execute(ctx, "doc.recompute()")
    ex.execute.assert_called_once_with("doc.recompute()")

    ctx["checkpoint_fcstd"] = "/tmp/wf.FCStd"
    orch._workflow_execute(ctx, "doc.recompute()")
    assert ex.execute.call_count == 2
    ex.execute.assert_called_with("doc.recompute()", document_path="/tmp/wf.FCStd")


def test_process_multi_step_uses_merged_script(monkeypatch):
    """``_process_multi_step_workflow`` must call merged single-script path."""
    from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor

    tb = {
        "total_steps": 2,
        "analysis": "two primitives",
        "steps": [
            {
                "step_number": 1,
                "description": "cyl",
                "action_type": "create",
                "target_object": "Cyl",
                "details": {
                    "object_type": "Part::Cylinder",
                    "parameters": {"radius": 2, "height": 5},
                    "positioning": {"x": 0, "y": 0, "z": 0, "explanation": ""},
                },
            },
            {
                "step_number": 2,
                "description": "box",
                "action_type": "create",
                "target_object": "Box",
                "details": {
                    "object_type": "Part::Box",
                    "parameters": {"length": 3, "width": 3, "height": 3},
                    "positioning": {"x": 0, "y": 0, "z": 0, "explanation": ""},
                },
            },
        ],
    }

    merge_calls: list = []

    def fake_merge(self, task_breakdown, nl_command):
        merge_calls.append((len(task_breakdown.get("steps", [])), nl_command))
        return {
            "status": "success",
            "executed_steps": 2,
            "total_steps": 2,
            "skipped_steps": 0,
            "execution_result": {"status": "success"},
            "analysis": task_breakdown["analysis"],
        }

    monkeypatch.setattr(
        StateAwareCommandProcessor,
        "_execute_as_single_script",
        fake_merge,
    )

    processor = StateAwareCommandProcessor(
        llm_client=MagicMock(),
        state_cache=MagicMock(),
        api_client=MagicMock(),
        command_executor=MagicMock(),
    )
    monkeypatch.setattr(processor, "_decompose_task", lambda nc, cs: tb)

    out = processor._process_multi_step_workflow(
        "add something", {}, {"strategy": "multi_step"}
    )

    assert len(merge_calls) == 1
    assert merge_calls[0][0] == 2
    assert out["workflow"] == "multi_step"
    assert out["steps_executed"] == 2
    assert len(out["execution_results"]) == 1
    assert out["execution_results"][0]["step"] == "merged_subprocess"

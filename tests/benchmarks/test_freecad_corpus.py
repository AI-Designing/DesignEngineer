"""Real FreeCAD subprocess benchmarks (optional; skipped without CLI)."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from tests.benchmarks import golden_scripts
from tests.benchmarks.assertions import assert_execution_meets_criteria
from tests.benchmarks.freecad_env import (
    is_freecad_available,
    resolve_benchmark_freecad_cli,
)
from tests.fixtures import sample_scripts


def _script_for_key(script_key: str) -> str:
    if script_key in golden_scripts.SCRIPTS:
        return golden_scripts.get_script(script_key)
    return sample_scripts.get_script(script_key)


pytestmark = [
    pytest.mark.requires_freecad,
    pytest.mark.freecad,
    pytest.mark.cad_e2e,
    pytest.mark.slow,
    pytest.mark.skipif(
        not is_freecad_available(),
        reason=(
            "No headless FreeCAD for -c scripts: install distro ``freecadcmd`` (or set "
            "``FREECAD_PATH`` to a console binary, e.g. AppImage AppRun / extracted "
            "``freecadcmd``). GUI ``freecad`` / snap wrappers are not used for benchmarks."
        ),
    ),
]

_CORPUS_PATH = Path(__file__).resolve().parent / "corpus.yaml"


def _load_corpus_cases() -> List[Dict[str, Any]]:
    raw = yaml.safe_load(_CORPUS_PATH.read_text(encoding="utf-8"))
    return list(raw.get("cases") or [])


def _pytest_params():
    """Build ids and params; corpus rows with skip:true become pytest.skip marks."""
    out = []
    for row in _load_corpus_cases():
        cid = row["id"]
        if row.get("skip"):
            reason = row.get("skip_reason") or "skipped in corpus"
            out.append(pytest.param(row, id=cid, marks=pytest.mark.skip(reason=reason)))
        else:
            out.append(pytest.param(row, id=cid))
    return out


@pytest.fixture
def executor(tmp_path):
    from ai_designer.agents.executor import FreeCADExecutor

    cli = resolve_benchmark_freecad_cli()
    assert cli, "benchmarks require freecadcmd, FREECAD_PATH, or a FreeCAD AppImage"
    return FreeCADExecutor(
        timeout=120,
        freecad_path=cli,
        save_outputs=True,
        outputs_dir=str(tmp_path / "fc_out"),
        use_headless=True,
    )


@pytest.mark.parametrize("case", _pytest_params())
def test_corpus_case(executor, case: Dict[str, Any]):
    """Sync wrapper so benchmarks run without pytest-asyncio (e.g. minimal plugin set)."""
    script_key = case.get("script_key")
    assert script_key, f"case {case.get('id')} missing script_key"
    script = _script_for_key(script_key)
    expect_success = bool(case.get("expect_success", True))
    criteria = dict(case.get("criteria") or {})

    result = asyncio.run(
        executor.execute(
            {"task_1": script},
            document_name=f"bench_{case['id']}_{uuid.uuid4().hex[:8]}",
            request_id=str(uuid.uuid4()),
        )
    )

    assert_execution_meets_criteria(
        result,
        expect_success=expect_success,
        criteria=criteria,
    )

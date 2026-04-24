"""
Canonical CLI helpers: LangGraph agent pipeline (same stack as ``POST /design``).
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional
from uuid import uuid4

from ai_designer.orchestration.pipeline import PipelineExecutor
from ai_designer.runtime.pipeline_factory import build_cli_pipeline_executor
from ai_designer.schemas.design_state import DesignRequest, DesignState, ExecutionStatus


def print_design_result(state: DesignState, file=sys.stdout) -> None:
    """Print a human-readable summary of a completed design run."""
    print("", file=file)
    print("--- Design pipeline result ---", file=file)
    print(f"  request_id:   {state.request_id}", file=file)
    print(f"  status:       {state.status.value}", file=file)
    if state.error_message:
        print(f"  error:        {state.error_message}", file=file)
    if state.is_valid is not None:
        print(f"  is_valid:     {state.is_valid}", file=file)
    if state.current_iteration:
        print(f"  iterations:   {state.current_iteration}", file=file)
    if state.task_graph_id:
        print(f"  plan_id:      {state.task_graph_id}", file=file)
    if state.freecad_script:
        preview = state.freecad_script.strip().splitlines()
        head = "\n".join(preview[:12])
        more = len(preview) - 12
        print("  script (head):", file=file)
        for line in head.splitlines():
            print(f"    {line}", file=file)
        if more > 0:
            print(f"    ... ({more} more lines)", file=file)
    print("------------------------------", file=file)


async def run_single_design_async(
    user_prompt: str,
    *,
    max_iterations: int = 5,
    pipeline: Optional[PipelineExecutor] = None,
) -> DesignState:
    """Run one design request through the pipeline."""
    if len(user_prompt.strip()) < 5:
        raise ValueError("Prompt must be at least 5 characters (schema constraint).")
    pipe = pipeline or build_cli_pipeline_executor(max_iterations=max_iterations)
    request = DesignRequest(request_id=uuid4(), user_prompt=user_prompt.strip())
    return await pipe.execute(request)


def run_single_design(
    user_prompt: str,
    *,
    max_iterations: int = 5,
    pipeline: Optional[PipelineExecutor] = None,
) -> DesignState:
    """Sync wrapper for :func:`run_single_design_async`."""
    return asyncio.run(
        run_single_design_async(
            user_prompt, max_iterations=max_iterations, pipeline=pipeline
        )
    )


async def run_interactive_agent_loop(
    *,
    max_iterations: int = 5,
    pipeline: Optional[PipelineExecutor] = None,
) -> None:
    """
    Minimal REPL: natural-language prompts only (same stack as API).

    Advanced debugging commands live behind ``python -m ai_designer --legacy-cli``.
    """
    print(
        "Agent design mode (LangGraph pipeline). Enter a design prompt, or "
        "'exit' / 'quit' to leave.\n"
        "For the legacy FreeCAD CLI (help, state, gui, …), start with: "
        "python -m ai_designer --legacy-cli\n",
        file=sys.stderr,
    )
    pipe = pipeline or build_cli_pipeline_executor(max_iterations=max_iterations)

    while True:
        try:
            line = input("design> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        if len(line) < 5:
            print("Prompt must be at least 5 characters.", file=sys.stderr)
            continue

        try:
            state = await run_single_design_async(
                line, max_iterations=max_iterations, pipeline=pipe
            )
        except Exception as exc:  # noqa: BLE001 — surface any failure to the REPL user
            print(f"Error: {exc}", file=sys.stderr)
            continue

        if state.status == ExecutionStatus.COMPLETED:
            print("Status: completed")
        elif state.status == ExecutionStatus.FAILED:
            print("Status: failed", file=sys.stderr)
        else:
            print(f"Status: {state.status.value}")
        print_design_result(state)


def run_interactive_agent(
    *,
    max_iterations: int = 5,
    pipeline: Optional[PipelineExecutor] = None,
) -> None:
    asyncio.run(
        run_interactive_agent_loop(max_iterations=max_iterations, pipeline=pipeline)
    )

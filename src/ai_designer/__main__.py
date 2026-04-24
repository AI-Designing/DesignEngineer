#!/usr/bin/env python3
"""
AI Designer Package Main Entry Point
This file allows running the package with: python -m ai_designer
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Optional, Sequence

from ai_designer.runtime.cli_routing import (
    build_parser,
    parse_arguments,
    resolve_runtime_route,
    warn_deprecated_enhanced_flag_if_needed,
)

# Load .env files so API keys (OPPER_API_KEY etc.) are available before any imports
try:
    from dotenv import load_dotenv

    _here = os.path.dirname(os.path.abspath(__file__))
    # _here = src/ai_designer/ → ../../ = project root (freecad-llm-automation/)
    _project_root = os.path.abspath(os.path.join(_here, "..", ".."))
    load_dotenv(
        os.path.join(_project_root, ".env"), override=False
    )  # root .env (OPPER_API_KEY, infra)
    load_dotenv(
        os.path.join(_project_root, "src", ".env"), override=False
    )  # src/.env (legacy keys)
except ImportError:
    pass  # python-dotenv not installed; fall back to env vars already set

# Ensure the package is importable when run as ``python src/.../__main__.py``
if __name__ == "__main__":
    package_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(package_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)


def _emit_legacy_cli_notice() -> None:
    print(
        "[ai_designer] Using legacy FreeCAD CLI (--legacy-cli). "
        'Canonical design path: python -m ai_designer "<prompt>" '
        "or HTTP POST /api/v1/design. Details: docs/ENTRYPOINTS.md\n",
        file=sys.stderr,
    )


def _emit_legacy_enhanced_notice() -> None:
    print(
        "[ai_designer] Using legacy SystemOrchestrator (--legacy-enhanced). "
        "Prefer the default agent pipeline for new CAD generation. "
        "See docs/ENTRYPOINTS.md\n",
        file=sys.stderr,
    )


def _run_legacy_enhanced(args: argparse.Namespace) -> None:
    warn_deprecated_enhanced_flag_if_needed(args)
    if args.legacy_cli:
        print(
            "[ai_designer] Both --legacy-cli and legacy enhanced flags were set; "
            "using legacy enhanced only.\n",
            file=sys.stderr,
        )
    _emit_legacy_enhanced_notice()

    from ai_designer.core.orchestrator import SystemOrchestrator

    config = {
        "redis_host": args.redis_host,
        "redis_port": args.redis_port,
        "llm_provider": args.llm_provider,
        "llm_api_key": args.llm_api_key,
        "headless": args.headless,
        "max_concurrent": args.max_concurrent,
        "enable_realtime": not args.disable_realtime,
        "websocket_host": "localhost",
        "websocket_port": args.websocket_port,
        "state_checkpoint_interval": 30,
    }

    print("Starting legacy enhanced AI Designer (SystemOrchestrator)")
    print(f"LLM provider: {config['llm_provider']}")
    print(
        f"Real-time features: {'enabled' if config['enable_realtime'] else 'disabled'}"
    )

    async def run_enhanced() -> None:
        orchestrator = SystemOrchestrator(config)

        try:
            orchestrator.start_system()
            print("Legacy enhanced system started.")

            if args.command:
                command = " ".join(args.command)
                session_id = "cli_session"
                print(f"Executing: {command}")
                result = orchestrator.process_user_input_enhanced(command, session_id)

                status = result.get("status", "unknown")
                if status == "success":
                    print("Command finished successfully.")
                else:
                    print(f"Command failed: {result.get('error', 'Unknown error')}")
            else:
                print("Interactive mode — type 'exit' or 'quit' to stop.")
                session_id = "interactive_session"
                while True:
                    try:
                        command = input("AI Designer> ").strip()
                        if command.lower() in ["exit", "quit"]:
                            break
                        if not command:
                            continue

                        result = orchestrator.process_user_input_enhanced(
                            command, session_id
                        )
                        status = result.get("status", "unknown")

                        if status == "success":
                            print("Command finished successfully.")
                        else:
                            print(f"Error: {result.get('error', 'Unknown error')}")

                    except (KeyboardInterrupt, EOFError):
                        break

        finally:
            orchestrator.stop_system()

    asyncio.run(run_enhanced())


def _run_legacy_cli(args: argparse.Namespace) -> None:
    from ai_designer.cli import FreeCADCLI

    _emit_legacy_cli_notice()
    auto_gui = args.auto_gui and not args.no_auto_gui

    cli = FreeCADCLI(
        use_headless=args.headless,
        llm_provider=args.llm_provider,
        llm_api_key=args.llm_api_key,
        auto_open_gui=auto_gui,
    )

    if args.analyze:
        print(f"Analyzing file: {args.analyze}")
        if cli.initialize():
            cli.analyze_state(args.analyze)
    elif args.command:
        command = " ".join(args.command)
        print(f"Executing command: {command}")
        if cli.initialize():
            cli.execute_command(command)
    else:
        print("Legacy FreeCAD interactive mode")
        print("Type 'help' for commands, 'quit' to exit")
        print("Auto-save is enabled when using real execution paths in this CLI.")
        if auto_gui:
            print("Auto-GUI is enabled — objects may open in FreeCAD GUI.")
        else:
            print("Auto-GUI is disabled — use the 'gui' command to view objects.")
        cli.interactive_mode()


def _run_canonical(args: argparse.Namespace) -> None:
    """LangGraph agent pipeline (same stack as FastAPI ``POST /api/v1/design``)."""
    from ai_designer.cli_agent import (
        print_design_result,
        run_interactive_agent,
        run_single_design,
    )

    if args.analyze:
        # Still uses legacy analyzer implementation today
        print(
            "[ai_designer] --analyze uses the legacy FreeCADCLI analyzer.\n",
            file=sys.stderr,
        )
        _run_legacy_cli_namespace(args, force_analyze_only=True)
        return

    if args.command:
        prompt = " ".join(args.command)
        print(f"Running agent pipeline for: {prompt!r}")
        try:
            state = run_single_design(prompt, max_iterations=args.max_iterations)
        except Exception as exc:  # noqa: BLE001
            print(f"Pipeline failed to start or run: {exc}", file=sys.stderr)
            sys.exit(1)
        print_design_result(state)
        if state.status.value == "failed":
            sys.exit(1)
        return

    # Default: minimal agent REPL
    if args.interactive:
        print(
            "[ai_designer] Note: --interactive is implicit in default agent REPL mode.\n",
            file=sys.stderr,
        )
    run_interactive_agent(max_iterations=args.max_iterations)


def _run_legacy_cli_namespace(
    args: argparse.Namespace, *, force_analyze_only: bool = False
) -> None:
    """Invoke FreeCADCLI without emitting the legacy notice twice when nested."""
    from ai_designer.cli import FreeCADCLI

    auto_gui = args.auto_gui and not args.no_auto_gui
    cli = FreeCADCLI(
        use_headless=args.headless,
        llm_provider=args.llm_provider,
        llm_api_key=args.llm_api_key,
        auto_open_gui=auto_gui,
    )

    if force_analyze_only or args.analyze:
        path = args.analyze
        print(f"Analyzing file: {path}")
        if cli.initialize():
            cli.analyze_state(path)
        return

    if args.command:
        command = " ".join(args.command)
        print(f"Executing command: {command}")
        if cli.initialize():
            cli.execute_command(command)
    else:
        print("Legacy FreeCAD interactive mode")
        print("Type 'help' for commands, 'quit' to exit")
        cli.interactive_mode()


def main(argv: Optional[Sequence[str]] = None) -> None:
    """
    Main entry point for AI Designer.

    Args:
        argv: Optional argv list (defaults to ``sys.argv[1:]``) for testing.
    """
    args = parse_arguments(argv)
    print("AI Designer - FreeCAD LLM Automation System")
    print("=" * 50)

    route = resolve_runtime_route(args)

    if route == "legacy_enhanced":
        _run_legacy_enhanced(args)
    elif route == "legacy_cli":
        _run_legacy_cli(args)
    else:
        _run_canonical(args)


if __name__ == "__main__":
    main()

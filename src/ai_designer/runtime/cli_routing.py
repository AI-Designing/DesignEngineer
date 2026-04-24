"""
CLI argument parsing and canonical vs legacy route resolution.

Kept free of heavy imports (``cli.FreeCADCLI``, orchestrator) so tests and
``python -c`` snippets can run without optional LLM/FreeCAD deps.
"""

from __future__ import annotations

import argparse
import os
import warnings
from typing import Literal, Optional, Sequence

# Redis defaults (match ``__main__`` env convention)
_REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
_REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

RuntimeRoute = Literal["canonical", "legacy_cli", "legacy_enhanced"]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser (used by tests and ``__main__``)."""
    parser = argparse.ArgumentParser(
        description="AI Designer - FreeCAD LLM Automation System"
    )

    parser.add_argument(
        "--legacy-cli",
        action="store_true",
        help=(
            "Use the legacy FreeCAD CLI (rich REPL, command executor, WebSocket hooks). "
            "Prefer the default agent pipeline for new work; see docs/ENTRYPOINTS.md."
        ),
    )
    parser.add_argument(
        "--legacy-enhanced",
        action="store_true",
        help=(
            "Use the legacy SystemOrchestrator stack (Redis, real-time). "
            "See docs/ENTRYPOINTS.md."
        ),
    )

    parser.add_argument(
        "--llm-provider",
        choices=["openai", "google"],
        default="openai",
        help="LLM provider to use (default: openai)",
    )
    parser.add_argument("--llm-api-key", type=str, help="API key for the LLM provider")

    parser.add_argument(
        "--interactive", action="store_true", help="Start in interactive mode"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default: True)",
    )
    parser.add_argument(
        "--auto-gui",
        action="store_true",
        default=True,
        help="Automatically open objects in FreeCAD GUI after creation (default: True)",
    )
    parser.add_argument(
        "--no-auto-gui", action="store_true", help="Disable automatic GUI opening"
    )

    parser.add_argument(
        "--enhanced",
        action="store_true",
        help="Deprecated: same as --legacy-enhanced.",
    )
    parser.add_argument(
        "--redis-host",
        default=_REDIS_HOST,
        help=f"Redis host for enhanced mode (default: {_REDIS_HOST})",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=_REDIS_PORT,
        help=f"Redis port for enhanced mode (default: {_REDIS_PORT})",
    )
    parser.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket port for enhanced mode (default: 8765)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent operations for enhanced mode (default: 3)",
    )
    parser.add_argument(
        "--disable-realtime",
        action="store_true",
        help="Disable real-time WebSocket features in enhanced mode",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        metavar="N",
        help="Max LangGraph refinement iterations for the agent pipeline (default: 5)",
    )

    parser.add_argument(
        "--analyze", type=str, metavar="FILE", help="Analyze a FreeCAD file"
    )

    parser.add_argument("command", nargs="*", help="Command to execute")
    return parser


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    return build_parser().parse_args(argv)


def warn_deprecated_enhanced_flag_if_needed(args: argparse.Namespace) -> None:
    """Emit ``DeprecationWarning`` when ``--enhanced`` is used without ``--legacy-enhanced``."""
    if args.enhanced and not args.legacy_enhanced:
        warnings.warn(
            "Flag --enhanced is deprecated; use --legacy-enhanced instead.",
            DeprecationWarning,
            stacklevel=2,
        )


def resolve_runtime_route(args: argparse.Namespace) -> RuntimeRoute:
    """
    Decide which runtime stack to use.

    ``--legacy-enhanced`` (or deprecated ``--enhanced``) wins over ``--legacy-cli``.
    """
    if args.legacy_enhanced or args.enhanced:
        return "legacy_enhanced"
    if args.legacy_cli:
        return "legacy_cli"
    return "canonical"

"""CLI routing for Track 1 canonical vs legacy entrypoints."""

from __future__ import annotations

import warnings

import pytest

from ai_designer.runtime.cli_routing import (
    build_parser,
    parse_arguments,
    resolve_runtime_route,
    warn_deprecated_enhanced_flag_if_needed,
)


@pytest.mark.parametrize(
    "argv,expected",
    [
        ([], "canonical"),
        (["--legacy-cli"], "legacy_cli"),
        (["--legacy-enhanced"], "legacy_enhanced"),
        (["--enhanced"], "legacy_enhanced"),
        (["--legacy-cli", "--legacy-enhanced"], "legacy_enhanced"),
        (["--legacy-enhanced", "--legacy-cli"], "legacy_enhanced"),
        (["--legacy-cli", "help"], "legacy_cli"),
        (["some", "prompt"], "canonical"),
    ],
)
def test_resolve_runtime_route(argv: list[str], expected: str) -> None:
    args = parse_arguments(argv)
    assert resolve_runtime_route(args) == expected


def test_enhanced_emits_deprecation_warning() -> None:
    args = parse_arguments(["--enhanced"])
    assert resolve_runtime_route(args) == "legacy_enhanced"
    with pytest.warns(DeprecationWarning, match="--legacy-enhanced"):
        warn_deprecated_enhanced_flag_if_needed(args)


def test_legacy_enhanced_explicit_no_deprecation_warning() -> None:
    args = parse_arguments(["--legacy-enhanced"])
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        warn_deprecated_enhanced_flag_if_needed(args)
        assert w == []


def test_both_enhanced_flags_no_deprecation_warning() -> None:
    args = parse_arguments(["--enhanced", "--legacy-enhanced"])
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        warn_deprecated_enhanced_flag_if_needed(args)
        assert w == []


def test_max_iterations_and_positional_prompt() -> None:
    args = parse_arguments(["--max-iterations", "7", "make", "a", "10mm", "cube"])
    assert resolve_runtime_route(args) == "canonical"
    assert args.max_iterations == 7
    assert args.command == ["make", "a", "10mm", "cube"]


def test_build_parser_help_does_not_crash() -> None:
    parser = build_parser()
    parser.print_help()

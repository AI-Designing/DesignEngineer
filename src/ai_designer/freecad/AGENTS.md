# AGENTS.md — `src/ai_designer/freecad`

## Purpose

FreeCAD integration — headless execution, state extraction, path resolution.

## Production role

Execution and geometry I/O for the Executor agent.

## Key modules

headless_runner.py, api_client.py, state_extractor.py, path_resolver.py, state_diff.py

## Dependencies

sandbox/ for script safety; path_resolver for FREECAD_PATH.

## Conventions

Prefer HeadlessRunner for production; no raw exec().

## Commands

pytest tests/unit/freecad/

## Do not

Do not hardcode host-specific FreeCAD paths.

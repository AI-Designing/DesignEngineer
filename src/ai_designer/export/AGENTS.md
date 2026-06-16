# AGENTS.md — `src/ai_designer/export`

## Purpose

CAD export helpers (STL, STEP, etc.).

## Production role

Used by API export endpoints and Executor outputs.

## Key modules

exporter.py

## Dependencies

freecad/ headless paths

## Conventions

Validate output paths under outputs/.

## Commands

pytest tests/integration/api/test_export_endpoints.py

## Do not

Do not write outside configured output directories.

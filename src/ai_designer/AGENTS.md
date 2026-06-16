# AGENTS.md — `src/ai_designer`

## Purpose

Root Python package for AI Designer.

## Production role

Organizes API, agents, orchestration, FreeCAD, LLM, and shared infra.

## Key modules

__init__.py, api/, agents/, orchestration/, runtime/, freecad/, llm/, sandbox/, schemas/

## Dependencies

May import any subpackage. Must not depend on tools/ or tests/.

## Conventions

API-only runtime; no CLI modules. Prefer schemas for I/O contracts.

## Commands

pytest tests/unit; mypy src/ai_designer

## Do not

Do not add cli.py or __main__.py entry points.

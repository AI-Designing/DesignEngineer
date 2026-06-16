# AGENTS.md — `src/ai_designer/schemas`

## Purpose

Pydantic models for API, pipeline state, plans, and validation scores.

## Production role

Shared contracts across api/, agents/, orchestration/.

## Key modules

design_state.py, api_schemas.py, planner_plan.py, task_graph.py, validation.py

## Dependencies

pydantic only — no business logic imports.

## Conventions

Backward-compatible field additions preferred over renames.

## Commands

pytest tests/unit/schemas/

## Do not

Do not import agents or freecad here.

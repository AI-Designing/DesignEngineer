# AGENTS.md — `src/ai_designer/services`

## Purpose

Application services (state persistence helpers).

## Production role

state_service.py bridges FreeCAD state and Redis.

## Key modules

state_service.py

## Dependencies

freecad/state_manager.py, redis_utils/

## Conventions

Async-friendly where used from API.

## Commands

pytest tests/integration/

## Do not

Do not duplicate redis_utils low-level client code.

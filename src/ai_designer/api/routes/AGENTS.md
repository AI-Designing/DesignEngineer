# AGENTS.md — `src/ai_designer/api/routes`

## Purpose

HTTP and WebSocket route handlers.

## Production role

Maps REST/WS to pipeline and health endpoints.

## Key modules

design.py, health.py, ws.py, agent_config.py

## Dependencies

Use api/deps.py for agent instances; schemas for request/response bodies.

## Conventions

Pydantic models from schemas/api_schemas.py and design_state.py.

## Commands

pytest tests/integration/test_api.py

## Do not

Do not call FreeCAD or LLM providers directly — use injected agents.

# AGENTS.md — `src/ai_designer/api`

## Purpose

FastAPI application factory, dependency injection, middleware wiring.

## Production role

Production HTTP/WebSocket gateway — sole external runtime.

## Key modules

app.py (create_app, main), deps.py, middleware/, routes/

## Dependencies

Imports agents/, orchestration/, schemas/, core/ (exceptions, metrics).

## Conventions

Thin routes; business logic in agents/ and orchestration/.

## Commands

uvicorn ai_designer.api.app:app --reload

## Do not

Do not embed LLM prompts or FreeCAD execution here.

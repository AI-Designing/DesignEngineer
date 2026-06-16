# AGENTS.md — `src/ai_designer/runtime`

## Purpose

Pipeline factory and startup wiring shared by API deps.

## Production role

build_cli_pipeline_executor → build_pipeline_executor for DI.

## Key modules

pipeline_factory.py

## Dependencies

orchestration/, agents/, llm/provider.py

## Conventions

Single factory for consistent agent configuration.

## Commands

pytest tests/unit/orchestration/

## Do not

Do not add CLI routing modules.

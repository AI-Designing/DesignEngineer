# AGENTS.md — `src/ai_designer/agents`

## Purpose

Multi-agent LLM workers (Planner, Generator, Validator, Orchestrator, Executor).

## Production role

Core intelligence layer invoked by orchestration/pipeline.py.

## Key modules

planner.py, generator.py, validator.py, orchestrator.py, executor.py, base.py

## Dependencies

llm/provider.py, schemas/, freecad/ (executor only), sandbox/.

## Conventions

Extend BaseAgent; use get_logger from core/logging_config.

## Commands

pytest tests/unit/agents/

## Do not

Do not import api/ or CLI modules.

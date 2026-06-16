# AGENTS.md — `src/ai_designer/core`

## Purpose

Cross-cutting infrastructure only.

## Production role

exceptions, structured logging, Prometheus metrics.

## Key modules

exceptions.py, logging_config.py, metrics.py

## Dependencies

stdlib + structlog/prometheus as needed

## Conventions

No domain logic — keep this package minimal.

## Commands

mypy src/ai_designer/core

## Do not

Do not reintroduce orchestrators or LLM code here.

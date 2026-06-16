# AGENTS.md — `src/ai_designer/orchestration`

## Purpose

StateGraph pipeline — wires agents with conditional routing and retries.

## Production role

Executes Planner → Generator → Validator → Executor flow.

## Key modules

pipeline.py, nodes.py, routing.py, state.py, callbacks.py

## Dependencies

agents/, schemas/design_state.py, core/exceptions.py

## Conventions

Node functions are pure-ish; side effects in agents only.

## Commands

pytest tests/integration/test_pipeline.py tests/unit/orchestration/

## Do not

Do not duplicate agent logic inside nodes.

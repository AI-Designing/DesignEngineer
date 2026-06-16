# AGENTS.md — `src/ai_designer/agents/prompts`

## Purpose

System prompts, few-shot examples, FreeCAD API reference snippets.

## Production role

Prompt assets consumed by agents.

## Key modules

system_prompts.py, few_shot_examples.py, freecad_reference.py, error_correction.py

## Dependencies

Imported only by agents/ — no runtime side effects.

## Conventions

Keep prompts versioned in git; test prompt changes via agent unit tests.

## Commands

pytest tests/unit/agents/

## Do not

Do not hardcode API keys or user-specific paths in prompts.

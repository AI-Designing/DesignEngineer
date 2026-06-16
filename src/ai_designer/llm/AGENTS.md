# AGENTS.md — `src/ai_designer/llm`

## Purpose

Unified LLM provider (Opper) and per-agent model configuration.

## Production role

All LLM calls route through provider.py.

## Key modules

provider.py, model_config.py, agent_config_store.py, prompt_templates.py

## Dependencies

core/exceptions.py, schemas/llm_schemas.py

## Conventions

OPPER_API_KEY from env; per-agent tags for analytics.

## Commands

pytest tests/unit/llm/

## Do not

Do not add legacy client wrappers — extend provider.py.

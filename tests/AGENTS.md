# AGENTS.md — `tests`

## Purpose

Test suite root — unit, integration, benchmarks, load.

## Production role

Validates production API pipeline and modules.

## Key modules

conftest.py, unit/, integration/, benchmarks/, load/

## Dependencies

pytest, pytest-mock, httpx for API tests

## Conventions

Mirror src/ai_designer/ layout; mark integration tests.

## Commands

make test-unit; make test-integration

## Do not

Do not require live OPPER calls in unit tests — mock LLM.

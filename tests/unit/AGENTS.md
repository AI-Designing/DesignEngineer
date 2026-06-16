# AGENTS.md — `tests/unit`

## Purpose

Fast isolated tests with mocks.

## Production role

No Redis/FreeCAD required for most tests.

## Key modules

agents/, freecad/, sandbox/, schemas/, llm/, orchestration/

## Dependencies

conftest.py fixtures

## Conventions

Use @pytest.mark.skipif for optional FreeCAD binaries.

## Commands

make test-unit

## Do not

Do not hit production APIs or commit secrets in fixtures.

# AGENTS.md — `src/ai_designer/utils`

## Purpose

Non-domain helpers and analysis utilities.

## Production role

Shared small functions not tied to a domain package.

## Key modules

helpers.py, analysis.py

## Dependencies

Avoid importing agents/ or api/

## Conventions

Keep utilities generic.

## Commands

pytest tests/unit/

## Do not

Do not place FreeCAD execution logic here.

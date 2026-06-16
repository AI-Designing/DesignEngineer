# AGENTS.md — `src/ai_designer/sandbox`

## Purpose

AST validation and subprocess-isolated script execution.

## Production role

Security boundary for generated FreeCAD Python.

## Key modules

sandbox.py, validator.py, executor.py, freecad_execution.py, result.py

## Dependencies

stdlib only + internal modules.

## Conventions

Whitelist FreeCAD modules; block os/sys/subprocess in user scripts.

## Commands

pytest tests/unit/sandbox/

## Do not

Never disable validation in production paths.

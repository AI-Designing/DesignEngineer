# AGENTS.md — `src/ai_designer/parsers`

## Purpose

Natural-language command parsing utilities.

## Production role

Optional helpers; primary NL handling is in Planner agent.

## Key modules

command_parser.py

## Dependencies

Minimal — avoid heavy imports

## Conventions

Pure functions where possible.

## Commands

pytest tests/unit/ -k parser

## Do not

Do not become a second orchestration layer.

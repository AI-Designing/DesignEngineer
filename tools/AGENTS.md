# AGENTS.md — `tools`

## Purpose

Dev-only scripts — not part of the installed package.

## Production role

Demos, monitors, debug helpers.

## Key modules

demo_screenshot.sh, monitoring/, gui/, testing/

## Dependencies

May call HTTP API; must not be production entry points

## Conventions

No hardcoded API keys or user home paths

## Commands

tools/demo_screenshot.sh (API must be running)

## Do not

Do not import tools/ from src/ai_designer/.

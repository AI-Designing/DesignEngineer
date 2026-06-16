# AGENTS.md — `docker`

## Purpose

Container build definitions.

## Production role

Dockerfile.production for prod; Dockerfile.dev for local dev.

## Key modules

Dockerfile.production, Dockerfile.dev

## Dependencies

pyproject.toml dependencies

## Conventions

CMD runs uvicorn ai_designer.api.app:app

## Commands

docker compose --profile prod build

## Do not

Do not bake .env secrets into images.

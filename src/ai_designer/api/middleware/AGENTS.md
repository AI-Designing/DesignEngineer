# AGENTS.md — `src/ai_designer/api/middleware`

## Purpose

Auth and rate-limit middleware.

## Production role

Protects API routes before handlers run.

## Key modules

auth.py, rate_limit.py

## Dependencies

redis_utils for rate limiting; env for JWT secrets.

## Conventions

Middleware order matters — see app.py registration.

## Commands

pytest tests/integration/

## Do not

Do not bypass auth in production code paths.

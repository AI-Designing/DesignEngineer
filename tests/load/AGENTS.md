# AGENTS.md — `tests/load`

## Purpose

Locust load tests for API endpoints.

## Production role

Performance and soak testing — not run in default CI.

## Key modules

locustfile.py, README.md

## Dependencies

locust; running API + Redis

## Conventions

Run against dev/staging only.

## Commands

locust -f tests/load/locustfile.py

## Do not

Do not load-test production without approval.

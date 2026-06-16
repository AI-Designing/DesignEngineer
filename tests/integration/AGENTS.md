# AGENTS.md — `tests/integration`

## Purpose

API and pipeline integration tests.

## Production role

Requires Redis; may use TestClient.

## Key modules

test_api.py, test_pipeline.py, api/test_export_endpoints.py

## Dependencies

Redis running on localhost:6379

## Conventions

pytest markers: integration

## Commands

make test-integration

## Do not

Do not depend on removed CLI entry points.

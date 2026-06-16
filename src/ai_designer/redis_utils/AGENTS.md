# AGENTS.md — `src/ai_designer/redis_utils`

## Purpose

Redis client, state cache, audit trail, pub/sub bridge.

## Production role

Persistence and real-time event bus.

## Key modules

client.py, state_cache.py, audit.py, pubsub_bridge.py

## Dependencies

redis package; config from env.

## Conventions

Graceful degradation when Redis unavailable in tests.

## Commands

pytest tests/integration/

## Do not

Do not store secrets in Redis keys.

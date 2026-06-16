# AGENTS.md — `src/ai_designer/realtime`

## Purpose

WebSocket progress manager for design pipeline events.

## Production role

Pushes status updates to /ws clients.

## Key modules

websocket_manager.py

## Dependencies

redis_utils/pubsub_bridge.py optional

## Conventions

JSON-serializable event payloads only.

## Commands

pytest tests/integration/

## Do not

Do not block the pipeline on slow WS clients.

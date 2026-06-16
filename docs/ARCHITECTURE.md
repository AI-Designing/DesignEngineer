# Architecture

## Overview

Natural-language CAD requests enter through the **FastAPI gateway**, run through a **multi-agent pipeline** (`PipelineExecutor`), and execute FreeCAD Python in a **sandboxed headless runner**.

```
Client (HTTP/WS)
    → api/ (routes, auth, rate limits)
    → orchestration/ (StateGraph pipeline)
    → agents/ (Planner → Generator → Validator → Executor)
    → freecad/ (headless_runner, state extraction)
    → sandbox/ (AST validation, safe execution)
    → redis_utils/ (cache, audit, pubsub)
```

## Agents

| Agent | Role |
|-------|------|
| **Planner** | Decomposes user intent into a task graph |
| **Generator** | Produces FreeCAD Python per task |
| **Validator** | Scores geometry and script quality; drives retries |
| **Executor** | Runs scripts via `HeadlessRunner` |
| **Orchestrator** | Coordinates iteration and routing decisions |

LLM calls go through `llm/provider.py` (`UnifiedLLMProvider`, Opper-backed).

## Shared infrastructure

- **Redis** — state cache, audit trail, rate limiting, pub/sub
- **WebSocket** — `realtime/websocket_manager.py` for progress events
- **Schemas** — Pydantic contracts in `schemas/` (API + pipeline)
- **core/** — exceptions, structured logging, Prometheus metrics only

## Configuration

| Source | Purpose |
|--------|---------|
| `.env` | Secrets (`OPPER_API_KEY`, Redis, auth) |
| `config/config.yaml` | FreeCAD paths, agent model overrides |
| `llm/model_config.py` | Default per-agent model routing |

## Deployment

- **Production image:** `docker/Dockerfile.production` → `uvicorn ai_designer.api.app:app`
- **Dev image:** `docker/Dockerfile.dev` with mounted `src/`
- Optional **Prometheus** profile: `docker compose --profile monitoring up`

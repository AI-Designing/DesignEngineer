# AGENTS.md — AI Designer (repository root)

## Mission

Natural-language → FreeCAD automation via a **multi-agent LLM pipeline**, deployed as a **FastAPI service** (API-only — no CLI runtime).

## Architecture

```
HTTP/WS → api/ → orchestration/ → agents/ → freecad/ + sandbox/
                ↘ redis_utils/ + realtime/
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ENTRYPOINTS.md](docs/ENTRYPOINTS.md).

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `OPPER_API_KEY` | Yes | Opper LLM platform key |
| `REDIS_URL` / `REDIS_HOST` | Integration/prod | Redis for cache, audit, rate limits |
| `FREECAD_PATH` | Optional | FreeCAD binary or AppImage |
| `FREECAD_ROOT` | Docker dev | Host mount for `/opt/freecad` |

## Dev workflow

```bash
make install-dev
make test-unit
make test-integration   # Redis required
make ci
docker compose --profile dev up
```

## Child AGENTS.md index

| Path | Focus |
|------|-------|
| [src/ai_designer/AGENTS.md](src/ai_designer/AGENTS.md) | Package map |
| [src/ai_designer/api/AGENTS.md](src/ai_designer/api/AGENTS.md) | FastAPI gateway |
| [src/ai_designer/agents/AGENTS.md](src/ai_designer/agents/AGENTS.md) | LLM agents |
| [src/ai_designer/orchestration/AGENTS.md](src/ai_designer/orchestration/AGENTS.md) | Pipeline graph |
| [src/ai_designer/freecad/AGENTS.md](src/ai_designer/freecad/AGENTS.md) | FreeCAD execution |
| [src/ai_designer/sandbox/AGENTS.md](src/ai_designer/sandbox/AGENTS.md) | Script safety |
| [src/ai_designer/llm/AGENTS.md](src/ai_designer/llm/AGENTS.md) | LLM provider |
| [src/ai_designer/schemas/AGENTS.md](src/ai_designer/schemas/AGENTS.md) | Pydantic contracts |
| [tests/AGENTS.md](tests/AGENTS.md) | Test layout |
| [config/AGENTS.md](config/AGENTS.md) | Runtime config |
| [docker/AGENTS.md](docker/AGENTS.md) | Containers |
| [tools/AGENTS.md](tools/AGENTS.md) | Dev scripts |

(Full list: every folder under `src/ai_designer/*` and `tests/*` has its own `AGENTS.md`.)

## Global rules

- **API-only production** — do not add `cli.py`, `__main__.py`, or console CLIs.
- **No raw `exec()`** on generated scripts — use `sandbox/` or `headless_runner`.
- **No hardcoded paths or secrets** — use env and `path_resolver`.
- **No auto git push** — user must request commits explicitly.

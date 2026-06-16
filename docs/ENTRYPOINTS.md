# Runtime Entry Points

AI Designer is **API-only** in production. All design requests flow through the FastAPI service.

## Production

| Entry | Command | Notes |
|-------|---------|-------|
| Docker (prod) | `docker compose --profile prod up` | Builds `docker/Dockerfile.production`, exposes port 8000 |
| Docker (dev) | `docker compose --profile dev up` | Hot-reload via `docker/Dockerfile.dev` |
| Local (optional) | `ai-designer-api` or `uvicorn ai_designer.api.app:app --host 0.0.0.0 --port 8000` | Requires Redis and `OPPER_API_KEY` |

## Primary HTTP routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/api/v1/design` | Submit NL design request (multi-agent pipeline) |
| GET | `/api/v1/design/{request_id}` | Poll design status |
| WS | `/ws/progress/{request_id}` | Real-time pipeline progress |
| GET | `/metrics` | Prometheus metrics |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the agent pipeline and [README.md](../README.md) for setup.

## Removed entry points

The following were removed in the production restructure:

- `python -m ai_designer` / `ai-designer` CLI
- `FreeCADCLI` / `cli_pkg/`
- `SystemOrchestrator` (`--enhanced` / `--legacy-enhanced`)
- Legacy LLM wrappers (`llm/client.py`, `unified_manager.py`, etc.)

Use the HTTP API for all new integrations.

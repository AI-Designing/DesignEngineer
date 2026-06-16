# AI Designer — FreeCAD LLM Automation

Natural-language CAD automation for FreeCAD using a multi-agent LLM pipeline (Planner → Generator → Validator → Executor), exposed as a **production FastAPI service**.

## Features

- Multi-agent design pipeline with retry and validation loops
- Headless FreeCAD script execution with AST sandboxing
- Redis-backed state cache and audit trail
- WebSocket progress streaming
- Prometheus metrics and structured logging
- Docker-based deployment (dev and prod profiles)

## Quick start

```bash
cp .env.example .env
# Set OPPER_API_KEY (https://platform.opper.ai/)

docker compose --profile dev up
curl http://localhost:8000/health
```

Submit a design request:

```bash
curl -X POST http://localhost:8000/api/v1/design \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a 20mm cube with a 5mm hole through the center"}'
```

## Project structure

```
freecad-llm-automation/
├── src/ai_designer/     # Python package
│   ├── api/               # FastAPI gateway (production entry)
│   ├── agents/            # Planner, Generator, Validator, Executor
│   ├── orchestration/     # Pipeline graph
│   ├── runtime/           # Pipeline factory / startup wiring
│   ├── freecad/           # Headless runner, state I/O
│   ├── llm/               # Unified LLM provider (Opper)
│   ├── sandbox/           # AST validation + safe execution
│   ├── schemas/           # Pydantic contracts
│   └── redis_utils/       # Cache, audit, pubsub
├── config/                # config.yaml, redis, prometheus
├── docker/                # Dockerfile.dev, Dockerfile.production
├── tests/                 # unit, integration, benchmarks, load
├── tools/                 # Dev-only utilities (not production API)
├── docs/                  # Architecture and entrypoint docs
└── AGENTS.md              # Agent instructions (see per-folder AGENTS.md)
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design
- [docs/ENTRYPOINTS.md](docs/ENTRYPOINTS.md) — runtime entry points (API-only)
- [CONTRIBUTING.md](CONTRIBUTING.md) — development workflow
- Per-module guidance in `**/AGENTS.md`

## Development

```bash
make install-dev
make test-unit
make test-integration   # Redis required
make ci
```

Local API without Docker:

```bash
pip install -e ".[dev]"
uvicorn ai_designer.api.app:app --reload --port 8000
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPPER_API_KEY` | Yes | Opper platform API key |
| `REDIS_URL` / `REDIS_HOST` | Yes (integration) | Redis connection |
| `FREECAD_PATH` | No | FreeCAD AppImage or binary path |
| `FREECAD_ROOT` | No (Docker) | Host path mounted as `/opt/freecad` in dev compose |

## License

MIT — see [LICENSE](LICENSE).

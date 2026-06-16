#!/usr/bin/env python3
"""Generate per-folder AGENTS.md files for the production restructure."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SPECS: dict[str, dict[str, str]] = {
    "src/ai_designer": {
        "purpose": "Root Python package for AI Designer.",
        "role": "Organizes API, agents, orchestration, FreeCAD, LLM, and shared infra.",
        "modules": "__init__.py, api/, agents/, orchestration/, runtime/, freecad/, llm/, sandbox/, schemas/",
        "deps": "May import any subpackage. Must not depend on tools/ or tests/.",
        "conventions": "API-only runtime; no CLI modules. Prefer schemas for I/O contracts.",
        "commands": "pytest tests/unit; mypy src/ai_designer",
        "dont": "Do not add cli.py or __main__.py entry points.",
    },
    "src/ai_designer/api": {
        "purpose": "FastAPI application factory, dependency injection, middleware wiring.",
        "role": "Production HTTP/WebSocket gateway — sole external runtime.",
        "modules": "app.py (create_app, main), deps.py, middleware/, routes/",
        "deps": "Imports agents/, orchestration/, schemas/, core/ (exceptions, metrics).",
        "conventions": "Thin routes; business logic in agents/ and orchestration/.",
        "commands": "uvicorn ai_designer.api.app:app --reload",
        "dont": "Do not embed LLM prompts or FreeCAD execution here.",
    },
    "src/ai_designer/api/routes": {
        "purpose": "HTTP and WebSocket route handlers.",
        "role": "Maps REST/WS to pipeline and health endpoints.",
        "modules": "design.py, health.py, ws.py, agent_config.py",
        "deps": "Use api/deps.py for agent instances; schemas for request/response bodies.",
        "conventions": "Pydantic models from schemas/api_schemas.py and design_state.py.",
        "commands": "pytest tests/integration/test_api.py",
        "dont": "Do not call FreeCAD or LLM providers directly — use injected agents.",
    },
    "src/ai_designer/api/middleware": {
        "purpose": "Auth and rate-limit middleware.",
        "role": "Protects API routes before handlers run.",
        "modules": "auth.py, rate_limit.py",
        "deps": "redis_utils for rate limiting; env for JWT secrets.",
        "conventions": "Middleware order matters — see app.py registration.",
        "commands": "pytest tests/integration/",
        "dont": "Do not bypass auth in production code paths.",
    },
    "src/ai_designer/agents": {
        "purpose": "Multi-agent LLM workers (Planner, Generator, Validator, Orchestrator, Executor).",
        "role": "Core intelligence layer invoked by orchestration/pipeline.py.",
        "modules": "planner.py, generator.py, validator.py, orchestrator.py, executor.py, base.py",
        "deps": "llm/provider.py, schemas/, freecad/ (executor only), sandbox/.",
        "conventions": "Extend BaseAgent; use get_logger from core/logging_config.",
        "commands": "pytest tests/unit/agents/",
        "dont": "Do not import api/ or CLI modules.",
    },
    "src/ai_designer/agents/prompts": {
        "purpose": "System prompts, few-shot examples, FreeCAD API reference snippets.",
        "role": "Prompt assets consumed by agents.",
        "modules": "system_prompts.py, few_shot_examples.py, freecad_reference.py, error_correction.py",
        "deps": "Imported only by agents/ — no runtime side effects.",
        "conventions": "Keep prompts versioned in git; test prompt changes via agent unit tests.",
        "commands": "pytest tests/unit/agents/",
        "dont": "Do not hardcode API keys or user-specific paths in prompts.",
    },
    "src/ai_designer/orchestration": {
        "purpose": "StateGraph pipeline — wires agents with conditional routing and retries.",
        "role": "Executes Planner → Generator → Validator → Executor flow.",
        "modules": "pipeline.py, nodes.py, routing.py, state.py, callbacks.py",
        "deps": "agents/, schemas/design_state.py, core/exceptions.py",
        "conventions": "Node functions are pure-ish; side effects in agents only.",
        "commands": "pytest tests/integration/test_pipeline.py tests/unit/orchestration/",
        "dont": "Do not duplicate agent logic inside nodes.",
    },
    "src/ai_designer/runtime": {
        "purpose": "Pipeline factory and startup wiring shared by API deps.",
        "role": "build_cli_pipeline_executor → build_pipeline_executor for DI.",
        "modules": "pipeline_factory.py",
        "deps": "orchestration/, agents/, llm/provider.py",
        "conventions": "Single factory for consistent agent configuration.",
        "commands": "pytest tests/unit/orchestration/",
        "dont": "Do not add CLI routing modules.",
    },
    "src/ai_designer/freecad": {
        "purpose": "FreeCAD integration — headless execution, state extraction, path resolution.",
        "role": "Execution and geometry I/O for the Executor agent.",
        "modules": "headless_runner.py, api_client.py, state_extractor.py, path_resolver.py, state_diff.py",
        "deps": "sandbox/ for script safety; path_resolver for FREECAD_PATH.",
        "conventions": "Prefer HeadlessRunner for production; no raw exec().",
        "commands": "pytest tests/unit/freecad/",
        "dont": "Do not hardcode host-specific FreeCAD paths.",
    },
    "src/ai_designer/sandbox": {
        "purpose": "AST validation and subprocess-isolated script execution.",
        "role": "Security boundary for generated FreeCAD Python.",
        "modules": "sandbox.py, validator.py, executor.py, freecad_execution.py, result.py",
        "deps": "stdlib only + internal modules.",
        "conventions": "Whitelist FreeCAD modules; block os/sys/subprocess in user scripts.",
        "commands": "pytest tests/unit/sandbox/",
        "dont": "Never disable validation in production paths.",
    },
    "src/ai_designer/llm": {
        "purpose": "Unified LLM provider (Opper) and per-agent model configuration.",
        "role": "All LLM calls route through provider.py.",
        "modules": "provider.py, model_config.py, agent_config_store.py, prompt_templates.py",
        "deps": "core/exceptions.py, schemas/llm_schemas.py",
        "conventions": "OPPER_API_KEY from env; per-agent tags for analytics.",
        "commands": "pytest tests/unit/llm/",
        "dont": "Do not add legacy client wrappers — extend provider.py.",
    },
    "src/ai_designer/schemas": {
        "purpose": "Pydantic models for API, pipeline state, plans, and validation scores.",
        "role": "Shared contracts across api/, agents/, orchestration/.",
        "modules": "design_state.py, api_schemas.py, planner_plan.py, task_graph.py, validation.py",
        "deps": "pydantic only — no business logic imports.",
        "conventions": "Backward-compatible field additions preferred over renames.",
        "commands": "pytest tests/unit/schemas/",
        "dont": "Do not import agents or freecad here.",
    },
    "src/ai_designer/redis_utils": {
        "purpose": "Redis client, state cache, audit trail, pub/sub bridge.",
        "role": "Persistence and real-time event bus.",
        "modules": "client.py, state_cache.py, audit.py, pubsub_bridge.py",
        "deps": "redis package; config from env.",
        "conventions": "Graceful degradation when Redis unavailable in tests.",
        "commands": "pytest tests/integration/",
        "dont": "Do not store secrets in Redis keys.",
    },
    "src/ai_designer/realtime": {
        "purpose": "WebSocket progress manager for design pipeline events.",
        "role": "Pushes status updates to /ws clients.",
        "modules": "websocket_manager.py",
        "deps": "redis_utils/pubsub_bridge.py optional",
        "conventions": "JSON-serializable event payloads only.",
        "commands": "pytest tests/integration/",
        "dont": "Do not block the pipeline on slow WS clients.",
    },
    "src/ai_designer/export": {
        "purpose": "CAD export helpers (STL, STEP, etc.).",
        "role": "Used by API export endpoints and Executor outputs.",
        "modules": "exporter.py",
        "deps": "freecad/ headless paths",
        "conventions": "Validate output paths under outputs/.",
        "commands": "pytest tests/integration/api/test_export_endpoints.py",
        "dont": "Do not write outside configured output directories.",
    },
    "src/ai_designer/config": {
        "purpose": "Secure configuration loading from env and YAML.",
        "role": "Centralizes secrets and path resolution hooks.",
        "modules": "secure_config.py",
        "deps": "python-dotenv, PyYAML",
        "conventions": "Never log secret values.",
        "commands": "grep OPPER .env.example",
        "dont": "Do not commit credentials.",
    },
    "src/ai_designer/core": {
        "purpose": "Cross-cutting infrastructure only.",
        "role": "exceptions, structured logging, Prometheus metrics.",
        "modules": "exceptions.py, logging_config.py, metrics.py",
        "deps": "stdlib + structlog/prometheus as needed",
        "conventions": "No domain logic — keep this package minimal.",
        "commands": "mypy src/ai_designer/core",
        "dont": "Do not reintroduce orchestrators or LLM code here.",
    },
    "src/ai_designer/parsers": {
        "purpose": "Natural-language command parsing utilities.",
        "role": "Optional helpers; primary NL handling is in Planner agent.",
        "modules": "command_parser.py",
        "deps": "Minimal — avoid heavy imports",
        "conventions": "Pure functions where possible.",
        "commands": "pytest tests/unit/ -k parser",
        "dont": "Do not become a second orchestration layer.",
    },
    "src/ai_designer/services": {
        "purpose": "Application services (state persistence helpers).",
        "role": "state_service.py bridges FreeCAD state and Redis.",
        "modules": "state_service.py",
        "deps": "freecad/state_manager.py, redis_utils/",
        "conventions": "Async-friendly where used from API.",
        "commands": "pytest tests/integration/",
        "dont": "Do not duplicate redis_utils low-level client code.",
    },
    "src/ai_designer/utils": {
        "purpose": "Non-domain helpers and analysis utilities.",
        "role": "Shared small functions not tied to a domain package.",
        "modules": "helpers.py, analysis.py",
        "deps": "Avoid importing agents/ or api/",
        "conventions": "Keep utilities generic.",
        "commands": "pytest tests/unit/",
        "dont": "Do not place FreeCAD execution logic here.",
    },
    "tests": {
        "purpose": "Test suite root — unit, integration, benchmarks, load.",
        "role": "Validates production API pipeline and modules.",
        "modules": "conftest.py, unit/, integration/, benchmarks/, load/",
        "deps": "pytest, pytest-mock, httpx for API tests",
        "conventions": "Mirror src/ai_designer/ layout; mark integration tests.",
        "commands": "make test-unit; make test-integration",
        "dont": "Do not require live OPPER calls in unit tests — mock LLM.",
    },
    "tests/unit": {
        "purpose": "Fast isolated tests with mocks.",
        "role": "No Redis/FreeCAD required for most tests.",
        "modules": "agents/, freecad/, sandbox/, schemas/, llm/, orchestration/",
        "deps": "conftest.py fixtures",
        "conventions": "Use @pytest.mark.skipif for optional FreeCAD binaries.",
        "commands": "make test-unit",
        "dont": "Do not hit production APIs or commit secrets in fixtures.",
    },
    "tests/integration": {
        "purpose": "API and pipeline integration tests.",
        "role": "Requires Redis; may use TestClient.",
        "modules": "test_api.py, test_pipeline.py, api/test_export_endpoints.py",
        "deps": "Redis running on localhost:6379",
        "conventions": "pytest markers: integration",
        "commands": "make test-integration",
        "dont": "Do not depend on removed CLI entry points.",
    },
    "tests/benchmarks": {
        "purpose": "FreeCAD corpus benchmarks and golden scripts.",
        "role": "Regression harness for headless geometry operations.",
        "modules": "corpus.yaml, test_freecad_corpus.py, golden_scripts.py",
        "deps": "FreeCAD binary on PATH or FREECAD_PATH",
        "conventions": "Skip when FreeCAD unavailable.",
        "commands": "pytest tests/benchmarks/ -v",
        "dont": "Do not fail CI when FreeCAD is not installed unless explicitly required.",
    },
    "tests/load": {
        "purpose": "Locust load tests for API endpoints.",
        "role": "Performance and soak testing — not run in default CI.",
        "modules": "locustfile.py, README.md",
        "deps": "locust; running API + Redis",
        "conventions": "Run against dev/staging only.",
        "commands": "locust -f tests/load/locustfile.py",
        "dont": "Do not load-test production without approval.",
    },
    "config": {
        "purpose": "Runtime YAML and infra configs (Redis, Prometheus).",
        "role": "Mounted into Docker containers; read by app at startup.",
        "modules": "config.yaml, redis.conf, prometheus.yml",
        "deps": "Env vars override YAML paths",
        "conventions": "No secrets in config.yaml — use .env",
        "commands": "docker compose config",
        "dont": "Do not commit machine-specific absolute paths.",
    },
    "docker": {
        "purpose": "Container build definitions.",
        "role": "Dockerfile.production for prod; Dockerfile.dev for local dev.",
        "modules": "Dockerfile.production, Dockerfile.dev",
        "deps": "pyproject.toml dependencies",
        "conventions": "CMD runs uvicorn ai_designer.api.app:app",
        "commands": "docker compose --profile prod build",
        "dont": "Do not bake .env secrets into images.",
    },
    "docs": {
        "purpose": "Human-readable architecture and planning docs.",
        "role": "ARCHITECTURE.md and ENTRYPOINTS.md are canonical for runtime.",
        "modules": "ARCHITECTURE.md, ENTRYPOINTS.md, EXECUTION_PLAN.md, AUDIT_REPORT.md",
        "deps": "Keep in sync with README and AGENTS.md",
        "conventions": "API-only entry points documented in ENTRYPOINTS.md",
        "commands": "Read docs/ARCHITECTURE.md before large refactors",
        "dont": "Do not document removed CLI paths as current.",
    },
    "tools": {
        "purpose": "Dev-only scripts — not part of the installed package.",
        "role": "Demos, monitors, debug helpers.",
        "modules": "demo_screenshot.sh, monitoring/, gui/, testing/",
        "deps": "May call HTTP API; must not be production entry points",
        "conventions": "No hardcoded API keys or user home paths",
        "commands": "tools/demo_screenshot.sh (API must be running)",
        "dont": "Do not import tools/ from src/ai_designer/.",
    },
}


def render(rel: str, spec: dict[str, str]) -> str:
    name = rel.split("/")[-1] or "repository root"
    return f"""# AGENTS.md — `{rel}`

## Purpose

{spec["purpose"]}

## Production role

{spec["role"]}

## Key modules

{spec["modules"]}

## Dependencies

{spec["deps"]}

## Conventions

{spec["conventions"]}

## Commands

{spec["commands"]}

## Do not

{spec["dont"]}
"""


ROOT_MD = """# AGENTS.md — AI Designer (repository root)

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
"""


def main() -> None:
    (ROOT / "AGENTS.md").write_text(ROOT_MD, encoding="utf-8")
    for rel, spec in SPECS.items():
        path = ROOT / rel / "AGENTS.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(rel, spec), encoding="utf-8")
    print(f"Wrote {len(SPECS) + 1} AGENTS.md files")


if __name__ == "__main__":
    main()

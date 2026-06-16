# Contributing

## Setup

```bash
cp .env.example .env   # add OPPER_API_KEY and Redis settings
make install-dev
```

## Development workflow

```bash
make format
make lint
make test-unit
make test-integration   # requires Redis
make ci
```

## Running the API locally

```bash
docker compose --profile dev up
# or
uvicorn ai_designer.api.app:app --reload --port 8000
```

## Code guidelines

- Production runtime is **API-only** — do not reintroduce CLI entry points.
- Use `schemas/` for request/response contracts.
- Route LLM calls through `llm/provider.py`.
- Execute generated scripts via `sandbox/` or `freecad/headless_runner.py` — never raw `exec()`.
- Add tests under `tests/unit/` or `tests/integration/` mirroring `src/ai_designer/`.
- Update the relevant folder `AGENTS.md` when changing module boundaries.

## Pull requests

- Keep diffs focused; one concern per PR when possible.
- Ensure `make ci` passes before requesting review.
- Do not commit `.env`, credentials, or machine-specific paths.

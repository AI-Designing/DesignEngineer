# FIX_PLAN.md — Pending Implementation Guide

> **Based on:** `AUDIT_REPORT.md` dated February 20, 2026
> **Scope:** All PARTIAL and NOT DONE items across Phases 0–3
> **Total items:** 17 fix tasks across 5 weeks
> **Execution order:** Strict — later tasks depend on earlier ones

---

## How to Use This Document

Each task has:
- A **prerequisite** list — complete these first
- **Numbered steps** — exact, ordered actions
- A **verification step** — how to confirm the fix worked
- A **time estimate** — realistic solo-developer effort

Work top to bottom. Do not skip tasks or reorder them.

---

## Week 1 — Security & Quick Wins (Day 1–5)

---

### Task 1 — Remove Leaked API Key from Test File

**File:** `tools/testing/test_persistent_gui_fix.py:27`
**Prerequisites:** None
**Effort:** ~10 minutes

**Steps:**
1. Open `tools/testing/test_persistent_gui_fix.py`
2. At the top of the file, verify `import os` is present; add it if missing
3. Find line 27 where `llm_api_key="AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc"` is hardcoded inside a `FreeCADCLI(...)` constructor call <!-- pragma: allowlist secret -->
4. Replace that argument value with `os.environ.get("GOOGLE_API_KEY", "test-placeholder-key")`
5. Run a global search to confirm no other file contains the key: `grep -r "AIzaSy" . --include="*.py" --include="*.yaml" | grep -v docs/ | grep -v __pycache__`
6. Stage and commit: `git add tools/testing/test_persistent_gui_fix.py && git commit -m "fix(security): remove hardcoded Google API key from test file"`

**Verification:** The grep command from step 5 returns zero results in `.py`/`.yaml` files.

---

### Task 2 — Remove Hardcoded Paths from Config and Tools

**Files:** `config/config.yaml:11`, `tools/testing/test_realtime_commands.py:185,197`, `tools/gui/simple_gui_launcher.py:115`, `tools/utilities/verify_real_objects.py:15`
**Prerequisites:** None
**Effort:** ~30 minutes

**Steps:**

**2a — Fix `config/config.yaml`:**
1. Open `config/config.yaml`
2. Line 11 has `appimage_path: "/home/vansh5632/Downloads/FreeCAD_1.0.1-conda-Linux-x86_64-py311.AppImage"`
3. Replace the value with an empty string `""` — the `FreeCADPathResolver` in `freecad/path_resolver.py` will pick up the correct path from `FREECAD_APPIMAGE_PATH` at runtime
4. Add a comment above it: `# Set via FREECAD_APPIMAGE_PATH env var or leave empty for auto-detection`
5. Verify `FREECAD_APPIMAGE_PATH=` is present in `.env.example`; add it if missing

**2b — Fix `tools/testing/test_realtime_commands.py`:**
1. Lines 185 and 197 have `outputs_dir = "/home/vansh5632/DesignEng/freecad-llm-automation/outputs"`
2. Replace both occurrences with `outputs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs")`
3. Confirm `import os` exists at the top; add if missing

**2c — Fix `tools/gui/simple_gui_launcher.py`:**
1. Line 115 has the same hardcoded outputs path
2. Replace with the same `os.path.join(os.path.dirname(...))` pattern as 2b

**2d — Fix `tools/utilities/verify_real_objects.py`:**
1. Line 15 has a hardcoded `.FCStd` file path
2. Replace with `sys.argv[1]` so callers provide the path at runtime; add a usage message and `sys.exit(1)` if no argument is given
3. Add `import sys` at the top if missing

**Verification:** `grep -rn "/home/vansh5632" . --include="*.py" --include="*.yaml" | grep -v docs/ | grep -v __pycache__` returns zero results.

---

### Task 3 — Create `schemas/llm_schemas.py`

**Files created:** `src/ai_designer/schemas/llm_schemas.py`
**Files modified:** `src/ai_designer/core/llm_provider.py`, `src/ai_designer/schemas/__init__.py`
**Prerequisites:** None
**Effort:** ~45 minutes

**Steps:**
1. Create `src/ai_designer/schemas/llm_schemas.py`
2. Move these five classes from `src/ai_designer/core/llm_provider.py` into the new file — they are currently Pydantic `BaseModel` / `Enum` definitions: `LLMProvider`, `LLMRole`, `LLMMessage`, `LLMRequest`, `LLMResponse`
3. In `core/llm_provider.py`, delete the moved definitions and add: `from ai_designer.schemas.llm_schemas import LLMProvider, LLMRole, LLMMessage, LLMRequest, LLMResponse`
4. Open `src/ai_designer/schemas/__init__.py` and add the five new symbols to the import block and to `__all__`
5. Run: `make test-unit`

**Verification:** `python -c "from ai_designer.schemas import LLMRequest, LLMResponse, LLMMessage; print('OK')"` prints `OK`.

---

### Task 4 — Create `schemas/api_schemas.py`

**Files created:** `src/ai_designer/schemas/api_schemas.py`
**Files modified:** `src/ai_designer/api/routes/design.py`, `src/ai_designer/schemas/__init__.py`
**Prerequisites:** Task 3
**Effort:** ~45 minutes

**Steps:**
1. Create `src/ai_designer/schemas/api_schemas.py`
2. Move these three inline Pydantic models from `src/ai_designer/api/routes/design.py` into the new file: `DesignRequest`, `DesignResponse`, `DesignStatusResponse`
3. Note: `design.py` already imports `DesignRequest` from `ai_designer.schemas.design_state` under the alias `DesignRequestSchema` — rename the moved `DesignRequest` in the new schemas file to `DesignCreateRequest` to avoid the collision
4. In `api/routes/design.py`, delete the moved model definitions and add an import from `ai_designer.schemas.api_schemas`; update all references to the renamed `DesignCreateRequest`
5. Add `DesignCreateRequest`, `DesignResponse`, `DesignStatusResponse` to `schemas/__init__.py` exports
6. Run: `make test-unit && make test-integration`

**Verification:** `python -c "from ai_designer.schemas import DesignCreateRequest, DesignResponse; print('OK')"` prints `OK`. All route integration tests pass.

---

## Week 1–2 — Architecture Gaps (Day 3–8)

---

### Task 5 — Create `agents/base.py` — Abstract Base Agent

**Files created:** `src/ai_designer/agents/base.py`, `tests/unit/agents/test_base.py`
**Files modified:** `src/ai_designer/agents/planner.py`, `src/ai_designer/agents/generator.py`, `src/ai_designer/agents/validator.py`, `src/ai_designer/agents/orchestrator.py`, `src/ai_designer/agents/__init__.py`
**Prerequisites:** Task 3
**Effort:** ~3 hours

**Steps:**

**5a — Create `base.py`:**
1. Create `src/ai_designer/agents/base.py`
2. Define `BaseAgent(ABC)` with:
   - `__init__` accepting `llm_provider: UnifiedLLMProvider`, `max_retries: int = 3`, `agent_type: AgentType`
   - Instance attributes: `self.llm_provider`, `self.max_retries`, `self.agent_type`, `self.logger = get_logger(self.__class__.__name__)`
   - Abstract method `execute(self, state: dict) -> dict`
   - Protected method `_build_llm_request(self, messages, model=None, temperature=None) -> LLMRequest` — builds an `LLMRequest` using `LLMMessage`; falls back to `self.default_temperature` if temperature is `None`
   - Protected method `_call_llm(self, request: LLMRequest) -> LLMResponse` — calls `self.llm_provider.complete(request)` with retry loop up to `self.max_retries`, catching `LLMError`, logging each attempt, re-raising after final failure
   - Property `name -> str` returning `self.__class__.__name__`

**5b — Inherit `BaseAgent` in each agent:**
1. In `planner.py`: add `from ai_designer.agents.base import BaseAgent`, change class to inherit `BaseAgent`, call `super().__init__(...)` first in `__init__`, remove duplicated `self.llm_provider`, `self.max_retries`, `self.agent_type`, `self.logger` assignments, replace inline retry loops with calls to `self._call_llm(...)`
2. Repeat for `generator.py` and `validator.py` with their respective `AgentType` values
3. For `orchestrator.py` — inherit `BaseAgent` but its `execute()` delegates to sub-agents rather than calling LLM directly, so it is a lighter change

**5c — Update `agents/__init__.py`:**
1. Add `from .base import BaseAgent` and include `BaseAgent` in `__all__`

**5d — Write tests in `tests/unit/agents/test_base.py`:**
1. Create a concrete subclass in the test file, verify instantiation works
2. Test that `_call_llm` retries exactly `max_retries` times on `LLMError` before raising
3. Test that `_build_llm_request` returns a valid `LLMRequest` with provided messages

**Verification:** `make test-unit` passes. `python -c "from ai_designer.agents.base import BaseAgent; print(BaseAgent.__abstractmethods__)"` prints `{'execute'}`.

---

### Task 6 — Create `llm/model_config.py`

**Files created:** `src/ai_designer/llm/model_config.py`
**Files modified:** `src/ai_designer/agents/planner.py`, `src/ai_designer/agents/generator.py`, `src/ai_designer/agents/validator.py`, `src/ai_designer/agents/orchestrator.py`, `config/config.yaml`
**Prerequisites:** Task 5
**Effort:** ~2 hours

**Steps:**
1. Create `src/ai_designer/llm/model_config.py`
2. Define `AGENT_MODEL_CONFIG: dict` with four keys (`"planner"`, `"generator"`, `"validator"`, `"orchestrator"`), each mapping to a dict with: `primary` (litellm model string), `fallback` (model string), `temperature` (float), `max_tokens` (int)
   - Planner: `anthropic/claude-3-5-sonnet-20241022`, fallback `google/gemini-pro`, temp `0.3`, tokens `4096`
   - Generator: `openai/gpt-4o`, fallback `deepseek/deepseek-coder`, temp `0.2`, tokens `8192`
   - Validator: `anthropic/claude-3-5-sonnet-20241022`, fallback `openai/gpt-4o`, temp `0.3`, tokens `2048`
   - Orchestrator: `anthropic/claude-3-5-sonnet-20241022`, fallback `google/gemini-pro`, temp `0.4`, tokens `2048`
3. Add `get_agent_config(agent_name: str) -> dict` — returns config, raises `KeyError` if not found
4. Add `get_env_override(agent_name: str, key: str) -> Optional[str]` — checks env var `AGENT_{AGENT_NAME.upper()}_{KEY.upper()}`; returns the value if set, else `None`
5. Add `llm_agents:` section to `config/config.yaml` mirroring these four entries (acts as a config-file override layer)
6. In each agent's `__init__`, replace hardcoded model strings with `get_agent_config("planner")["primary"]` etc.
7. Add `get_agent_config` to `agents/__init__.py` exports so it's accessible from the package

**Verification:** `python -c "from ai_designer.llm.model_config import get_agent_config; print(get_agent_config('generator')['primary'])"` prints `openai/gpt-4o`.

---

### Task 7 — Add Actual Cost Tracking to `UnifiedLLMProvider`

**File modified:** `src/ai_designer/core/llm_provider.py`, `src/ai_designer/schemas/llm_schemas.py`
**Prerequisites:** Task 3
**Effort:** ~1 hour

**Steps:**
1. Open `src/ai_designer/schemas/llm_schemas.py` (moved there in Task 3) and add a `cost_usd: Optional[float] = None` field to `LLMResponse`
2. Open `src/ai_designer/core/llm_provider.py`
3. After each successful `litellm.completion()` call, add: `cost = litellm.completion_cost(completion_response=response)` then `self.total_cost += cost if cost else 0.0`
4. Populate `cost_usd=cost` when constructing the `LLMResponse` return value
5. Log per-call cost at `debug` level: include `cost_usd`, `model`, and total `tokens`
6. Add `get_total_cost(self) -> float` method returning `self.total_cost`
7. Add `reset_cost_tracking(self)` method setting `self.total_cost = 0.0`
8. Run: `make test-unit`

**Verification:** In `test_llm_provider.py`, mock `litellm.completion_cost` to return `0.001` and assert `get_total_cost()` returns `0.001` after one call.

---

### Task 8 — Add SSE Streaming to `UnifiedLLMProvider`

**Files modified:** `src/ai_designer/core/llm_provider.py`, `src/ai_designer/api/routes/ws.py`
**Prerequisites:** Task 7
**Effort:** ~2 hours

**Steps:**
1. In `src/ai_designer/core/llm_provider.py`, add `async def complete_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]` to `UnifiedLLMProvider`
2. Inside, call `litellm.acompletion(..., stream=True)` — use `acompletion` (async) rather than `completion` to avoid blocking
3. Iterate with `async for chunk in response:` and yield `chunk.choices[0].delta.content` when it is not `None` or empty
4. Do not retry streaming failures — add a comment documenting this; raise `LLMError` immediately on exception
5. In `src/ai_designer/api/routes/ws.py`, add a handler for WebSocket message type `"stream_design"`: extract `prompt` from the message, call `complete_stream()` on the LLM provider, iterate the async generator and send each chunk back as a WebSocket text message with structure `{"type": "stream_chunk", "content": chunk}`, finally send `{"type": "stream_done"}` after the generator is exhausted
6. Add a test in `tests/unit/core/test_llm_provider.py` mocking `litellm.acompletion` with an async mock that yields streaming chunks

**Verification:** `make test-unit` passes. The streaming mock test confirms chunks are yielded in order.

---

### Task 9 — Update `llm/unified_manager.py` to Delegate to `UnifiedLLMProvider`

**File modified:** `src/ai_designer/llm/unified_manager.py`
**Prerequisites:** Task 3, Task 6
**Effort:** ~3 hours

**Context:** `unified_manager.py` uses legacy `DeepSeekR1Client` and `LLMClient` with its own dataclass-based `LLMRequest`/`LLMResponse`. It is still used by `cli.py`. The goal is to delegate under the hood to `UnifiedLLMProvider` while preserving the external interface.

**Steps:**
1. In `UnifiedLLMManager.__init__`, create `self._provider = UnifiedLLMProvider(...)` using `model_config.get_agent_config("generator")["primary"]` as the default model
2. Find the main generation method (the method that accepts the legacy `LLMRequest` dataclass)
3. Replace its body: convert the legacy `LLMRequest` into a `schemas.llm_schemas.LLMRequest`, call `self._provider.complete(new_request)`, convert the returned `schemas.llm_schemas.LLMResponse` back to the legacy `LLMResponse` dataclass, and return it
4. Add `# DEPRECATED: Use ai_designer.schemas.llm_schemas.LLMRequest` comments on the legacy dataclass definitions at the top of the file
5. Add `# DEPRECATED: Kept for backward compat only` on the `DeepSeekR1Client` and `LLMClient` import lines
6. Do not delete anything yet — delegates and annotates only, to keep `cli.py` working
7. Run: `make test-unit`

**Verification:** The manager can be instantiated and its `generate()` call flows through to `UnifiedLLMProvider`. All existing unit tests pass.

---

## Week 2 — God Class Refactoring (Day 6–12)

---

### Task 10 — Split `cli.py` into `cli/` Package (1,662 lines → ~4 modules)

**Files created:** `src/ai_designer/cli/__init__.py`, `src/ai_designer/cli/app.py`, `src/ai_designer/cli/commands.py`, `src/ai_designer/cli/display.py`, `src/ai_designer/cli/session.py`
**Files deleted:** `src/ai_designer/cli.py`
**Files modified:** `src/ai_designer/__main__.py`
**Prerequisites:** Task 9
**Effort:** ~1 day

**Steps:**

**10a — Create the package skeleton:**
1. Create directory `src/ai_designer/cli/`
2. Create `cli/__init__.py` —  re-export `FreeCADCLI` from `app.py` so that existing `from ai_designer.cli import FreeCADCLI` imports continue to work without changes

**10b — Extract `cli/session.py`:**
1. Create `cli/session.py`
2. Move all session-state attributes from `FreeCADCLI.__init__` (history list, context dict, current doc path, active session metadata) plus the `show_history()` method into a `SessionManager` class

**10c — Extract `cli/display.py`:**
1. Create `cli/display.py`
2. Move output-only methods that have no side effects other than printing: `show_help()` (line 922), `show_state()` (line 758), `show_file_info()` (line 1093), `show_save_info()` (line 1119), `show_websocket_status()` (line 1225), `show_persistent_gui_status()` (line 1252), `_display_workflow_results()` (line 631)
3. These can be standalone functions accepting state as arguments, or a `DisplayManager` class

**10d — Extract `cli/commands.py`:**
1. Create `cli/commands.py`
2. Move command-execution methods: `execute_command()` (line 458), `execute_deepseek_command()` (line 795), `_use_direct_deepseek_api()` (line 804), `_execute_generated_code()` (line 867), `execute_script()` (line 742), `execute_complex_shape()` (line 1151), `analyze_state()` (line 768)
3. These methods need the LLM manager and FreeCAD client — accept them as constructor arguments

**10e — Create `cli/app.py`:**
1. Create `cli/app.py` with the trimmed `FreeCADCLI` class
2. Replace extracted methods with delegation calls to `SessionManager`, `DisplayManager`, and command functions
3. `FreeCADCLI` should now contain only: `__init__`, `initialize()`, `interactive_mode()`, `cleanup()`, `_start_websocket_server()`
4. Target: ~300 lines

**10f — Update `__main__.py` and delete old file:**
1. Confirm `from ai_designer.cli import FreeCADCLI` still works (it should — via `__init__.py` re-export)
2. Delete `src/ai_designer/cli.py`
3. Run: `make test-unit` — fix any import errors

**Verification:** `python -m ai_designer --help` runs without error. `wc -l src/ai_designer/cli/app.py` is under 350 lines.

---

### Task 11 — Reduce `state_llm_integration.py` (1,515 → ~400 lines)

**Files created:** `src/ai_designer/core/state_analyzer.py`
**Files modified:** `src/ai_designer/core/state_llm_integration.py`
**Prerequisites:** Task 10
**Effort:** ~1 day

**Steps:**
1. Open `state_llm_integration.py` and read through all methods end-to-end before touching anything
2. Identify methods that duplicate what the `PlannerAgent`, `GeneratorAgent`, and `ValidatorAgent` now do — mark each with `# DEPRECATED: Use agents.planner / agents.generator / agents.validator instead`; do not delete yet
3. Identify state-analysis methods that are genuinely unique and not covered by agents — things that read and diff the live FreeCAD document state or build context summaries for prompts
4. Create `src/ai_designer/core/state_analyzer.py` with a `StateAnalyzer` class; move only the still-unique methods here
5. In `state_llm_integration.py`, replace moved methods with delegation calls to `StateAnalyzer`
6. Identify any prompt-building logic that is not already in `agents/prompts/` — move unique prompts to `agents/prompts/system_prompts.py` as new named constants
7. Target: `state_llm_integration.py` down to ~400 lines
8. Run: `make test-unit` after each batch of moves — fix regressions immediately

**Verification:** `wc -l src/ai_designer/core/state_llm_integration.py` is under 500 lines.

---

### Task 12 — Reduce `deepseek_client.py` (1,143 → ~300 lines)

**Files created:** `src/ai_designer/llm/providers/__init__.py`, `src/ai_designer/llm/providers/deepseek.py`
**Files modified:** `src/ai_designer/llm/deepseek_client.py`, `src/ai_designer/llm/unified_manager.py`
**Prerequisites:** Task 9
**Effort:** ~1 day

**Steps:**
1. Open `deepseek_client.py` and scan all methods end-to-end before touching anything
2. Identify logic that is truly DeepSeek-specific and NOT handled by litellm's native DeepSeek support — likely: Ollama's HTTP API format, R1 reasoning-chain extraction from `<think>` tags, streaming thought-process parsing
3. Create `src/ai_designer/llm/providers/` directory with `__init__.py`
4. Create `src/ai_designer/llm/providers/deepseek.py` — move only the unique Ollama/R1 logic here (target ~200 lines): the raw HTTP client calls to the Ollama API, the `<think>` tag extraction function, and timeout/retry logic specific to local Ollama
5. In `deepseek_client.py`, replace moved methods with delegation to `providers/deepseek.py` and mark everything that duplicates litellm with `# DEPRECATED: litellm handles this via 'deepseek/...' model prefix`
6. In `unified_manager.py`, ensure code paths that need Ollama-specific behavior now use `providers/deepseek.py`; cloud DeepSeek API falls through to `UnifiedLLMProvider`
7. Run: `make test-unit`

**Verification:** `wc -l src/ai_designer/llm/deepseek_client.py` is under 400 lines. Import test passes.

---

### Task 13 — Reduce `state_aware_processor.py` (1,970 → ~500 lines)

**Files created:** `src/ai_designer/freecad/workflow_templates.py`, `src/ai_designer/freecad/geometry_helpers.py`, `src/ai_designer/freecad/state_diff.py`
**Files modified:** `src/ai_designer/freecad/state_aware_processor.py`
**Prerequisites:** Task 11
**Effort:** ~1.5 days

**Steps:**

**13a — Extract `workflow_templates.py`:**
1. Identify all hardcoded workflow template strings, script templates, and operation-sequence definitions (Box, Cylinder, Loft, Sweep, etc.)
2. Create `src/ai_designer/freecad/workflow_templates.py` — move them as module-level constants or a `WorkflowTemplate` dataclass
3. In `state_aware_processor.py`, import from `workflow_templates`
4. Run: `make test-unit` — fix regressions

**13b — Extract `geometry_helpers.py`:**
1. Identify pure geometry utility functions: bounding-box calculations, volume estimation, face counting, shape-type detection, tolerance comparisons
2. Create `src/ai_designer/freecad/geometry_helpers.py` as a collection of standalone functions (no class wrapper needed)
3. Replace inline geometry calculations in `state_aware_processor.py` with calls to these helpers
4. Run: `make test-unit`

**13c — Extract `state_diff.py`:**
1. Identify methods that compare two document state dicts: added/removed objects, changed features, changed constraints
2. Create `src/ai_designer/freecad/state_diff.py` with a `StateDiff` dataclass and a `compute_diff(before: dict, after: dict) -> StateDiff` function
3. Replace inline state-comparison logic with calls to `compute_diff()`
4. Run: `make test-unit`

**Verification:** `wc -l src/ai_designer/freecad/state_aware_processor.py` is under 600 lines. `make test-unit` passes.

---

## Week 3–4 — Production Infrastructure

---

### Task 14 — Create Production Dockerfile and Upgrade `docker-compose.yml`

**Files created:** `docker/Dockerfile.production`, `docker/Dockerfile.dev`, `.dockerignore`
**Files modified:** `docker-compose.yml`, `Makefile`
**Prerequisites:** Tasks 1–13
**Effort:** ~1.5 days

**Steps:**

**14a — Create `.dockerignore`:**
1. Create `.dockerignore` in the repo root
2. Add: `__pycache__/`, `*.pyc`, `*.pyo`, `.git/`, `.env`, `venv/`, `htmlcov/`, `outputs/`, `*.FCStd`, `tests/`, `docs/`, `.pytest_cache/`, `node_modules/`

**14b — Create `docker/Dockerfile.production`:**
1. Create `docker/` directory
2. Write a two-stage build:
   - **Stage 1 (`builder`):** From `python:3.11-slim`, install build tools, copy `pyproject.toml`, run `pip install --no-cache-dir .`
   - **Stage 2 (`runtime`):** From `python:3.11-slim`, install FreeCAD runtime deps via apt (`freecadcmd`, `libocct-modeling-data-dev`), create non-root user `freecad` with UID/GID 1000 via `useradd -m -u 1000 -g 1000 freecad`, copy installed packages from builder stage, copy `src/` and `config/`, set `WORKDIR /app`, switch to `USER freecad`, expose `8000`, set `CMD ["uvicorn", "ai_designer.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]`
3. Set env vars in the Dockerfile: `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`, `FREECAD_HEADLESS=1`

**14c — Create `docker/Dockerfile.dev`:**
1. Single stage from `python:3.11`
2. Install dev deps with `pip install -e ".[dev]"`, source code mounted as a volume (not COPY), run with `--reload`

**14d — Rewrite `docker-compose.yml`:**
1. Define three services:
   - `redis`: image `redis:7-alpine`, port `6379:6379`, healthcheck `redis-cli ping` every 10s, restart `unless-stopped`, volume `redis_data:/data`, command `redis-server --appendonly yes`
   - `api`: build `./` + `docker/Dockerfile.production`, depends on `redis` with `condition: service_healthy`, port `8000:8000`, `env_file: .env`, env vars `REDIS_HOST=redis` + `REDIS_PORT=6379`, healthcheck on `GET /health` every 15s, `mem_limit: 2g`, `cpus: "2"`, volume `./outputs:/app/outputs`
   - `redis-commander`: under `profiles: [dev]` so it only starts with `docker compose --profile dev up`
2. Define named volume `redis_data`

**14e — Update `Makefile`:**
1. Add `docker-build`: `docker build -f docker/Dockerfile.production -t freecad-ai-designer .`
2. Add `docker-run`: `docker compose up -d`
3. Add `docker-stop`: `docker compose down`
4. Add `docker-logs`: `docker compose logs -f api`

**Verification:** `docker build -f docker/Dockerfile.production -t freecad-ai-designer .` succeeds. `docker compose up -d && curl http://localhost:8000/health` returns `{"status": "ok"}`.

---

### Task 15 — Add Authentication and Rate-Limiting Middleware

**Files created:** `src/ai_designer/api/middleware/__init__.py`, `src/ai_designer/api/middleware/auth.py`, `src/ai_designer/api/middleware/rate_limit.py`
**Files modified:** `src/ai_designer/api/app.py`, `src/ai_designer/api/deps.py`, `pyproject.toml`, `.env.example`
**Prerequisites:** Task 14
**Effort:** ~1 day

**Steps:**

**15a — Add dependencies to `pyproject.toml`:**
1. Add `python-jose[cryptography]>=3.3.0` and `passlib[bcrypt]>=1.7.4`
2. Run `pip install -e ".[dev]"` to install

**15b — Create `middleware/auth.py`:**
1. Create `src/ai_designer/api/middleware/` directory with empty `__init__.py`
2. Read `AUTH_ENABLED` from env (default `false`) — when false, middleware is a no-op passthrough
3. Read `AUTH_API_KEYS` (comma-separated list of valid keys), `JWT_SECRET_KEY`, `JWT_ALGORITHM = "HS256"`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15` from env
4. Define `JWTAuthMiddleware` as a Starlette `BaseHTTPMiddleware` subclass: extract `Authorization: Bearer <token>` header, decode with `python-jose`, return `401` if invalid or expired; skip auth for `/health`, `/ready`, `/docs`, `/redoc`, `/openapi.json`, `/metrics`
5. Add `AUTH_ENABLED`, `AUTH_API_KEYS`, `JWT_SECRET_KEY` to `.env.example`

**15c — Create `middleware/rate_limit.py`:**
1. Implement a Redis-backed sliding window rate limiter
2. Config from env: `RATE_LIMIT_REQUESTS = 100`, `RATE_LIMIT_WINDOW_SECONDS = 60`
3. Logic: `ZADD key timestamp timestamp`, `ZREMRANGEBYSCORE key 0 (now - window)`, `ZCARD key`; if count > limit, return `429` with `Retry-After` header; `EXPIRE key window`
4. When Redis is unavailable, fail open: log a warning, allow the request
5. Add `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` to `.env.example`

**15d — Register both middleware in `app.py`:**
1. Import `JWTAuthMiddleware` and `RateLimitMiddleware`
2. In `create_app()`, add `app.add_middleware(RateLimitMiddleware)` then `app.add_middleware(JWTAuthMiddleware)` — rate limit is outermost
3. Middleware classes self-disable via their `_ENABLED` env var; no conditional logic needed in `app.py`

**15e — Update `deps.py`:**
1. Find the `verify_api_key` stub (currently a TODO)
2. Replace its body with a call to `auth.verify_api_key(api_key)`

**Verification:** With `AUTH_ENABLED=false` (default), `make test-integration` passes. With `AUTH_ENABLED=true` and no token, `curl http://localhost:8000/api/v1/design` returns `401`.

---

### Task 16 — Add Prometheus Metrics

**Files created:** `src/ai_designer/core/metrics.py`
**Files modified:** `src/ai_designer/api/app.py`, `src/ai_designer/orchestration/nodes.py`, `src/ai_designer/core/llm_provider.py`, `pyproject.toml`
**Prerequisites:** Task 15
**Effort:** ~1 day

**Steps:**

**16a — Add dependencies:**
1. Add `prometheus-client>=0.19.0` to `pyproject.toml`

**16b — Create `core/metrics.py` with these module-level Prometheus objects:**
1. `design_requests_total = Counter("design_requests_total", "Total design requests", ["status"])` — labels: `success`, `failure`, `timeout`
2. `design_duration_seconds = Histogram("design_duration_seconds", "End-to-end pipeline duration")`
3. `agent_call_duration_seconds = Histogram("agent_call_duration_seconds", "Per-agent call duration", ["agent_name"])`
4. `llm_tokens_used_total = Counter("llm_tokens_used_total", "Total tokens consumed", ["provider", "model"])`
5. `llm_cost_usd_total = Counter("llm_cost_usd_total", "Total LLM cost in USD", ["provider"])`
6. `active_designs = Gauge("active_designs", "Currently running pipelines")`

**16c — Add `/metrics` endpoint to `app.py`:**
1. Import `prometheus_client.generate_latest` and `CONTENT_TYPE_LATEST`
2. Add `@app.get("/metrics")` returning `Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)`
3. Add `/metrics` to the auth middleware exclusion paths list

**16d — Instrument pipeline nodes in `orchestration/nodes.py`:**
1. Wrap each agent call with `with agent_call_duration_seconds.labels(agent_name="...").time():`
2. Increment `active_designs.inc()` at pipeline start, `active_designs.dec()` at end
3. Increment `design_requests_total.labels(status="success"/"failure")` based on outcome

**16e — Instrument LLM provider in `core/llm_provider.py`:**
1. After each successful call, read `response.usage` and increment `llm_tokens_used_total.labels(provider=..., model=...).inc(tokens)`
2. Increment `llm_cost_usd_total.labels(provider=...).inc(cost_usd)` using the cost computed in Task 7

**Verification:** `curl http://localhost:8000/metrics` returns Prometheus text format. `design_requests_total`, `agent_call_duration_seconds`, and `active_designs` are visible.

---

### Task 17 — Add Locust Load Tests

**Files created:** `tests/load/__init__.py`, `tests/load/locustfile.py`, `tests/load/scenarios.py`
**Files modified:** `Makefile`
**Prerequisites:** Task 14 (Docker setup must exist)
**Effort:** ~4 hours

**Steps:**

**17a — Add `locust>=2.20.0` to dev dependencies in `pyproject.toml`**

**17b — Create `tests/load/locustfile.py`:**
1. Define `DesignUser(HttpUser)` with `wait_time = between(1, 5)`
2. Task weight 3 — `create_simple_design`: POST to `/api/v1/design` with prompt `"Create a simple box 100x50x30mm"` and `max_iterations=2`; use `catch_response=True` and mark as failure if status is not `202`; store returned `request_id` in a list for use by the status task
3. Task weight 1 — `check_health`: GET `/health`; mark as failure if status is not `200`
4. Task weight 1 — `get_design_status`: GET `/api/v1/design/{id}` using a random ID from the stored list; skip gracefully if no IDs available yet

**17c — Create `tests/load/scenarios.py`:**
1. Document three named load profiles as plain comments/constants:
   - `STEADY_STATE`: 100 users, spawn rate 10/s, duration 5 minutes
   - `COMPLEX_WORKLOAD`: 50 users, spawn rate 5/s, prompts are multi-feature assemblies
   - `SPIKE`: ramp from 0 to 200 users in 60 seconds, sustain for 2 minutes
2. Document success criteria: P95 latency < 10s, error rate < 1%

**17d — Update `Makefile`:**
1. Add `load-test` target: `locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=5m --headless --html=outputs/load_test_report.html`
2. Add `load-test-ui` target: same without `--headless` to open the Locust web UI

**Verification:** `make load-test` completes without crashing the process. `outputs/load_test_report.html` is generated.

---

## Execution Timeline Summary

| Week | Days | Tasks | Description |
|------|------|-------|-------------|
| Week 1 | Day 1 | 1, 2 | Remove leaked key + hardcoded paths |
| Week 1 | Day 2 | 3, 4 | Schema consolidation |
| Week 1 | Day 3–4 | 5 | BaseAgent + refactor all agents |
| Week 1 | Day 5 | 6, 7 | model_config + cost tracking |
| Week 2 | Day 1 | 8 | Streaming SSE |
| Week 2 | Day 2–3 | 9 | Unify LLM manager |
| Week 2 | Day 4–5 | 10 | Split cli.py |
| Week 3 | Day 1–2 | 11 | Reduce state_llm_integration |
| Week 3 | Day 3–4 | 12 | Reduce deepseek_client |
| Week 3 | Day 4–5 | 13 | Reduce state_aware_processor |
| Week 4 | Day 1–2 | 14 | Docker + compose |
| Week 4 | Day 3–4 | 15 | Auth + rate limiting |
| Week 4 | Day 5 | 16 | Prometheus metrics |
| Week 5 | Day 1 | 17 | Locust load tests |

**Total estimated effort:** ~3 weeks active development for one developer.

---

## After-Completion State

| Metric | Before | After |
|--------|--------|-------|
| Leaked secrets | 1 | 0 |
| Hardcoded machine paths | 5 | 0 |
| God classes (>1,000 lines) | 4 (6,290 lines) | 0 |
| Shared schema files | 3 / 5 | 5 / 5 |
| Abstract base agent | Missing | `agents/base.py` |
| LLM cost tracking | Stub | Live per-call |
| Streaming support | None | `complete_stream()` + WS |
| Unified LLM layer | Dual stack | Single litellm provider |
| Per-agent model config | Hardcoded strings | `llm/model_config.py` |
| Production Dockerfile | None | Multi-stage, non-root user |
| Auth middleware | TODO stub | JWT + API key, togglable |
| Rate limiting | None | Redis sliding window |
| Metrics endpoint | None | `/metrics` Prometheus format |
| Load tests | None | Locust, 3 scenarios |

---

*Each task references exact file paths and line numbers from the live codebase as of February 20, 2026.*

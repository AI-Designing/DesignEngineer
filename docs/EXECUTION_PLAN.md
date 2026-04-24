# Execution Plan — FreeCAD Multi-Agent System

> **Created:** February 9, 2026
> **Goal:** Transform the current monolithic prototype into a production-grade, multi-agent CAD automation system using online-hosted AI providers, following best coding practices at every step.

---

## Current State Assessment (What We Have)

| Area | Status | Key Files |
|------|--------|-----------|
| **LLM Integration** | ✅ Working — Gemini (LangChain) + DeepSeek R1 (Ollama) | `llm/client.py`, `llm/deepseek_client.py`, `llm/unified_manager.py` |
| **FreeCAD Execution** | ✅ Working — Direct import + subprocess fallback | `freecad/api_client.py`, `freecad/command_executor.py` |
| **State Management** | ✅ Working — Redis-backed caching | `redis_utils/client.py`, `redis_utils/state_cache.py`, `services/state_service.py` |
| **WebSocket** | ✅ Working — Real-time updates | `realtime/websocket_manager.py` |
| **Intent Processing** | ✅ Working — Regex-based | `core/intent_processor.py` |
| **Command Pipeline** | ✅ Working — Intent→Generate→Queue→Execute→State | `core/orchestrator.py`, `core/command_generator.py`, `core/queue_manager.py` |
| **CLI** | ✅ Working — Interactive mode | `cli.py` (1,663 lines — god class) |
| **Multi-Agent System** | ❌ Empty — `agents/` directory is empty | — |
| **FastAPI REST API** | ❌ Not built — dependency declared but no code | — |
| **LangGraph Orchestration** | ❌ Not built | — |
| **FEA/Simulation** | ❌ Not built | — |
| **Vector Store/RAG** | ❌ Not built | — |
| **ML Embeddings** | ❌ Not built — torch/transformers unused | — |
| **Tests** | ⚠️ Broken — reference non-existent classes, require live infra | `tests/` |
| **Security** | 🔴 Critical — API key hardcoded in source, `exec()` calls, hardcoded paths | Multiple files |

---

## Architecture Target (What We're Building)

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Gateway                         │
│              (REST + WebSocket endpoints)                   │
├─────────────┬──────────────┬──────────────┬─────────────────┤
│  Planner    │  Generator   │  Validator   │  Orchestrator   │
│  Agent      │  Agent       │  Agent       │  (LangGraph)    │
│  (Claude/   │  (GPT-4o/    │  (Geometry   │  State Machine  │
│   Gemini)   │   DeepSeek)  │   + LLM)     │  + Retry Logic  │
├─────────────┴──────────────┴──────────────┴─────────────────┤
│              Unified LLM Provider Layer (litellm)           │
│       OpenAI  |  Anthropic  |  Google  |  DeepSeek          │
├─────────────────────────────────────────────────────────────┤
│              Shared Infrastructure                          │
│   Redis (State + Pub/Sub + Streams)  |  FreeCAD (Headless)  │
└─────────────────────────────────────────────────────────────┘
```

---

## Online AI Providers Strategy

We use **online-hosted LLMs** via a unified interface (`litellm`), not local models:

| Role | Primary Provider | Fallback | Why |
|------|-----------------|----------|-----|
| **Planner Agent** (reasoning) | Anthropic Claude 3.5 Sonnet | Google Gemini Pro | Best chain-of-thought reasoning for task decomposition |
| **Generator Agent** (code) | OpenAI GPT-4o | DeepSeek Coder (API) | Best FreeCAD Python code generation accuracy |
| **Validator Agent** (critique) | Anthropic Claude 3.5 Sonnet | OpenAI GPT-4o | Best at structured analysis and error detection |
| **Vision Validation** | OpenAI GPT-4o (multimodal) | Google Gemini Pro Vision | Screenshot-based geometry critique |

**Key Decision:** Use `litellm` as the unified SDK — it wraps 100+ providers with a single `completion()` interface, handles retries, fallback chains, and cost tracking. This replaces our current fragmented `LLMClient` + `DeepSeekR1Client` approach.

---

## Execution Phases

### PHASE 0: Foundation Cleanup (Steps 1-6)
> Fix critical issues, eliminate tech debt, make the codebase safe and professional.

### PHASE 1: Core Architecture (Steps 7-12)
> Build the agent system, unified LLM layer, and FastAPI gateway.

### PHASE 2: Intelligence & Integration (Steps 13-17)
> Add LangGraph orchestration, validation pipeline, and advanced features.

### PHASE 3: Production Hardening (Steps 18-21)
> Testing, Docker, observability, security, and deployment.

---

## PHASE 0 — Foundation Cleanup

### Step 1: Security — Remove Hardcoded Secrets

**Priority:** 🔴 CRITICAL (do this first, before any other work)

**Problem:** A real Google API key is committed to version control in `src/ai_designer/core/state_llm_integration.py` line 669:
```python
self.api_key = "AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc"  # LEAKED  # pragma: allowlist secret
```

**Actions:**
- [ ] Remove the hardcoded API key from `state_llm_integration.py`
- [ ] Audit all files for any other hardcoded secrets
- [ ] Make all API key access go through `SecureConfig` → `.env` file
- [ ] Add `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` to `.env.example`
- [ ] Add a pre-commit hook via `detect-secrets` to prevent future leaks
- [ ] Rotate the leaked Google API key (it's compromised)

**Files to modify:**
- `src/ai_designer/core/state_llm_integration.py`
- `.env.example`
- `.pre-commit-config.yaml` (create)

---

### Step 2: Security — Replace `exec()` with Safe Execution

**Priority:** 🔴 CRITICAL

**Problem:** Arbitrary code execution via `exec()` in production code:
- `freecad/api_client.py:84` — `exec(command, local_env)`
- `freecad/persistent_gui_client.py:442` — `exec(script, globals_dict)`

**Actions:**
- [ ] Create `src/ai_designer/core/sandbox.py` — a safe script execution module that:
  1. Validates generated scripts against an **AST whitelist** (only allow `FreeCAD`, `Part`, `Sketcher`, `PartDesign` module calls)
  2. Blocks dangerous builtins (`__import__`, `open`, `os`, `sys`, `subprocess`)
  3. Executes via `subprocess` in an isolated process with timeout
  4. Returns structured results (stdout, stderr, exit code, created objects)
- [ ] Replace all `exec()` calls with calls to the new sandbox module
- [ ] Add unit tests for the sandbox (malicious script rejection, valid script acceptance)

**Files to create:**
- `src/ai_designer/core/sandbox.py`
- `tests/unit/test_sandbox.py`

**Files to modify:**
- `src/ai_designer/freecad/api_client.py`
- `src/ai_designer/freecad/persistent_gui_client.py`

---

### Step 3: Remove Hardcoded Paths — Use Configuration

**Priority:** 🟡 HIGH

**Problem:** FreeCAD paths hardcoded to a specific user's machine in 6+ files:
```python
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/lib/")  # Non-portable
```

**Actions:**
- [ ] Create `src/ai_designer/freecad/path_resolver.py` — centralized FreeCAD path resolution:
  1. Check `FREECAD_PATH` env var first
  2. Check `config.yaml` → `freecad.path`
  3. Auto-detect from common install locations (`/usr/lib/freecad`, AppImage paths)
  4. Raise clear error if not found
- [ ] Remove ALL `sys.path.append("/home/vansh5632/...")` lines from every file
- [ ] Update `config/config.yaml` with `freecad.lib_path` and `freecad.mod_path` keys
- [ ] Update `.env.example` with `FREECAD_PATH`

**Files to create:**
- `src/ai_designer/freecad/path_resolver.py`

**Files to modify:**
- `src/ai_designer/freecad/api_client.py`
- `src/ai_designer/freecad/state_manager.py`
- `src/ai_designer/freecad/command_executor.py`
- `src/ai_designer/freecad/face_selection_engine.py`
- `config/config.yaml`

---

### Step 4: Clean Up Dependencies — Remove Unused, Add Required

**Priority:** 🟡 HIGH

**Problem:** `pyproject.toml` declares heavy unused deps (torch ~2GB, transformers ~500MB) and is missing deps we'll actually need.

**Actions:**
- [ ] **Remove** from `dependencies` (re-add later if actually needed):
  - `Flask>=2.0.1` (no Flask code exists; we use FastAPI)
  - `torch>=1.9.0` (no ML code exists yet)
  - `transformers>=4.20.0` (no HF code exists yet)
  - `accelerate>=0.20.0` (no training code exists yet)
  - `openai>=0.11.3` (replace with litellm)
- [ ] **Add** new required dependencies:
  - `litellm>=1.30.0` (unified LLM provider — replaces individual SDKs)
  - `langgraph>=0.1.0` (agent orchestration state machine)
  - `networkx>=3.0` (task graph data structure)
  - `python-dotenv>=1.0.0` (explicit .env loading)
  - `structlog>=24.0.0` (structured logging)
  - `httpx>=0.25.0` (modern async HTTP client)
- [ ] **Keep** existing deps: `redis`, `requests`, `PyYAML`, `websockets`, `fastapi`, `uvicorn`, `pydantic`, `langchain`, `google-generativeai`
- [ ] Update `requires-python` from `>=3.8` to `>=3.10` (we need `TypedDict`, `match` statements, modern typing)

**Files to modify:**
- `pyproject.toml`

---

### Step 5: Establish Proper Logging — Replace Print Statements

**Priority:** 🟡 HIGH

**Problem:** Mix of `print()` and `logging` throughout. No structured format. No correlation IDs.

**Actions:**
- [ ] Create `src/ai_designer/core/logging_config.py`:
  1. Configure `structlog` with JSON output for production, colored console for dev
  2. Add correlation ID middleware (request_id binds to all logs in a request)
  3. Define log levels per module in config
  4. Never log sensitive data (API keys, full prompts if they contain PII)
- [ ] Create `src/ai_designer/core/exceptions.py` — custom exception hierarchy:
  ```
  AIDesignerError (base)
  ├── ConfigurationError (already exists, move here)
  ├── LLMError
  │   ├── LLMConnectionError
  │   ├── LLMRateLimitError
  │   └── LLMResponseError
  ├── FreeCADError
  │   ├── FreeCADConnectionError
  │   ├── FreeCADExecutionError
  │   └── FreeCADRecomputeError
  ├── AgentError
  │   ├── PlanningError
  │   ├── GenerationError
  │   └── ValidationError
  └── StateError
  ```
- [ ] Replace all `print()` calls in `src/` with proper `logger.info/warning/error`
- [ ] Replace bare `except Exception` with specific exception catches

**Files to create:**
- `src/ai_designer/core/logging_config.py`
- `src/ai_designer/core/exceptions.py`

---

### Step 6: Refactor God Classes — Single Responsibility

**Priority:** 🟡 HIGH

**Problem:** `cli.py` (1,663 lines), `state_aware_processor.py` (1,971 lines), `state_llm_integration.py` (1,517 lines), `deepseek_client.py` (1,144 lines) are all massive monoliths.

**Actions:**
- [ ] **Split `cli.py`** (1,663 lines) into:
  - `cli/app.py` — Main CLI class (command routing, REPL loop) — ~200 lines
  - `cli/commands.py` — Individual command handlers (create, modify, export, etc.) — ~400 lines
  - `cli/formatters.py` — Output formatting, colors, progress bars — ~200 lines
  - `cli/session.py` — Session management, history — ~150 lines
- [ ] **Split `state_llm_integration.py`** (1,517 lines) into:
  - Move LLM-calling logic → will be replaced by agents in Phase 1
  - Keep state integration logic in `core/state_integration.py` — ~300 lines
  - Mark deprecated code clearly with `# TODO: Remove after agent migration`
- [ ] **Split `deepseek_client.py`** (1,144 lines) into:
  - `llm/providers/deepseek.py` — Core DeepSeek client — ~300 lines
  - `llm/providers/deepseek_modes.py` — Mode configurations — ~200 lines
  - Most of this will be replaced by `litellm` in Step 8
- [ ] **Clean `state_aware_processor.py`** (1,971 lines):
  - Extract workflow templates → `freecad/workflow_templates.py`
  - Extract state analysis → already in `state_manager.py`
  - Keep core processor logic — ~500 lines
- [ ] Delete empty/dead files:
  - `freecad/workflow_planner.py` (empty file)
  - Remove any dead/duplicate code blocks

**Files to create/restructure:**
- `src/ai_designer/cli/` (new package replacing `cli.py`)
- `src/ai_designer/llm/providers/` (new package)

---

## PHASE 1 — Core Architecture

### Step 7: Define Shared Data Contracts (Schemas)

**Priority:** 🟢 ESSENTIAL

**Why first:** Every agent, the API, and state management need to agree on data shapes. Define these before building anything.

**Actions:**
- [ ] Create `src/ai_designer/schemas/` package with Pydantic models:
  - `design_state.py` — The core `DesignState` that flows through the pipeline:
    ```python
    class DesignState(BaseModel):
        request_id: str                      # UUID correlation ID
        user_prompt: str                     # Original user request
        task_graph: Optional[TaskGraph]      # Planner output
        generated_script: Optional[str]      # Generator output
        execution_result: Optional[ExecResult]  # FreeCAD execution result
        validation_result: Optional[ValidationResult]  # Validator output
        iteration: int = 0                   # Current refinement loop count
        max_iterations: int = 5              # Loop limit
        status: DesignStatus                 # Current pipeline stage
        created_at: datetime
        updated_at: datetime
    ```
  - `task_graph.py` — `TaskNode`, `TaskGraph`, `TaskDependency`
  - `llm_schemas.py` — `LLMRequest`, `LLMResponse` (replace current dataclasses)
  - `api_schemas.py` — `DesignRequest`, `DesignResponse`, `StatusResponse`
  - `validation.py` — `ValidationResult`, `GeometryCheck`, `ScriptCheck`
- [ ] All existing code that passes `Dict[str, Any]` should migrate to these schemas
- [ ] Add JSON serialization support for Redis storage

**Files to create:**
- `src/ai_designer/schemas/__init__.py`
- `src/ai_designer/schemas/design_state.py`
- `src/ai_designer/schemas/task_graph.py`
- `src/ai_designer/schemas/llm_schemas.py`
- `src/ai_designer/schemas/api_schemas.py`
- `src/ai_designer/schemas/validation.py`

---

### Step 8: Build Unified LLM Provider Layer (litellm)

**Priority:** 🟢 ESSENTIAL

**Why:** This is the backbone. Every agent calls LLMs. We need one clean interface for all providers.

**Actions:**
- [ ] Create `src/ai_designer/llm/provider.py` — unified provider using `litellm`:
  ```python
  class LLMProvider:
      """Single interface for all LLM providers via litellm."""

      async def complete(self, messages, model, **kwargs) -> LLMResponse:
          """Route to any provider: openai/gpt-4o, anthropic/claude-3.5, google/gemini-pro"""

      async def complete_with_fallback(self, messages, models, **kwargs) -> LLMResponse:
          """Try models in order, fall back on failure."""
  ```
  Features:
  1. **Automatic fallback chain** — if Claude fails, try GPT-4o, then Gemini
  2. **Cost tracking** — litellm tracks token usage and cost per call
  3. **Rate limit handling** — automatic retry with exponential backoff
  4. **Structured output** — support JSON mode for agents that need structured responses
  5. **Streaming** — support SSE streaming for real-time UI updates
- [ ] Create `src/ai_designer/llm/model_config.py` — model selection config:
  ```yaml
  # In config/config.yaml
  llm:
    planner:
      primary: "anthropic/claude-3-5-sonnet-20241022"
      fallback: "google/gemini-1.5-pro"
    generator:
      primary: "openai/gpt-4o"
      fallback: "deepseek/deepseek-coder"
    validator:
      primary: "anthropic/claude-3-5-sonnet-20241022"
      fallback: "openai/gpt-4o"
  ```
- [ ] Deprecate old `llm/client.py` and `llm/deepseek_client.py` (keep for backward compat, mark deprecated)
- [ ] Update `llm/unified_manager.py` to delegate to new `LLMProvider`

**Files to create:**
- `src/ai_designer/llm/provider.py`
- `src/ai_designer/llm/model_config.py`

**Files to modify:**
- `config/config.yaml`
- `src/ai_designer/llm/unified_manager.py`

---

### Step 9: Build the Planner Agent

**Priority:** 🟢 ESSENTIAL

**Role:** Takes user prompt → produces a structured task graph (what to build, in what order).

**Actions:**
- [ ] Create `src/ai_designer/agents/base.py` — abstract base agent:
  ```python
  class BaseAgent(ABC):
      def __init__(self, llm_provider: LLMProvider, config: dict):
          ...

      @abstractmethod
      async def run(self, state: DesignState) -> DesignState:
          """Process state and return updated state."""

      def _build_messages(self, state: DesignState) -> list[dict]:
          """Build provider-agnostic message list."""
  ```
- [ ] Create `src/ai_designer/agents/planner.py`:
  1. **System prompt** with CAD domain knowledge (FreeCAD PartDesign workflow rules)
  2. **Chain-of-thought** reasoning: analyze prompt → identify shapes → sequence operations
  3. **Structured JSON output** (via litellm JSON mode): return a `TaskGraph` with:
     - Nodes: individual operations (create sketch, pad, pocket, fillet, etc.)
     - Edges: dependencies (pad depends on sketch, fillet depends on pad)
     - Parameters: dimensions, positions, constraints
  4. **State awareness**: if `DesignState` has existing model state, plan modifications not creation
  5. Uses **Anthropic Claude** as primary (best reasoning), Gemini as fallback
- [ ] Create `src/ai_designer/agents/prompts/planner_prompts.py` — well-engineered system/user prompt templates
- [ ] Write unit tests with mocked LLM responses

**Files to create:**
- `src/ai_designer/agents/__init__.py`
- `src/ai_designer/agents/base.py`
- `src/ai_designer/agents/planner.py`
- `src/ai_designer/agents/prompts/__init__.py`
- `src/ai_designer/agents/prompts/planner_prompts.py`
- `tests/unit/agents/test_planner.py`

---

### Step 10: Build the Generator Agent

**Priority:** 🟢 ESSENTIAL

**Role:** Takes task graph → produces executable FreeCAD Python scripts.

**Actions:**
- [ ] Create `src/ai_designer/agents/generator.py`:
  1. **System prompt** with FreeCAD Python API reference, PartDesign best practices, and few-shot examples
  2. **Per-task generation**: generates a script for each node in the task graph
  3. **AST validation**: parses generated code with Python `ast` module before returning
  4. **Safety check**: validates against the sandbox whitelist (no os/sys/subprocess calls)
  5. **Iterative refinement**: if validator returns errors, receives feedback and regenerates
  6. Uses **OpenAI GPT-4o** as primary (best code gen), DeepSeek as fallback
- [ ] Create `src/ai_designer/agents/prompts/generator_prompts.py`:
  - System prompt with FreeCAD API cheatsheet
  - Few-shot examples library (box, cylinder, bracket, gear, etc.)
  - Error correction prompt (for refinement loops)
- [ ] Create `src/ai_designer/agents/script_validator.py` — lightweight pre-execution checks:
  - AST parse check (syntax valid?)
  - Import whitelist check (only FreeCAD modules?)
  - Dangerous pattern check (no `exec`, `eval`, `os.system`)
  - Returns structured `ScriptCheckResult`
- [ ] Write unit tests with mocked LLM responses and known-good/bad scripts

**Files to create:**
- `src/ai_designer/agents/generator.py`
- `src/ai_designer/agents/script_validator.py`
- `src/ai_designer/agents/prompts/generator_prompts.py`
- `tests/unit/agents/test_generator.py`

---

### Step 11: Build the Validator Agent

**Priority:** 🟢 ESSENTIAL

**Role:** Takes execution result → validates geometry, logic, and design intent.

**Actions:**
- [ ] Create `src/ai_designer/agents/validator.py`:
  1. **Geometric validation** (no LLM needed):
     - Check if FreeCAD recompute succeeded (no errors)
     - Check object count matches expected from task graph
     - Check volume/surface area are positive and within reasonable bounds
     - Check for self-intersections if OCC is available
  2. **LLM-based design review**:
     - Send execution state + original prompt to Claude/GPT-4o
     - Ask: "Does this result match the user's intent? List any issues."
     - Parse structured response into `ValidationResult`
  3. **Score** the result: 0.0-1.0 across dimensions (geometric_accuracy, intent_match, completeness)
  4. **Decision**: pass (score > 0.8), refine (0.4-0.8), fail (< 0.4)
- [ ] Create `src/ai_designer/agents/prompts/validator_prompts.py`
- [ ] Write unit tests

**Files to create:**
- `src/ai_designer/agents/validator.py`
- `src/ai_designer/agents/prompts/validator_prompts.py`
- `tests/unit/agents/test_validator.py`

---

### Step 12: Build the FastAPI REST API

**Priority:** 🟢 ESSENTIAL

**Why:** The CLI is fine for dev, but the system needs proper API endpoints for integration.

**Actions:**
- [ ] Create `src/ai_designer/api/` package:
  - `app.py` — FastAPI application factory with middleware (CORS, error handling, request ID injection)
  - `routes/design.py` — Design endpoints:
    ```
    POST   /api/v1/design          — Submit a design prompt (returns request_id)
    GET    /api/v1/design/{id}     — Get design status + result
    POST   /api/v1/design/{id}/refine  — Submit refinement feedback
    GET    /api/v1/design/{id}/export  — Export model (STEP/STL/FCStd)
    DELETE /api/v1/design/{id}     — Cancel/delete a design
    ```
  - `routes/health.py` — `GET /health`, `GET /ready` (for K8s probes later)
  - `routes/ws.py` — WebSocket endpoint for real-time streaming (wraps existing `websocket_manager.py`)
  - `middleware/auth.py` — API key authentication (simple for now, OAuth later)
  - `middleware/rate_limit.py` — Per-key rate limiting via Redis
  - `deps.py` — FastAPI dependency injection (LLM provider, Redis, state service)
- [ ] Wire the API to call the agent pipeline (Planner → Generator → Executor → Validator)
- [ ] Add request/response logging with correlation IDs
- [ ] Write API integration tests using `httpx` + FastAPI test client

**Files to create:**
- `src/ai_designer/api/__init__.py`
- `src/ai_designer/api/app.py`
- `src/ai_designer/api/deps.py`
- `src/ai_designer/api/routes/__init__.py`
- `src/ai_designer/api/routes/design.py`
- `src/ai_designer/api/routes/health.py`
- `src/ai_designer/api/routes/ws.py`
- `src/ai_designer/api/middleware/__init__.py`
- `src/ai_designer/api/middleware/auth.py`
- `src/ai_designer/api/middleware/rate_limit.py`
- `tests/integration/test_api.py`

---

## PHASE 2 — Intelligence & Integration

### Step 13: Build LangGraph Orchestration Pipeline

**Priority:** 🟢 ESSENTIAL

**Why:** This is the brain that wires agents together with retry logic, conditional routing, and state management.

**Actions:**
- [ ] Create `src/ai_designer/orchestration/` package:
  - `pipeline.py` — LangGraph state machine:
    ```python
    def build_design_pipeline():
        workflow = StateGraph(DesignState)
        workflow.add_node("planner", planner_agent.run)
        workflow.add_node("generator", generator_agent.run)
        workflow.add_node("executor", freecad_executor.run)
        workflow.add_node("validator", validator_agent.run)

        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "generator")
        workflow.add_edge("generator", "executor")
        workflow.add_edge("executor", "validator")

        # Conditional: validator decides next step
        workflow.add_conditional_edges("validator", route_after_validation, {
            "success": END,
            "refine": "generator",    # Loop back with feedback
            "replan": "planner",      # Major issue, replan entirely
            "fail": "human_review"    # Give up, ask human
        })

        return workflow.compile()
    ```
  - `executor_node.py` — FreeCAD execution node (wraps sandbox from Step 2)
  - `routing.py` — Conditional edge logic (score thresholds, iteration limits)
  - `callbacks.py` — WebSocket progress updates on each node transition
- [ ] Integrate with the FastAPI design endpoint (Step 12)
- [ ] Add iteration limit (max 5 refinement loops to prevent infinite cycles)
- [ ] Add timeout per node (30s for LLM calls, 60s for FreeCAD execution)
- [ ] Write integration tests for the full pipeline with mocked agents

**Files to create:**
- `src/ai_designer/orchestration/__init__.py`
- `src/ai_designer/orchestration/pipeline.py`
- `src/ai_designer/orchestration/executor_node.py`
- `src/ai_designer/orchestration/routing.py`
- `src/ai_designer/orchestration/callbacks.py`
- `tests/integration/test_pipeline.py`

---

### Step 14: Enhanced State Management — Redis Streams Audit Trail

**Priority:** 🟢 HIGH

**Actions:**
- [ ] Upgrade `redis_utils/` to support Redis Streams:
  - `redis_utils/audit.py` — Immutable audit log:
    ```python
    class AuditLogger:
        async def log_event(self, event: AuditEvent):
            """Write to Redis Stream: design:{id}:audit"""

        async def get_history(self, design_id: str) -> list[AuditEvent]:
            """Read full audit trail for a design"""
    ```
  - Events: `prompt_received`, `plan_generated`, `script_generated`, `execution_completed`, `validation_passed`, `validation_failed`, `refinement_started`, `design_exported`
- [ ] Upgrade `redis_utils/state_cache.py` to store `DesignState` (Pydantic model serialization)
- [ ] Add TTL-based cleanup for completed designs (configurable, default 24h)
- [ ] Add Redis Pub/Sub for real-time state change notifications → WebSocket bridge

**Files to create:**
- `src/ai_designer/redis_utils/audit.py`

**Files to modify:**
- `src/ai_designer/redis_utils/state_cache.py`
- `src/ai_designer/redis_utils/client.py`

---

### Step 15: FreeCAD Headless Execution Engine

**Priority:** 🟢 HIGH

**Actions:**
- [ ] Create `src/ai_designer/freecad/headless_runner.py`:
  1. Spawn FreeCAD via `freecadcmd` subprocess (no GUI dependency)
  2. Pass generated script via temp file
  3. Capture stdout/stderr + exit code
  4. Parse FreeCAD document state after execution (object list, errors, warnings)
  5. Auto-save output to `outputs/` with metadata (timestamp, request_id, prompt)
  6. Handle recompute errors with retry (exponential backoff, max 3 attempts)
  7. Return structured `ExecutionResult` (Pydantic model from Step 7)
- [ ] Create `src/ai_designer/freecad/state_extractor.py` — extract document state after execution:
  - Object names, types, dimensions
  - Feature tree (parent/child relationships)
  - Any recompute errors or warnings
  - Export as JSON for state management
- [ ] Support STEP and STL export (not just FCStd)
- [ ] Write tests with mock subprocess

**Files to create:**
- `src/ai_designer/freecad/headless_runner.py`
- `src/ai_designer/freecad/state_extractor.py`
- `tests/unit/freecad/test_headless_runner.py`

---

### Step 16: Prompt Engineering Library

**Priority:** 🟢 HIGH

**Why:** The quality of the entire system depends on prompt quality. This deserves its own well-organized module.

**Actions:**
- [ ] Organize `src/ai_designer/agents/prompts/` as a structured library:
  - `system_prompts.py` — Base system prompts per agent role
  - `freecad_reference.py` — FreeCAD API reference formatted for LLM context:
    - PartDesign workflow rules (must create Body → Sketch → Feature)
    - Common API patterns (with correct imports)
    - Constraint types and usage
    - Face selection patterns
  - `few_shot_examples.py` — Curated input/output pairs:
    - 10 simple shapes (box, cylinder, sphere, cone, etc.)
    - 10 intermediate shapes (bracket, flange, housing, etc.)
    - 5 complex shapes (gear, spring, threaded bolt, etc.)
  - `error_correction.py` — Prompts for handling validation failures:
    - Script syntax errors → fix prompt
    - Recompute failures → diagnostic prompt
    - Design intent mismatch → clarification prompt
- [ ] Version the prompts (include a version string) for A/B testing later

**Files to create:**
- `src/ai_designer/agents/prompts/system_prompts.py`
- `src/ai_designer/agents/prompts/freecad_reference.py`
- `src/ai_designer/agents/prompts/few_shot_examples.py`
- `src/ai_designer/agents/prompts/error_correction.py`

---

### Step 17: Export Pipeline

**Priority:** 🟡 MEDIUM

**Actions:**
- [ ] Create `src/ai_designer/export/` package:
  - `exporter.py` — Multi-format export:
    ```python
    class CADExporter:
        def export_step(self, doc, path) -> Path:
            """Export as STEP AP214"""
        def export_stl(self, doc, path, resolution="high") -> Path:
            """Export as STL (configurable resolution)"""
        def export_fcstd(self, doc, path) -> Path:
            """Save native FreeCAD format"""
    ```
  - Add metadata injection (creation timestamp, request_id, prompt hash)
- [ ] Wire into the API `GET /design/{id}/export?format=step`

**Files to create:**
- `src/ai_designer/export/__init__.py`
- `src/ai_designer/export/exporter.py`

---

## PHASE 3 — Production Hardening

### Step 18: Comprehensive Test Suite

**Priority:** 🟢 ESSENTIAL

**Actions:**
- [ ] Restructure `tests/` directory:
  ```
  tests/
  ├── conftest.py          # Shared fixtures (mock LLM, mock Redis, mock FreeCAD)
  ├── unit/
  │   ├── agents/
  │   │   ├── test_planner.py
  │   │   ├── test_generator.py
  │   │   ├── test_validator.py
  │   │   └── test_script_validator.py
  │   ├── llm/
  │   │   └── test_provider.py
  │   ├── core/
  │   │   ├── test_sandbox.py
  │   │   └── test_exceptions.py
  │   ├── freecad/
  │   │   ├── test_headless_runner.py
  │   │   └── test_path_resolver.py
  │   └── schemas/
  │       └── test_design_state.py
  ├── integration/
  │   ├── test_pipeline.py       # Full agent pipeline (mocked LLMs)
  │   ├── test_api.py            # FastAPI endpoint tests
  │   └── test_state_management.py  # Redis integration
  └── fixtures/
      ├── sample_prompts.json    # Test prompts
      ├── sample_scripts.py      # Known-good FreeCAD scripts
      └── sample_responses.json  # Mock LLM responses
  ```
- [ ] Create `tests/conftest.py` with shared fixtures:
  - `mock_llm_provider` — Returns canned responses, no real API calls
  - `mock_redis` — `fakeredis` in-memory
  - `mock_freecad` — Stub FreeCAD module
- [ ] Delete broken/outdated test files that reference non-existent classes
- [ ] Add to Makefile: `make test-unit` (fast, no infra), `make test-integration` (needs Redis)
- [ ] Target: **80% coverage on `agents/`, `llm/`, `core/`, `schemas/`**

**Files to create:**
- `tests/conftest.py`
- All test files listed above
- `tests/fixtures/sample_prompts.json`
- `tests/fixtures/sample_scripts.py`
- `tests/fixtures/sample_responses.json`

---

### Step 19: Docker & Docker Compose — Production Setup

**Priority:** 🟡 HIGH

**Actions:**
- [ ] Create `docker/Dockerfile.app` — App container:
  ```dockerfile
  FROM python:3.11-slim
  # Non-root user
  RUN useradd -m -u 1000 appuser
  WORKDIR /app
  COPY . .
  RUN pip install -e .
  USER appuser
  CMD ["uvicorn", "ai_designer.api.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- [ ] Create `docker/Dockerfile.freecad` — Headless FreeCAD container:
  ```dockerfile
  FROM ubuntu:22.04
  RUN apt-get update && apt-get install -y freecad-daily xvfb
  # Xvfb for headless rendering
  CMD ["xvfb-run", "--auto-servernum", "freecadcmd"]
  ```
- [ ] Update `docker-compose.yml`:
  ```yaml
  services:
    api:           # FastAPI app
    freecad:       # Headless FreeCAD worker
    redis:         # State + Pub/Sub + Streams
  ```
- [ ] Add health checks for all services
- [ ] Add volume mounts for outputs and config
- [ ] Create `docker-compose.dev.yml` override for local development

**Files to create:**
- `docker/Dockerfile.app`
- `docker/Dockerfile.freecad`
- `docker-compose.dev.yml`

**Files to modify:**
- `docker-compose.yml`

---

### Step 20: Observability — Metrics & Health Checks

**Priority:** 🟡 MEDIUM

**Actions:**
- [ ] Add `/health` and `/ready` endpoints (Step 12 health route)
- [ ] Add Prometheus metrics via `prometheus-fastapi-instrumentator`:
  - Request count, latency (P50/P95/P99)
  - LLM call count, latency, cost per provider
  - Agent pipeline success/failure rate
  - FreeCAD execution time
  - Redis connection pool stats
- [ ] Add structured request logging (already set up in Step 5)
- [ ] Create a Grafana dashboard config (optional, for docker-compose)

**Files to create:**
- `src/ai_designer/api/middleware/metrics.py`
- `config/grafana/` (optional)

---

### Step 21: CI/CD Pipeline

**Priority:** 🟡 MEDIUM

**Actions:**
- [ ] Create `.github/workflows/ci.yml`:
  ```yaml
  on: [push, pull_request]
  jobs:
    lint:
      - black --check
      - ruff check (replace flake8 — faster, more rules)
      - mypy
    test:
      - pytest tests/unit/ -v --cov
      - pytest tests/integration/ -v (with Redis service)
    security:
      - bandit -r src/
      - detect-secrets scan
  ```
- [ ] Create `.github/workflows/release.yml` for tagged releases
- [ ] Add branch protection rules (require CI pass before merge)
- [ ] Create `.pre-commit-config.yaml`:
  ```yaml
  repos:
    - repo: https://github.com/psf/black
    - repo: https://github.com/astral-sh/ruff-pre-commit
    - repo: https://github.com/pre-commit/mirrors-mypy
    - repo: https://github.com/Yelp/detect-secrets
  ```

**Files to create:**
- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`

---

## Final Target Directory Structure

```
src/ai_designer/
├── __init__.py
├── __main__.py
│
├── agents/                          # NEW — Multi-Agent System
│   ├── __init__.py
│   ├── base.py                      # Abstract base agent
│   ├── planner.py                   # Task decomposition agent
│   ├── generator.py                 # FreeCAD script generation agent
│   ├── validator.py                 # Geometry + design validation agent
│   ├── script_validator.py          # AST-based script safety checks
│   └── prompts/
│       ├── __init__.py
│       ├── system_prompts.py
│       ├── planner_prompts.py
│       ├── generator_prompts.py
│       ├── validator_prompts.py
│       ├── freecad_reference.py
│       ├── few_shot_examples.py
│       └── error_correction.py
│
├── api/                             # NEW — FastAPI REST API
│   ├── __init__.py
│   ├── app.py
│   ├── deps.py
│   ├── routes/
│   │   ├── design.py
│   │   ├── health.py
│   │   └── ws.py
│   └── middleware/
│       ├── auth.py
│       ├── rate_limit.py
│       └── metrics.py
│
├── orchestration/                   # NEW — LangGraph Pipeline
│   ├── __init__.py
│   ├── pipeline.py
│   ├── executor_node.py
│   ├── routing.py
│   └── callbacks.py
│
├── schemas/                         # NEW — Pydantic Data Contracts
│   ├── __init__.py
│   ├── design_state.py
│   ├── task_graph.py
│   ├── llm_schemas.py
│   ├── api_schemas.py
│   └── validation.py
│
├── llm/                             # REFACTORED — Unified LLM Layer
│   ├── __init__.py
│   ├── provider.py                  # NEW — litellm unified provider
│   ├── model_config.py              # NEW — Model selection config
│   ├── client.py                    # DEPRECATED — old Gemini client
│   ├── deepseek_client.py           # DEPRECATED — old DeepSeek client
│   ├── unified_manager.py           # DEPRECATED — old manager
│   └── prompt_templates.py
│
├── core/                            # CLEANED — Core business logic
│   ├── __init__.py
│   ├── sandbox.py                   # NEW — Safe script execution
│   ├── exceptions.py                # NEW — Exception hierarchy
│   ├── logging_config.py            # NEW — Structured logging
│   ├── orchestrator.py              # KEEP — Legacy orchestrator (deprecated)
│   ├── intent_processor.py          # KEEP
│   ├── command_generator.py         # KEEP (used by CLI)
│   └── queue_manager.py             # KEEP
│
├── freecad/                         # ENHANCED — FreeCAD Integration
│   ├── __init__.py
│   ├── path_resolver.py             # NEW — Centralized path resolution
│   ├── headless_runner.py           # NEW — Subprocess-based execution
│   ├── state_extractor.py           # NEW — Post-execution state extraction
│   ├── api_client.py                # CLEANED — No hardcoded paths
│   ├── command_executor.py          # CLEANED
│   ├── state_manager.py             # CLEANED
│   └── workflow_orchestrator.py     # KEEP
│
├── export/                          # NEW — Multi-format export
│   ├── __init__.py
│   └── exporter.py
│
├── cli/                             # REFACTORED from cli.py
│   ├── __init__.py
│   ├── app.py
│   ├── commands.py
│   ├── formatters.py
│   └── session.py
│
├── config/                          # KEEP
│   ├── __init__.py
│   └── secure_config.py
│
├── redis_utils/                     # ENHANCED
│   ├── __init__.py
│   ├── client.py
│   ├── state_cache.py
│   └── audit.py                     # NEW — Redis Streams audit trail
│
├── realtime/                        # KEEP
│   └── websocket_manager.py
│
└── services/                        # KEEP
    └── state_service.py
```

---

## Implementation Order & Dependencies

```
Step 1  (Security: Remove secrets)          ──┐
Step 2  (Security: Replace exec)            ──┤── Can be done in parallel
Step 3  (Remove hardcoded paths)            ──┤
Step 4  (Clean dependencies)                ──┘
                                              │
Step 5  (Logging & exceptions)              ──┤── Depends on Step 4 (new deps)
Step 6  (Refactor god classes)              ──┘
                                              │
Step 7  (Schemas / data contracts)          ──── Foundation for everything below
                                              │
Step 8  (litellm unified provider)          ──┤── Can be done in parallel
Step 9  (Planner agent)                     ──┤── Depends on Step 7 + 8
Step 10 (Generator agent)                   ──┤── Depends on Step 7 + 8
Step 11 (Validator agent)                   ──┘── Depends on Step 7 + 8
                                              │
Step 12 (FastAPI REST API)                  ──── Depends on Step 7
Step 13 (LangGraph pipeline)               ──── Depends on Steps 9-12
Step 14 (Redis Streams audit)              ──── Depends on Step 7
Step 15 (Headless FreeCAD runner)           ──── Depends on Steps 2, 3
Step 16 (Prompt engineering library)        ──── Depends on Steps 9-11
Step 17 (Export pipeline)                   ──── Depends on Step 15
                                              │
Step 18 (Test suite)                        ──── Depends on Steps 7-13
Step 19 (Docker production)                 ──── Depends o# AI Pipeline Stabilization Plan

## Summary
Build the next backend-only AI pipeline layer that makes the current graph/classifier/retrieval system reliable before adding new product features. The goal is not UI, connectors, Slack Q&A migration, spec generation, or new recommendation features. The goal is: signals can be classified, linked, indexed, retrieved, audited, and operationally recovered with confidence.

Current verified state:
- `pnpm type-check` passed.
- Targeted graph tests passed: 15 tests across classifier, curation, and problem services.
- `pnpm db:check-migration` passed.
- `pnpm ai:memory:test:mocked` and stress eval passed.
- The main remaining AI-pipeline gaps are observability, retrieval packaging, index recovery, and stronger operational validation.

## Key Changes

### 1. Persist Resolver Diagnostics
Add a lightweight diagnostic record for every signal classification attempt.

Implement a new Prisma model, tentatively `SignalResolverDiagnostic`, linked to workspace and signal. Store:
- `workspaceId`
- `signalId`
- `outcomeType`: `linked_existing_problem`, `created_candidate_problem`, `no_match`, or `failed`
- `resolverPath`: `AUTO_DIRECT`, `AUTO_MODEL`, or `NONE`
- `promptVersion`
- `embeddingModel`
- `informativeTokenCount`
- `isMultiIssueSignal`
- `workspaceProblemDensity`
- selected `problemIds` as JSON
- candidate scores/thresholds as JSON
- model issue count
- `errorMessage`
- `createdAt`

Record diagnostics from:
- direct-link path
- model-link path
- candidate-created path
- no-match path
- failed classification path

Do not implement automatic recalibration yet. Use diagnostics only to make current resolver behavior inspectable and debuggable.

### 2. Add an Internal Retrieval Context Package
Keep `searchMemoryGraph()` as the low-level graph retrieval API, then add an internal packaging layer for AI use.

Create a service like `services/graph/memory-context-package-service.ts` that converts hydrated matches into a stable `MemoryContextPackage`.

The package should include:
- normalized memory items
- citation IDs
- source node type
- source object ID
- source URL when available
- short evidence text
- score
- linked problem/feature/decision summaries when available

Default behavior:
- hide `CANDIDATE` problems unless explicitly allowed
- cap total package size
- cap supporting signals per problem
- trim long evidence text
- preserve enough source metadata for later citation rendering

Do not connect this to Slack, frontend, or a public API in this pass. This is internal plumbing so future answer generation does not reason over raw hydrated DB rows.

### 3. Add Vector Index Recovery Tooling
Add backend operational tooling so Postgres remains recoverable as the source of truth when Qdrant is stale or missing.

Create a script such as `scripts/reindex-memory.ts` and package command like:

```bash
pnpm ai:memory:reindex -- --workspaceId=<id> --execute
```

Defaults:
- dry-run unless `--execute` is provided
- optional `--workspaceId`
- optional `--aggregateType`
- do not delete Qdrant points by default

Behavior:
- load current graph nodes from Postgres
- rebuild the same outbox payload text used by graph services
- enqueue new outbox events for those nodes
- log counts by aggregate type
- fail clearly if no workspace/nodes are found

Do not build a UI for this.

### 4. Strengthen Pipeline Health Checks
Extend existing synthetic/eval tooling instead of adding product features.

Enhance the current AI memory validation scripts to report and fail on:
- stale `PROCESSING` signals beyond timeout
- terminally failed classifier rows
- failed outbox rows after max attempts
- missing Qdrant points for active graph nodes
- candidate problems visible in default retrieval
- human-confirmed links overwritten by automated relinking
- unexpected `ProblemSignalEdge` status distribution

Keep mocked/stress eval deterministic. Keep live eval report-only.

## Public Interfaces / Types
Add only backend/internal interfaces:

- `SignalResolverDiagnostic` Prisma model and migration.
- `recordSignalResolverDiagnostic(input)` service helper.
- `MemoryContextPackage` TypeScript interface.
- `buildMemoryContextPackage(input)` service helper.
- `pnpm ai:memory:reindex` script command.

No frontend routes. No connector changes. No Slack answer rewrite. No automatic calibration learning.

## Test Plan
Add or update tests for:

- resolver diagnostics are written for direct match, model match, candidate creation, no-match, and failure
- diagnostics include `promptVersion` only when model classification ran
- diagnostics do not break classification when diagnostic write fails; log and continue
- memory context package hides candidates by default
- memory context package includes citations for signals and problem-supporting signals
- memory context package respects caps/trimming
- reindex script dry-run does not write outbox rows
- reindex script execute mode enqueues expected outbox rows
- synthetic check catches stale processing rows and failed outbox/classifier states

Run before considering the pass complete:

```bash
pnpm type-check
pnpm db:check-migration
pnpm test:unit tests/unit/services/graph/signal-classification-service.test.ts tests/unit/services/graph/problem-curation-service.test.ts tests/unit/services/graph/problem-service.test.ts tests/unit/services/graph/retrieval-service.test.ts
pnpm ai:memory:test:mocked
pnpm ai:memory:test:stress -- --size=1000
git diff --check
```

## Assumptions
- AI pipeline scope means graph memory, signal classification, vector indexing, retrieval packaging, diagnostics, and validation.
- Frontend, connector work, Slack Q&A migration, Jira work, spec generation, and task generation are out of scope.
- Candidate review APIs may remain backend-only for now.
- Calibration stays manual/report-only until diagnostics provide enough data to tune safely.
n Steps 12, 15
Step 20 (Observability)                     ──── Depends on Step 12
Step 21 (CI/CD)                             ──── Depends on Step 18
```

---

## Best Practices Checklist (Enforced at Every Step)

- [ ] **Type hints everywhere** — All function signatures have type annotations, enforced by mypy
- [ ] **Pydantic for data** — No `Dict[str, Any]` passed between components; use typed schemas
- [ ] **Dependency injection** — Components receive dependencies via constructor, not global imports
- [ ] **Async-first** — All agent and API code is async (LLM calls are I/O-bound)
- [ ] **Single responsibility** — No file exceeds ~400 lines; each class does one thing
- [ ] **No secrets in code** — All sensitive values from `.env` via `SecureConfig`
- [ ] **Structured logging** — JSON logs with correlation IDs, no `print()` in production code
- [ ] **Tests alongside code** — Every new module gets unit tests before merge
- [ ] **Error handling** — Custom exception hierarchy, never bare `except Exception`
- [ ] **Documentation** — Docstrings on all public classes and methods (Google style)
- [ ] **Git hygiene** — One feature per branch, descriptive commits, PR reviews
- [ ] **Configuration over code** — Behavior changes via `config.yaml`, not code changes

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Unified LLM SDK** | `litellm` | Wraps 100+ providers with one `completion()` call. Handles retries, fallback, cost tracking. Avoids maintaining separate clients for each provider. |
| **Agent framework** | `langgraph` | Lightweight state machine built for agent loops. Better than AutoGen (too opinionated) or CrewAI (too magical). Clean conditional edges and retry logic. |
| **Planner LLM** | Anthropic Claude 3.5 Sonnet | Best chain-of-thought reasoning. Excellent at structured JSON output. |
| **Generator LLM** | OpenAI GPT-4o | Best code generation accuracy. Strong FreeCAD Python knowledge. |
| **API framework** | FastAPI (already declared) | Async, auto-docs, Pydantic integration. Already a dependency. |
| **Logging** | `structlog` | Structured JSON logging with context binding. Better than stdlib `logging` for production. |
| **Python version** | 3.10+ | Need `TypedDict` improvements, `match` statements, modern union types (`X \| Y`). |
| **Testing** | pytest + fakeredis + respx | Mock Redis with fakeredis, mock HTTP with respx, no real infra needed for unit tests. |
| **Deferred: Vector DB/RAG** | Phase 2+ | Agents should work well with pure LLM reasoning first. RAG adds complexity without proven need yet. |
| **Deferred: ML Embeddings** | Phase 2+ | PointNet++/GraphSAGE require training data and GPUs. Get the pipeline working first. |
| **Deferred: Ray distributed** | Phase 3+ | Premature until we prove the pipeline works at single-node scale. K8s scaling is simpler. |

---

## Ready to Start

**First task:** Step 1 — Remove the leaked API key and secure all secret access.

> Tell me "let's start" and we'll implement Step 1 immediately.

# Entrypoints: canonical vs legacy stacks

This matrix documents how to run AI Designer after **Track 1 (canonical runtime path)**. The **LangGraph multi-agent pipeline** (`PlannerAgent` → `GeneratorAgent` → `FreeCADExecutor` → `ValidatorAgent`) is the same stack as `POST /api/v1/design` (see FastAPI app).

## Quick reference

| Goal | Command / entry |
|------|------------------|
| **Design from a prompt (recommended)** | `python -m ai_designer "Your natural language prompt here"` |
| **Interactive design (agent REPL)** | `python -m ai_designer` (no sub-args) |
| **HTTP API** | `uvicorn ai_designer.api.app:app --host 0.0.0.0 --port 8000` then `POST /api/v1/design` |
| **Legacy FreeCAD CLI** (full REPL, `execute_command`, etc.) | `python -m ai_designer --legacy-cli ...` |
| **Legacy enhanced orchestrator** (Redis / WebSocket stack) | `python -m ai_designer --legacy-enhanced` (or `--enhanced`, deprecated) |
| **Analyze a `.FCStd` file** | `python -m ai_designer --analyze /path/to/file.FCStd` (uses legacy analyzer today) |

## Full matrix

| Entry | Module | Stack | Notes |
|-------|--------|-------|--------|
| `uvicorn ai_designer.api.app:app` | `api/routes/design.py` | `PipelineExecutor` (LangGraph) | Stable HTTP contract: `DesignCreateRequest` / `DesignResponse`. |
| `python -m ai_designer "<prompt>"` | `__main__.py` → `cli_agent` + `runtime/pipeline_factory` | Same `PipelineExecutor` as API | Canonical CLI for one-shot NL design. |
| `python -m ai_designer` (no args) | `cli_agent` | Same pipeline, minimal REPL | Reads prompts until `exit` / EOF. |
| `python -m ai_designer --legacy-cli ...` | `cli.py` (`FreeCADCLI`) | Command executor + unified LLM + enhanced generator | Opt-in; stderr notice on startup. |
| `python -m ai_designer --legacy-enhanced` | `core/orchestrator.py` (`SystemOrchestrator`) | Intent / state-aware command path + Redis | Opt-in. |
| `python -m ai_designer --enhanced` | Same as `--legacy-enhanced` | Same | **Deprecated** alias; emits `DeprecationWarning`. |
| `python -m ai_designer --analyze FILE` | `FreeCADCLI` | Legacy analyzer | Still uses legacy stack internally; no need for `--legacy-cli`. |
| Docker `CMD` | `docker/Dockerfile.*` | Typically uvicorn | Same as API row. |

## API stability

- **Stable:** JSON request/response shapes for published `/design` routes (see OpenAPI / `schemas/api_schemas.py`).
- **CLI:** New flags (`--legacy-cli`, `--legacy-enhanced`) may evolve; positional prompt behavior is the documented primary CLI.

## Manual smoke (canonical + legacy)

Run when validating releases (optional FreeCAD / LLM env required):

1. **Canonical one-shot:**
   `python -m ai_designer "Create a simple 10mm cube named TestCube"`
   Expect planner/generator/executor activity; final status printed.

2. **Canonical REPL:**
   `python -m ai_designer` → enter a prompt → `exit`.

3. **Legacy CLI:**
   `python -m ai_designer --legacy-cli "help"` (or interactive) → confirm legacy banner/notice.

4. **Legacy enhanced:**
   `python -m ai_designer --legacy-enhanced` (Redis optional) → single command or interactive.

After **Track 5** (executor–validator contract), re-run smoke with focus on metrics/refinement on the canonical path; legacy removal is a later milestone.

## Related docs

- [PARALLEL_REMEDIATION_PLAN.md](./PARALLEL_REMEDIATION_PLAN.md) — Track 1 context and merge order with Track 5.

# Repository Analysis: Why Complex 3D Model Quality Is Still Weak

Date: 2026-04-23

## Scope

This report is based on static inspection of the current repository. I did not run full FreeCAD generation benchmarks, so the conclusions below are drawn from the implemented runtime paths, data contracts, prompts, workflow logic, and tests.

## Short Answer

The repository can build simple primitives and some scripted multi-step examples, but it is not yet a reliable complex CAD generation system.

The main reason is not one single bug. It is a stack problem:

1. The default runtime path still goes through older heuristic code paths.
2. The newer multi-agent path is more structured, but its planning/generation/validation loop is still too primitive for complex PartDesign work.
3. Several "advanced" workflow pieces are placeholders or mock implementations.
4. State understanding and quality validation are too shallow to support robust refinement.

As a result, the system can often produce something simple, but it does not yet have the modeling semantics, execution feedback loop, or real validation needed for high-quality and complex 3D outputs.

## What The Repo Already Has

The repo is not empty. It already contains useful building blocks:

- Headless FreeCAD execution and document saving in `src/ai_designer/freecad/headless_runner.py`.
- Document state extraction in `src/ai_designer/freecad/state_extractor.py`.
- A newer planner/generator/validator stack in `src/ai_designer/agents/`.
- A FastAPI layer and orchestration package in `src/ai_designer/api/` and `src/ai_designer/orchestration/`.
- Legacy state-aware and workflow-oriented utilities in `src/ai_designer/core/` and `src/ai_designer/freecad/`.

The problem is that these pieces do not yet form one coherent, high-fidelity CAD generation system.

## Core Findings

### 1. The repo has two overlapping architectures, and the default user path still uses the older one

The default CLI path in `src/ai_designer/__main__.py:133-219` routes users either to `SystemOrchestrator` or `FreeCADCLI`, not directly to the newer agent pipeline.

`FreeCADCLI` in `src/ai_designer/cli.py:58-237` initializes:

- `CommandExecutor`
- `StateAwareCommandProcessor`
- `UnifiedLLMManager`
- `EnhancedComplexShapeGenerator`

The "enhanced" CLI path also still builds the legacy stack through `SystemOrchestrator` in `src/ai_designer/core/orchestrator.py:70-165`, which wires:

- `IntentProcessor`
- `StateAwareCommandGenerator`
- `CommandExecutor`
- `StateLLMIntegration`

That means the repo's primary user-facing path is still mostly heuristic and legacy-oriented. The newer planner/generator/validator code exists, but it is not the main default experience.

Why this hurts quality:

- improvements in the new stack do not automatically improve the main runtime path
- behavior differs by entrypoint
- debugging becomes harder because there is no single canonical modeling pipeline

### 2. Planning is still too primitive for complex CAD

The active `PlannerAgent` only exposes a small operation set in `src/ai_designer/agents/planner.py:55-113`:

- `create_box`
- `create_cylinder`
- `create_sphere`
- `create_cone`
- `create_torus`
- boolean ops
- `fillet`
- `chamfer`
- `extrude`
- `revolve`

What is missing for good complex parametric models:

- explicit `PartDesign::Body` creation
- sketch creation as a first-class planning step
- sketch geometry primitives and constraints
- `Pad` / `Pocket` / `Groove` / `Loft` / `Sweep` / `Pipe` / `Shell` / `Draft`
- datum planes / attachment references
- linear and polar patterns
- mirror operations
- assembly constraints
- topological reference strategy

There is a richer prompt library in `src/ai_designer/agents/prompts/system_prompts.py:20-137`, but the runtime `PlannerAgent` does not use that richer PartDesign-oriented prompt. It uses its own simpler embedded prompt instead.

Why this hurts quality:

- the planner cannot express the kinds of feature trees that complex CAD models need
- the system is biased toward primitive solids plus booleans instead of stable parametric modeling
- even a strong LLM cannot plan features the schema does not represent well

### 3. The generator is still centered on primitive object creation, not robust feature-tree modeling

`GeneratorAgent` uses an embedded system prompt in `src/ai_designer/agents/generator.py:48-129`. Its examples are mostly:

- `Part::Box`
- `Part::Cylinder`
- `Part::Cut`
- `Part::Fillet`

That is useful for simple geometry, but high-quality complex CAD usually needs:

- a body-first workflow
- sketches with constraints
- face- or datum-attached downstream features
- stable reference management
- repeated features and patterns
- controlled feature ordering

The legacy rule-based generator is even more limited. `StateAwareCommandGenerator` only has direct rule logic for box/cylinder/sphere creation in `src/ai_designer/core/command_generator.py:181-240`.

Why this hurts quality:

- primitive-first generation tends to create brittle models
- complex mechanical parts need constrained sketches and feature history, not just free-form object creation
- downstream edits become unstable without a proper PartDesign structure

### 4. The "complex workflow" engine is partly placeholder code

The repo has a `WorkflowOrchestrator`, but several advanced steps are not actually implemented.

In `src/ai_designer/freecad/workflow_orchestrator.py:485-515`, unsupported step types are treated as successful mock execution.

More specifically:

- hole execution is a mock in `src/ai_designer/freecad/workflow_orchestrator.py:876-891`
- pattern execution is a mock in `src/ai_designer/freecad/workflow_orchestrator.py:893-908`
- fillet/chamfer feature execution is a mock in `src/ai_designer/freecad/workflow_orchestrator.py:910-925`
- housing workflow is a placeholder in `src/ai_designer/freecad/workflow_orchestrator.py:1162-1167`
- assembly workflow is a placeholder in `src/ai_designer/freecad/workflow_orchestrator.py:1169-1174`

Why this hurts quality:

- the code can report workflow success without creating the real CAD feature
- advanced commands look supported at the API level but are not fully implemented
- complex model generation appears broader than it really is

### 5. The newer validation loop is structurally mismatched

This is one of the most important concrete problems.

`ValidatorAgent` expects execution feedback like:

- `object_count`
- `total_volume`
- `bounding_box`
- `is_manifold`
- `has_invalid_faces`
- `has_self_intersections`

See `src/ai_designer/agents/validator.py:196-277`.

But the executor path used by the orchestration nodes strips execution output down to:

- `success`
- `output`
- `error`
- `execution_time`
- `document_path`

See `src/ai_designer/orchestration/nodes.py:255-270`.

And `FreeCADExecutor.execute()` itself mainly returns:

- `created_objects`
- `errors`
- `execution_time`
- `document_path`
- optional `state`

See `src/ai_designer/agents/executor.py:136-145` and `src/ai_designer/agents/executor.py:169-194`.

So the validator asks for geometry metrics that the pipeline does not actually pass through.

Practical effect:

- `object_count` falls back to `0`
- `total_volume` falls back to `0`
- geometric validation can degrade even when execution succeeded
- refinement decisions become low quality because the feedback signal is incomplete

This is a major reason the system cannot improve complex outputs reliably through iteration.

### 6. Semantic validation is too shallow for complex design intent

Semantic validation in `src/ai_designer/agents/validator.py:313-391` works by looking for string tokens such as:

- `"Box"`
- `"Cylinder"`
- `"Cut"`
- `"Fuse"`
- `"Fillet"`

and matching them back to expected task types.

That is not enough for complex CAD quality. It does not check:

- whether the part dimensions really satisfy the prompt
- whether hole locations are correct
- whether feature order is sensible
- whether constraints preserve design intent
- whether the geometry is manufacturable
- whether a pattern/mirror/assembly is actually correct

Why this hurts quality:

- the system can score itself as semantically acceptable while still producing a poor part
- refinement suggestions are driven by weak signals

### 7. State understanding is too shallow for difficult CAD work

`StateExtractor` in `src/ai_designer/freecad/state_extractor.py:122-250` extracts:

- object list
- feature tree links
- bounding boxes
- basic dimensions
- sketch constraint counts
- recompute errors

That is useful, but not enough for advanced reasoning.

What is missing:

- robust topology graph for faces/edges/vertices
- persistent reference strategy across recomputes
- sketch degrees of freedom / underconstraint details
- feature dependency semantics beyond parent/child names
- exact geometric measurements needed for refinement
- manufacturability metrics
- tolerance / clearance checks

Why this hurts quality:

- complex CAD refinement depends on precise state
- without strong state representation, the LLM is mostly guessing from a shallow summary

### 8. Face selection can silently fall back to fake geometry

The face-selection subsystem is not reliable enough for advanced operations.

If parsing fails or no faces are found, `FaceDetectionEngine` returns mock face data in `src/ai_designer/freecad/face_selection_engine.py:160-167` and `src/ai_designer/freecad/face_selection_engine.py:191-214`.

Why this hurts quality:

- wrong faces can be treated as valid faces
- downstream hole/pocket/feature operations can target non-real geometry
- failures get masked instead of surfaced

### 9. The legacy path uses keyword heuristics instead of geometric reasoning

The old path still makes many decisions using regexes and keyword counts:

- `IntentProcessor` in `src/ai_designer/core/intent_processor.py:22-64`
- workflow selection in `src/ai_designer/freecad/workflow_templates.py:67-162`
- geometry extraction in `src/ai_designer/freecad/geometry_helpers.py:14-68`

For example, `analyze_geometry_requirements()` only really knows how to interpret:

- cylinder
- box
- hole
- diameter
- height

See `src/ai_designer/freecad/geometry_helpers.py:25-68`.

Why this hurts quality:

- complex commands are being reduced to weak keyword-based structure
- there is no deep geometric parse of user intent
- anything beyond simple patterns becomes brittle

### 10. Multi-step state persistence is still fragile

`StateAwareCommandProcessor` explicitly notes that in subprocess mode each step runs in an isolated process, so final workflow saves may not reflect accumulated modeling state. See `src/ai_designer/freecad/state_aware_processor.py:190-198`.

Why this hurts quality:

- multi-step workflows are much harder to trust if state is not carried forward robustly
- complex modeling depends on accumulating correct document state across steps

### 11. Tests are broad, but not strong evidence of real complex-CAD capability

The test suite includes many files, but much of the unit coverage is mocked:

- FreeCAD is heavily mocked in `tests/conftest.py:101-139`
- generator tests focus on box/cylinder/cut patterns in `tests/unit/agents/test_generator.py:65-158`
- sample scripts are mostly box, cylinder, L-bracket, and box-with-hole in `tests/fixtures/sample_scripts.py:7-165`

What is missing from the test strategy:

- a benchmark corpus of real complex prompts
- execution against real FreeCAD for multi-feature parts
- quantitative quality metrics for geometry correctness
- regression tests for patterns, assemblies, lofts, sweeps, shells, and complex sketches

Why this hurts quality:

- the repo can look mature from unit-test count alone while still lacking proof on hard CAD tasks

## What Is Missing

These are the highest-value missing capabilities if the goal is good complex 3D model generation.

### Modeling capabilities

- true PartDesign-first planning and generation
- explicit sketch geometry and constraint planning
- pocket, groove, loft, sweep, shell, draft, mirror, pattern support
- datum planes and robust support references
- assembly modeling beyond placeholders

### State and geometry understanding

- persistent face/edge reference strategy
- richer B-Rep/topology summaries
- real geometric measurements for refinement
- sketch constraint and underconstraint analysis
- manufacturability and tolerance checks

### Validation and refinement

- a consistent executor -> validator data contract
- real geometry quality metrics propagated into the loop
- image/mesh/B-Rep-based validation, not only keyword checks
- robust error-correction based on real FreeCAD failures

### Evaluation

- real benchmark prompt set for simple, medium, and hard parts
- pass/fail criteria tied to expected geometry
- regression harness for complex workflows

## Root Cause Summary

The deepest reason the repo struggles is this:

It is currently closer to a promising CAD automation framework than to a finished complex CAD generation engine.

It has many components, but several of them are:

- duplicated across old and new architectures
- not fully wired together
- still heuristic
- still placeholder implementations
- not validated on real complex part benchmarks

So the quality ceiling is low. The system does not yet have enough deterministic CAD structure, rich state feedback, or real validation to reliably synthesize complex, high-quality 3D models.

## Priority Fix Order

If the goal is to materially improve quality, the fastest high-impact sequence is:

1. Pick one canonical runtime path and retire or isolate the older one.
2. Fix the executor/validator contract so real geometry metrics flow into refinement.
3. Upgrade planning from primitive ops to true PartDesign feature planning.
4. Replace placeholder workflow steps with real implementations or remove them from claimed capability.
5. Wire the richer prompt/reference libraries into the active planner and generator.
6. Add a real complex-model benchmark suite with FreeCAD execution in the loop.
7. Add topology-aware state extraction and stable reference handling.

## Bottom Line

The repo is not failing because FreeCAD or the LLM alone is weak. It is failing because the current system still mixes:

- heuristic intent parsing
- primitive-first generation
- placeholder advanced workflows
- shallow validation
- split architectures

Until those are unified and the refinement loop is fed with real geometry signals, the system will remain decent at simple shapes and inconsistent on high-quality complex mechanical models.

"""
Versioned planner JSON schema and operation vocabulary.

Track 3 (generator) imports :func:`assert_generator_can_emit` and
:data:`OPERATION_API_HINTS` from this module. ``planned_only`` operations are
schema-valid but the generator rejects them until implemented.

Supported ``plan_version`` values: ``1`` only.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Literal, Optional, Set, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Plan version
# ---------------------------------------------------------------------------

CURRENT_PLAN_VERSION: Literal[1] = 1
SUPPORTED_PLAN_VERSIONS: FrozenSet[int] = frozenset({1})

# ---------------------------------------------------------------------------
# Operation tiers
# ---------------------------------------------------------------------------
# Executable: generator emits task-block FreeCAD code (Part primitives + first
# PartDesign slice: body, sketch, pad). See docs/PARALLEL_REMEDIATION_PLAN.md Track 3.

EXECUTABLE_PLANNER_OPS: FrozenSet[str] = frozenset(
    {
        "boolean_common",
        "boolean_cut",
        "boolean_fuse",
        "chamfer",
        "create_body",
        "create_box",
        "create_cone",
        "create_cylinder",
        "create_sketch",
        "create_sphere",
        "create_torus",
        "extrude",
        "fillet",
        "pad",
        "revolve",
    }
)

# PartDesign-oriented and auxiliary ops: valid in JSON; generator fails fast.
PLANNED_ONLY_PLANNER_OPS: FrozenSet[str] = frozenset(
    {
        "add_angle_constraint",
        "add_arc",
        "add_circle",
        "add_coincident",
        "add_distance_constraint",
        "add_line",
        "add_polygon",
        "add_rectangle",
        "add_tangent",
        "close_sketch",
        "datum_line",
        "datum_plane",
        "datum_point",
        "draft",
        "linear_pattern",
        "loft",
        "mirror",
        "move",
        "pocket",
        "polar_pattern",
        "revolution",
        "rotate",
        "scale",
        "shell",
        "sweep",
    }
)

ALL_PLANNER_OPERATIONS: Tuple[str, ...] = tuple(
    sorted(EXECUTABLE_PLANNER_OPS | PLANNED_ONLY_PLANNER_OPS)
)
ALL_PLANNER_OPERATIONS_SET: FrozenSet[str] = frozenset(ALL_PLANNER_OPERATIONS)


class UnsupportedGeneratorOperation(ValueError):
    """Raised when :class:`~ai_designer.agents.generator.GeneratorAgent` cannot emit code."""

    pass


def is_planner_operation(name: str) -> bool:
    return name in ALL_PLANNER_OPERATIONS_SET


def is_executable_operation(name: str) -> bool:
    return name in EXECUTABLE_PLANNER_OPS


def is_generator_executable(name: str) -> bool:
    """True if the generator will attempt code generation for this ``operation_type``."""
    return name in EXECUTABLE_PLANNER_OPS


def assert_generator_can_emit(operation_type: str) -> None:
    """Raise :exc:`UnsupportedGeneratorOperation` if the generator cannot run this op."""
    if operation_type in EXECUTABLE_PLANNER_OPS:
        return
    if operation_type in PLANNED_ONLY_PLANNER_OPS:
        raise UnsupportedGeneratorOperation(
            f"Generator: operation {operation_type!r} is schema-valid (planned_only) "
            "but not implemented in the generator yet. "
            "See docs/PARALLEL_REMEDIATION_PLAN.md Track 3."
        )
    raise UnsupportedGeneratorOperation(
        f"Generator: unknown operation {operation_type!r}. "
        "Extend ai_designer.schemas.planner_plan if this op should exist."
    )


# Short API hints appended to per-task USER messages (concrete FreeCAD script shape).
OPERATION_API_HINTS: Dict[str, str] = {
    "create_box": (
        "Use doc.addObject('Part::Box', unique_name); set .Length, .Width, .Height (mm floats)."
    ),
    "create_cylinder": (
        "Use doc.addObject('Part::Cylinder', unique_name); set .Radius, .Height; "
        "optional .Placement.Base for position (floats or .Value from deps)."
    ),
    "create_sphere": "Use doc.addObject('Part::Sphere', unique_name); set .Radius.",
    "create_cone": (
        "Use doc.addObject('Part::Cone', unique_name); set .Radius1, .Radius2, .Height."
    ),
    "create_torus": (
        "Use doc.addObject('Part::Torus', unique_name); set .Radius1, .Radius2 as needed."
    ),
    "boolean_cut": (
        "Use doc.addObject('Part::Cut', unique_name); set .Base and .Tool to dependency variables."
    ),
    "boolean_fuse": "Use doc.addObject('Part::Fuse', unique_name); set .Base and .Tool.",
    "boolean_common": "Use doc.addObject('Part::Common', unique_name); set .Base and .Tool.",
    "fillet": (
        "Use doc.addObject('Part::Fillet', unique_name); set .Base to solid; "
        ".Edges as list of (edge_index, start_rad, end_rad) tuples."
    ),
    "chamfer": (
        "Use doc.addObject('Part::Chamfer', unique_name); set .Base; "
        ".Edges similar to fillet per FreeCAD API."
    ),
    "extrude": (
        "Prefer PartDesign: dependency sketch variable → doc.addObject('PartDesign::Pad', …); "
        "set .Profile = sketch, .Length = distance (mm). Or Part extrusion if sketch is wire."
    ),
    "revolve": (
        "PartDesign::Revolution or revolve sketch profile around axis; set Profile from sketch dep."
    ),
    "create_body": (
        "doc.addObject('PartDesign::Body', unique_name); result is the PartDesign body container."
    ),
    "create_sketch": (
        "Depends on PartDesign::Body variable: sketch = doc.addObject('Sketcher::SketchObject', "
        "name); body.addObject(sketch); sketch.MapMode = 'FlatFace'; "
        "sketch.Support = (doc.XY_Plane, ['']) or doc.XZ_Plane / doc.YZ_Plane; "
        "addGeometry with Part.LineSegment / Part.Circle using App.Vector (App/Part in scope)."
    ),
    "pad": (
        "Depends on body + sketch: pad = doc.addObject('PartDesign::Pad', unique_name); "
        "body.addObject(pad); pad.Profile = sketch_var; pad.Length = extrude_length (float mm)."
    ),
}


def format_planner_op_list_for_prompt() -> str:
    """Human-readable op lists for system prompt (avoids drift from registry)."""
    exe = "\n".join(f"- {op}" for op in sorted(EXECUTABLE_PLANNER_OPS))
    planned = "\n".join(f"- {op}" for op in sorted(PLANNED_ONLY_PLANNER_OPS))
    return (
        "**Executable in the default generator pipeline (Part primitives + PartDesign body/sketch/pad):**\n"
        f"{exe}\n\n"
        "**Planned vocabulary (schema-valid; generator fails fast until implemented):**\n"
        f"{planned}"
    )


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class PlanDependency(BaseModel):
    model_config = ConfigDict(extra="ignore")

    from_task_id: str
    to_task_id: str
    dependency_type: str = "requires"


class PlanTask(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., min_length=1)
    operation: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"


class PlanEnvelope(BaseModel):
    """Validated planner output before :class:`TaskGraph` construction."""

    model_config = ConfigDict(extra="ignore")

    plan_version: int = 1
    tasks: List[PlanTask]
    dependencies: List[PlanDependency] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("plan_version")
    @classmethod
    def _plan_version_supported(cls, v: int) -> int:
        if v not in SUPPORTED_PLAN_VERSIONS:
            supported = ", ".join(str(x) for x in sorted(SUPPORTED_PLAN_VERSIONS))
            raise ValueError(
                f"Unsupported plan_version {v!r}. Supported values: {supported}"
            )
        return v

    @model_validator(mode="after")
    def _operations_known(self) -> PlanEnvelope:
        for t in self.tasks:
            if t.operation not in ALL_PLANNER_OPERATIONS_SET:
                raise ValueError(
                    f"Unknown operation {t.operation!r} on task {t.id!r}. "
                    f"Allowed operations are defined in "
                    f"ai_designer.schemas.planner_plan.ALL_PLANNER_OPERATIONS "
                    f"({len(ALL_PLANNER_OPERATIONS)} ops)."
                )
        return self

    def to_task_graph_dict(self) -> Dict[str, Any]:
        """Shape expected by :meth:`PlannerAgent._build_task_graph`."""
        out: Dict[str, Any] = {
            "plan_version": self.plan_version,
            "tasks": [
                {
                    "id": t.id,
                    "operation": t.operation,
                    "description": t.description,
                    "parameters": t.parameters,
                    "status": t.status,
                }
                for t in self.tasks
            ],
            "dependencies": [
                {
                    "from_task_id": d.from_task_id,
                    "to_task_id": d.to_task_id,
                    "dependency_type": d.dependency_type,
                }
                for d in self.dependencies
            ],
        }
        return out


def _dedupe_dependencies(
    deps: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    seen: Set[Tuple[str, str, str]] = set()
    out: List[Dict[str, Any]] = []
    for d in deps:
        key = (
            d["from_task_id"],
            d["to_task_id"],
            d.get("dependency_type", "requires"),
        )
        if key not in seen:
            seen.add(key)
            out.append(
                {
                    "from_task_id": d["from_task_id"],
                    "to_task_id": d["to_task_id"],
                    "dependency_type": d.get("dependency_type", "requires"),
                }
            )
    return out


def normalize_raw_llm_plan_dict(raw: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    """Normalize LLM JSON before Pydantic validation.

    - Accepts ``steps`` as an alias for ``tasks``.
    - Maps per-task ``type`` → ``operation``.
    - Merges per-task ``depends_on`` into top-level ``dependencies``.
    - Defaults ``plan_version`` to ``1`` when missing (backward compatibility).
    """
    if not isinstance(raw, dict):
        raise TypeError(f"Planner plan must be a dict, got {type(raw).__name__}")

    data: Dict[str, Any] = dict(raw)

    if "tasks" not in data and "steps" in data:
        data["tasks"] = data["steps"]

    if "tasks" not in data:
        raise ValueError("Response missing 'tasks' (or alias 'steps') field")

    if not isinstance(data["tasks"], list):
        raise ValueError("'tasks' must be a list")

    deps: List[Dict[str, Any]] = []
    existing = data.get("dependencies")
    if existing is not None:
        if not isinstance(existing, list):
            raise ValueError("'dependencies' must be a list")
        for d in existing:
            if not isinstance(d, dict):
                continue
            fid = d.get("from_task_id")
            tid = d.get("to_task_id")
            if not fid or not tid:
                continue
            deps.append(
                {
                    "from_task_id": fid,
                    "to_task_id": tid,
                    "dependency_type": d.get("dependency_type", "requires"),
                }
            )

    norm_tasks: List[Dict[str, Any]] = []
    for item in data["tasks"]:
        if not isinstance(item, dict):
            raise ValueError("Each task must be an object")
        t = dict(item)
        if "operation" not in t and "type" in t:
            t["operation"] = t.pop("type")
        if "operation" not in t:
            raise ValueError("Each task must have 'operation' (or legacy 'type')")
        tid = t.get("id")
        if not tid:
            raise ValueError("Each task must have 'id'")
        for prereq in t.pop("depends_on", []) or []:
            if not isinstance(prereq, str):
                raise ValueError("depends_on entries must be task id strings")
            deps.append(
                {
                    "from_task_id": prereq,
                    "to_task_id": tid,
                    "dependency_type": "requires",
                }
            )
        norm_tasks.append(t)

    data["tasks"] = norm_tasks
    data["dependencies"] = _dedupe_dependencies(deps)

    if "plan_version" not in data:
        data["plan_version"] = CURRENT_PLAN_VERSION

    return data


def parse_and_validate_plan_dict(raw: Dict[str, Any]) -> PlanEnvelope:
    """Normalize then validate planner JSON."""
    normalized = normalize_raw_llm_plan_dict(raw)
    return PlanEnvelope.model_validate(normalized)

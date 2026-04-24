"""Unit tests for versioned planner JSON schema (``planner_plan``)."""

import pytest

from ai_designer.agents.prompts.system_prompts import (
    get_agent_prompt,
    get_planner_system_prompt,
)
from ai_designer.schemas.planner_plan import (
    CURRENT_PLAN_VERSION,
    UnsupportedGeneratorOperation,
    assert_generator_can_emit,
    parse_and_validate_plan_dict,
)


def test_plan_version_defaults_when_omitted() -> None:
    raw = {
        "tasks": [
            {
                "id": "t1",
                "operation": "create_box",
                "description": "Box",
                "status": "pending",
            }
        ],
        "dependencies": [],
    }
    env = parse_and_validate_plan_dict(raw)
    assert env.plan_version == CURRENT_PLAN_VERSION


def test_reject_unsupported_plan_version() -> None:
    raw = {
        "plan_version": 999,
        "tasks": [],
        "dependencies": [],
    }
    with pytest.raises(ValueError, match="Unsupported plan_version"):
        parse_and_validate_plan_dict(raw)


def test_unknown_operation_rejected() -> None:
    raw = {
        "plan_version": 1,
        "tasks": [
            {
                "id": "t1",
                "operation": "not_a_registered_op",
                "description": "Bad",
                "status": "pending",
            }
        ],
        "dependencies": [],
    }
    with pytest.raises(ValueError, match="Unknown operation"):
        parse_and_validate_plan_dict(raw)


def test_steps_alias_for_tasks() -> None:
    raw = {
        "plan_version": 1,
        "steps": [
            {
                "id": "s1",
                "operation": "pad",
                "description": "Pad base",
                "status": "pending",
            }
        ],
        "dependencies": [],
    }
    env = parse_and_validate_plan_dict(raw)
    assert len(env.tasks) == 1
    assert env.tasks[0].id == "s1"
    assert env.tasks[0].operation == "pad"


def test_type_alias_maps_to_operation() -> None:
    raw = {
        "plan_version": 1,
        "tasks": [
            {
                "id": "t1",
                "type": "pocket",
                "description": "Pocket feature",
                "status": "pending",
            }
        ],
        "dependencies": [],
    }
    env = parse_and_validate_plan_dict(raw)
    assert env.tasks[0].operation == "pocket"


def test_depends_on_merged_into_dependencies() -> None:
    raw = {
        "plan_version": 1,
        "tasks": [
            {
                "id": "t1",
                "operation": "create_body",
                "description": "Body",
                "status": "pending",
            },
            {
                "id": "t2",
                "operation": "create_sketch",
                "description": "Sketch",
                "status": "pending",
                "depends_on": ["t1"],
            },
            {
                "id": "t3",
                "operation": "add_rectangle",
                "description": "Rect",
                "status": "pending",
                "depends_on": ["t2"],
            },
            {
                "id": "t4",
                "operation": "pad",
                "description": "Pad",
                "status": "pending",
                "depends_on": ["t3"],
            },
        ],
        "dependencies": [],
    }
    env = parse_and_validate_plan_dict(raw)
    edges = {(d.from_task_id, d.to_task_id) for d in env.dependencies}
    assert ("t1", "t2") in edges
    assert ("t2", "t3") in edges
    assert ("t3", "t4") in edges


def test_explicit_dependencies_equivalent_to_depends_on() -> None:
    tasks = [
        {
            "id": "t1",
            "operation": "create_body",
            "description": "Body",
            "status": "pending",
        },
        {
            "id": "t2",
            "operation": "pad",
            "description": "Pad",
            "status": "pending",
        },
    ]
    with_depends = {
        "plan_version": 1,
        "tasks": [
            tasks[0],
            {**tasks[1], "depends_on": ["t1"]},
        ],
        "dependencies": [],
    }
    explicit = {
        "plan_version": 1,
        "tasks": [tasks[0], tasks[1]],
        "dependencies": [
            {"from_task_id": "t1", "to_task_id": "t2", "dependency_type": "requires"}
        ],
    }
    a = parse_and_validate_plan_dict(with_depends).to_task_graph_dict()
    b = parse_and_validate_plan_dict(explicit).to_task_graph_dict()
    assert a["tasks"] == b["tasks"]
    assert {(d["from_task_id"], d["to_task_id"]) for d in a["dependencies"]} == {
        (d["from_task_id"], d["to_task_id"]) for d in b["dependencies"]
    }


def test_get_agent_prompt_planner_matches_get_planner_system_prompt() -> None:
    assert get_agent_prompt("planner") == get_planner_system_prompt()


def test_partdesign_style_chain_valid() -> None:
    raw = {
        "plan_version": 1,
        "tasks": [
            {
                "id": "task_1",
                "operation": "create_body",
                "description": "PartDesign body",
                "parameters": {"name": "Body"},
                "status": "pending",
            },
            {
                "id": "task_2",
                "operation": "create_sketch",
                "description": "XY sketch",
                "parameters": {"plane": "XY"},
                "status": "pending",
            },
            {
                "id": "task_3",
                "operation": "add_rectangle",
                "description": "Footprint",
                "parameters": {"width": 100, "height": 50},
                "status": "pending",
            },
            {
                "id": "task_4",
                "operation": "pad",
                "description": "Extrude",
                "parameters": {"length": 30},
                "status": "pending",
            },
        ],
        "dependencies": [
            {"from_task_id": "task_1", "to_task_id": "task_2"},
            {"from_task_id": "task_2", "to_task_id": "task_3"},
            {"from_task_id": "task_3", "to_task_id": "task_4"},
        ],
    }
    env = parse_and_validate_plan_dict(raw)
    assert len(env.tasks) == 4
    assert {t.operation for t in env.tasks} == {
        "create_body",
        "create_sketch",
        "add_rectangle",
        "pad",
    }


def test_assert_generator_can_emit_accepts_partdesign_slice() -> None:
    for op in ("create_body", "create_sketch", "pad", "create_box"):
        assert_generator_can_emit(op)


def test_assert_generator_can_emit_rejects_planned_only() -> None:
    with pytest.raises(UnsupportedGeneratorOperation, match="planned_only"):
        assert_generator_can_emit("pocket")


def test_plan_operations_reexports_registry() -> None:
    from ai_designer.schemas import plan_operations as po
    from ai_designer.schemas import planner_plan as pp

    assert po.GENERATOR_EXECUTABLE_OPS == pp.EXECUTABLE_PLANNER_OPS
    assert po.GENERATOR_PLANNED_ONLY_OPS == pp.PLANNED_ONLY_PLANNER_OPS

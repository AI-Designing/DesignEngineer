"""
Planner ↔ generator operation vocabulary (Track 2/3).

Single source of truth is :mod:`ai_designer.schemas.planner_plan`; this module
re-exports stable names expected by remediation / agent docs.
"""

from ai_designer.schemas.planner_plan import (
    ALL_PLANNER_OPERATIONS,
    ALL_PLANNER_OPERATIONS_SET,
    EXECUTABLE_PLANNER_OPS,
    OPERATION_API_HINTS,
    PLANNED_ONLY_PLANNER_OPS,
    UnsupportedGeneratorOperation,
    assert_generator_can_emit,
    is_generator_executable,
)

# Aliases for documentation / imports
GENERATOR_EXECUTABLE_OPS = EXECUTABLE_PLANNER_OPS
GENERATOR_PLANNED_ONLY_OPS = PLANNED_ONLY_PLANNER_OPS
SUPPORTED_OPERATIONS = ALL_PLANNER_OPERATIONS_SET

__all__ = [
    "ALL_PLANNER_OPERATIONS",
    "ALL_PLANNER_OPERATIONS_SET",
    "GENERATOR_EXECUTABLE_OPS",
    "GENERATOR_PLANNED_ONLY_OPS",
    "OPERATION_API_HINTS",
    "SUPPORTED_OPERATIONS",
    "UnsupportedGeneratorOperation",
    "assert_generator_can_emit",
    "is_generator_executable",
]

"""
Prompt Engineering Library for FreeCAD AI Designer Agents

This package contains structured prompts for the multi-agent system:
- System prompts: Base instructions for each agent role
- FreeCAD reference: API documentation formatted for LLM context
- Few-shot examples: Curated input/output pairs for in-context learning
- Error correction: Prompts for handling validation failures

Version: 1.0.0
"""

from .error_correction import (
    ERROR_CORRECTION_PROMPTS,
    get_error_correction_prompt,
    get_recompute_fix_prompt,
    get_syntax_fix_prompt,
)
from .few_shot_examples import (
    COMPLEX_EXAMPLES,
    INTERMEDIATE_EXAMPLES,
    SIMPLE_EXAMPLES,
    get_examples_by_complexity,
    get_random_examples,
)
from .freecad_reference import (
    CONSTRAINT_REFERENCE,
    FREECAD_API_REFERENCE,
    PARTDESIGN_WORKFLOW,
    SKETCH_REFERENCE,
    get_api_reference_context,
)
from .system_prompts import (
    GENERATOR_SYSTEM_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    VALIDATOR_SYSTEM_PROMPT,
    get_agent_prompt,
)

__all__ = [
    # System prompts
    "PLANNER_SYSTEM_PROMPT",
    "GENERATOR_SYSTEM_PROMPT",
    "VALIDATOR_SYSTEM_PROMPT",
    "get_agent_prompt",
    # FreeCAD reference
    "FREECAD_API_REFERENCE",
    "PARTDESIGN_WORKFLOW",
    "SKETCH_REFERENCE",
    "CONSTRAINT_REFERENCE",
    "get_api_reference_context",
    # Few-shot examples
    "SIMPLE_EXAMPLES",
    "INTERMEDIATE_EXAMPLES",
    "COMPLEX_EXAMPLES",
    "get_examples_by_complexity",
    "get_random_examples",
    # Error correction
    "ERROR_CORRECTION_PROMPTS",
    "get_error_correction_prompt",
    "get_syntax_fix_prompt",
    "get_recompute_fix_prompt",
]

__version__ = "1.0.0"

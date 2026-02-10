"""Multi-agent system for AI-driven CAD design.

This package provides specialized agents that work together to decompose,
generate, and validate FreeCAD designs:

- PlannerAgent: Decomposes natural language prompts into hierarchical task graphs
- GeneratorAgent: Converts task graphs into executable FreeCAD Python scripts
- ValidatorAgent: Performs multi-faceted validation (geometric, semantic, LLM-based)

Each agent uses the UnifiedLLMProvider for LLM interactions and operates on
standardized Pydantic schemas for type safety and data validation.
"""

from ai_designer.agents.planner import PlannerAgent

__all__ = ["PlannerAgent"]

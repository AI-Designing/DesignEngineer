"""Multi-agent system for AI-driven CAD design.

This package provides specialized agents that work together to decompose,
generate, and validate FreeCAD designs:

- PlannerAgent: Decomposes natural language prompts into hierarchical task graphs
- GeneratorAgent: Converts task graphs into executable FreeCAD Python scripts
- ValidatorAgent: Performs multi-faceted validation (geometric, semantic, LLM-based)
- OrchestratorAgent: Coordinates the complete multi-agent workflow with refinement loops

Each agent uses the UnifiedLLMProvider for LLM interactions and operates on
standardized Pydantic schemas for type safety and data validation.
"""

from ai_designer.agents.base import BaseAgent
from ai_designer.agents.generator import GeneratorAgent
from ai_designer.agents.orchestrator import OrchestratorAgent
from ai_designer.agents.planner import PlannerAgent
from ai_designer.agents.validator import ValidatorAgent

__all__ = ["BaseAgent", "PlannerAgent", "GeneratorAgent", "ValidatorAgent", "OrchestratorAgent"]

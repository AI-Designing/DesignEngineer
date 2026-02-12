"""
FreeCAD Integration Module

Provides headless execution, state extraction, and multi-format export
for FreeCAD documents.

Main Components:
- HeadlessRunner: Subprocess-based FreeCAD script execution
- StateExtractor: Document state and feature tree extraction
- FreeCADPathResolver: FreeCAD installation path resolution

Usage:
    >>> from ai_designer.freecad import HeadlessRunner, StateExtractor
    >>> runner = HeadlessRunner(outputs_dir="outputs")
    >>> result = await runner.execute_script(
    ...     script="box = Part.makeBox(10, 10, 10)\\nPart.show(box)",
    ...     prompt="Create a box",
    ...     request_id="test-123"
    ... )
    >>> print(f"Created {len(result.created_objects)} objects")
"""

from .headless_runner import HeadlessRunner, get_execution_semaphore
from .path_resolver import FreeCADPathResolver
from .state_extractor import StateExtractor

__all__ = [
    "HeadlessRunner",
    "StateExtractor",
    "FreeCADPathResolver",
    "get_execution_semaphore",
]

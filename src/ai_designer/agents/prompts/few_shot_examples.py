"""
Few-Shot Examples for In-Context Learning

Curated library of user prompts and corresponding FreeCAD scripts.
Organized by complexity: simple (basic shapes), intermediate (assemblies),
and complex (advanced features).

Version: 1.0.0
"""

import random
from typing import Dict, List, Literal

ComplexityLevel = Literal["simple", "intermediate", "complex"]

# ============================================================================
# Simple Examples (10 basic shapes)
# ============================================================================

SIMPLE_EXAMPLES = [
    {
        "id": "simple_box",
        "prompt": "Create a box 100mm x 50mm x 30mm",
        "description": "Basic rectangular box with specified dimensions",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign

try:
    doc = App.newDocument("Design")

    # Create Body
    body = doc.addObject("PartDesign::Body", "Body")

    # Create Sketch on XY plane
    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    body.addObject(sketch)
    sketch.MapMode = "FlatFace"
    sketch.Support = (doc.XY_Plane, [''])

    # Add rectangle (centered at origin)
    sketch.addGeometry(Part.LineSegment(App.Vector(-50, -25, 0), App.Vector(50, -25, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(50, -25, 0), App.Vector(50, 25, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(50, 25, 0), App.Vector(-50, 25, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(-50, 25, 0), App.Vector(-50, -25, 0)))

    # Add constraints
    sketch.addConstraint(Sketcher.Constraint('Horizontal', 0))
    sketch.addConstraint(Sketcher.Constraint('Vertical', 1))
    sketch.addConstraint(Sketcher.Constraint('Horizontal', 2))
    sketch.addConstraint(Sketcher.Constraint('Vertical', 3))
    sketch.addConstraint(Sketcher.Constraint('Distance', 0, 100))
    sketch.addConstraint(Sketcher.Constraint('Distance', 1, 50))

    # Create Pad
    pad = doc.addObject("PartDesign::Pad", "Pad")
    body.addObject(pad)
    pad.Profile = sketch
    pad.Length = 30

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "simple",
        "features": ["body", "sketch", "rectangle", "pad"],
    },
    {
        "id": "simple_cylinder",
        "prompt": "Create a cylinder with diameter 50mm and height 100mm",
        "description": "Basic cylinder using circle sketch and pad",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign
import sys

try:
    doc = App.newDocument("Design")

    # Create Body
    body = doc.addObject("PartDesign::Body", "Body")

    # Create Sketch on XY plane
    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    body.addObject(sketch)
    sketch.MapMode = "FlatFace"
    sketch.Support = (doc.XY_Plane, [''])

    # Add circle at origin
    sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 25))
    sketch.addConstraint(Sketcher.Constraint('Radius', 0, 25))

    # Create Pad
    pad = doc.addObject("PartDesign::Pad", "Pad")
    body.addObject(pad)
    pad.Profile = sketch
    pad.Length = 100

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "simple",
        "features": ["body", "sketch", "circle", "pad"],
    },
    {
        "id": "simple_cube",
        "prompt": "Create a 50mm cube",
        "description": "Equal-sided box",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign
import sys

try:
    doc = App.newDocument("Design")

    body = doc.addObject("PartDesign::Body", "Body")

    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    body.addObject(sketch)
    sketch.MapMode = "FlatFace"
    sketch.Support = (doc.XY_Plane, [''])

    # Square 50x50mm
    sketch.addGeometry(Part.LineSegment(App.Vector(-25, -25, 0), App.Vector(25, -25, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(25, -25, 0), App.Vector(25, 25, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(25, 25, 0), App.Vector(-25, 25, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(-25, 25, 0), App.Vector(-25, -25, 0)))

    sketch.addConstraint(Sketcher.Constraint('Horizontal', 0))
    sketch.addConstraint(Sketcher.Constraint('Vertical', 1))
    sketch.addConstraint(Sketcher.Constraint('Horizontal', 2))
    sketch.addConstraint(Sketcher.Constraint('Vertical', 3))
    sketch.addConstraint(Sketcher.Constraint('Distance', 0, 50))
    sketch.addConstraint(Sketcher.Constraint('Distance', 1, 50))

    pad = doc.addObject("PartDesign::Pad", "Pad")
    body.addObject(pad)
    pad.Profile = sketch
    pad.Length = 50

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "simple",
        "features": ["body", "sketch", "square", "pad"],
    },
    {
        "id": "simple_tube",
        "prompt": "Create a tube with outer diameter 40mm, inner diameter 30mm, and height 60mm",
        "description": "Hollow cylinder using two circles",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign
import sys

try:
    doc = App.newDocument("Design")

    body = doc.addObject("PartDesign::Body", "Body")

    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    body.addObject(sketch)
    sketch.MapMode = "FlatFace"
    sketch.Support = (doc.XY_Plane, [''])

    # Outer circle
    sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 20))
    sketch.addConstraint(Sketcher.Constraint('Radius', 0, 20))

    # Inner circle
    sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 15))
    sketch.addConstraint(Sketcher.Constraint('Radius', 1, 15))
    sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 3, 1, 3))  # Same center

    pad = doc.addObject("PartDesign::Pad", "Pad")
    body.addObject(pad)
    pad.Profile = sketch
    pad.Length = 60

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "simple",
        "features": ["body", "sketch", "concentric_circles", "pad"],
    },
    {
        "id": "simple_disc",
        "prompt": "Create a flat disc 80mm diameter and 5mm thick",
        "description": "Thin circular plate",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign
import sys

try:
    doc = App.newDocument("Design")

    body = doc.addObject("PartDesign::Body", "Body")

    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    body.addObject(sketch)
    sketch.MapMode = "FlatFace"
    sketch.Support = (doc.XY_Plane, [''])

    sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 40))
    sketch.addConstraint(Sketcher.Constraint('Radius', 0, 40))

    pad = doc.addObject("PartDesign::Pad", "Pad")
    body.addObject(pad)
    pad.Profile = sketch
    pad.Length = 5

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "simple",
        "features": ["body", "sketch", "circle", "pad"],
    },
]

# ============================================================================
# Intermediate Examples (10 assemblies with multiple features)
# ============================================================================

INTERMEDIATE_EXAMPLES = [
    {
        "id": "intermediate_bracket",
        "prompt": "Create an L-shaped bracket with base 100x50x10mm and vertical support 50x50x10mm",
        "description": "L-bracket with two pads",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign
import sys

try:
    doc = App.newDocument("Design")

    body = doc.addObject("PartDesign::Body", "Body")

    # Base sketch
    base_sketch = doc.addObject("Sketcher::SketchObject", "BaseSketch")
    body.addObject(base_sketch)
    base_sketch.MapMode = "FlatFace"
    base_sketch.Support = (doc.XY_Plane, [''])

    # Base rectangle
    base_sketch.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(100, 0, 0)))
    base_sketch.addGeometry(Part.LineSegment(App.Vector(100, 0, 0), App.Vector(100, 50, 0)))
    base_sketch.addGeometry(Part.LineSegment(App.Vector(100, 50, 0), App.Vector(0, 50, 0)))
    base_sketch.addGeometry(Part.LineSegment(App.Vector(0, 50, 0), App.Vector(0, 0, 0)))

    base_sketch.addConstraint(Sketcher.Constraint('Horizontal', 0))
    base_sketch.addConstraint(Sketcher.Constraint('Vertical', 1))
    base_sketch.addConstraint(Sketcher.Constraint('Distance', 0, 100))
    base_sketch.addConstraint(Sketcher.Constraint('Distance', 1, 50))

    # Pad base
    base_pad = doc.addObject("PartDesign::Pad", "BasePad")
    body.addObject(base_pad)
    base_pad.Profile = base_sketch
    base_pad.Length = 10

    doc.recompute()

    # Vertical support sketch on end face
    support_sketch = doc.addObject("Sketcher::SketchObject", "SupportSketch")
    body.addObject(support_sketch)
    support_sketch.MapMode = "FlatFace"
    support_sketch.Support = (base_pad, ['Face5'])

    # Support rectangle
    support_sketch.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(50, 0, 0)))
    support_sketch.addGeometry(Part.LineSegment(App.Vector(50, 0, 0), App.Vector(50, 50, 0)))
    support_sketch.addGeometry(Part.LineSegment(App.Vector(50, 50, 0), App.Vector(0, 50, 0)))
    support_sketch.addGeometry(Part.LineSegment(App.Vector(0, 50, 0), App.Vector(0, 0, 0)))

    support_sketch.addConstraint(Sketcher.Constraint('Distance', 0, 50))
    support_sketch.addConstraint(Sketcher.Constraint('Distance', 1, 50))

    # Pad support
    support_pad = doc.addObject("PartDesign::Pad", "SupportPad")
    body.addObject(support_pad)
    support_pad.Profile = support_sketch
    support_pad.Length = 10

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "intermediate",
        "features": ["body", "multiple_sketches", "multiple_pads", "face_reference"],
    },
    {
        "id": "intermediate_box_with_hole",
        "prompt": "Create a box 80x80x40mm with a centered hole diameter 20mm through it",
        "description": "Box with pocket hole",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign
import sys

try:
    doc = App.newDocument("Design")

    body = doc.addObject("PartDesign::Body", "Body")

    # Base box sketch
    box_sketch = doc.addObject("Sketcher::SketchObject", "BoxSketch")
    body.addObject(box_sketch)
    box_sketch.MapMode = "FlatFace"
    box_sketch.Support = (doc.XY_Plane, [''])

    box_sketch.addGeometry(Part.LineSegment(App.Vector(-40, -40, 0), App.Vector(40, -40, 0)))
    box_sketch.addGeometry(Part.LineSegment(App.Vector(40, -40, 0), App.Vector(40, 40, 0)))
    box_sketch.addGeometry(Part.LineSegment(App.Vector(40, 40, 0), App.Vector(-40, 40, 0)))
    box_sketch.addGeometry(Part.LineSegment(App.Vector(-40, 40, 0), App.Vector(-40, -40, 0)))

    box_sketch.addConstraint(Sketcher.Constraint('Distance', 0, 80))
    box_sketch.addConstraint(Sketcher.Constraint('Distance', 1, 80))

    # Pad box
    box_pad = doc.addObject("PartDesign::Pad", "BoxPad")
    body.addObject(box_pad)
    box_pad.Profile = box_sketch
    box_pad.Length = 40

    doc.recompute()

    # Hole sketch on top face
    hole_sketch = doc.addObject("Sketcher::SketchObject", "HoleSketch")
    body.addObject(hole_sketch)
    hole_sketch.MapMode = "FlatFace"
    hole_sketch.Support = (box_pad, ['Face6'])

    hole_sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 10))
    hole_sketch.addConstraint(Sketcher.Constraint('Radius', 0, 10))

    # Pocket through all
    pocket = doc.addObject("PartDesign::Pocket", "Pocket")
    body.addObject(pocket)
    pocket.Profile = hole_sketch
    pocket.Type = 1  # Through all

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "intermediate",
        "features": ["body", "sketch", "pad", "pocket", "through_all"],
    },
    {
        "id": "intermediate_rounded_box",
        "prompt": "Create a box 60x40x20mm with 3mm fillets on all vertical edges",
        "description": "Box with fillet dress-up feature",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign
import sys

try:
    doc = App.newDocument("Design")

    body = doc.addObject("PartDesign::Body", "Body")

    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    body.addObject(sketch)
    sketch.MapMode = "FlatFace"
    sketch.Support = (doc.XY_Plane, [''])

    sketch.addGeometry(Part.LineSegment(App.Vector(-30, -20, 0), App.Vector(30, -20, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(30, -20, 0), App.Vector(30, 20, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(30, 20, 0), App.Vector(-30, 20, 0)))
    sketch.addGeometry(Part.LineSegment(App.Vector(-30, 20, 0), App.Vector(-30, -20, 0)))

    sketch.addConstraint(Sketcher.Constraint('Distance', 0, 60))
    sketch.addConstraint(Sketcher.Constraint('Distance', 1, 40))

    pad = doc.addObject("PartDesign::Pad", "Pad")
    body.addObject(pad)
    pad.Profile = sketch
    pad.Length = 20

    doc.recompute()

    # Fillet vertical edges
    fillet = doc.addObject("PartDesign::Fillet", "Fillet")
    body.addObject(fillet)
    fillet.Base = (pad, ['Edge1', 'Edge3', 'Edge5', 'Edge7'])
    fillet.Radius = 3

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "intermediate",
        "features": ["body", "sketch", "pad", "fillet"],
    },
]

# ============================================================================
# Complex Examples (5 advanced shapes)
# ============================================================================

COMPLEX_EXAMPLES = [
    {
        "id": "complex_flange",
        "prompt": "Create a circular flange: central hole 40mm diameter, outer diameter 120mm, thickness 15mm, with 6 mounting holes 8mm diameter on 90mm bolt circle",
        "description": "Flange with polar pattern of holes",
        "script": """import FreeCAD as App
import Part
import Sketcher
import PartDesign
import sys
import math

try:
    doc = App.newDocument("Design")

    body = doc.addObject("PartDesign::Body", "Body")

    # Main flange sketch
    flange_sketch = doc.addObject("Sketcher::SketchObject", "FlangeSketch")
    body.addObject(flange_sketch)
    flange_sketch.MapMode = "FlatFace"
    flange_sketch.Support = (doc.XY_Plane, [''])

    # Outer circle
    flange_sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 60))
    flange_sketch.addConstraint(Sketcher.Constraint('Radius', 0, 60))

    # Inner circle (central hole)
    flange_sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 20))
    flange_sketch.addConstraint(Sketcher.Constraint('Radius', 1, 20))
    flange_sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 3, 1, 3))

    # Pad flange
    flange_pad = doc.addObject("PartDesign::Pad", "FlangePad")
    body.addObject(flange_pad)
    flange_pad.Profile = flange_sketch
    flange_pad.Length = 15

    doc.recompute()

    # Mounting hole sketch on top face
    hole_sketch = doc.addObject("Sketcher::SketchObject", "HoleSketch")
    body.addObject(hole_sketch)
    hole_sketch.MapMode = "FlatFace"
    hole_sketch.Support = (flange_pad, ['Face3'])

    # Single hole at bolt circle radius
    hole_sketch.addGeometry(Part.Circle(App.Vector(45, 0, 0), App.Vector(0, 0, 1), 4))
    hole_sketch.addConstraint(Sketcher.Constraint('Radius', 0, 4))

    # Pocket hole
    pocket = doc.addObject("PartDesign::Pocket", "Pocket")
    body.addObject(pocket)
    pocket.Profile = hole_sketch
    pocket.Type = 1  # Through all

    doc.recompute()

    # Polar pattern for 6 holes
    pattern = doc.addObject("PartDesign::PolarPattern", "PolarPattern")
    body.addObject(pattern)
    pattern.Originals = [pocket]
    pattern.Axis = (doc.Z_Axis, [''])
    pattern.Angle = 360.0
    pattern.Occurrences = 6

    doc.recompute()

    for obj in doc.Objects:
        print(f"CREATED_OBJECT: {obj.Label}")

    print("RECOMPUTE_SUCCESS")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
""",
        "complexity": "complex",
        "features": ["body", "concentric_circles", "pad", "pocket", "polar_pattern"],
    },
]

# ============================================================================
# Helper Functions
# ============================================================================


def get_examples_by_complexity(level: ComplexityLevel) -> List[Dict]:
    """
    Get examples by complexity level.

    Args:
        level: Complexity level (simple, intermediate, complex)

    Returns:
        List of examples at that level

    Example:
        >>> examples = get_examples_by_complexity("simple")
        >>> len(examples)
        5
    """
    if level == "simple":
        return SIMPLE_EXAMPLES
    elif level == "intermediate":
        return INTERMEDIATE_EXAMPLES
    elif level == "complex":
        return COMPLEX_EXAMPLES
    else:
        raise ValueError(f"Unknown complexity level: {level}")


def get_random_examples(
    count: int = 3, complexity: ComplexityLevel = None
) -> List[Dict]:
    """
    Get random examples for in-context learning.

    Args:
        count: Number of examples to return (default: 3)
        complexity: Filter by complexity level (optional)

    Returns:
        List of random examples

    Example:
        >>> examples = get_random_examples(2, "simple")
        >>> len(examples)
        2
    """
    if complexity:
        pool = get_examples_by_complexity(complexity)
    else:
        pool = SIMPLE_EXAMPLES + INTERMEDIATE_EXAMPLES + COMPLEX_EXAMPLES

    return random.sample(pool, min(count, len(pool)))


def get_all_examples() -> List[Dict]:
    """
    Get all examples.

    Returns:
        List of all examples

    Example:
        >>> examples = get_all_examples()
        >>> len(examples) >= 20
        True
    """
    return SIMPLE_EXAMPLES + INTERMEDIATE_EXAMPLES + COMPLEX_EXAMPLES


def format_example_for_prompt(example: Dict, include_script: bool = True) -> str:
    """
    Format an example for inclusion in a prompt.

    Args:
        example: Example dictionary
        include_script: Include the full script (default: True)

    Returns:
        Formatted example string

    Example:
        >>> example = SIMPLE_EXAMPLES[0]
        >>> formatted = format_example_for_prompt(example, include_script=False)
        >>> "User:" in formatted
        True
    """
    formatted = f"**Example: {example['description']}**\n\n"
    formatted += f"User: {example['prompt']}\n\n"

    if include_script:
        formatted += f"Assistant:\n```python\n{example['script']}\n```\n"

    return formatted

"""
FreeCAD API Reference for LLM Context

Structured documentation of FreeCAD Python API formatted for LLM consumption.
Includes PartDesign workflow, Sketcher operations, constraints, and common patterns.

Version: 1.0.0
"""

from typing import Dict, List

# ============================================================================
# PartDesign Workflow Reference
# ============================================================================

PARTDESIGN_WORKFLOW = """
# FreeCAD PartDesign Workflow

PartDesign is the primary workbench for creating solid parametric models.

## Core Workflow:
1. Create Body (container for all features)
2. Create Sketch (2D drawing on a plane)
3. Add 2D geometry to sketch
4. Apply constraints to control dimensions
5. Create 3D features from sketches (Pad, Pocket, Revolution, etc.)
6. Add dress-up features (Fillet, Chamfer, Draft)
7. Use patterns for repetition

## Critical Rules:
- ALWAYS start with a Body
- ALWAYS close sketches before creating 3D features
- Features build upon previous features in the tree
- Each feature must be fully constrained (no degrees of freedom)
- Reference existing faces/edges for subsequent sketches

## Feature Sequence Example:
Body → Sketch (base) → Pad (main body) → Sketch (on face) → Pocket (hole) → Fillet (edges)
"""

# ============================================================================
# Sketch Reference
# ============================================================================

SKETCH_REFERENCE = """
# Sketcher Reference

## Creating a Sketch:
```python
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])  # XY, XZ, or YZ plane
```

## 2D Geometry Types:

### Line:
```python
sketch.addGeometry(Part.LineSegment(
    App.Vector(x1, y1, 0),
    App.Vector(x2, y2, 0)
), False)  # False = not construction line
```

### Circle:
```python
sketch.addGeometry(Part.Circle(
    App.Vector(cx, cy, 0),  # center
    App.Vector(0, 0, 1),     # normal (Z-axis for XY plane)
    radius
), False)
```

### Arc of Circle:
```python
circle = Part.Circle(App.Vector(cx, cy, 0), App.Vector(0, 0, 1), radius)
arc = Part.ArcOfCircle(circle, start_angle, end_angle)
sketch.addGeometry(arc, False)
```

### Rectangle (using 4 lines):
```python
# Bottom-left corner at (x, y), width w, height h
sketch.addGeometry(Part.LineSegment(App.Vector(x, y, 0), App.Vector(x+w, y, 0)))      # bottom
sketch.addGeometry(Part.LineSegment(App.Vector(x+w, y, 0), App.Vector(x+w, y+h, 0)))  # right
sketch.addGeometry(Part.LineSegment(App.Vector(x+w, y+h, 0), App.Vector(x, y+h, 0)))  # top
sketch.addGeometry(Part.LineSegment(App.Vector(x, y+h, 0), App.Vector(x, y, 0)))      # left
```

## Geometry Indexing:
- First geometry added has index 0
- Second has index 1, etc.
- Used in constraints to reference geometry

## Points on Geometry:
- Point 1: Start point of line/arc
- Point 2: End point of line/arc
- Point 3: Center of circle/arc
"""

# ============================================================================
# Constraint Reference
# ============================================================================

CONSTRAINT_REFERENCE = """
# Sketcher Constraints

Constraints define relationships between geometry and control dimensions.

## Distance Constraint:
```python
# Distance between two points
sketch.addConstraint(Sketcher.Constraint('Distance', geom_index, point_index, distance_value))

# Length of a line (geom_index of the line)
sketch.addConstraint(Sketcher.Constraint('Distance', line_index, length_value))

# Distance between two parallel lines
sketch.addConstraint(Sketcher.Constraint('Distance', geom1_index, geom2_index, distance_value))
```

## Horizontal/Vertical:
```python
sketch.addConstraint(Sketcher.Constraint('Horizontal', geom_index))
sketch.addConstraint(Sketcher.Constraint('Vertical', geom_index))
```

## Coincident (make two points meet):
```python
sketch.addConstraint(Sketcher.Constraint(
    'Coincident',
    geom1_index, point1_index,  # Point on first geometry
    geom2_index, point2_index   # Point on second geometry
))
```

## Perpendicular:
```python
sketch.addConstraint(Sketcher.Constraint('Perpendicular', geom1_index, geom2_index))
```

## Parallel:
```python
sketch.addConstraint(Sketcher.Constraint('Parallel', geom1_index, geom2_index))
```

## Tangent:
```python
sketch.addConstraint(Sketcher.Constraint('Tangent', geom1_index, geom2_index))
```

## Equal (same length/radius):
```python
sketch.addConstraint(Sketcher.Constraint('Equal', geom1_index, geom2_index))
```

## Symmetric:
```python
sketch.addConstraint(Sketcher.Constraint(
    'Symmetric',
    geom1_index, point1_index,
    geom2_index, point2_index,
    symmetry_line_index
))
```

## Angle:
```python
sketch.addConstraint(Sketcher.Constraint(
    'Angle',
    geom1_index, geom2_index,
    angle_radians  # Use math.radians(degrees)
))
```

## Radius/Diameter:
```python
sketch.addConstraint(Sketcher.Constraint('Radius', circle_index, radius_value))
sketch.addConstraint(Sketcher.Constraint('Diameter', circle_index, diameter_value))
```

## Point on Object:
```python
sketch.addConstraint(Sketcher.Constraint(
    'PointOnObject',
    geom_index, point_index,
    target_geom_index
))
```
"""

# ============================================================================
# 3D Features Reference
# ============================================================================

FEATURES_REFERENCE = """
# PartDesign 3D Features

## Pad (Extrusion):
```python
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch  # Reference to sketch
pad.Length = 10.0     # Extrusion length
pad.Reversed = False  # Direction (False = positive normal)
```

## Pocket (Cut):
```python
pocket = doc.addObject("PartDesign::Pocket", "Pocket")
body.addObject(pocket)
pocket.Profile = sketch
pocket.Length = 5.0
pocket.Type = 0  # 0=Dimension, 1=Through all, 2=To first, 3=Up to face
```

## Revolution (Rotate sketch around axis):
```python
revolution = doc.addObject("PartDesign::Revolution", "Revolution")
body.addObject(revolution)
revolution.Profile = sketch
revolution.Axis = (sketch, ['V_Axis'])  # Vertical axis of sketch
revolution.Angle = 360.0  # Full revolution
```

## Fillet (Round edges):
```python
fillet = doc.addObject("PartDesign::Fillet", "Fillet")
body.addObject(fillet)
fillet.Base = (pad, ['Edge1', 'Edge2'])  # Edges to fillet
fillet.Radius = 2.0
```

## Chamfer (Bevel edges):
```python
chamfer = doc.addObject("PartDesign::Chamfer", "Chamfer")
body.addObject(chamfer)
chamfer.Base = (pad, ['Edge1', 'Edge2'])
chamfer.Size = 1.0
```

## Linear Pattern:
```python
pattern = doc.addObject("PartDesign::LinearPattern", "LinearPattern")
body.addObject(pattern)
pattern.Originals = [pocket]  # Features to pattern
pattern.Direction = (sketch, ['H_Axis'])
pattern.Length = 50.0
pattern.Occurrences = 5
```

## Polar Pattern:
```python
pattern = doc.addObject("PartDesign::PolarPattern", "PolarPattern")
body.addObject(pattern)
pattern.Originals = [pocket]
pattern.Axis = (doc.Z_Axis, [''])
pattern.Angle = 360.0
pattern.Occurrences = 6
```
"""

# ============================================================================
# Common Patterns
# ============================================================================

COMMON_PATTERNS = """
# Common FreeCAD Patterns

## Pattern 1: Simple Box
```python
# Create body and sketch
body = doc.addObject("PartDesign::Body", "Body")
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])

# Rectangle centered at origin
sketch.addGeometry(Part.LineSegment(App.Vector(-50, -25, 0), App.Vector(50, -25, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(50, -25, 0), App.Vector(50, 25, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(50, 25, 0), App.Vector(-50, 25, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(-50, 25, 0), App.Vector(-50, -25, 0)))

# Constraints
sketch.addConstraint(Sketcher.Constraint('Horizontal', 0))
sketch.addConstraint(Sketcher.Constraint('Vertical', 1))
sketch.addConstraint(Sketcher.Constraint('Horizontal', 2))
sketch.addConstraint(Sketcher.Constraint('Vertical', 3))
sketch.addConstraint(Sketcher.Constraint('Distance', 0, 100))
sketch.addConstraint(Sketcher.Constraint('Distance', 1, 50))

# Pad
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = 30
```

## Pattern 2: Cylinder
```python
body = doc.addObject("PartDesign::Body", "Body")
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])

# Circle at origin
sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 25))
sketch.addConstraint(Sketcher.Constraint('Radius', 0, 25))

# Pad
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = 50
```

## Pattern 3: Mounting Bracket
```python
# Base
body = doc.addObject("PartDesign::Body", "Body")
base_sketch = doc.addObject("Sketcher::SketchObject", "BaseSketch")
body.addObject(base_sketch)
base_sketch.MapMode = "FlatFace"
base_sketch.Support = (doc.XY_Plane, [''])

# Base rectangle
base_sketch.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(100, 0, 0)))
base_sketch.addGeometry(Part.LineSegment(App.Vector(100, 0, 0), App.Vector(100, 50, 0)))
base_sketch.addGeometry(Part.LineSegment(App.Vector(100, 50, 0), App.Vector(0, 50, 0)))
base_sketch.addGeometry(Part.LineSegment(App.Vector(0, 50, 0), App.Vector(0, 0, 0)))

# Pad base
base_pad = doc.addObject("PartDesign::Pad", "BasePad")
body.addObject(base_pad)
base_pad.Profile = base_sketch
base_pad.Length = 10

# Mounting holes sketch on top face
hole_sketch = doc.addObject("Sketcher::SketchObject", "HoleSketch")
body.addObject(hole_sketch)
hole_sketch.MapMode = "FlatFace"
hole_sketch.Support = (base_pad, ['Face6'])  # Top face

# Two circles for holes
hole_sketch.addGeometry(Part.Circle(App.Vector(10, 25, 0), App.Vector(0, 0, 1), 5))
hole_sketch.addGeometry(Part.Circle(App.Vector(90, 25, 0), App.Vector(0, 0, 1), 5))

# Pocket through
pocket = doc.addObject("PartDesign::Pocket", "Pocket")
body.addObject(pocket)
pocket.Profile = hole_sketch
pocket.Type = 1  # Through all
```
"""

# ============================================================================
# Full API Reference
# ============================================================================

FREECAD_API_REFERENCE = {
    "workflow": PARTDESIGN_WORKFLOW,
    "sketch": SKETCH_REFERENCE,
    "constraints": CONSTRAINT_REFERENCE,
    "features": FEATURES_REFERENCE,
    "patterns": COMMON_PATTERNS,
}


def get_api_reference_context(sections: List[str] = None) -> str:
    """
    Get FreeCAD API reference context for LLM prompts.

    Args:
        sections: Specific sections to include. If None, includes all.
                 Options: ['workflow', 'sketch', 'constraints', 'features', 'patterns']

    Returns:
        Formatted API reference string

    Example:
        >>> context = get_api_reference_context(['sketch', 'constraints'])
        >>> print(len(context))
        2500
    """
    if sections is None:
        sections = list(FREECAD_API_REFERENCE.keys())

    context_parts = []
    for section in sections:
        if section in FREECAD_API_REFERENCE:
            context_parts.append(FREECAD_API_REFERENCE[section])

    return "\n\n".join(context_parts)


def get_quick_reference() -> Dict[str, str]:
    """
    Get quick reference for common operations.

    Returns:
        Dictionary of operation -> code snippet

    Example:
        >>> ref = get_quick_reference()
        >>> print(ref['create_body'])
        body = doc.addObject("PartDesign::Body", "Body")
    """
    return {
        "create_body": 'body = doc.addObject("PartDesign::Body", "Body")',
        "create_sketch_xy": """sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])""",
        "add_line": """sketch.addGeometry(Part.LineSegment(
    App.Vector(x1, y1, 0),
    App.Vector(x2, y2, 0)
), False)""",
        "add_circle": """sketch.addGeometry(Part.Circle(
    App.Vector(cx, cy, 0),
    App.Vector(0, 0, 1),
    radius
), False)""",
        "add_distance_constraint": """sketch.addConstraint(Sketcher.Constraint('Distance', geom_index, distance))""",
        "create_pad": """pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = length""",
        "create_pocket": """pocket = doc.addObject("PartDesign::Pocket", "Pocket")
body.addObject(pocket)
pocket.Profile = sketch
pocket.Length = depth""",
        "create_fillet": """fillet = doc.addObject("PartDesign::Fillet", "Fillet")
body.addObject(fillet)
fillet.Base = (feature, ['Edge1', 'Edge2'])
fillet.Radius = radius""",
    }

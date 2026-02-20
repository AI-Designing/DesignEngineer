"""
freecad/geometry_helpers.py
============================
Pure geometry-parsing helpers extracted from StateAwareCommandProcessor.

These functions accept strings/dicts and return dicts. They do NOT call any
FreeCAD API directly (API calls still live in the methods that use these).
"""

import re
from typing import Any, Dict


def analyze_geometry_requirements(nl_command: str) -> Dict[str, Any]:
    """Extract geometry requirements from a natural-language FreeCAD command.

    Extracted from ``StateAwareCommandProcessor._analyze_geometry_requirements``.

    Args:
        nl_command: E.g. ``"Create a 50mm diameter cylinder that is 100mm tall"``

    Returns:
        Dict with keys: ``shape``, ``operation``, ``plane``, ``dimensions``.
    """
    geometry: Dict[str, Any] = {
        "shape": "unknown",
        "operation": "pad",
        "plane": "XY",
        "dimensions": {},
    }

    nl_lower = nl_command.lower()

    # Identify shape type
    if "cylinder" in nl_lower:
        geometry["shape"] = "circle"
        geometry["operation"] = "pad"
    elif "box" in nl_lower or "cube" in nl_lower:
        geometry["shape"] = "rectangle"
        geometry["operation"] = "pad"
    elif "hole" in nl_lower:
        geometry["shape"] = "circle"
        geometry["operation"] = "pocket"

    # Extract explicit diameter
    diameter_match = re.search(r"(\d+(?:\.\d+)?)\s*mm\s+diameter", nl_command)
    if diameter_match:
        d = float(diameter_match.group(1))
        geometry["dimensions"]["diameter"] = d
        geometry["dimensions"]["radius"] = d / 2

    # Extract explicit height
    height_match = re.search(
        r"(\d+(?:\.\d+)?)\s*mm\s+(?:tall|high|height)", nl_command
    )
    if height_match:
        geometry["dimensions"]["height"] = float(height_match.group(1))

    # Fallback: extract any bare mm values
    if not geometry["dimensions"]:
        all_dims = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*mm", nl_command)]
        if len(all_dims) >= 2:
            if geometry["shape"] == "circle":
                geometry["dimensions"]["radius"] = all_dims[0] / 2
                geometry["dimensions"]["height"] = all_dims[1]
            else:
                geometry["dimensions"]["width"] = all_dims[0]
                geometry["dimensions"]["height"] = all_dims[1]

    return geometry


def build_circle_sketch_script(dimensions: Dict[str, float], plane: str = "XY") -> str:
    """Return a FreeCAD Python script string that creates a circle sketch.

    Extracted from ``StateAwareCommandProcessor._create_circle_sketch``.

    Args:
        dimensions: Must contain ``radius`` (float, mm).
        plane: Sketch plane name, default ``"XY"``.

    Returns:
        Multi-line Python script string ready to pass to ``api_client.execute_command``.
    """
    radius = dimensions.get("radius", 25.0)
    return f"""
import FreeCAD
import Part
import Sketcher

doc = FreeCAD.ActiveDocument

# Get active body
activeBody = None
for obj in doc.Objects:
    if hasattr(obj, 'TypeId') and obj.TypeId == 'PartDesign::Body':
        activeBody = obj
        break

if not activeBody:
    raise Exception("No active PartDesign Body found")

# Create sketch on {plane} plane
sketch = activeBody.newObject('Sketcher::SketchObject', 'Sketch')
sketch.Support = (doc.getObject('{plane}_Plane'),[''])
sketch.MapMode = 'FlatFace'

# Add circle at origin
circle = sketch.addGeometry(Part.Circle(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), {radius}), False)
sketch.addConstraint(Sketcher.Constraint('Radius', circle, {radius}))
sketch.addConstraint(Sketcher.Constraint('Coincident', circle, 3, -1, 1))

doc.recompute()
print(f"SUCCESS: Circle sketch created with radius {radius}mm")
"""


def build_rectangle_sketch_script(
    dimensions: Dict[str, float], plane: str = "XY"
) -> str:
    """Return a FreeCAD Python script string that creates a rectangle sketch.

    Extracted from ``StateAwareCommandProcessor._create_rectangle_sketch``.

    Args:
        dimensions: Must contain ``width`` and ``height`` (float, mm).
        plane: Sketch plane name, default ``"XY"``.

    Returns:
        Multi-line Python script string.
    """
    width = dimensions.get("width", 20.0)
    height = dimensions.get("height", 20.0)
    x1, y1 = -width / 2, -height / 2
    x2, y2 = width / 2, height / 2

    return f"""
import FreeCAD
import Part
import Sketcher

doc = FreeCAD.ActiveDocument

# Get active body
activeBody = None
for obj in doc.Objects:
    if hasattr(obj, 'TypeId') and obj.TypeId == 'PartDesign::Body':
        activeBody = obj
        break

if not activeBody:
    raise Exception("No active PartDesign Body found")

# Create sketch on {plane} plane
sketch = activeBody.newObject('Sketcher::SketchObject', 'Sketch')
sketch.Support = (doc.getObject('{plane}_Plane'),[''])
sketch.MapMode = 'FlatFace'

# Add rectangle centered at origin
x1, y1 = {x1}, {y1}
x2, y2 = {x2}, {y2}
line1 = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x1, y1, 0), FreeCAD.Vector(x2, y1, 0)), False)
line2 = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x2, y1, 0), FreeCAD.Vector(x2, y2, 0)), False)
line3 = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x2, y2, 0), FreeCAD.Vector(x1, y2, 0)), False)
line4 = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x1, y2, 0), FreeCAD.Vector(x1, y1, 0)), False)

# Constraints
sketch.addConstraint(Sketcher.Constraint('Coincident', line1, 2, line2, 1))
sketch.addConstraint(Sketcher.Constraint('Coincident', line2, 2, line3, 1))
sketch.addConstraint(Sketcher.Constraint('Coincident', line3, 2, line4, 1))
sketch.addConstraint(Sketcher.Constraint('Coincident', line4, 2, line1, 1))
sketch.addConstraint(Sketcher.Constraint('DistanceX', line1, {width}))
sketch.addConstraint(Sketcher.Constraint('DistanceY', line2, {height}))
sketch.addConstraint(Sketcher.Constraint('Symmetric', line1, 1, line1, 2, -1, 1))
sketch.addConstraint(Sketcher.Constraint('Symmetric', line2, 1, line2, 2, -1, 2))

doc.recompute()
print(f"SUCCESS: Rectangle sketch created {width}x{height}mm")
"""

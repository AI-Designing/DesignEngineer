"""
Sample FreeCAD scripts for testing.

These are known-good scripts that can be used as test fixtures.
"""

# Box script
BOX_SCRIPT = """import FreeCAD as App
import Part
import PartDesign

# Create document
doc = App.newDocument("Box")

# Create body
body = doc.addObject("PartDesign::Body", "Body")

# Create sketch on XY plane
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])

# Add rectangle geometry (10x10mm)
sketch.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(10, 0, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(10, 0, 0), App.Vector(10, 10, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(10, 10, 0), App.Vector(0, 10, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(0, 10, 0), App.Vector(0, 0, 0)))

# Create pad (extrude 10mm)
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = 10

doc.recompute()
print("CREATED_OBJECT: Body")
print("CREATED_OBJECT: Sketch")
print("CREATED_OBJECT: Pad")
"""

# Cylinder script
CYLINDER_SCRIPT = """import FreeCAD as App
import Part
import PartDesign

# Create document
doc = App.newDocument("Cylinder")

# Create body
body = doc.addObject("PartDesign::Body", "Body")

# Create sketch
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])

# Add circle (radius 10mm)
circle = Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 10)
sketch.addGeometry(circle)

# Create pad (height 20mm)
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = 20

doc.recompute()
print("CREATED_OBJECT: Body")
print("CREATED_OBJECT: Sketch")
print("CREATED_OBJECT: Pad")
"""

# L-Bracket script
L_BRACKET_SCRIPT = """import FreeCAD as App
import Part
import PartDesign

# Create document
doc = App.newDocument("LBracket")

# Create body
body = doc.addObject("PartDesign::Body", "Body")

# Create base sketch
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])

# L-shape profile
sketch.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(50, 0, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(50, 0, 0), App.Vector(50, 10, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(50, 10, 0), App.Vector(10, 10, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(10, 10, 0), App.Vector(10, 50, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(10, 50, 0), App.Vector(0, 50, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(0, 50, 0), App.Vector(0, 0, 0)))

# Pad to 10mm thickness
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = 10

doc.recompute()
print("CREATED_OBJECT: Body")
print("CREATED_OBJECT: Sketch")
print("CREATED_OBJECT: Pad")
"""

# Box with hole
BOX_WITH_HOLE_SCRIPT = """import FreeCAD as App
import Part
import PartDesign

# Create document
doc = App.newDocument("BoxWithHole")

# Create body
body = doc.addObject("PartDesign::Body", "Body")

# Base box sketch
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
body.addObject(sketch)
sketch.MapMode = "FlatFace"
sketch.Support = (doc.XY_Plane, [''])

# Rectangle 30x30mm
sketch.addGeometry(Part.LineSegment(App.Vector(-15, -15, 0), App.Vector(15, -15, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(15, -15, 0), App.Vector(15, 15, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(15, 15, 0), App.Vector(-15, 15, 0)))
sketch.addGeometry(Part.LineSegment(App.Vector(-15, 15, 0), App.Vector(-15, -15, 0)))

# Pad base
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = sketch
pad.Length = 20

doc.recompute()

# Hole sketch on top face
hole_sketch = doc.addObject("Sketcher::SketchObject", "HoleSketch")
body.addObject(hole_sketch)
hole_sketch.Support = (pad, ['Face6'])
hole_sketch.MapMode = "FlatFace"

# Circle for hole (radius 5mm)
circle = Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 5)
hole_sketch.addGeometry(circle)

# Pocket through all
pocket = doc.addObject("PartDesign::Pocket", "Pocket")
body.addObject(pocket)
pocket.Profile = hole_sketch
pocket.Type = 1  # Through all

doc.recompute()
print("CREATED_OBJECT: Body")
print("CREATED_OBJECT: Sketch")
print("CREATED_OBJECT: Pad")
print("CREATED_OBJECT: HoleSketch")
print("CREATED_OBJECT: Pocket")
"""

# Invalid script (syntax error)
INVALID_SYNTAX_SCRIPT = """import FreeCAD as App
import Part

doc = App.newDocument("Invalid"
box = Part.makeBox(10, 10, 10)
"""

# Incomplete script (missing recompute)
INCOMPLETE_SCRIPT = """import FreeCAD as App
import Part

doc = App.newDocument("Incomplete")
box = Part.makeBox(10, 10, 10)
Part.show(box)
# Missing doc.recompute()
"""

# Script collection
SCRIPTS = {
    "box": BOX_SCRIPT,
    "cylinder": CYLINDER_SCRIPT,
    "l_bracket": L_BRACKET_SCRIPT,
    "box_with_hole": BOX_WITH_HOLE_SCRIPT,
    "invalid_syntax": INVALID_SYNTAX_SCRIPT,
    "incomplete": INCOMPLETE_SCRIPT,
}


def get_script(name: str) -> str:
    """Get a sample script by name."""
    return SCRIPTS.get(name, BOX_SCRIPT)


def get_all_valid_scripts() -> dict:
    """Get all valid scripts."""
    return {
        k: v for k, v in SCRIPTS.items() if k not in ["invalid_syntax", "incomplete"]
    }

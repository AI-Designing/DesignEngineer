"""
FreeCAD 1.x–friendly scripts for subprocess benchmarks.

Fragments assume ``doc`` already exists (see HeadlessRunner template). They must
not call ``App.newDocument`` — the runner opens the document before the fragment.
"""

# 10 mm cube solid
SOLID_BOX_10MM = """
import Part
feat = doc.addObject("Part::Feature", "BoxSolid")
feat.Shape = Part.makeBox(10, 10, 10)
"""

# Cylinder r=10, h=20 on Z
SOLID_CYLINDER_PAD = """
import Part
import FreeCAD as App
feat = doc.addObject("Part::Feature", "CylinderSolid")
feat.Shape = Part.makeCylinder(10, 20, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
"""

# L-shaped volume from two fused boxes (no Sketcher / Support API)
SOLID_L_BRACKET_PROXY = """
import Part
import FreeCAD as App
a = Part.makeBox(50, 10, 10)
b = Part.makeBox(10, 50, 10)
b.translate(App.Vector(40, 0, 0))
shape = a.fuse(b)
feat = doc.addObject("Part::Feature", "LBracketProxy")
feat.Shape = shape
"""

# 30x30x20 block with through-hole (Part boolean — non-trivial golden)
SOLID_BLOCK_WITH_THROUGH_HOLE = """
import Part
import FreeCAD as App
base = Part.makeBox(30, 30, 20)
hole = Part.makeCylinder(5, 40, App.Vector(15, 15, -5), App.Vector(0, 0, 1))
shape = base.cut(hole)
feat = doc.addObject("Part::Feature", "BlockWithHole")
feat.Shape = shape
"""

SCRIPTS = {
    "solid_box_10mm": SOLID_BOX_10MM,
    "solid_cylinder_pad": SOLID_CYLINDER_PAD,
    "solid_l_bracket_proxy": SOLID_L_BRACKET_PROXY,
    "solid_block_with_through_hole": SOLID_BLOCK_WITH_THROUGH_HOLE,
}


def get_script(name: str) -> str:
    return SCRIPTS.get(name, SOLID_BOX_10MM)

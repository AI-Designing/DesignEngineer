import FreeCAD
import Part
import Mesh

# Create a new document
doc = FreeCAD.newDocument("Unnamed")

# Create a cylinder
cylinder = Part.makeCylinder(5, 10)  # Radius 5, height 10
cylinder_obj = doc.addObject("Part::Feature", "Cylinder")
cylinder_obj.Shape = cylinder

# Make sure the object is visible (only works in GUI mode)
if hasattr(cylinder_obj, "ViewObject") and cylinder_obj.ViewObject is not None:
    cylinder_obj.ViewObject.Visibility = True

# Recompute to update the document
doc.recompute()

# Export as STL
Mesh.export([cylinder_obj], "/home/vansh5632/DesignEng/freecad-llm-automation/output.stl")

# Save the FreeCAD document so you can see it in GUI
doc.saveAs("/home/vansh5632/DesignEng/freecad-llm-automation/cylinder_model.FCStd")

print("Files saved: cylinder_model.FCStd and output.stl")
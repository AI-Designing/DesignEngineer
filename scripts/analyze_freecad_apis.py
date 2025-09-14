#!/usr/bin/env python3
"""
Analyze specific FreeCAD API errors and create better prompting examples
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_freecad_apis():
    """Test actual FreeCAD APIs to understand correct usage"""
    try:
        # Test FreeCAD imports
        import math

        import FreeCAD as App
        import Part

        print("🔍 Testing FreeCAD API patterns...")

        # Create a test document
        if not App.ActiveDocument:
            doc = App.newDocument("APITest")
        else:
            doc = App.ActiveDocument

        print(f"✅ Document: {doc.Name}")

        # Test basic shapes
        print("\n📐 Testing basic shape APIs:")

        # Cylinder
        try:
            cyl = Part.makeCylinder(10, 20)
            print("✅ Part.makeCylinder(radius, height) - WORKS")
        except Exception as e:
            print(f"❌ Part.makeCylinder error: {e}")

        # Box
        try:
            box = Part.makeBox(10, 10, 10)
            print("✅ Part.makeBox(length, width, height) - WORKS")
        except Exception as e:
            print(f"❌ Part.makeBox error: {e}")

        # Sphere
        try:
            sphere = Part.makeSphere(10)
            print("✅ Part.makeSphere(radius) - WORKS")
        except Exception as e:
            print(f"❌ Part.makeSphere error: {e}")

        # Circle (common error source)
        print("\n🔍 Testing circle creation methods:")
        try:
            # Method 1: Simple circle
            circle = Part.makeCircle(10)
            print("✅ Part.makeCircle(radius) - WORKS")
        except Exception as e:
            print(f"❌ Part.makeCircle(radius) error: {e}")

        try:
            # Method 2: Circle with center
            circle = Part.makeCircle(10, App.Vector(0, 0, 0))
            print("✅ Part.makeCircle(radius, center) - WORKS")
        except Exception as e:
            print(f"❌ Part.makeCircle(radius, center) error: {e}")

        try:
            # Method 3: Circle with normal
            circle = Part.makeCircle(10, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
            print("✅ Part.makeCircle(radius, center, normal) - WORKS")
        except Exception as e:
            print(f"❌ Part.makeCircle(radius, center, normal) error: {e}")

        # Test wire creation for complex shapes
        print("\n🔧 Testing wire and compound operations:")
        try:
            from Part import Edge, Wire

            edges = []
            # Create multiple circles for gear teeth
            for i in range(6):
                angle = i * math.pi / 3
                x = 20 * math.cos(angle)
                y = 20 * math.sin(angle)
                circle = Part.makeCircle(2, App.Vector(x, y, 0))
                edges.append(circle)
            print("✅ Multiple circles for complex shapes - WORKS")
        except Exception as e:
            print(f"❌ Complex shape creation error: {e}")

        # Test boolean operations
        print("\n🔄 Testing boolean operations:")
        try:
            box1 = Part.makeBox(20, 20, 20)
            cyl1 = Part.makeCylinder(5, 25)
            cut_result = box1.cut(cyl1)
            print("✅ Boolean cut operation - WORKS")
        except Exception as e:
            print(f"❌ Boolean cut error: {e}")

        # Test extrusion
        print("\n⬆️ Testing extrusion operations:")
        try:
            circle = Part.makeCircle(10)
            wire = Part.Wire([circle])
            face = Part.Face(wire)
            solid = face.extrude(App.Vector(0, 0, 20))
            print("✅ Extrusion operation - WORKS")
        except Exception as e:
            print(f"❌ Extrusion error: {e}")

        print("\n🎉 FreeCAD API analysis completed!")

    except ImportError as e:
        print(f"⚠️ FreeCAD not available for testing: {e}")
        print("This is expected in venv - testing patterns from documentation")
        return create_api_patterns_from_docs()


def create_api_patterns_from_docs():
    """Create API patterns based on FreeCAD documentation"""
    patterns = {
        "basic_shapes": {
            "cylinder": "Part.makeCylinder(radius, height)",
            "box": "Part.makeBox(length, width, height)",
            "sphere": "Part.makeSphere(radius)",
            "cone": "Part.makeCone(radius1, radius2, height)",
            "torus": "Part.makeTorus(radius1, radius2)",
        },
        "2d_shapes": {
            "circle": "Part.makeCircle(radius)",
            "circle_positioned": "Part.makeCircle(radius, App.Vector(x, y, z))",
            "line": "Part.makeLine(App.Vector(x1, y1, z1), App.Vector(x2, y2, z2))",
            "polygon": "Part.makePolygon([App.Vector(x1, y1, z1), App.Vector(x2, y2, z2), ...])",
        },
        "complex_operations": {
            "extrude": "face.extrude(App.Vector(0, 0, height))",
            "revolve": "face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)",
            "boolean_cut": "shape1.cut(shape2)",
            "boolean_fuse": "shape1.fuse(shape2)",
            "boolean_common": "shape1.common(shape2)",
        },
    }

    print("📚 Created API patterns from documentation")
    return patterns


if __name__ == "__main__":
    test_freecad_apis()

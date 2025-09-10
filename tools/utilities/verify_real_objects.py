#!/usr/bin/env python3
"""
Verify that real FreeCAD objects were created by opening a saved file
"""

import os

import FreeCAD


def verify_created_objects():
    """Open the latest saved file and verify objects exist"""

    # Path to the latest saved file
    file_path = "/home/vansh5632/DesignEng/freecad-llm-automation/outputs/freecad_auto_save_20250818_185507_003.FCStd"

    print("🔍 Verifying Real FreeCAD Objects")
    print("=" * 50)
    print(f"📂 Opening file: {os.path.basename(file_path)}")

    if not os.path.exists(file_path):
        print("❌ File not found!")
        return False

    try:
        # Open the document
        doc = FreeCAD.openDocument(file_path)

        print(f"✅ Document opened successfully: {doc.Name}")
        print(f"📊 Number of objects: {len(doc.Objects)}")

        # List all objects
        print(f"\n🏗️ Objects found in document:")
        for i, obj in enumerate(doc.Objects, 1):
            print(f"  {i}. {obj.Label} ({obj.TypeId})")

            # Get object properties
            if (
                hasattr(obj, "Length")
                and hasattr(obj, "Width")
                and hasattr(obj, "Height")
            ):
                print(f"     📏 Dimensions: {obj.Length} x {obj.Width} x {obj.Height}")
            elif hasattr(obj, "Radius") and hasattr(obj, "Height"):
                print(f"     📏 Radius: {obj.Radius}, Height: {obj.Height}")
            elif hasattr(obj, "Radius"):
                print(f"     📏 Radius: {obj.Radius}")

        # Verify specific objects exist
        box_found = any(obj.TypeId == "Part::Box" for obj in doc.Objects)
        cylinder_found = any(obj.TypeId == "Part::Cylinder" for obj in doc.Objects)
        sphere_found = any(obj.TypeId == "Part::Sphere" for obj in doc.Objects)

        print(f"\n✅ Verification Results:")
        print(f"  📦 Box found: {'✅ Yes' if box_found else '❌ No'}")
        print(f"  🗂️ Cylinder found: {'✅ Yes' if cylinder_found else '❌ No'}")
        print(f"  🌐 Sphere found: {'✅ Yes' if sphere_found else '❌ No'}")

        # Get file size
        file_size = os.path.getsize(file_path)
        print(f"  📄 File size: {file_size} bytes")

        if len(doc.Objects) >= 3 and box_found and cylinder_found and sphere_found:
            print(f"\n🎉 SUCCESS: All real objects verified!")
            print(f"✅ The '--real' flag actually created FreeCAD objects")
            return True
        else:
            print(f"\n❌ FAILED: Not all objects found")
            return False

    except Exception as e:
        print(f"❌ Error opening document: {e}")
        return False
    finally:
        # Close the document
        if "doc" in locals():
            FreeCAD.closeDocument(doc.Name)


if __name__ == "__main__":
    verify_created_objects()

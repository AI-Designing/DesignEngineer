#!/usr/bin/env python3
"""
Test with corrected FreeCAD code that doesn't create new documents
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    print("🔍 Testing with corrected FreeCAD code...")
    from ai_designer.cli import FreeCADCLI

    # Initialize CLI
    cli = FreeCADCLI(
        use_headless=True,
        llm_provider="deepseek",
        enable_websocket=False,
        enable_persistent_gui=False,
        deepseek_enabled=True,
    )

    print("🔧 Initializing CLI...")
    success = cli.initialize()
    if not success:
        print("❌ CLI initialization failed")
        exit(1)

    print("✅ CLI ready")

    # Check FreeCAD state before
    print(f"\n📊 FreeCAD state before:")
    if hasattr(cli, "api_client") and cli.api_client and hasattr(cli.api_client, "doc"):
        if cli.api_client.doc:
            objects_before = [obj.Label for obj in cli.api_client.doc.Objects]
            print(f"   Document: {cli.api_client.doc.Name}")
            print(f"   Objects: {objects_before}")
        else:
            print("   No active document")
    else:
        print("   API client not properly initialized")

    # Test with proper FreeCAD code that uses existing document
    correct_code = """
import FreeCAD as App
import Part

# Get the active document (don't create new one)
doc = App.ActiveDocument
if not doc:
    print("No active document available")
else:
    print(f"Using active document: {doc.Name}")

    # Create a 10x10x10 cube at origin
    cube_shape = Part.makeBox(10, 10, 10)

    # Create a Part feature and assign the shape
    cube_obj = doc.addObject("Part::Feature", "Cube")
    cube_obj.Shape = cube_shape

    # Set position at origin (though makeBox already creates at origin)
    cube_obj.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

    # Optional: Set color for visibility
    if hasattr(cube_obj, 'ViewObject'):
        cube_obj.ViewObject.ShapeColor = (0.0, 1.0, 0.0)  # Green

    # Recompute to ensure everything is updated
    doc.recompute()

    print(f"✅ Cube created successfully!")
    print(f"   Name: {cube_obj.Label}")
    print(f"   Type: {cube_obj.TypeId}")
    print(f"   Shape valid: {cube_obj.Shape.isValid() if cube_obj.Shape else False}")
    if cube_obj.Shape:
        print(f"   Volume: {cube_obj.Shape.Volume}")
        print(f"   BoundBox: {cube_obj.Shape.BoundBox}")
"""

    print("\n🔧 Executing corrected code manually...")

    # Execute using the command executor
    if cli.command_executor:
        result = cli.command_executor.execute(correct_code)
        print(f"\n📊 Execution result: {result}")

        # Check state after execution
        print(f"\n📊 FreeCAD state after execution:")
        if cli.api_client and cli.api_client.doc:
            objects_after = [obj.Label for obj in cli.api_client.doc.Objects]
            print(f"   Document: {cli.api_client.doc.Name}")
            print(f"   Objects: {objects_after}")

            # Check each object in detail
            for obj in cli.api_client.doc.Objects:
                print(f"   - {obj.Label} ({obj.TypeId})")
                if hasattr(obj, "Shape") and obj.Shape:
                    print(f"     Shape valid: {obj.Shape.isValid()}")
                    print(f"     Volume: {obj.Shape.Volume}")
                    print(f"     BoundBox: {obj.Shape.BoundBox}")
                else:
                    print(f"     No shape data")

        # If we have a file saved, check its size
        if result and result.get("saved_path"):
            file_path = result["saved_path"]
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"\n📁 File: {file_path}")
                print(f"   Size: {file_size} bytes")

                # Compare with the small file from before
                if file_size > 2000:  # Should be much larger if it contains geometry
                    print("   ✅ File size suggests it contains actual geometry")
                else:
                    print("   ⚠️ File size is still small, might not contain geometry")

    print("\n✅ Test completed")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()

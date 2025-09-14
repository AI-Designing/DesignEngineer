#!/usr/bin/env python3
"""
Quick re-test of the basic cylinder to verify fixes
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_cylinder_validation():
    """Test just the cylinder with corrected validation"""
    try:
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
            return

        print("✅ CLI ready")

        # Test the cylinder
        print("\n🧪 Testing cylinder with corrected validation...")

        # Check initial state
        initial_objects = []
        if (
            hasattr(cli, "api_client")
            and cli.api_client
            and hasattr(cli.api_client, "document")
        ):
            if cli.api_client.document:
                initial_objects = [obj.Label for obj in cli.api_client.document.Objects]

        print(f"📊 Initial objects: {initial_objects}")

        # Execute command
        start_time = time.time()
        result = cli.execute_unified_command(
            command="Create a cylinder with radius 10 and height 20", mode="standard"
        )
        execution_time = time.time() - start_time

        print(f"⏱️  Execution time: {execution_time:.1f}s")

        # Check objects created
        current_objects = [obj.Label for obj in cli.api_client.document.Objects]
        new_objects = [obj for obj in current_objects if obj not in initial_objects]

        print(f"📊 New objects: {new_objects}")

        # Validate each object
        for obj_name in new_objects:
            obj = cli.api_client.document.getObject(obj_name)
            if obj and hasattr(obj, "Shape") and obj.Shape and obj.Shape.isValid():
                volume = obj.Shape.Volume
                faces = len(obj.Shape.Faces)
                print(f"   ✅ {obj_name}: Volume={volume:.1f}, Faces={faces}")

                # Cylinder validation
                if "cylinder" in obj_name.lower():
                    if faces == 3:
                        print(f"   ✅ Cylinder face count correct: {faces}")
                    else:
                        print(
                            f"   ⚠️ Cylinder face count unexpected: {faces} (expected 3)"
                        )

                    expected_volume = 3.14159 * 10 * 10 * 20  # π * r² * h
                    if abs(volume - expected_volume) < 100:  # Allow some tolerance
                        print(
                            f"   ✅ Cylinder volume correct: {volume:.1f} (expected ~{expected_volume:.1f})"
                        )
                    else:
                        print(
                            f"   ⚠️ Cylinder volume unexpected: {volume:.1f} (expected ~{expected_volume:.1f})"
                        )

                print(f"   ✅ {obj_name} validation: PASSED")
            else:
                print(f"   ❌ {obj_name}: Invalid or missing shape")

        print("\n🎉 Cylinder test completed with corrected validation!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_cylinder_validation()

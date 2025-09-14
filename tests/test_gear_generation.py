#!/usr/bin/env python3
"""
Test gear generation with improved math API guidance
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_gear_generation():
    """Test gear generation with corrected API usage"""
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

        # Test gear generation
        print("\n🧪 Testing gear generation with improved API guidance...")

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

        # Execute gear command
        start_time = time.time()
        result = cli.execute_unified_command(
            command="Create a simple gear with 12 teeth, radius 25mm, and thickness 5mm",
            mode="standard",
        )
        execution_time = time.time() - start_time

        print(f"⏱️  Execution time: {execution_time:.1f}s")

        # Check objects created
        if cli.api_client and cli.api_client.document:
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
                    print(f"   ✅ {obj_name} validation: PASSED")
                else:
                    print(f"   ❌ {obj_name}: Invalid or missing shape")

        print("\n🎉 Gear test completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_gear_generation()

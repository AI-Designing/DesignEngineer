#!/usr/bin/env python3
"""
Test improved DeepSeek R1 prompting with unified LLM manager
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    print("🔍 Testing improved DeepSeek R1 prompting...")
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

    # Check initial outputs
    outputs_dir = "/home/vansh5632/DesignEng/freecad-llm-automation/outputs"
    before_files = (
        set(os.listdir(outputs_dir)) if os.path.exists(outputs_dir) else set()
    )

    # Test with a simple cube command using improved prompting
    print("\n🚀 Testing improved prompting: Create a cube...")
    start_time = time.time()

    result = cli.execute_unified_command(
        command="Create a 15x15x15 cube centered at origin with green color",
        mode="standard",
    )

    execution_time = time.time() - start_time
    print(f"\n⏱️  Total execution time: {execution_time:.2f} seconds")

    # Check what files were created
    after_files = set(os.listdir(outputs_dir)) if os.path.exists(outputs_dir) else set()
    new_files = after_files - before_files

    if new_files:
        print(f"\n📁 New files created: {len(new_files)}")
        for f in sorted(new_files):
            full_path = os.path.join(outputs_dir, f)
            size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            print(f"   - {f} ({size} bytes)")

            # Check if it's a reasonable size for a file with geometry
            if size > 2000:
                print("     ✅ File size suggests it contains geometry")
            elif size > 1000:
                print("     ⚠️ File size is moderate - may contain some geometry")
            else:
                print("     ❌ File size is too small - likely no geometry")
    else:
        print("⚠️ No new files created")

    # Check FreeCAD document state
    if (
        hasattr(cli, "api_client")
        and cli.api_client
        and hasattr(cli.api_client, "document")
    ):
        if cli.api_client.document:
            objects = [obj.Label for obj in cli.api_client.document.Objects]
            print(f"\n📊 FreeCAD objects: {objects}")

            # Check object details
            for obj in cli.api_client.document.Objects:
                if hasattr(obj, "Shape") and obj.Shape and obj.Shape.isValid():
                    print(
                        f"   ✅ {obj.Label}: Volume={obj.Shape.Volume:.1f}, Faces={len(obj.Shape.Faces)}"
                    )
                else:
                    print(f"   ❌ {obj.Label}: Invalid or missing shape")

    print("\n✅ Test completed")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()

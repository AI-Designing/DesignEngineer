#!/usr/bin/env python3
"""
Test actual command execution and track where code is stored
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    print("🔍 Testing command execution and storage...")
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

    # Test a simple command
    print("\n🚀 Testing unified command: Create a simple cube...")

    # Check initial state of outputs folder
    outputs_dir = "/home/vansh5632/DesignEng/freecad-llm-automation/outputs"
    print(f"\n📁 Contents of {outputs_dir} before command:")
    if os.path.exists(outputs_dir):
        before_files = set(os.listdir(outputs_dir))
        print(f"   Files: {len(before_files)}")
        for f in sorted(before_files)[-5:]:  # Show last 5 files
            print(f"   - {f}")
    else:
        before_files = set()
        print("   Directory doesn't exist")

    # Execute command
    start_time = time.time()

    result = cli.execute_unified_command(
        command="Create a simple 10x10x10 cube at origin", mode="standard"
    )

    execution_time = time.time() - start_time
    print(f"\n⏱️  Command execution took: {execution_time:.2f} seconds")

    print(f"\n📊 Result: {result}")

    # Check what files were created
    print(f"\n📁 Contents of {outputs_dir} after command:")
    if os.path.exists(outputs_dir):
        after_files = set(os.listdir(outputs_dir))
        new_files = after_files - before_files
        print(f"   Files: {len(after_files)} (new: {len(new_files)})")

        if new_files:
            print("   🆕 New files created:")
            for f in sorted(new_files):
                full_path = os.path.join(outputs_dir, f)
                size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                print(f"   - {f} ({size} bytes)")
        else:
            print("   ⚠️  No new files created")
            print("   Last 5 files:")
            for f in sorted(after_files)[-5:]:
                print(f"   - {f}")

    # Check if code was generated
    if hasattr(cli, "unified_llm_manager") and cli.unified_llm_manager:
        print("\n🧠 LLM Manager status:")
        status = cli.unified_llm_manager.get_provider_status()
        print(f"   Active provider: {status['active_provider']}")

    print("\n✅ Test completed")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()

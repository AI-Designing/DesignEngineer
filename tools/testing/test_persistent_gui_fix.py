#!/usr/bin/env python3
"""
Test script to verify persistent GUI fix:
- One window stays open
- Step-by-step updates in the same window
- No new windows opening
"""

import os
import sys
import time


# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from src.ai_designer.cli import FreeCADCLI


def test_persistent_gui_steps():
    """Test that commands execute in same persistent window"""
    print("🧪 Testing Persistent GUI Fix")
    print("=" * 50)

    # Create CLI with persistent GUI enabled
    cli = FreeCADCLI(
        llm_provider="google",
        llm_api_key=os.environ.get("GOOGLE_API_KEY", "test-placeholder-key"),
        enable_persistent_gui=True,
        enable_websocket=True,
    )

    # Initialize the system
    if not cli.initialize():
        print("❌ Failed to initialize CLI")
        return False

    print("\n🎯 Test Plan:")
    print("1. Create box - should open ONE persistent window")
    print("2. Create cylinder - should UPDATE the same window")
    print("3. Create sphere - should UPDATE the same window")
    print("4. Each step should be visible progressively")

    # Step 1: Create box
    print("\n📦 Step 1: Creating box...")
    cli.execute_command("create box 20x20x20 --real")

    print(
        "\n⏸️  Waiting 3 seconds - check that ONE FreeCAD window is open with a box..."
    )
    time.sleep(3)

    # Step 2: Create cylinder
    print("\n🛢️  Step 2: Creating cylinder...")
    cli.execute_command("create cylinder radius 10 height 15 --real")

    print("\n⏸️  Waiting 3 seconds - check SAME window now shows box + cylinder...")
    time.sleep(3)

    # Step 3: Create sphere
    print("\n⚪ Step 3: Creating sphere...")
    cli.execute_command("create sphere radius 8 --real")

    print(
        "\n⏸️  Waiting 3 seconds - check SAME window now shows box + cylinder + sphere..."
    )
    time.sleep(3)

    # Step 4: Create cone
    print("\n🔺 Step 4: Creating cone...")
    cli.execute_command("create cone radius1 12 radius2 6 height 18 --real")

    print("\n✅ Test completed!")
    print("Expected result: ONE FreeCAD window with all 4 objects visible")
    print("🔍 Check that no new windows opened during the test")

    # Keep GUI open for manual verification
    input("\nPress Enter after verifying the GUI shows all objects in ONE window...")

    # Cleanup
    cli.cleanup()
    return True


if __name__ == "__main__":
    try:
        test_persistent_gui_steps()
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()

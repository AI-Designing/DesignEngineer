#!/usr/bin/env python3
"""
Test script for state-aware command processing
"""

import os
import sys

# Add src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)


def test_cone_cylinder():
    """Test creating cone and cylinder together"""
    try:
        from cli import FreeCADCLI

        print("🚀 Testing State-Aware Command Processing")
        print("=" * 50)

        # Create CLI instance
        cli = FreeCADCLI(
            use_headless=True,
            llm_provider="google",
            llm_api_key="AIzaSyDjw_g1kQZAofU-DOsdsCjgkf3_06R2UEk",
            auto_open_gui=True,
        )

        # Initialize
        if cli.initialize():
            print("✅ FreeCAD CLI initialized successfully")

            # Test the complex command
            test_command = "create a cone and cylinder together"
            print(f"🧪 Testing command: '{test_command}'")

            result = cli.execute_command(test_command)

            print("🎯 Test Result:")
            print(f"Status: {result.get('status', 'Unknown')}")
            if "summary" in result:
                print(f"Summary: {result['summary']}")

        else:
            print("❌ Failed to initialize FreeCAD CLI")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_cone_cylinder()

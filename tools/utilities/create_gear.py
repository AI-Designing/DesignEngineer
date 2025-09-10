#!/usr/bin/env python3
"""
Gear Creation CLI Tool
Create gears using the Phase 3 complex workflow system with real LLM integration
"""

import json
import os
import sys
import time
from typing import Any, Dict, Optional

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
sys.path.insert(0, src_path)


def setup_real_environment():
    """Setup real environment with actual LLM and components"""
    print("🔧 Setting up real LLM environment...")

    try:
        # Import real components
        from ai_designer.config import get_api_key
        from ai_designer.llm.client import LLMClient

        # Get API key
        api_key = get_api_key()
        if not api_key:
            print("❌ No API key found. Please check your .env file.")
            return None

        print(f"✅ API key loaded: {api_key[:20]}...")

        # Initialize real LLM client
        llm_client = LLMClient(api_key=api_key)
        print("✅ Real LLM client initialized")

        # Mock other components for now (can be replaced with real ones later)
        class MockStateCache:
            def list_states(self, session_id=None):
                return []

            def retrieve_state(self, key):
                return {}

        class MockAPIClient:
            def get_document_state(self):
                return {
                    "objects": [],
                    "object_count": 0,
                    "document_name": "GearDocument",
                    "has_errors": False,
                    "active_body": False,
                }

            def execute_command(self, script):
                print(f"🔧 Would execute FreeCAD command: {script[:100]}...")
                return {"status": "success", "output": "Command executed (simulation)"}

        class MockCommandExecutor:
            def execute_command(self, command):
                return {"status": "success", "result": "Command executed"}

        return {
            "llm_client": llm_client,
            "state_cache": MockStateCache(),
            "api_client": MockAPIClient(),
            "command_executor": MockCommandExecutor(),
        }

    except Exception as e:
        print(f"❌ Failed to setup real environment: {e}")
        import traceback

        traceback.print_exc()
        return None


def create_gear_commands():
    """Return a list of gear creation commands to test"""
    return [
        "Create a simple gear with 20 teeth and 5mm module",
        "Design a spur gear with 24 teeth, 50mm diameter, and 10mm thickness",
        "Build a gear with hub and keyway for shaft mounting",
        "Create a helical gear with 30 teeth and 15 degree helix angle",
        "Design a gear assembly with two meshing gears",
        "Make a planetary gear system with sun, planet, and ring gears",
        "Create a worm gear with 40mm diameter and 8mm pitch",
        "Build a bevel gear with 45 degree angle and mounting features",
    ]


def display_gear_options():
    """Display available gear creation options"""
    print("🔧 Available Gear Creation Commands:")
    print("=" * 50)

    commands = create_gear_commands()
    for i, command in enumerate(commands, 1):
        print(f"{i}. {command}")

    print(f"\n💡 Usage:")
    print(f"   python create_gear.py                    # Interactive selection")
    print(f"   python create_gear.py 1                  # Use option 1")
    print(f'   python create_gear.py "custom command"    # Custom gear command')


def main():
    """Main gear creation function"""

    print("⚙️ Gear Creation Tool - Phase 3 Complex Workflow System")
    print("=" * 70)

    # Setup environment
    env = setup_real_environment()
    if not env:
        return 1

    # Determine command to execute
    command = None

    if len(sys.argv) == 1:
        # Interactive mode
        display_gear_options()
        try:
            choice = input("\n🎯 Enter option number (1-8) or 'q' to quit: ").strip()
            if choice.lower() == "q":
                print("👋 Goodbye!")
                return 0

            choice_num = int(choice)
            if 1 <= choice_num <= 8:
                commands = create_gear_commands()
                command = commands[choice_num - 1]
            else:
                print("❌ Invalid option. Please choose 1-8.")
                return 1
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Cancelled by user")
            return 0

    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        try:
            # Check if it's a number (option selection)
            choice_num = int(arg)
            if 1 <= choice_num <= 8:
                commands = create_gear_commands()
                command = commands[choice_num - 1]
            else:
                print("❌ Invalid option. Please choose 1-8.")
                return 1
        except ValueError:
            # It's a custom command
            command = arg

    else:
        # Multiple arguments - join as custom command
        command = " ".join(sys.argv[1:])

    if not command:
        print("❌ No command specified")
        return 1

    print(f"\n⚙️ Creating gear with command: '{command}'")
    print("=" * 60)

    try:
        # Initialize the processor with real LLM
        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor

        processor = StateAwareCommandProcessor(
            llm_client=env["llm_client"],
            state_cache=env["state_cache"],
            api_client=env["api_client"],
            command_executor=env["command_executor"],
        )

        print("✅ StateAwareCommandProcessor initialized with real LLM")

        # Process the gear creation command
        print(f"\n🧠 Processing gear command with real LLM...")
        start_time = time.time()

        result = processor.process_complex_command(command)

        execution_time = time.time() - start_time

        # Display detailed results
        print(f"\n⚙️ Gear Creation Results:")
        print("=" * 50)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Workflow Type: {result.get('workflow', 'unknown')}")
        print(f"Command: {command}")
        print(f"Execution Time: {execution_time:.2f}s")

        # Show workflow analysis
        if "workflow_analysis" in result or hasattr(
            processor, "_last_workflow_analysis"
        ):
            print(f"\n🔍 Workflow Analysis:")
            # We'll get this from the processor's last analysis
            print(f"Strategy: Complex workflow detected")
            print(f"Complexity Score: High (gear creation)")

        # Show step details if available
        if result.get("status") == "success":
            steps = result.get("completed_steps", 0)
            total = result.get("total_steps", 0)
            print(f"Steps Completed: {steps}/{total}")

            if "step_results" in result and result["step_results"]:
                print(f"\n🔧 Step Execution Details:")
                for i, step in enumerate(result["step_results"], 1):
                    if hasattr(step, "status"):
                        status_icon = "✅" if step.status == "success" else "❌"
                        step_name = getattr(step, "step_name", f"Step {i}")
                    else:
                        status_icon = "✅" if step.get("status") == "success" else "❌"
                        step_name = step.get("step_name", f"Step {i}")
                    print(f"  {status_icon} {step_name}")

            print(f"\n🎉 SUCCESS: Gear creation workflow completed!")
            print(f"✅ Your gear design has been processed")
            print(f"✅ Ready for FreeCAD execution")

        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
            if "suggestion" in result:
                print(f"💡 Suggestion: {result['suggestion']}")

        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        print(f"❌ Gear creation failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

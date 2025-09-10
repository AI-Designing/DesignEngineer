#!/usr/bin/env python3
"""
Quick CLI Test for Complex Workflow
Test specific command: "Create a bracket with 4 mounting holes and fillets"
"""

import os
import sys

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
sys.path.insert(0, src_path)


def main():
    """Quick test of the complex workflow system"""

    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = "Create a bracket with 4 mounting holes and fillets"

    print(f"🎯 Testing Complex Workflow Command: '{command}'")
    print("=" * 60)

    try:
        # Import test functions from our comprehensive test
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from test_complex_workflow import setup_test_environment

        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor

        # Setup test environment
        mocks = setup_test_environment()
        if not mocks:
            print("❌ Failed to setup test environment")
            return 1

        # Initialize processor
        processor = StateAwareCommandProcessor(
            llm_client=mocks["MockLLMClient"](),
            state_cache=mocks["MockStateCache"](),
            api_client=mocks["MockAPIClient"](),
            command_executor=mocks["MockCommandExecutor"](),
        )

        # Override workflow orchestrator with mock
        processor.workflow_orchestrator = mocks["MockWorkflowOrchestrator"](
            state_processor=processor
        )
        processor.multi_step_workflows_available = True

        print("✅ Phase 3 Complex Workflow System initialized")

        # Process the command
        print(f"\n🧠 Processing: '{command}'")
        result = processor.process_complex_command(command)

        # Show results
        print(f"\n📊 Results:")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Workflow: {result.get('workflow', 'unknown')}")
        print(
            f"Steps: {result.get('completed_steps', 0)}/{result.get('total_steps', 0)}"
        )
        print(f"Time: {result.get('execution_time', 0):.2f}s")

        if result.get("status") == "success":
            print("\n🎉 SUCCESS: Complex workflow executed successfully!")
            return 0
        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

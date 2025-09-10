#!/usr/bin/env python3
"""
Test to see the actual generated code and debug 3D model creation
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    print("🔍 Testing code generation and execution details...")
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

    # Test with direct unified manager call to see full response
    print("\n🚀 Testing direct unified manager call...")

    from ai_designer.llm.unified_manager import GenerationMode, LLMRequest

    # Get current state
    current_state = None
    if cli.state_analyzer:
        try:
            current_state = cli.state_analyzer.get_current_state()
            print(f"📊 Current FreeCAD state: {current_state}")
        except Exception as e:
            print(f"⚠️ Could not get current state: {e}")

    # Create request
    request = LLMRequest(
        command="Create a simple 10x10x10 cube at origin and ensure it's visible in FreeCAD",
        state=current_state,
        mode=GenerationMode.STANDARD,
        context={"session_id": "debug_session"},
    )

    print("\n🧠 Generating code with unified manager...")
    response = cli.unified_llm_manager.generate_command(request)

    print(f"\n📊 Response status: {response.status}")
    print(f"📊 Provider: {response.provider}")
    print(f"📊 Confidence: {response.confidence_score}")
    print(f"📊 Execution time: {response.execution_time:.1f}s")

    if response.reasoning_chain:
        print(f"📊 Reasoning steps: {len(response.reasoning_chain)}")
        for i, step in enumerate(response.reasoning_chain[:2]):  # Show first 2 steps
            step_text = str(step)[:100] if step else "No content"
            print(f"   Step {i+1}: {step_text}...")

    print(f"\n📝 Full Generated Code:")
    print("=" * 60)
    print(response.generated_code)
    print("=" * 60)

    # Now execute manually and check
    if response.generated_code and cli.command_executor:
        print("\n🔧 Executing code manually...")

        # Check what's in FreeCAD before execution
        print("\n📊 FreeCAD state before execution:")
        if hasattr(cli.freecad_api, "doc") and cli.freecad_api.doc:
            objects_before = [obj.Label for obj in cli.freecad_api.doc.Objects]
            print(f"   Objects: {objects_before}")
        else:
            print("   No active document")

        # Execute the code
        result = cli.command_executor.execute(response.generated_code)
        print(f"\n📊 Execution result: {result}")

        # Check what's in FreeCAD after execution
        print("\n📊 FreeCAD state after execution:")
        if hasattr(cli.freecad_api, "doc") and cli.freecad_api.doc:
            objects_after = [obj.Label for obj in cli.freecad_api.doc.Objects]
            print(f"   Objects: {objects_after}")

            # Check each object
            for obj in cli.freecad_api.doc.Objects:
                print(f"   - {obj.Label} ({obj.TypeId})")
                if hasattr(obj, "Shape") and obj.Shape:
                    print(f"     Shape: {obj.Shape}")
                    print(
                        f"     Volume: {obj.Shape.Volume if hasattr(obj.Shape, 'Volume') else 'N/A'}"
                    )
                else:
                    print(f"     No shape data")

        # Force recompute
        if hasattr(cli.freecad_api, "doc") and cli.freecad_api.doc:
            print("\n🔄 Forcing FreeCAD recompute...")
            cli.freecad_api.doc.recompute()

            # Check again after recompute
            print("\n📊 FreeCAD state after recompute:")
            for obj in cli.freecad_api.doc.Objects:
                print(f"   - {obj.Label} ({obj.TypeId})")
                if hasattr(obj, "Shape") and obj.Shape:
                    print(f"     Shape valid: {obj.Shape.isValid()}")
                    print(f"     Volume: {obj.Shape.Volume}")
                    print(f"     BoundBox: {obj.Shape.BoundBox}")

    print("\n✅ Debug test completed")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()

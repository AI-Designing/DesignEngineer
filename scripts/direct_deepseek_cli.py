#!/usr/bin/env python3
"""
Direct DeepSeek CLI command - bypasses complex workflows and uses DeepSeek R1 directly
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_designer.freecad.api_client import FreeCADAPIClient
from ai_designer.llm.deepseek_client import (
    DeepSeekConfig,
    DeepSeekMode,
    DeepSeekR1Client,
)


def main():
    """Main CLI function for direct DeepSeek usage"""
    command = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Create a simple cube with dimensions 10x10x10mm"
    )

    print("🚀 Direct DeepSeek FreeCAD CLI")
    print("=" * 50)
    print(f"Command: {command}")
    print("")

    # Initialize DeepSeek client
    print("🧠 Initializing DeepSeek R1...")
    try:
        config = DeepSeekConfig(
            host="localhost",
            port=11434,
            model_name="deepseek-r1:14b",
            timeout=300,  # 5 minutes
        )
        deepseek_client = DeepSeekR1Client(config)
        print("✅ DeepSeek R1 ready")
    except Exception as e:
        print(f"❌ Failed to initialize DeepSeek: {e}")
        return

    # Initialize FreeCAD connection
    print("🔧 Connecting to FreeCAD...")
    try:
        freecad_client = FreeCADAPIClient()
        freecad_client.connect()
        print("✅ FreeCAD connected")
    except Exception as e:
        print(f"❌ Failed to connect to FreeCAD: {e}")
        return

    # Generate code with DeepSeek
    print(f"⏳ Generating FreeCAD code... (this may take 2-3 minutes)")
    try:
        response = deepseek_client.generate_complex_part(
            requirements=command,
            mode=DeepSeekMode.FAST
            if "simple" in command.lower()
            else DeepSeekMode.REASONING,
        )

        if response.status == "success":
            print("✅ Code generation successful!")
            print(f"   Confidence: {response.confidence_score:.2f}")
            print(f"   Generation time: {response.execution_time:.1f}s")

            # Show generated code
            print("\n📝 Generated FreeCAD Code:")
            print("=" * 50)
            print(response.generated_code)
            print("=" * 50)

            # Execute code in FreeCAD
            print("\n🔧 Executing in FreeCAD...")
            try:
                result = freecad_client.execute_command(response.generated_code)
                print("✅ Code executed successfully!")
                print(f"📄 Result: {result}")

                # Recompute and save
                freecad_client.execute_command("doc.recompute()")
                print("✅ Document recomputed - check FreeCAD GUI for results")

            except Exception as e:
                print(f"❌ Execution failed: {e}")
                print("You can manually copy the code above and paste it into FreeCAD")
        else:
            print(f"❌ Code generation failed: {response.error_message}")

    except Exception as e:
        print(f"❌ Generation error: {e}")


if __name__ == "__main__":
    main()

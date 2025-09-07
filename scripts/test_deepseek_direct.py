#!/usr/bin/env python3
"""
Direct DeepSeek R1 test script to verify local model integration
"""

import logging
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_designer.llm.deepseek_client import (
    DeepSeekConfig,
    DeepSeekMode,
    DeepSeekR1Client,
)


def test_deepseek_connection():
    """Test basic DeepSeek connection"""
    print("🧠 Testing DeepSeek R1 Connection...")

    try:
        config = DeepSeekConfig(
            host="localhost",
            port=11434,
            model_name="deepseek-r1:14b",
            timeout=180,  # 3 minutes for 14B model
        )

        client = DeepSeekR1Client(config)
        print("✅ DeepSeek R1 client initialized successfully")
        return client
    except Exception as e:
        print(f"❌ Failed to initialize DeepSeek client: {e}")
        return None


def test_simple_generation(client):
    """Test simple code generation"""
    print("\n🔧 Testing Simple Code Generation...")

    try:
        simple_request = "Create a simple cube with dimensions 10x10x10mm"

        print(f"Request: {simple_request}")
        print("⏳ Generating... (this may take 30-60 seconds)")

        response = client.generate_complex_part(
            requirements=simple_request, mode=DeepSeekMode.FAST
        )

        if response.status == "success":
            print("✅ Generation successful!")
            print(f"   Confidence: {response.confidence_score:.2f}")
            print(f"   Execution time: {response.execution_time:.2f}s")
            print(f"   Code length: {len(response.generated_code)} characters")
            print(f"   Reasoning steps: {len(response.reasoning_chain)}")

            print("\n📝 Generated Code:")
            print("=" * 50)
            print(
                response.generated_code[:500] + "..."
                if len(response.generated_code) > 500
                else response.generated_code
            )
            print("=" * 50)

            return True
        else:
            print(f"❌ Generation failed: {response.error_message}")
            return False

    except Exception as e:
        print(f"❌ Generation exception: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 DeepSeek R1 Direct Test")
    print("=" * 50)

    # Test 1: Connection
    client = test_deepseek_connection()
    if not client:
        print("\n❌ Cannot proceed without DeepSeek connection")
        return False

    # Test 2: Simple generation
    success = test_simple_generation(client)

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! DeepSeek R1 is working correctly.")
        print("\n🎯 Next steps:")
        print("  1. DeepSeek R1 local model is responding")
        print("  2. Code generation is functional")
        print("  3. Integration with FreeCAD CLI should work")
    else:
        print("❌ Tests failed. Check DeepSeek R1 setup.")
        print("\n🔧 Troubleshooting:")
        print("  1. Ensure ollama is running: ollama serve")
        print("  2. Ensure model is available: ollama list")
        print("  3. Check model name: deepseek-r1:14b")

    return success


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

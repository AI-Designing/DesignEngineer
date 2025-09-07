#!/usr/bin/env python3
"""
Unified LLM System Demo
Demonstrates switching between DeepSeek R1 and Google Gemini
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_designer.llm.unified_manager import (
    GenerationMode,
    LLMProvider,
    LLMRequest,
    UnifiedLLMManager,
)


def main():
    """Demo the unified LLM system"""
    print("🚀 Unified LLM System Demo")
    print("=" * 50)

    # Initialize unified manager
    print("🧠 Initializing Unified LLM Manager...")
    try:
        config = {
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "deepseek_host": "localhost",
            "deepseek_port": 11434,
            "deepseek_model": "deepseek-r1:14b",
            "deepseek_timeout": 300,
        }

        manager = UnifiedLLMManager(config=config)
        print("✅ Unified LLM Manager initialized")

        # Show provider status
        print("\n📊 Provider Status:")
        status = manager.get_provider_status()
        for provider, info in status["providers"].items():
            status_icon = "✅" if info["available"] else "❌"
            print(
                f"   {status_icon} {provider}: {'Available' if info['available'] else 'Unavailable'}"
            )

    except Exception as e:
        print(f"❌ Failed to initialize manager: {e}")
        return

    # Test commands
    test_commands = [
        {
            "command": "Create a simple cube with dimensions 10x10x10mm",
            "mode": GenerationMode.FAST,
            "description": "Simple command (should use Gemini)",
        },
        {
            "command": "Create a complex mechanical gear with 20 teeth, hub, and keyway",
            "mode": GenerationMode.COMPLEX,
            "description": "Complex command (should use DeepSeek R1)",
        },
        {
            "command": "Design an innovative bracket with organic curves",
            "mode": GenerationMode.CREATIVE,
            "description": "Creative command (should use DeepSeek R1 creative mode)",
        },
    ]

    print(f"\n🧪 Testing {len(test_commands)} commands...")

    for i, test in enumerate(test_commands, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test['description']}")
        print(f"Command: {test['command']}")
        print(f"Mode: {test['mode'].value}")
        print("-" * 60)

        # Create request
        request = LLMRequest(
            command=test["command"],
            mode=test["mode"],
            context={"test": True},
        )

        # Generate
        try:
            response = manager.generate_command(request)

            if response.status == "success":
                print(f"✅ SUCCESS")
                print(f"   Provider used: {response.provider.value}")
                print(f"   Confidence: {response.confidence_score:.2f}")
                print(f"   Generation time: {response.execution_time:.1f}s")
                print(f"   Code length: {len(response.generated_code)} characters")

                if response.reasoning_chain:
                    print(f"   Reasoning steps: {len(response.reasoning_chain)}")

                # Show code preview
                preview = (
                    response.generated_code[:200] + "..."
                    if len(response.generated_code) > 200
                    else response.generated_code
                )
                print(f"   Code preview: {preview}")

            else:
                print(f"❌ FAILED: {response.error_message}")

        except Exception as e:
            print(f"❌ ERROR: {e}")

    # Show performance summary
    print(f"\n{'='*60}")
    print("📈 Performance Summary:")
    performance = manager.get_performance_summary()

    if performance["total_generations"] > 0:
        print(f"Total generations: {performance['total_generations']}")
        for provider, usage in performance["provider_usage"].items():
            if usage > 0:
                success_rate = performance["success_rates"][provider] * 100
                avg_time = performance["average_times"][provider]
                print(
                    f"   {provider}: {usage} requests, {success_rate:.1f}% success, {avg_time:.1f}s avg"
                )
    else:
        print("No generations completed")

    print(f"\n✅ Demo completed!")
    print("\n💡 Key Features Demonstrated:")
    print("   • Auto provider selection based on command complexity")
    print("   • Seamless fallback between providers")
    print("   • Performance tracking and metrics")
    print("   • Unified interface for different LLM providers")


if __name__ == "__main__":
    main()

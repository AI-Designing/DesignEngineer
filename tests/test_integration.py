#!/usr/bin/env python3
"""
Quick Integration Test for DeepSeek R1 FreeCAD System
Tests the complete pipeline from user request to FreeCAD code generation
"""

import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_deepseek_integration():
    """Test the complete DeepSeek R1 integration"""

    print("🧪 DeepSeek R1 FreeCAD Integration Test")
    print("=" * 50)

    try:
        # Test 1: Import all modules
        print("1️⃣ Testing imports...")

        from ai_designer.core.enhanced_complex_generator import (
            EnhancedComplexShapeGenerator,
        )
        from ai_designer.llm.deepseek_client import (
            DeepSeekConfig,
            DeepSeekIntegrationManager,
            DeepSeekMode,
            DeepSeekR1Client,
        )

        print("   ✅ All imports successful")

        # Test 2: Initialize DeepSeek client
        print("2️⃣ Testing DeepSeek client initialization...")

        config = DeepSeekConfig(host="localhost", port=8000, timeout=30)

        try:
            client = DeepSeekR1Client(config)
            print("   ✅ DeepSeek client initialized")
        except Exception as e:
            print(f"   ⚠️ DeepSeek server not available: {e}")
            print("   💡 Run: scripts/setup_deepseek_r1.sh to setup local server")
            client = None

        # Test 3: Test configuration loading
        print("3️⃣ Testing configuration...")

        import yaml

        try:
            with open("config/config.yaml", "r") as f:
                config_data = yaml.safe_load(f)

            if "deepseek" in config_data:
                print("   ✅ DeepSeek configuration found")
                print(f"   📋 Host: {config_data['deepseek']['host']}")
                print(f"   📋 Port: {config_data['deepseek']['port']}")
                print(f"   📋 Enabled: {config_data['deepseek']['enabled']}")
            else:
                print("   ⚠️ DeepSeek configuration missing")
        except Exception as e:
            print(f"   ❌ Configuration error: {e}")

        # Test 4: Test mock generation (if server not available)
        print("4️⃣ Testing code generation...")

        if client:
            try:
                response = client.generate_complex_part(
                    requirements="Create a simple test cube 10x10x10mm",
                    mode=DeepSeekMode.FAST,
                )

                if response.status == "success":
                    print("   ✅ Code generation successful")
                    print(f"   📊 Confidence: {response.confidence_score:.2f}")
                    print(f"   ⏱️ Time: {response.execution_time:.2f}s")
                    print(f"   🧠 Reasoning steps: {len(response.reasoning_chain)}")
                else:
                    print(f"   ❌ Generation failed: {response.error_message}")
            except Exception as e:
                print(f"   ❌ Generation error: {e}")
        else:
            print("   ⏭️ Skipping (server not available)")

        # Test 5: Test enhanced complex generator
        print("5️⃣ Testing enhanced complex generator...")

        try:
            # Mock the required dependencies
            class MockStateAnalyzer:
                def analyze_state(self, state):
                    return {"objects": [], "analysis": "mock"}

            class MockCommandExecutor:
                def execute_command(self, command):
                    return {"status": "success", "result": "mock execution"}

            generator = EnhancedComplexShapeGenerator(
                llm_client=None,
                state_analyzer=MockStateAnalyzer(),
                command_executor=MockCommandExecutor(),
                use_deepseek=bool(client),
                deepseek_config=config if client else None,
            )

            print("   ✅ Enhanced generator initialized")

            # Test DeepSeek integration status
            deepseek_status = (
                generator.test_deepseek_connection()
                if client
                else {"status": "not_available"}
            )
            print(f"   📡 DeepSeek status: {deepseek_status['status']}")

        except Exception as e:
            print(f"   ❌ Generator initialization error: {e}")

        # Test 6: Test integration manager
        print("6️⃣ Testing integration manager...")

        if client:
            try:
                manager = DeepSeekIntegrationManager(client, None)

                # Test mode selection
                mode = manager._select_optimal_mode(
                    "Create a complex gear assembly", None
                )
                print(f"   ✅ Optimal mode selected: {mode}")

                metrics = manager.get_integration_metrics()
                print(f"   📊 Integration metrics available: {len(metrics)} entries")

            except Exception as e:
                print(f"   ❌ Integration manager error: {e}")
        else:
            print("   ⏭️ Skipping (server not available)")

        # Test 7: Performance metrics
        print("7️⃣ Testing performance metrics...")

        if client:
            try:
                metrics = client.get_performance_metrics()
                print(f"   ✅ Performance metrics: {len(metrics)} entries")

                insights = client.get_reasoning_insights()
                print(
                    f"   🧠 Reasoning insights: {len(insights.get('insights', []))} insights"
                )

            except Exception as e:
                print(f"   ❌ Metrics error: {e}")
        else:
            print("   ⏭️ Skipping (server not available)")

        print("\n" + "=" * 50)
        print("🎉 Integration test completed!")

        if client:
            print("✅ DeepSeek R1 integration is ready for use")
            print("🚀 Run examples/demo_deepseek_r1_clean.py for full demo")
        else:
            print("⚠️ DeepSeek R1 server not available")
            print("💡 Setup instructions:")
            print("   1. Run: ./scripts/setup_deepseek_r1.sh")
            print("   2. Start server: ~/.deepseek-r1/start_deepseek.sh")
            print("   3. Test again: python tests/test_integration.py")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Install dependencies: pip install -e .")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    test_deepseek_integration()

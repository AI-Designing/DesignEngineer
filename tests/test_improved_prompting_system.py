#!/usr/bin/env python3
"""
Test the improved DeepSeek prompting with different complexity levels
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_improved_prompting():
    """Test improved prompting system with different complexity levels"""
    try:
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
            return

        print("✅ CLI ready")

        # Test cases with different complexity levels
        test_cases = [
            {
                "name": "Basic Shape",
                "command": "Create a simple cylinder with radius 8 and height 15",
                "expected_complexity": "basic",
            },
            {
                "name": "Medium Complexity",
                "command": "Create a cube with a cylindrical hole through the center",
                "expected_complexity": "medium",
            },
            {
                "name": "Complex Shape",
                "command": "Create a simple gear with 8 teeth approximated using circular profiles",
                "expected_complexity": "complex",
            },
        ]

        results = []

        for i, test_case in enumerate(test_cases):
            print(f"\n{'='*60}")
            print(f"🧪 TEST {i+1}/3: {test_case['name']}")
            print(f"📝 Command: {test_case['command']}")
            print(f"🎯 Expected complexity: {test_case['expected_complexity']}")
            print(f"{'='*60}")

            # Test complexity analysis
            if hasattr(
                cli.unified_llm_manager.providers["deepseek"]["client"],
                "_analyze_requirement_complexity",
            ):
                detected_complexity = cli.unified_llm_manager.providers["deepseek"][
                    "client"
                ]._analyze_requirement_complexity(test_case["command"])
                print(f"🔍 Detected complexity: {detected_complexity}")

                if detected_complexity == test_case["expected_complexity"]:
                    print("✅ Complexity detection: CORRECT")
                else:
                    print(
                        f"⚠️ Complexity detection: Expected {test_case['expected_complexity']}, got {detected_complexity}"
                    )

            # Get initial state
            initial_objects = []
            if (
                hasattr(cli, "api_client")
                and cli.api_client
                and hasattr(cli.api_client, "document")
            ):
                if cli.api_client.document:
                    initial_objects = [
                        obj.Label for obj in cli.api_client.document.Objects
                    ]

            print(f"📊 Initial objects: {initial_objects}")

            # Execute command
            start_time = time.time()
            try:
                result = cli.execute_unified_command(
                    command=test_case["command"], mode="standard"
                )
                execution_time = time.time() - start_time

                print(f"⏱️  Execution time: {execution_time:.1f}s")

                # Check results
                success = True
                if cli.api_client and cli.api_client.document:
                    current_objects = [
                        obj.Label for obj in cli.api_client.document.Objects
                    ]
                    new_objects = [
                        obj for obj in current_objects if obj not in initial_objects
                    ]

                    print(f"📊 New objects: {new_objects}")

                    if new_objects:
                        for obj_name in new_objects:
                            obj = cli.api_client.document.getObject(obj_name)
                            if (
                                obj
                                and hasattr(obj, "Shape")
                                and obj.Shape
                                and obj.Shape.isValid()
                            ):
                                volume = obj.Shape.Volume
                                faces = len(obj.Shape.Faces)
                                print(
                                    f"   ✅ {obj_name}: Volume={volume:.1f}, Faces={faces}"
                                )
                            else:
                                success = False
                                print(f"   ❌ {obj_name}: Invalid shape")
                    else:
                        success = False
                        print("   ❌ No objects created")

                results.append(
                    {
                        "name": test_case["name"],
                        "success": success,
                        "time": execution_time,
                        "complexity": test_case["expected_complexity"],
                    }
                )

                if success:
                    print(f"✅ TEST PASSED: {test_case['name']}")
                else:
                    print(f"❌ TEST FAILED: {test_case['name']}")

            except Exception as e:
                execution_time = time.time() - start_time
                print(f"❌ TEST ERROR: {test_case['name']} - {e}")
                results.append(
                    {
                        "name": test_case["name"],
                        "success": False,
                        "time": execution_time,
                        "error": str(e),
                    }
                )

            # Brief pause between tests
            print("\n⏸️  Pausing 3 seconds between tests...")
            time.sleep(3)

        # Final summary
        print(f"\n{'='*80}")
        print("📊 IMPROVED PROMPTING TEST RESULTS")
        print(f"{'='*80}")

        passed = sum(1 for r in results if r["success"])
        total = len(results)
        total_time = sum(r["time"] for r in results)

        print(f"✅ Tests passed: {passed}/{total}")
        print(f"⏱️  Total time: {total_time:.1f}s")
        print(f"📈 Success rate: {(passed/total)*100:.1f}%")

        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"   {status} {result['name']} ({result['time']:.1f}s)")

        print("\n🎉 Improved prompting test completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_improved_prompting()

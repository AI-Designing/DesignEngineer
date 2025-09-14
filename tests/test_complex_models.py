#!/usr/bin/env python3
"""
Comprehensive test suite for complex 3D model generation using unified LLM system
"""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_complex_model(cli, test_name, command, expected_objects=1, min_volume=0):
    """Test a complex model and validate results"""
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {test_name}")
    print(f"📝 Command: {command}")
    print(f"{'='*60}")

    # Check initial state
    outputs_dir = "/home/vansh5632/DesignEng/freecad-llm-automation/outputs"
    before_files = (
        set(os.listdir(outputs_dir)) if os.path.exists(outputs_dir) else set()
    )

    # Get initial object count
    initial_objects = []
    if (
        hasattr(cli, "api_client")
        and cli.api_client
        and hasattr(cli.api_client, "document")
    ):
        if cli.api_client.document:
            initial_objects = [obj.Label for obj in cli.api_client.document.Objects]

    print(f"📊 Initial objects: {initial_objects}")

    # Execute command
    start_time = time.time()
    try:
        result = cli.execute_unified_command(command=command, mode="complex")
        execution_time = time.time() - start_time

        print(f"⏱️  Execution time: {execution_time:.1f}s")

        # Check results
        success = True
        issues = []

        # Check file creation
        after_files = (
            set(os.listdir(outputs_dir)) if os.path.exists(outputs_dir) else set()
        )
        new_files = after_files - before_files

        if new_files:
            for f in sorted(new_files):
                full_path = os.path.join(outputs_dir, f)
                size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                print(f"📁 New file: {f} ({size} bytes)")

                if size < 1500:  # More reasonable threshold for FreeCAD files
                    issues.append(
                        f"File size too small ({size} bytes) - may not contain geometry"
                    )
                    success = False
        else:
            issues.append("No new files created")
            success = False

        # Check FreeCAD objects
        if cli.api_client and cli.api_client.document:
            current_objects = [obj.Label for obj in cli.api_client.document.Objects]
            new_objects = [obj for obj in current_objects if obj not in initial_objects]

            print(f"📊 New objects created: {new_objects}")

            if len(new_objects) < expected_objects:
                issues.append(
                    f"Expected {expected_objects} objects, got {len(new_objects)}"
                )
                success = False

            # Check object details
            total_volume = 0
            for obj_name in new_objects:
                obj = cli.api_client.document.getObject(obj_name)
                if obj and hasattr(obj, "Shape") and obj.Shape and obj.Shape.isValid():
                    volume = obj.Shape.Volume
                    faces = len(obj.Shape.Faces)
                    total_volume += volume
                    print(f"   ✅ {obj_name}: Volume={volume:.1f}, Faces={faces}")

                    # Check face count based on object type (different shapes have different expected face counts)
                    expected_faces = {
                        "cube": 6,
                        "box": 6,
                        "cylinder": 3,  # 2 circular faces + 1 curved surface
                        "sphere": 1,  # 1 curved surface
                        "cone": 2,  # 1 circular base + 1 curved surface
                        "torus": 1,  # 1 curved surface
                    }

                    # Try to determine object type from name or use generic validation
                    obj_type = obj_name.lower()
                    min_faces = 1  # At least 1 face for any valid 3D object
                    for shape_type, face_count in expected_faces.items():
                        if shape_type in obj_type:
                            min_faces = face_count
                            break

                    if faces < min_faces:
                        issues.append(
                            f"{obj_name} has too few faces ({faces}) - expected at least {min_faces}"
                        )
                        success = False
                else:
                    issues.append(f"{obj_name} has invalid or missing shape")
                    success = False

            if min_volume > 0 and total_volume < min_volume:
                issues.append(
                    f"Total volume {total_volume:.1f} below expected minimum {min_volume}"
                )
                success = False

        # Report results
        if success:
            print(f"✅ TEST PASSED: {test_name}")
        else:
            print(f"❌ TEST FAILED: {test_name}")
            for issue in issues:
                print(f"   ⚠️  {issue}")

        return success, execution_time, issues

    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ TEST FAILED: {test_name}")
        print(f"   Exception: {e}")
        return False, execution_time, [str(e)]


def main():
    try:
        print("🔍 Starting comprehensive complex model testing...")
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

        print("✅ CLI ready for complex model testing")

        # Define test cases with increasing complexity
        test_cases = [
            {
                "name": "Basic Cylinder",
                "command": "Create a cylinder with radius 10 and height 20",
                "expected_objects": 1,
                "min_volume": 6000,  # π * 10² * 20 ≈ 6283
            },
            {
                "name": "Multi-Part Assembly",
                "command": "Create a gear with 12 teeth, radius 25mm, and thickness 5mm",
                "expected_objects": 1,
                "min_volume": 8000,  # More reasonable for gear volume
            },
            {
                "name": "Boolean Operations",
                "command": "Create a cube 20x20x20 with a cylindrical hole diameter 10 through the center",
                "expected_objects": 1,
                "min_volume": 6000,  # 8000 - π*5²*20 ≈ 6429, lower threshold for safety
            },
            {
                "name": "Complex Sweep",
                "command": "Create a helical spring with 5 coils, diameter 30mm, pitch 10mm, wire diameter 3mm",
                "expected_objects": 1,
                "min_volume": 50,  # Spring should have some volume
            },
            {
                "name": "Parametric Part",
                "command": "Create a bracket with mounting holes: base 50x30x5mm, vertical arm 30x40x5mm, 4 holes diameter 6mm",
                "expected_objects": 1,
                "min_volume": 5000,  # Bracket volume minus holes
            },
            {
                "name": "Organic Shape",
                "command": "Create a bottle shape: cylindrical body height 100mm diameter 40mm, neck height 30mm diameter 20mm, smooth transition",
                "expected_objects": 1,
                "min_volume": 80000,  # Bottle volume
            },
        ]

        # Run tests
        results = []
        total_time = 0

        for i, test_case in enumerate(test_cases):
            print(f"\n🚀 Running test {i+1}/{len(test_cases)}")
            success, exec_time, issues = test_complex_model(
                cli,
                test_case["name"],
                test_case["command"],
                test_case["expected_objects"],
                test_case["min_volume"],
            )

            results.append(
                {
                    "name": test_case["name"],
                    "success": success,
                    "time": exec_time,
                    "issues": issues,
                }
            )
            total_time += exec_time

            # Brief pause between tests
            time.sleep(2)

        # Summary report
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE TEST RESULTS")
        print(f"{'='*80}")

        passed = sum(1 for r in results if r["success"])
        total = len(results)

        print(f"Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        print(f"Total execution time: {total_time:.1f}s")
        print(f"Average time per test: {total_time/total:.1f}s")

        print("\nDetailed Results:")
        for r in results:
            status = "✅ PASS" if r["success"] else "❌ FAIL"
            print(f"{status} {r['name']:<25} ({r['time']:.1f}s)")
            for issue in r["issues"]:
                print(f"      ⚠️  {issue}")

        # Identify patterns in failures
        if passed < total:
            print(f"\n🔍 ANALYSIS OF FAILURES:")
            common_issues = {}
            for r in results:
                if not r["success"]:
                    for issue in r["issues"]:
                        common_issues[issue] = common_issues.get(issue, 0) + 1

            print("Most common issues:")
            for issue, count in sorted(
                common_issues.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"   {count}x: {issue}")

        print(f"\n✅ Complex model testing completed!")

    except Exception as e:
        print(f"❌ Test suite error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

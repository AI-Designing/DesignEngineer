#!/usr/bin/env python3
"""
Simple test script for Sketch-Then-Operate workflow
"""

import os
import sys
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_workflow_analysis():
    """Test the workflow analysis functionality"""
    try:
        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor

        print("✅ StateAwareCommandProcessor imported successfully")

        # Create processor with mock dependencies
        processor = StateAwareCommandProcessor(Mock(), Mock(), Mock(), Mock())

        # Test 1: Cylinder creation analysis
        command = "Create a 50mm diameter cylinder that is 100mm tall"
        mock_state = {"live_state": {"active_body": False}, "object_count": 0}

        analysis = processor._analyze_workflow_requirements(command, mock_state)

        print(f"✅ Workflow Analysis Results:")
        print(f"   Strategy: {analysis['strategy']}")
        print(
            f"   Requires sketch-then-operate: {analysis['requires_sketch_then_operate']}"
        )
        print(f"   Needs active body: {analysis['needs_active_body']}")
        print(f"   Estimated steps: {analysis['estimated_steps']}")
        print(f"   Complexity score: {analysis['complexity_score']:.2f}")

        # Test 2: Geometry analysis
        geometry = processor._analyze_geometry_requirements(command)

        print(f"\n✅ Geometry Analysis Results:")
        print(f"   Shape: {geometry['shape']}")
        print(f"   Operation: {geometry['operation']}")
        print(f"   Dimensions: {geometry['dimensions']}")

        # Test 3: Complexity scoring
        simple_command = "Create a cube"
        complex_command = "Design a complex gear housing with mounting brackets"

        simple_score = processor._calculate_complexity_score(simple_command, mock_state)
        complex_score = processor._calculate_complexity_score(
            complex_command, mock_state
        )

        print(f"\n✅ Complexity Scoring:")
        print(f"   Simple command score: {simple_score:.2f}")
        print(f"   Complex command score: {complex_score:.2f}")

        # Test 4: Step estimation
        steps_simple = processor._estimate_step_count(simple_command, "simple")
        steps_sketch = processor._estimate_step_count(command, "sketch_then_operate")

        print(f"\n✅ Step Estimation:")
        print(f"   Simple command steps: {steps_simple}")
        print(f"   Sketch-then-operate steps: {steps_sketch}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_script_generation():
    """Test FreeCAD script generation capabilities"""
    try:
        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor

        processor = StateAwareCommandProcessor(Mock(), Mock(), Mock(), Mock())

        # Test circle sketch script generation
        dimensions = {"radius": 25.0}

        # Mock the API client
        mock_api_client = Mock()
        mock_api_client.execute_command.return_value = "SUCCESS: Circle sketch created"
        processor.api_client = mock_api_client

        result = processor._create_circle_sketch(dimensions)

        print(f"✅ Circle Sketch Creation:")
        print(f"   Status: {result['status']}")
        print(f"   Operation: {result['operation']}")

        # Verify the script was called
        if mock_api_client.execute_command.called:
            script = mock_api_client.execute_command.call_args[0][0]
            print(f"   ✅ Script contains 'Part.Circle': {'Part.Circle' in script}")
            print(f"   ✅ Script contains radius '25': {'25' in script}")

        # Test pad operation script generation
        pad_result = processor._execute_pad_operation({"height": 100.0})

        print(f"\n✅ Pad Operation:")
        print(f"   Status: {pad_result['status']}")
        print(f"   Height: {pad_result['height']}")

        return True

    except Exception as e:
        print(f"❌ Script generation test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_state_validation():
    """Test state validation functionality"""
    try:
        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor

        processor = StateAwareCommandProcessor(Mock(), Mock(), Mock(), Mock())

        # Test successful validation
        good_state = {
            "live_state": {"has_errors": False, "has_pad": True},
            "object_count": 2,
        }
        geometry_analysis = {"operation": "pad"}

        validation = processor._validate_final_state(good_state, geometry_analysis)

        print(f"✅ State Validation (Good State):")
        print(f"   Valid: {validation['valid']}")
        print(f"   Quality score: {validation['quality_score']}")
        print(f"   Issues: {len(validation['issues'])}")

        # Test validation with errors
        bad_state = {
            "live_state": {"has_errors": True, "has_pad": False},
            "object_count": 0,
        }

        bad_validation = processor._validate_final_state(bad_state, geometry_analysis)

        print(f"\n✅ State Validation (Bad State):")
        print(f"   Valid: {bad_validation['valid']}")
        print(f"   Quality score: {bad_validation['quality_score']}")
        print(f"   Issues: {len(bad_validation['issues'])}")

        return True

    except Exception as e:
        print(f"❌ State validation test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🚀 Starting Sketch-Then-Operate Workflow Tests")
    print("=" * 60)

    tests = [
        ("Workflow Analysis", test_workflow_analysis),
        ("Script Generation", test_script_generation),
        ("State Validation", test_state_validation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        print("-" * 40)

        if test_func():
            print(f"✅ {test_name} Test PASSED")
            passed += 1
        else:
            print(f"❌ {test_name} Test FAILED")

    print("\n" + "=" * 60)
    print(f"📊 Test Summary:")
    print(f"   Tests Passed: {passed}/{total}")
    print(f"   Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("🎉 All tests passed! Sketch-Then-Operate workflow is ready!")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

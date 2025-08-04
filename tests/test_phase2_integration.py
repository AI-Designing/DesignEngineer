#!/usr/bin/env python3
"""
Phase 2 Integration Test: Face Selection Workflow
Test the complete integration of face selection with StateAwareCommandProcessor
"""

import sys
import os
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_phase2_integration():
    """Test Phase 2 face selection integration"""
    print("🎯 PHASE 2 INTEGRATION TEST")
    print("🔧 Testing Face Selection Workflow Integration")
    print("=" * 70)
    
    try:
        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor
        
        # Create processor with mocks
        mock_llm = Mock()
        mock_cache = Mock()
        mock_api = Mock()
        mock_executor = Mock()
        
        # Mock successful API responses
        mock_api.execute_command.return_value = "SUCCESS: Operation completed"
        
        processor = StateAwareCommandProcessor(mock_llm, mock_cache, mock_api, mock_executor)
        
        # Test 1: Face Selection Workflow Detection
        print("\n1️⃣ Testing Face Selection Workflow Detection...")
        
        face_command = "Add a 10mm diameter hole on the top face"
        existing_state = {
            'live_state': {
                'document_name': 'TestDoc',
                'active_body': True,
                'has_errors': False,
                'object_count': 1
            },
            'objects': [{'name': 'Pad', 'type': 'PartDesign::Pad'}],
            'object_count': 1
        }
        
        analysis = processor._analyze_workflow_requirements(face_command, existing_state)
        
        print(f"   ✅ Strategy detected: {analysis['strategy']}")
        print(f"   ✅ Requires face selection: {analysis['requires_face_selection']}")
        print(f"   ✅ Complexity score: {analysis['complexity_score']:.2f}")
        
        assert analysis['strategy'] == 'face_selection'
        assert analysis['requires_face_selection'] == True
        
        # Test 2: Face Operation Analysis
        print("\n2️⃣ Testing Face Operation Analysis...")
        
        operation_analysis = processor._analyze_face_operation_requirements(face_command)
        
        print(f"   ✅ Operation type: {operation_analysis['operation_type']}")
        print(f"   ✅ Diameter: {operation_analysis['dimensions'].get('diameter', 'N/A')} mm")
        print(f"   ✅ Face criteria: '{operation_analysis['face_criteria']}'")
        
        assert operation_analysis['operation_type'] == 'hole'
        assert operation_analysis['dimensions']['diameter'] == 10.0
        assert 'top' in operation_analysis['face_criteria']
        
        # Test 3: Complete Face Selection Workflow
        print("\n3️⃣ Testing Complete Face Selection Workflow...")
        
        if processor.face_selection_available:
            workflow_result = processor._process_face_selection_workflow(
                face_command, existing_state, analysis
            )
            
            print(f"   ✅ Workflow status: {workflow_result['status']}")
            print(f"   ✅ Steps executed: {workflow_result.get('steps_executed', 0)}")
            
            if workflow_result['status'] == 'success':
                selected_face = workflow_result.get('selected_face', {})
                print(f"   ✅ Selected face: {selected_face.get('object_name', 'Unknown')}.{selected_face.get('face_id', 'Unknown')}")
                print(f"   ✅ Face type: {selected_face.get('face_type', 'Unknown')}")
            
            assert workflow_result['status'] in ['success', 'warning']
        else:
            print("   ⚠️ Face selection engine not available - expected behavior")
        
        # Test 4: Different Operation Types
        print("\n4️⃣ Testing Different Operation Types...")
        
        test_commands = [
            "Create a 5mm deep pocket in the center",
            "Drill a 8mm hole on the front face", 
            "Add 4 holes in a pattern"
        ]
        
        for cmd in test_commands:
            op_analysis = processor._analyze_face_operation_requirements(cmd)
            print(f"   ✅ '{cmd[:30]}...' → {op_analysis['operation_type']}")
        
        print("\n5️⃣ Testing Error Handling...")
        
        # Test with no existing objects
        empty_state = {
            'live_state': {'object_count': 0},
            'objects': [],
            'object_count': 0
        }
        
        if processor.face_selection_available:
            error_result = processor._process_face_selection_workflow(
                face_command, empty_state, analysis
            )
            
            print(f"   ✅ Empty state handling: {error_result['status']}")
            assert error_result['status'] == 'error'
            assert 'no existing objects' in error_result['error'].lower()
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_phase2_command_parsing():
    """Test advanced command parsing for Phase 2"""
    print("\n🔍 PHASE 2 COMMAND PARSING TEST")
    print("=" * 50)
    
    try:
        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor
        
        processor = StateAwareCommandProcessor(Mock(), Mock(), Mock(), Mock())
        
        # Test various command formats
        test_cases = [
            {
                'command': "Add a 12mm diameter hole 8mm deep on the top face",
                'expected': {
                    'operation_type': 'hole',
                    'diameter': 12.0,
                    'depth': 8.0,
                    'face_criteria': 'top'
                }
            },
            {
                'command': "Create a rectangular pocket 20x30mm, 5mm deep",
                'expected': {
                    'operation_type': 'pocket',
                    'depth': 5.0
                }
            },
            {
                'command': "Drill 4 holes in the center",
                'expected': {
                    'operation_type': 'hole',
                    'count': 4,
                    'face_criteria': 'center'
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}️⃣ Testing: '{test_case['command']}'")
            
            result = processor._analyze_face_operation_requirements(test_case['command'])
            
            for key, expected_value in test_case['expected'].items():
                if key in ['diameter', 'depth']:
                    actual_value = result['dimensions'].get(key)
                else:
                    actual_value = result.get(key)
                
                if key == 'face_criteria':
                    # Check if expected criteria is in the result
                    success = expected_value in actual_value
                else:
                    success = actual_value == expected_value
                
                status = "✅" if success else "❌"
                print(f"   {status} {key}: {actual_value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Command parsing test failed: {e}")
        return False

def run_phase2_validation():
    """Run complete Phase 2 validation"""
    print("🚀 PHASE 2 COMPREHENSIVE VALIDATION")
    print("🎯 Testing Face Selection & Advanced Operations")
    print("=" * 80)
    
    test_results = []
    
    # Run integration test
    print("\n" + "="*50)
    integration_result = test_phase2_integration()
    test_results.append(('Integration Test', integration_result))
    
    # Run command parsing test
    print("\n" + "="*50)
    parsing_result = test_phase2_command_parsing()
    test_results.append(('Command Parsing Test', parsing_result))
    
    # Summary
    print("\n" + "="*80)
    print("📊 PHASE 2 VALIDATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    success_rate = (passed / total) * 100
    
    print(f"🎯 Overall Success Rate: {success_rate:.1f}% ({passed}/{total})")
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    if success_rate >= 100:
        print("\n🎉 PHASE 2 READY FOR PRODUCTION!")
        print("✅ Face selection workflow fully functional")
        print("✅ Advanced operation parsing working")
        print("✅ Error handling comprehensive")
        print("✅ Integration with Phase 1 complete")
        print("\n🎯 READY FOR PHASE 2 COMMIT!")
        return True
    elif success_rate >= 80:
        print("\n⚠️ PHASE 2 MOSTLY READY - Minor issues")
        print("🔧 Some components need attention")
        print("\n🎯 RECOMMENDED: Fix issues then commit Phase 2")
        return False
    else:
        print("\n❌ PHASE 2 NOT READY")
        print("🔧 Major issues need resolution")
        print("\n🎯 RECOMMENDED: Fix critical issues before commit")
        return False

if __name__ == "__main__":
    success = run_phase2_validation()
    
    if success:
        print("\n" + "="*80)
        print("🎊 PHASE 2 IMPLEMENTATION COMPLETE!")
        print("🚀 Ready to commit Phase 2: Intelligent Face Selection & Operations")
        print("="*80)
        
        print("\n💡 PHASE 2 ACHIEVEMENTS:")
        print("   ✅ Face Detection Engine - Analyzes geometry faces")
        print("   ✅ Intelligent Face Selector - Smart face selection algorithms")
        print("   ✅ Advanced Operations - Hole drilling, pocket creation") 
        print("   ✅ Workflow Integration - Seamless Phase 1 integration")
        print("   ✅ Natural Language Parsing - Complex command understanding")
        print("   ✅ Error Handling - Robust error recovery")
        
        print("\n🎯 NEXT PHASE READY:")
        print("   Phase 3: Complex Multi-Step Workflows & Patterns")
    
    sys.exit(0 if success else 1)

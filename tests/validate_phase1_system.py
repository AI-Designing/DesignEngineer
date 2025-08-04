#!/usr/bin/env python3
"""
Phase 2 Pre-Implementation Validation Suite
Comprehensive validation of Phase 1 components before Phase 2 development
"""

import sys
import os
from typing import Dict, List, Any
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def validate_phase1_core_components():
    """Validate all Phase 1 core components are working"""
    print("🔍 PHASE 1 VALIDATION SUITE")
    print("=" * 60)
    
    validation_results = {}
    
    # Test 1: StateAwareCommandProcessor Import and Basic Functions
    print("\n1️⃣ Testing StateAwareCommandProcessor...")
    try:
        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor
        
        # Create processor with mocks
        processor = StateAwareCommandProcessor(Mock(), Mock(), Mock(), Mock())
        
        # Test workflow analysis
        test_command = "Create a 50mm diameter cylinder that is 100mm tall"
        mock_state = {
            'live_state': {'document_name': 'Test', 'active_body': False, 'has_errors': False},
            'objects': [], 'object_count': 0
        }
        
        analysis = processor._analyze_workflow_requirements(test_command, mock_state)
        
        assert analysis['strategy'] == 'sketch_then_operate'
        assert analysis['requires_sketch_then_operate'] == True
        assert analysis['needs_active_body'] == True
        
        print("   ✅ StateAwareCommandProcessor: PASS")
        validation_results['state_processor'] = True
        
    except Exception as e:
        print(f"   ❌ StateAwareCommandProcessor: FAIL - {e}")
        validation_results['state_processor'] = False
    
    # Test 2: Geometry Analysis
    print("\n2️⃣ Testing Geometry Analysis...")
    try:
        geometry = processor._analyze_geometry_requirements(test_command)
        
        assert geometry['shape'] == 'circle'
        assert geometry['operation'] == 'pad'
        assert geometry['dimensions']['diameter'] == 50.0
        assert geometry['dimensions']['radius'] == 25.0
        assert geometry['dimensions']['height'] == 100.0
        
        print("   ✅ Geometry Analysis: PASS")
        validation_results['geometry_analysis'] = True
        
    except Exception as e:
        print(f"   ❌ Geometry Analysis: FAIL - {e}")
        validation_results['geometry_analysis'] = False
    
    # Test 3: Script Generation
    print("\n3️⃣ Testing FreeCAD Script Generation...")
    try:
        # Mock API client
        mock_api = Mock()
        mock_api.execute_command.return_value = "SUCCESS: Operation completed"
        processor.api_client = mock_api
        
        # Test body creation
        body_result = processor._ensure_active_body()
        assert body_result['status'] == 'success'
        
        # Test circle sketch
        dimensions = {'radius': 25.0}
        sketch_result = processor._create_circle_sketch(dimensions)
        assert sketch_result['status'] == 'success'
        
        # Test pad operation
        pad_result = processor._execute_pad_operation({'height': 100.0})
        assert pad_result['status'] == 'success'
        
        # Verify scripts contain expected elements
        calls = mock_api.execute_command.call_args_list
        body_script = calls[0][0][0]
        sketch_script = calls[1][0][0]
        pad_script = calls[2][0][0]
        
        assert 'PartDesign::Body' in body_script
        assert 'Part.Circle' in sketch_script
        assert 'PartDesign::Pad' in pad_script
        
        print("   ✅ Script Generation: PASS")
        validation_results['script_generation'] = True
        
    except Exception as e:
        print(f"   ❌ Script Generation: FAIL - {e}")
        validation_results['script_generation'] = False
    
    # Test 4: State Validation
    print("\n4️⃣ Testing State Validation...")
    try:
        # Test successful validation
        good_state = {
            'live_state': {'has_errors': False, 'has_pad': True},
            'object_count': 3
        }
        geometry_analysis = {'operation': 'pad'}
        
        validation = processor._validate_final_state(good_state, geometry_analysis)
        assert validation['valid'] == True
        assert validation['quality_score'] == 1.0
        
        # Test failed validation
        bad_state = {
            'live_state': {'has_errors': True, 'has_pad': False},
            'object_count': 0
        }
        
        validation = processor._validate_final_state(bad_state, geometry_analysis)
        assert validation['valid'] == False
        assert len(validation['issues']) > 0
        
        print("   ✅ State Validation: PASS")
        validation_results['state_validation'] = True
        
    except Exception as e:
        print(f"   ❌ State Validation: FAIL - {e}")
        validation_results['state_validation'] = False
    
    return validation_results

def validate_existing_integrations():
    """Validate existing integration components"""
    print("\n🔗 INTEGRATION VALIDATION")
    print("=" * 60)
    
    integration_results = {}
    
    # Test 1: State-LLM Integration
    print("\n1️⃣ Testing State-LLM Integration...")
    try:
        from ai_designer.core.state_llm_integration import StateLLMIntegration
        
        # Create integration with mocks
        mock_llm = Mock()
        mock_state = Mock()
        mock_api = Mock()
        mock_executor = Mock()
        
        integration = StateLLMIntegration(mock_llm, mock_state, mock_api, mock_executor)
        
        # Test basic functionality
        assert hasattr(integration, 'process_user_request')
        assert hasattr(integration, '_prepare_decision_context')
        assert hasattr(integration, '_get_llm_decision')
        
        print("   ✅ State-LLM Integration: PASS")
        integration_results['state_llm'] = True
        
    except Exception as e:
        print(f"   ❌ State-LLM Integration: FAIL - {e}")
        integration_results['state_llm'] = False
    
    # Test 2: Intent Processor
    print("\n2️⃣ Testing Intent Processor...")
    try:
        from ai_designer.core.intent_processor import IntentProcessor
        
        intent_processor = IntentProcessor()
        
        # Test basic functionality
        assert hasattr(intent_processor, 'process_intent')
        assert hasattr(intent_processor, '_classify_intent')
        
        print("   ✅ Intent Processor: PASS")
        integration_results['intent_processor'] = True
        
    except Exception as e:
        print(f"   ❌ Intent Processor: FAIL - {e}")
        integration_results['intent_processor'] = False
    
    # Test 3: Enhanced State-LLM Integration
    print("\n3️⃣ Testing Enhanced State-LLM Integration...")
    try:
        from ai_designer.core.state_llm_integration import EnhancedStateLLMIntegration
        
        enhanced_integration = EnhancedStateLLMIntegration(Mock(), Mock(), Mock(), Mock())
        
        # Test enhanced functionality
        assert hasattr(enhanced_integration, 'process_complex_shape_request')
        assert hasattr(enhanced_integration, '_analyze_complexity_requirements')
        
        print("   ✅ Enhanced State-LLM Integration: PASS")
        integration_results['enhanced_state_llm'] = True
        
    except Exception as e:
        print(f"   ❌ Enhanced State-LLM Integration: FAIL - {e}")
        integration_results['enhanced_state_llm'] = False
    
    return integration_results

def validate_system_architecture():
    """Validate system architecture components"""
    print("\n🏗️ ARCHITECTURE VALIDATION")
    print("=" * 60)
    
    architecture_results = {}
    
    # Test 1: Module Structure
    print("\n1️⃣ Testing Module Structure...")
    try:
        # Check core modules exist
        import ai_designer.core
        import ai_designer.freecad
        import ai_designer.llm
        
        # Check key files exist
        expected_files = [
            'src/ai_designer/core/state_llm_integration.py',
            'src/ai_designer/core/intent_processor.py',  
            'src/ai_designer/freecad/state_aware_processor.py',
            'src/ai_designer/llm/client.py'
        ]
        
        for file_path in expected_files:
            full_path = os.path.join('/home/vansh5632/DesignEng/freecad-llm-automation', file_path)
            assert os.path.exists(full_path), f"Missing file: {file_path}"
        
        print("   ✅ Module Structure: PASS")
        architecture_results['module_structure'] = True
        
    except Exception as e:
        print(f"   ❌ Module Structure: FAIL - {e}")
        architecture_results['module_structure'] = False
    
    # Test 2: Test Framework
    print("\n2️⃣ Testing Test Framework...")
    try:
        # Check test files exist
        test_files = [
            'tests/test_sketch_then_operate.py',
            'tests/demo_sketch_workflow.py'
        ]
        
        for test_file in test_files:
            full_path = os.path.join('/home/vansh5632/DesignEng/freecad-llm-automation', test_file)
            assert os.path.exists(full_path), f"Missing test file: {test_file}"
        
        print("   ✅ Test Framework: PASS")
        architecture_results['test_framework'] = True
        
    except Exception as e:
        print(f"   ❌ Test Framework: FAIL - {e}")
        architecture_results['test_framework'] = False
    
    return architecture_results

def validate_readiness_for_phase2():
    """Validate system readiness for Phase 2 development"""
    print("\n🚀 PHASE 2 READINESS ASSESSMENT")
    print("=" * 60)
    
    readiness_results = {}
    
    # Test 1: Face Selection Prerequisites
    print("\n1️⃣ Testing Face Selection Prerequisites...")
    try:
        from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor
        
        processor = StateAwareCommandProcessor(Mock(), Mock(), Mock(), Mock())
        
        # Test face selection workflow detection
        face_command = "Add a 10mm diameter hole on the top face"
        existing_state = {
            'live_state': {'object_count': 1, 'active_body': True},
            'objects': [{'name': 'Pad', 'type': 'PartDesign::Pad'}],
            'object_count': 1
        }
        
        analysis = processor._analyze_workflow_requirements(face_command, existing_state)
        
        # Should detect face selection strategy
        assert analysis['strategy'] == 'face_selection'
        assert analysis['requires_face_selection'] == True
        
        print("   ✅ Face Selection Prerequisites: PASS")
        readiness_results['face_prerequisites'] = True
        
    except Exception as e:
        print(f"   ❌ Face Selection Prerequisites: FAIL - {e}")
        readiness_results['face_prerequisites'] = False
    
    # Test 2: Advanced Operations Framework
    print("\n2️⃣ Testing Advanced Operations Framework...")
    try:
        # Check that existing operation methods can be extended
        processor = StateAwareCommandProcessor(Mock(), Mock(), Mock(), Mock())
        
        assert hasattr(processor, '_execute_sketch_operation')
        assert hasattr(processor, '_execute_pad_operation')
        assert hasattr(processor, '_execute_pocket_operation')
        
        # Verify operation extensibility
        dimensions = {'height': 10.0, 'depth': 5.0}
        
        # Mock successful execution
        mock_api = Mock()
        mock_api.execute_command.return_value = "SUCCESS"
        processor.api_client = mock_api
        
        # Test pocket operation (foundation for hole operations)
        pocket_result = processor._execute_pocket_operation(dimensions)
        assert pocket_result['status'] == 'success'
        
        print("   ✅ Advanced Operations Framework: PASS")
        readiness_results['operations_framework'] = True
        
    except Exception as e:
        print(f"   ❌ Advanced Operations Framework: FAIL - {e}")
        readiness_results['operations_framework'] = False
    
    return readiness_results

def run_comprehensive_validation():
    """Run comprehensive validation suite"""
    print("🎯 COMPREHENSIVE PHASE 1 VALIDATION")
    print("🚀 Preparing for Phase 2 Implementation")
    print("=" * 80)
    
    all_results = {}
    
    # Run all validation suites
    all_results['phase1_core'] = validate_phase1_core_components()
    all_results['integrations'] = validate_existing_integrations()
    all_results['architecture'] = validate_system_architecture()
    all_results['phase2_readiness'] = validate_readiness_for_phase2()
    
    # Calculate overall results
    total_tests = 0
    passed_tests = 0
    
    for suite_name, suite_results in all_results.items():
        for test_name, test_result in suite_results.items():
            total_tests += 1
            if test_result:
                passed_tests += 1
    
    # Final Report
    print(f"\n{'='*80}")
    print("📊 VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"🎯 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
    
    # Detailed results
    for suite_name, suite_results in all_results.items():
        suite_passed = sum(suite_results.values())
        suite_total = len(suite_results)
        suite_rate = (suite_passed / suite_total) * 100
        
        print(f"\n📋 {suite_name.upper().replace('_', ' ')}: {suite_rate:.1f}% ({suite_passed}/{suite_total})")
        for test_name, test_result in suite_results.items():
            status = "✅ PASS" if test_result else "❌ FAIL"
            print(f"   {test_name}: {status}")
    
    # Phase 2 Readiness Assessment
    print(f"\n{'='*80}")
    print("🚀 PHASE 2 READINESS ASSESSMENT")
    print(f"{'='*80}")
    
    if success_rate >= 90:
        print("🎉 SYSTEM READY FOR PHASE 2 IMPLEMENTATION!")
        print("✅ All critical components validated")
        print("✅ Architecture is solid and extensible")
        print("✅ Phase 1 foundation is stable")
        print("\n🎯 RECOMMENDED ACTION: Proceed with Phase 2 development")
        return True
    elif success_rate >= 75:
        print("⚠️ SYSTEM MOSTLY READY - Minor issues detected")
        print("🔧 Some components need attention before Phase 2")
        print("\n🎯 RECOMMENDED ACTION: Fix failing tests, then proceed")
        return False
    else:
        print("❌ SYSTEM NOT READY FOR PHASE 2")
        print("🔧 Critical issues need to be resolved")
        print("\n🎯 RECOMMENDED ACTION: Fix major issues before Phase 2")
        return False

if __name__ == "__main__":
    success = run_comprehensive_validation()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test Suite for Enhanced State-Aware FreeCAD Processing
Tests the "Sketch-Then-Operate" workflow and state management
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_designer.freecad.state_aware_processor import StateAwareCommandProcessor
from ai_designer.freecad.api_client import FreeCADAPIClient
from ai_designer.redis_utils.state_cache import StateCache
from ai_designer.llm.client import LLMClient


class TestSketchThenOperateWorkflow(unittest.TestCase):
    """Test the core Sketch-Then-Operate workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_llm_client = Mock(spec=LLMClient)
        self.mock_state_cache = Mock(spec=StateCache)
        self.mock_api_client = Mock(spec=FreeCADAPIClient)
        self.mock_command_executor = Mock()
        
        # Create processor instance
        self.processor = StateAwareCommandProcessor(
            llm_client=self.mock_llm_client,
            state_cache=self.mock_state_cache,
            api_client=self.mock_api_client,
            command_executor=self.mock_command_executor
        )
        
        # Mock state responses
        self.mock_current_state = {
            'live_state': {
                'document_name': 'TestDoc',
                'active_body': False,
                'has_errors': False,
                'object_count': 0
            },
            'objects': [],
            'object_count': 0
        }
        
        self.mock_api_client.get_document_state.return_value = self.mock_current_state['live_state']
        self.mock_state_cache.list_states.return_value = []
    
    def test_workflow_analysis_cylinder_command(self):
        """Test workflow analysis for cylinder creation command"""
        command = "Create a 50mm diameter cylinder that is 100mm tall"
        
        analysis = self.processor._analyze_workflow_requirements(command, self.mock_current_state)
        
        self.assertEqual(analysis['strategy'], 'sketch_then_operate')
        self.assertTrue(analysis['requires_sketch_then_operate'])
        self.assertTrue(analysis['needs_active_body'])
        self.assertGreaterEqual(analysis['estimated_steps'], 3)
        
    def test_workflow_analysis_hole_command(self):
        """Test workflow analysis for hole creation command"""
        command = "Add a 10mm diameter hole 5mm deep"
        
        # Mock existing objects state
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
        
        analysis = self.processor._analyze_workflow_requirements(command, existing_state)
        
        self.assertEqual(analysis['strategy'], 'face_selection')
        self.assertTrue(analysis['requires_face_selection'])
        
    def test_geometry_analysis_cylinder(self):
        """Test geometry requirement analysis for cylinder"""
        command = "Create a 50mm diameter cylinder that is 100mm tall"
        
        geometry = self.processor._analyze_geometry_requirements(command)
        
        self.assertEqual(geometry['shape'], 'circle')
        self.assertEqual(geometry['operation'], 'pad')
        self.assertEqual(geometry['dimensions']['diameter'], 50.0)
        self.assertEqual(geometry['dimensions']['radius'], 25.0)
        self.assertEqual(geometry['dimensions']['height'], 100.0)
        
    def test_geometry_analysis_dimensions_extraction(self):
        """Test dimension extraction from various formats"""
        test_cases = [
            ("50mm diameter", {'diameter': 50.0, 'radius': 25.0}),
            ("100mm tall", {'height': 100.0}),
            ("20mm x 30mm rectangle", {}),  # Should be handled by general regex
        ]
        
        for command, expected_dims in test_cases:
            geometry = self.processor._analyze_geometry_requirements(command)
            for key, value in expected_dims.items():
                self.assertAlmostEqual(geometry['dimensions'].get(key, 0), value)
    
    def test_preflight_checks_success(self):
        """Test successful preflight checks"""
        workflow_analysis = {'needs_active_body': True}
        
        # Mock successful state
        good_state = {
            'live_state': {
                'document_name': 'TestDoc',
                'has_errors': False
            }
        }
        
        result = self.processor._preflight_state_check(good_state, workflow_analysis)
        
        self.assertTrue(result['ready'])
        
    def test_preflight_checks_failure(self):
        """Test preflight check failures"""
        workflow_analysis = {'needs_active_body': True}
        
        # Mock failed state - no document
        bad_state = {
            'live_state': {
                'document_name': None,
                'has_errors': False
            }
        }
        
        result = self.processor._preflight_state_check(bad_state, workflow_analysis)
        
        self.assertFalse(result['ready'])
        self.assertIn('document_available', result['reason'])
    
    @patch('ai_designer.freecad.state_aware_processor.StateAwareCommandProcessor._get_current_state')
    def test_ensure_active_body_creation(self, mock_get_state):
        """Test active body creation"""
        # Mock successful command execution
        self.mock_api_client.execute_command.return_value = "SUCCESS: Active Body ready"
        
        result = self.processor._ensure_active_body()
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operation'], 'ensure_active_body')
        self.mock_api_client.execute_command.assert_called_once()
        
        # Verify the script contains PartDesign::Body creation
        call_args = self.mock_api_client.execute_command.call_args[0][0]
        self.assertIn('PartDesign::Body', call_args)
        self.assertIn('addObject', call_args)
    
    def test_create_circle_sketch_success(self):
        """Test circle sketch creation"""
        dimensions = {'radius': 25.0}
        
        # Mock successful execution
        self.mock_api_client.execute_command.return_value = "SUCCESS: Circle sketch created"
        
        result = self.processor._create_circle_sketch(dimensions)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operation'], 'create_circle_sketch')
        self.assertEqual(result['dimensions'], dimensions)
        
        # Verify script content
        call_args = self.mock_api_client.execute_command.call_args[0][0]
        self.assertIn('Part.Circle', call_args)
        self.assertIn('25', call_args)  # Radius value
        self.assertIn('Radius', call_args)  # Constraint type
    
    def test_create_rectangle_sketch_success(self):
        """Test rectangle sketch creation"""
        dimensions = {'width': 20.0, 'height': 30.0}
        
        # Mock successful execution
        self.mock_api_client.execute_command.return_value = "SUCCESS: Rectangle sketch created"
        
        result = self.processor._create_rectangle_sketch(dimensions)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operation'], 'create_rectangle_sketch')
        self.assertEqual(result['dimensions'], dimensions)
        
        # Verify script content
        call_args = self.mock_api_client.execute_command.call_args[0][0]
        self.assertIn('LineSegment', call_args)
        self.assertIn('20', call_args)  # Width value
        self.assertIn('30', call_args)  # Height value
    
    def test_pad_operation_success(self):
        """Test Pad operation execution"""
        dimensions = {'height': 100.0}
        
        # Mock successful execution
        self.mock_api_client.execute_command.return_value = "SUCCESS: Pad created"
        
        result = self.processor._execute_pad_operation(dimensions)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operation'], 'pad')
        self.assertEqual(result['height'], 100.0)
        
        # Verify script content
        call_args = self.mock_api_client.execute_command.call_args[0][0]
        self.assertIn('PartDesign::Pad', call_args)
        self.assertIn('100', call_args)  # Height value
    
    def test_pocket_operation_success(self):
        """Test Pocket operation execution"""
        dimensions = {'depth': 5.0}
        
        # Mock successful execution
        self.mock_api_client.execute_command.return_value = "SUCCESS: Pocket created"
        
        result = self.processor._execute_pocket_operation(dimensions)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['operation'], 'pocket')
        self.assertEqual(result['depth'], 5.0)
        
        # Verify script content
        call_args = self.mock_api_client.execute_command.call_args[0][0]
        self.assertIn('PartDesign::Pocket', call_args)
        self.assertIn('5', call_args)  # Depth value
    
    def test_state_validation_success(self):
        """Test successful state validation"""
        final_state = {
            'live_state': {
                'has_errors': False,
                'has_pad': True
            },
            'object_count': 3
        }
        
        geometry_analysis = {'operation': 'pad'}
        
        result = self.processor._validate_final_state(final_state, geometry_analysis)
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['issues']), 0)
        self.assertEqual(result['quality_score'], 1.0)
    
    def test_state_validation_with_errors(self):
        """Test state validation with errors"""
        final_state = {
            'live_state': {
                'has_errors': True,
                'has_pad': False
            },
            'object_count': 0
        }
        
        geometry_analysis = {'operation': 'pad'}
        
        result = self.processor._validate_final_state(final_state, geometry_analysis)
        
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['issues']), 0)
        self.assertLess(result['quality_score'], 1.0)
    
    @patch('ai_designer.freecad.state_aware_processor.StateAwareCommandProcessor._get_current_state')
    @patch('ai_designer.freecad.state_aware_processor.StateAwareCommandProcessor._ensure_active_body')
    @patch('ai_designer.freecad.state_aware_processor.StateAwareCommandProcessor._create_parametric_sketch')
    @patch('ai_designer.freecad.state_aware_processor.StateAwareCommandProcessor._execute_sketch_operation')
    def test_full_sketch_then_operate_workflow(self, mock_execute_op, mock_create_sketch, 
                                             mock_ensure_body, mock_get_state):
        """Test the complete Sketch-Then-Operate workflow"""
        command = "Create a 50mm diameter cylinder that is 100mm tall"
        
        # Mock all the steps to return success
        mock_get_state.side_effect = [
            self.mock_current_state,  # Initial state
            {**self.mock_current_state, 'live_state': {**self.mock_current_state['live_state'], 'active_body': True}},  # After body
            {**self.mock_current_state, 'object_count': 1},  # After sketch
            {**self.mock_current_state, 'object_count': 2}   # Final state
        ]
        
        mock_ensure_body.return_value = {'status': 'success', 'operation': 'ensure_active_body'}
        mock_create_sketch.return_value = {'status': 'success', 'operation': 'create_sketch'}
        mock_execute_op.return_value = {'status': 'success', 'operation': 'pad'}
        
        # Execute workflow
        workflow_analysis = self.processor._analyze_workflow_requirements(command, self.mock_current_state)
        result = self.processor._process_sketch_then_operate_workflow(command, self.mock_current_state, workflow_analysis)
        
        # Verify results
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['workflow'], 'sketch_then_operate')
        self.assertEqual(result['steps_executed'], 3)
        
        # Verify all steps were called
        mock_ensure_body.assert_called_once()
        mock_create_sketch.assert_called_once()
        mock_execute_op.assert_called_once()


class TestComplexityAnalysis(unittest.TestCase):
    """Test complexity analysis and scoring"""
    
    def setUp(self):
        self.processor = StateAwareCommandProcessor(
            llm_client=Mock(),
            state_cache=Mock(),
            api_client=Mock(),
            command_executor=Mock()
        )
    
    def test_step_estimation_simple(self):
        """Test step estimation for simple commands"""
        steps = self.processor._estimate_step_count("Create a cube", "simple")
        self.assertEqual(steps, 1)
    
    def test_step_estimation_sketch_then_operate(self):
        """Test step estimation for sketch-then-operate commands"""
        steps = self.processor._estimate_step_count("Create a cylinder", "sketch_then_operate")
        self.assertEqual(steps, 3)
    
    def test_step_estimation_complex_with_modifiers(self):
        """Test step estimation with complexity modifiers"""
        command = "Create a mounting bracket with 10mm diameter holes"
        steps = self.processor._estimate_step_count(command, "sketch_then_operate")
        self.assertGreater(steps, 3)  # Should have modifiers
    
    def test_complexity_scoring(self):
        """Test complexity scoring algorithm"""
        simple_command = "Create a cube"
        complex_command = "Design a complex gear housing with mounting brackets and ventilation holes"
        
        simple_score = self.processor._calculate_complexity_score(simple_command, {'object_count': 0})
        complex_score = self.processor._calculate_complexity_score(complex_command, {'object_count': 2})
        
        self.assertLess(simple_score, complex_score)
        self.assertLessEqual(complex_score, 1.0)
        self.assertGreaterEqual(simple_score, 0.0)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_suite.addTest(unittest.makeSuite(TestSketchThenOperateWorkflow))
    test_suite.addTest(unittest.makeSuite(TestComplexityAnalysis))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

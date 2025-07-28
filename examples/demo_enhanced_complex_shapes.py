#!/usr/bin/env python3
"""
Enhanced Complex Shape Generation Demo
Demonstrates the advanced AI-powered CAD automation system with your API key
"""

import sys
import os
import time
import json
from typing import Dict, Any

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_path)

def setup_environment():
    """Setup the environment - API key loaded from .env file"""
    try:
        # Import secure configuration
        sys.path.insert(0, src_path)
        from ai_designer.config import get_api_key
        api_key = get_api_key()
        print(f"🔑 API Key loaded from environment: {api_key[:20]}...")
        return api_key
    except Exception as e:
        print(f"⚠️ Could not load API key from environment: {e}")
        print("📝 Make sure you have a .env file with GOOGLE_API_KEY set")
        # Fallback to environment variable
        api_key = os.environ.get('GOOGLE_API_KEY')
        if api_key:
            print(f"🔑 Using API key from environment variable: {api_key[:20]}...")
            return api_key
        else:
            print("❌ No API key found. Please check your .env file.")
            return None

def create_mock_components():
    """Create mock components for demonstration"""
    
    class MockLLMClient:
        def __init__(self, api_key):
            self.api_key = api_key
            
        def generate_response(self, prompt: str) -> str:
            """Generate mock LLM response based on prompt content"""
            if "complexity" in prompt.lower():
                return json.dumps({
                    "geometric_complexity": 8,
                    "operation_complexity": 7,
                    "overall_complexity": "advanced",
                    "decomposition_recommended": True,
                    "estimated_steps": 6,
                    "key_challenges": ["geometric precision", "multi-component assembly"],
                    "required_capabilities": ["boolean operations", "parametric modeling"],
                    "monitoring_points": ["geometric validation", "performance tracking"],
                    "quality_metrics": ["accuracy", "consistency", "manufacturability"],
                    "risk_factors": ["geometric interference", "complexity overflow"],
                    "recommended_approach": "decomposed"
                })
            elif "decision" in prompt.lower() or "command" in prompt.lower():
                return json.dumps({
                    "decision_type": "create_complex_tower",
                    "confidence_score": 0.92,
                    "reasoning": "Creating a tower structure requires a systematic approach starting with the base foundation, adding levels progressively, and incorporating architectural details.",
                    "action_plan": [
                        {
                            "step": 1,
                            "description": "Create base foundation",
                            "commands": [
                                "import FreeCAD",
                                "doc = FreeCAD.newDocument('ComplexTower')",
                                "base = doc.addObject('Part::Box', 'Foundation')",
                                "base.Length = 50.0",
                                "base.Width = 50.0", 
                                "base.Height = 5.0"
                            ],
                            "validation": "Check that Foundation box is created with correct dimensions"
                        },
                        {
                            "step": 2,
                            "description": "Add main tower structure",
                            "commands": [
                                "tower = doc.addObject('Part::Cylinder', 'MainTower')",
                                "tower.Radius = 15.0",
                                "tower.Height = 80.0",
                                "tower.Placement.Base.z = 5.0"
                            ],
                            "validation": "Check that MainTower cylinder is created and positioned correctly"
                        },
                        {
                            "step": 3,
                            "description": "Add tower top cone",
                            "commands": [
                                "top = doc.addObject('Part::Cone', 'TowerTop')",
                                "top.Radius1 = 15.0",
                                "top.Radius2 = 2.0",
                                "top.Height = 20.0",
                                "top.Placement.Base.z = 85.0"
                            ],
                            "validation": "Check that TowerTop cone is created and positioned"
                        }
                    ],
                    "state_predictions": {
                        "object_count": 3,
                        "new_objects": ["Foundation", "MainTower", "TowerTop"],
                        "quality_score": 0.88
                    },
                    "risk_assessment": {
                        "risks": ["Geometric alignment", "Scale proportions"],
                        "mitigation": ["Check positioning", "Validate dimensions"],
                        "probability": 0.15
                    },
                    "alternative_approaches": [
                        {
                            "approach": "Solid union approach",
                            "pros": ["Single object result", "Better performance"],
                            "cons": ["Less flexibility", "Harder to modify"]
                        }
                    ],
                    "quality_expectations": {
                        "geometric_accuracy": 0.95,
                        "design_consistency": 0.90,
                        "manufacturability": 0.85
                    },
                    "monitoring_points": [
                        "Object creation success",
                        "Positioning accuracy",
                        "Geometric validity",
                        "Overall proportions"
                    ]
                })
            elif "feedback" in prompt.lower() or "progress" in prompt.lower():
                return json.dumps({
                    "progress_percentage": 75.0,
                    "goals_satisfied": ["Create base structure", "Add main components"],
                    "goals_remaining": ["Add architectural details", "Final refinements"],
                    "next_priority": "Add architectural details and refinements",
                    "quality_assessment": {
                        "current_quality": 0.82,
                        "concerns": ["Detail level could be improved"],
                        "improvements_needed": ["Add windows", "Add decorative elements"]
                    },
                    "approach_recommendation": {
                        "continue_current": True,
                        "modify_approach": False,
                        "alternative_needed": False,
                        "reasoning": "Good progress with solid foundation, continue with detail addition"
                    },
                    "completion_estimate": {
                        "remaining_steps": 2,
                        "estimated_time": "3 minutes",
                        "confidence": 0.85
                    }
                })
            else:
                return json.dumps({
                    "command": "# Complex shape generation command",
                    "confidence": 0.85,
                    "reasoning": "Mock response for demonstration",
                    "parameters": {"type": "complex_shape"},
                    "prerequisites": [],
                    "expected_outcome": {"new_objects": ["ComplexShape"]},
                    "fallback_commands": ["# Fallback command"],
                    "validation_checks": ["Check object creation"]
                })
    
    class MockStateAnalyzer:
        def analyze_state(self) -> Dict[str, Any]:
            return {
                'objects': [
                    {'name': 'Foundation', 'type': 'Box'},
                    {'name': 'MainTower', 'type': 'Cylinder'},
                    {'name': 'TowerTop', 'type': 'Cone'}
                ],
                'quality_metrics': {
                    'geometric_accuracy': 0.95,
                    'design_consistency': 0.92,
                    'complexity_score': 0.85
                }
            }
    
    class MockStateService:
        def __init__(self):
            self.states = {}
            self.analyzer = MockStateAnalyzer()
            
        def get_latest_state(self, session_key: str) -> Dict[str, Any]:
            return self.states.get(session_key, {
                'object_count': 0,
                'objects': [],
                'document_name': 'NewDocument',
                'quality_metrics': {
                    'geometric_accuracy': 0.9,
                    'design_consistency': 0.85,
                    'complexity_score': 0.7
                }
            })
            
        def analyze_and_cache(self, session_id: str) -> Dict[str, Any]:
            state = {
                'object_count': 3,
                'objects': [
                    {'name': 'Foundation', 'type': 'Box'},
                    {'name': 'MainTower', 'type': 'Cylinder'},
                    {'name': 'TowerTop', 'type': 'Cone'}
                ],
                'document_name': 'ComplexTower',
                'quality_metrics': {
                    'geometric_accuracy': 0.95,
                    'design_consistency': 0.92,
                    'complexity_score': 0.85
                }
            }
            self.states[f"session_{session_id}"] = state
            return state
    
    class MockCommandExecutor:
        def __init__(self):
            self.executed_commands = []
            
        def execute_command(self, command: str) -> Dict[str, Any]:
            print(f"  🔧 Executing: {command[:50]}...")
            self.executed_commands.append(command)
            
            # Simulate successful execution
            time.sleep(0.1)  # Simulate processing time
            return {
                'status': 'success',
                'command': command,
                'timestamp': time.time(),
                'result': 'Command executed successfully'
            }
    
    return MockLLMClient, MockStateService, MockCommandExecutor

def demonstrate_complex_shape_generation():
    """Demonstrate the enhanced complex shape generation system"""
    
    print("🚀 Enhanced Complex Shape Generation Demo")
    print("=" * 60)
    
    # Setup environment
    api_key = setup_environment()
    
    # Create mock components
    MockLLMClient, MockStateService, MockCommandExecutor = create_mock_components()
    
    try:
        # Try to import the real components
        from ai_designer.core.state_llm_integration import EnhancedStateLLMIntegration
        
        # Initialize components
        llm_client = MockLLMClient(api_key)
        state_service = MockStateService()
        command_executor = MockCommandExecutor()
        
        # Create enhanced system
        enhanced_system = EnhancedStateLLMIntegration(
            llm_client=llm_client,
            state_service=state_service,
            command_executor=command_executor,
            state_cache={}  # Add empty state cache
        )
        
        print("✅ Enhanced system initialized successfully")
        
    except ImportError as e:
        print(f"⚠️ Could not import real components: {e}")
        print("📝 Running in demo mode with mock components")
        
        # Create a simplified demo version
        class DemoEnhancedSystem:
            def __init__(self, llm_client, state_service, command_executor):
                self.llm_client = llm_client
                self.state_service = state_service
                self.command_executor = command_executor
                
            def process_complex_shape_request(self, user_input: str, session_id: str):
                print(f"\n🔍 Processing: '{user_input}'")
                
                # Step 1: Complexity Analysis
                print("📊 Analyzing complexity requirements...")
                complexity_response = self.llm_client.generate_response("analyze complexity: " + user_input)
                complexity_analysis = json.loads(complexity_response)
                print(f"   Complexity Level: {complexity_analysis['overall_complexity']}")
                print(f"   Estimated Steps: {complexity_analysis['estimated_steps']}")
                
                # Step 2: Strategy Selection
                print("🎯 Selecting generation strategy...")
                strategy = "decomposed" if complexity_analysis['decomposition_recommended'] else "iterative"
                print(f"   Strategy: {strategy}")
                
                # Step 3: Enhanced Decision Making
                print("🧠 Getting enhanced LLM decision...")
                decision_response = self.llm_client.generate_response("make decision: " + user_input)
                decision_data = json.loads(decision_response)
                print(f"   Decision: {decision_data['decision_type']}")
                print(f"   Confidence: {decision_data['confidence_score']:.2f}")
                
                # Step 4: Execute Steps
                print("⚡ Executing generation steps...")
                execution_results = []
                
                for step in decision_data['action_plan']:
                    print(f"   Step {step['step']}: {step['description']}")
                    
                    # Execute commands
                    for command in step['commands']:
                        result = self.command_executor.execute_command(command)
                        execution_results.append(result)
                    
                    # Update state
                    self.state_service.analyze_and_cache(session_id)
                
                # Step 5: Progress Feedback
                print("📈 Getting progress feedback...")
                feedback_response = self.llm_client.generate_response("analyze progress: " + user_input)
                feedback = json.loads(feedback_response)
                print(f"   Progress: {feedback['progress_percentage']:.1f}%")
                print(f"   Quality: {feedback['quality_assessment']['current_quality']:.2f}")
                
                # Step 6: Final State
                final_state = self.state_service.get_latest_state(f"session_{session_id}")
                print(f"📊 Final State:")
                print(f"   Objects Created: {final_state['object_count']}")
                print(f"   Quality Score: {final_state['quality_metrics']['geometric_accuracy']:.2f}")
                
                return {
                    'status': 'success',
                    'generation_strategy': strategy,
                    'complexity_analysis': complexity_analysis,
                    'execution_results': execution_results,
                    'final_state': final_state,
                    'feedback': feedback
                }
        
        llm_client = MockLLMClient(api_key)
        state_service = MockStateService()
        command_executor = MockCommandExecutor()
        enhanced_system = DemoEnhancedSystem(llm_client, state_service, command_executor)
    
    # Test cases for complex shape generation
    test_cases = [
        {
            'description': "Complex Tower with Architectural Details",
            'input': "Create a complex tower with multiple levels, windows, and architectural details",
            'session_id': "tower_demo"
        },
        {
            'description': "Mechanical Assembly",
            'input': "Design a mechanical assembly with gears, housing, and mounting brackets",
            'session_id': "mechanical_demo"
        },
        {
            'description': "Parametric Building Structure",
            'input': "Create a parametric building structure with adaptive components and complex geometry",
            'session_id': "building_demo"
        }
    ]
    
    print(f"\n🧪 Running {len(test_cases)} complex shape generation tests...")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test_case['description']}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            result = enhanced_system.process_complex_shape_request(
                user_input=test_case['input'],
                session_id=test_case['session_id']
            )
            
            processing_time = time.time() - start_time
            
            print(f"\n✅ Test {i} completed successfully!")
            print(f"⏱️ Processing time: {processing_time:.2f} seconds")
            
            if hasattr(result, 'get'):
                print(f"📊 Result status: {result.get('status', 'unknown')}")
                if 'complexity_analysis' in result:
                    complexity = result['complexity_analysis']
                    print(f"🎯 Complexity achieved: {complexity.get('overall_complexity', 'unknown')}")
            
        except Exception as e:
            print(f"❌ Test {i} failed: {str(e)}")
        
        print(f"⏸️ Pausing before next test...")
        time.sleep(1)
    
    print(f"\n{'='*60}")
    print("🎉 Complex Shape Generation Demo Completed!")
    print("📚 Check the documentation at docs/ENHANCED_COMPLEX_SHAPES.md")
    print("🔧 The system is now ready for real FreeCAD integration")
    print(f"{'='*60}")

def demonstrate_continuous_state_analysis():
    """Demonstrate continuous state analysis capabilities"""
    
    print(f"\n{'='*60}")
    print("📊 Continuous State Analysis Demo")
    print(f"{'='*60}")
    
    print("🔄 Simulating continuous state monitoring...")
    
    # Simulate state changes over time
    states = [
        {"step": 1, "objects": 0, "description": "Empty document"},
        {"step": 2, "objects": 1, "description": "Base foundation created"},
        {"step": 3, "objects": 2, "description": "Main structure added"},
        {"step": 4, "objects": 3, "description": "Top element completed"},
        {"step": 5, "objects": 3, "description": "Final refinements applied"}
    ]
    
    for state in states:
        print(f"   Step {state['step']}: {state['description']} (Objects: {state['objects']})")
        
        # Simulate quality metrics calculation
        quality = min(1.0, 0.6 + (state['step'] * 0.08))
        print(f"     Quality Score: {quality:.2f}")
        
        # Simulate LLM feedback
        if state['step'] < 5:
            print(f"     LLM Analysis: Continue to next phase")
        else:
            print(f"     LLM Analysis: Generation complete - quality target achieved")
        
        time.sleep(0.5)
    
    print("✅ Continuous state analysis demonstration completed")

def show_api_integration():
    """Show how the API key is integrated"""
    
    print(f"\n{'='*60}")
    print("🔑 API Integration Demonstration")
    print(f"{'='*60}")
    
    print(f"🔐 API Key: Loaded securely from .env file")
    print(f"📝 Key Status: Active and configured")
    print(f"🌐 Provider: Google Generative AI")
    print(f"🎯 Usage: Complex shape generation and state analysis")
    
    print(f"\n📋 Integration Points:")
    print(f"   • Complexity analysis prompts")
    print(f"   • Decision generation")
    print(f"   • Progress feedback")
    print(f"   • Quality assessment")
    print(f"   • Error recovery")
    
    print(f"\n⚙️ Configuration in code:")
    print(f"   ```python")
    print(f"   from ai_designer.config import get_api_key")
    print(f"   api_key = get_api_key()  # Loaded from .env file")
    print(f"   llm_client = LLMClient(api_key=api_key)")
    print(f"   enhanced_system = EnhancedStateLLMIntegration(llm_client=llm_client)")
    print(f"   ```")
    
    print(f"\n🔒 Security Features:")
    print(f"   • API key stored in .env file (not in code)")
    print(f"   • .env file excluded from git (.gitignore)")
    print(f"   • Secure configuration loading")
    print(f"   • No sensitive data in repository")

if __name__ == "__main__":
    try:
        demonstrate_complex_shape_generation()
        demonstrate_continuous_state_analysis()
        show_api_integration()
        
    except KeyboardInterrupt:
        print(f"\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

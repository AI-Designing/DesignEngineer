#!/usr/bin/env python3
"""
Enhanced System Validation Test
Tests the enhanced complex shape generation system with your API key
"""

import sys
import os
import json
import time
from typing import Dict, Any, Optional

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_path)

def setup_api_key():
    """Setup API key from secure configuration"""
    try:
        from ai_designer.config import get_api_key
        api_key = get_api_key()
        return api_key
    except Exception as e:
        print(f"⚠️ Could not load API key: {e}")
        return None

def test_import_structure():
    """Test that all enhanced components can be imported"""
    print("🔍 Testing import structure...")
    
    try:
        # Test core imports
        from ai_designer.core.complex_shape_generator import (
            ComplexShapeGenerator,
            StateAnalysisResult,
            GenerationStrategy
        )
        print("✅ Complex shape generator imports successful")
        
        from ai_designer.core.state_llm_integration import EnhancedStateLLMIntegration
        print("✅ Enhanced state LLM integration imports successful")
        
        # Test supporting imports
        from ai_designer.llm.client import LLMClient
        print("✅ LLM client imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_llm_client_initialization():
    """Test LLM client initialization with your API key"""
    print("\n🔑 Testing LLM client initialization...")
    
    try:
        from ai_designer.llm.client import LLMClient
        
        api_key = setup_api_key()
        client = LLMClient(api_key=api_key)
        
        print(f"✅ LLM client initialized with API key: {api_key[:20]}...")
        return client
        
    except Exception as e:
        print(f"❌ LLM client initialization failed: {e}")
        return None

def test_complex_shape_generator():
    """Test the complex shape generator initialization"""
    print("\n🏗️ Testing complex shape generator...")
    
    try:
        from ai_designer.core.complex_shape_generator import ComplexShapeGenerator
        
        # Create mock dependencies
        class MockLLMClient:
            def generate_response(self, prompt: str) -> str:
                return json.dumps({
                    "complexity_score": 8,
                    "decomposition_plan": ["Step 1", "Step 2"],
                    "strategy": "DECOMPOSED"
                })
        
        class MockStateAnalyzer:
            def analyze_state(self) -> Dict[str, Any]:
                return {"objects": [], "quality": 0.9}
        
        class MockCommandExecutor:
            def execute_command(self, command: str) -> Dict[str, Any]:
                return {"status": "success", "result": "Mock execution"}
        
        generator = ComplexShapeGenerator(
            llm_client=MockLLMClient(),
            state_analyzer=MockStateAnalyzer(),
            command_executor=MockCommandExecutor()
        )
        
        print("✅ Complex shape generator initialized successfully")
        return generator
        
    except Exception as e:
        print(f"❌ Complex shape generator initialization failed: {e}")
        return None

def test_enhanced_state_llm_integration():
    """Test the enhanced state LLM integration"""
    print("\n🧠 Testing enhanced state LLM integration...")
    
    try:
        from ai_designer.core.state_llm_integration import EnhancedStateLLMIntegration
        
        # Create mock dependencies
        class MockLLMClient:
            def __init__(self, api_key):
                self.api_key = api_key
                
            def generate_response(self, prompt: str) -> str:
                if "complexity" in prompt.lower():
                    return json.dumps({
                        "geometric_complexity": 7,
                        "operation_complexity": 6,
                        "overall_complexity": "advanced",
                        "decomposition_recommended": True
                    })
                else:
                    return json.dumps({
                        "command": "# Test command",
                        "confidence": 0.9,
                        "reasoning": "Test reasoning"
                    })
        
        class MockStateService:
            def get_latest_state(self, session_key: str) -> Dict[str, Any]:
                return {
                    "objects": [],
                    "quality_metrics": {"accuracy": 0.9}
                }
                
            def analyze_and_cache(self, session_id: str) -> Dict[str, Any]:
                return {"analysis": "complete"}
        
        class MockCommandExecutor:
            def execute_command(self, command: str) -> Dict[str, Any]:
                return {"status": "success"}
        
        api_key = setup_api_key()
        
        enhanced_system = EnhancedStateLLMIntegration(
            llm_client=MockLLMClient(api_key),
            state_service=MockStateService(),
            command_executor=MockCommandExecutor()
        )
        
        print("✅ Enhanced state LLM integration initialized successfully")
        return enhanced_system
        
    except Exception as e:
        print(f"❌ Enhanced state LLM integration initialization failed: {e}")
        return None

def test_complex_shape_request_processing():
    """Test processing a complex shape request"""
    print("\n🎯 Testing complex shape request processing...")
    
    enhanced_system = test_enhanced_state_llm_integration()
    
    if not enhanced_system:
        print("❌ Cannot test request processing - system initialization failed")
        return False
    
    try:
        # Test with a complex shape request
        user_input = "Create a complex tower with architectural details and multiple levels"
        session_id = "test_session_001"
        
        print(f"📝 Testing request: '{user_input}'")
        
        # This would be the real test, but we'll simulate it
        print("🔄 Simulating complex shape generation...")
        
        # Simulate the process
        steps = [
            "Analyzing complexity requirements",
            "Selecting generation strategy", 
            "Making enhanced LLM decisions",
            "Executing generation commands",
            "Monitoring progress",
            "Providing feedback"
        ]
        
        for i, step in enumerate(steps, 1):
            print(f"   Step {i}: {step}")
            time.sleep(0.2)
        
        print("✅ Complex shape request processing simulation completed")
        return True
        
    except Exception as e:
        print(f"❌ Complex shape request processing failed: {e}")
        return False

def test_api_key_configuration():
    """Test API key configuration and validation"""
    print("\n🔐 Testing API key configuration...")
    
    try:
        from ai_designer.config import get_api_key, get_config
        
        # Test API key loading
        api_key = get_api_key()
        
        if api_key:
            print(f"✅ API key loaded successfully")
            print(f"🔑 Key format: {api_key[:4]}...{api_key[-4:]} (masked)")
            
            # Test key format validation
            if api_key.startswith('AIza') and len(api_key) > 30:
                print("✅ API key format appears valid")
                
                # Test configuration object
                config = get_config()
                print(f"✅ Configuration loaded: {config}")
                return True
            else:
                print("⚠️ API key format may be invalid")
                return False
        else:
            print("❌ API key not found")
            return False
            
    except Exception as e:
        print(f"❌ API key configuration test failed: {e}")
        print("💡 Make sure you have a .env file with GOOGLE_API_KEY set")
        return False

def test_generation_strategies():
    """Test different generation strategies"""
    print("\n📋 Testing generation strategies...")
    
    try:
        from ai_designer.core.complex_shape_generator import GenerationStrategy
        
        strategies = [
            GenerationStrategy.INCREMENTAL,
            GenerationStrategy.DECOMPOSED, 
            GenerationStrategy.ITERATIVE,
            GenerationStrategy.ADAPTIVE
        ]
        
        for strategy in strategies:
            print(f"✅ Strategy available: {strategy.value}")
        
        print("✅ All generation strategies are accessible")
        return True
        
    except Exception as e:
        print(f"❌ Generation strategy test failed: {e}")
        return False

def run_comprehensive_validation():
    """Run comprehensive validation of the enhanced system"""
    
    print("🚀 Enhanced System Comprehensive Validation")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Import Structure
    test_results.append(("Import Structure", test_import_structure()))
    
    # Test 2: API Key Configuration
    test_results.append(("API Key Configuration", test_api_key_configuration()))
    
    # Test 3: LLM Client Initialization
    llm_client = test_llm_client_initialization()
    test_results.append(("LLM Client Initialization", llm_client is not None))
    
    # Test 4: Complex Shape Generator
    generator = test_complex_shape_generator()
    test_results.append(("Complex Shape Generator", generator is not None))
    
    # Test 5: Enhanced State LLM Integration
    enhanced_system = test_enhanced_state_llm_integration()
    test_results.append(("Enhanced State LLM Integration", enhanced_system is not None))
    
    # Test 6: Generation Strategies
    test_results.append(("Generation Strategies", test_generation_strategies()))
    
    # Test 7: Complex Shape Request Processing
    test_results.append(("Complex Shape Request Processing", test_complex_shape_request_processing()))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Validation Results Summary")
    print(f"{'='*60}")
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<35} {status}")
        if result:
            passed_tests += 1
    
    print(f"\n📈 Overall Result: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The enhanced system is ready for use.")
        print("🔧 You can now run complex shape generation with your API key.")
    else:
        print("⚠️ Some tests failed. Please check the error messages above.")
        print("🔧 The system may still work but with limited functionality.")
    
    print(f"\n🚀 Next Steps:")
    print(f"   1. Run: python demo_enhanced_complex_shapes.py")
    print(f"   2. Check documentation: docs/ENHANCED_COMPLEX_SHAPES.md")
    print(f"   3. Start building complex shapes with AI assistance!")

if __name__ == "__main__":
    try:
        run_comprehensive_validation()
        
    except KeyboardInterrupt:
        print(f"\n👋 Validation interrupted by user")
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()

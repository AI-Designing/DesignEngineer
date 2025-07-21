#!/usr/bin/env python3
"""
Test script for FreeCAD State Analysis functionality
"""
import sys
import os
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_designer.freecad.api_client import FreeCADAPIClient
from ai_designer.freecad.state_manager import FreeCADStateAnalyzer
from ai_designer.freecad.command_executor import CommandExecutor

def test_basic_analysis():
    """Test basic analysis functionality"""
    print("🧪 Testing FreeCAD State Analysis...")
    
    try:
        # Initialize components
        api_client = FreeCADAPIClient(use_headless=True)
        if not api_client.connect():
            print("❌ Failed to connect to FreeCAD")
            return False
        
        analyzer = FreeCADStateAnalyzer(api_client)
        executor = CommandExecutor(api_client)
        
        print("✅ Components initialized successfully")
        
        # Create a simple box for testing
        print("📦 Creating test objects...")
        result = executor.execute("""
box = doc.addObject("Part::Box", "TestBox")
box.Length = 10
box.Width = 10
box.Height = 10
doc.recompute()
""")
        
        if result["status"] != "success":
            print(f"❌ Failed to create test box: {result['message']}")
            return False
        
        print("✅ Test box created")
        
        # Perform analysis
        print("🔍 Running state analysis...")
        analysis = analyzer.analyze_document_state()
        
        if "error" in analysis:
            print(f"❌ Analysis failed: {analysis['error']}")
            return False
        
        print("✅ Analysis completed successfully")
        
        # Print results
        analyzer.print_analysis_results(analysis)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_command_integration():
    """Test integration with command executor"""
    print("\n🧪 Testing Command Integration...")
    
    try:
        api_client = FreeCADAPIClient(use_headless=True)
        if not api_client.connect():
            print("❌ Failed to connect to FreeCAD")
            return False
        
        executor = CommandExecutor(api_client)
        
        # Execute a command that should trigger analysis
        print("⚙️ Executing command with automatic analysis...")
        result = executor.execute("""
cylinder = doc.addObject("Part::Cylinder", "TestCylinder")
cylinder.Radius = 5
cylinder.Height = 20
doc.recompute()
""")
        
        return result["status"] == "success"
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    print("FreeCAD State Analysis Test Suite")
    print("=" * 50)
    
    # Run tests
    test1_result = test_basic_analysis()
    test2_result = test_command_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Basic Analysis: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"  Command Integration: {'✅ PASS' if test2_result else '❌ FAIL'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! The system is ready to use.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

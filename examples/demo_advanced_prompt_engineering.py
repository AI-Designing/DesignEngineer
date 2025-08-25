"""
Advanced Prompt Engineering Demonstration
Shows how the enhanced system understands → breaks down → implements complex designs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from typing import Dict, Any
from src.ai_designer.core.advanced_prompt_engine import EnhancedLLMIntegration, ProblemComplexity
from src.ai_designer.core.enhanced_complex_generator import EnhancedComplexShapeGenerator


class MockLLMClient:
    """Mock LLM client for demonstration purposes"""
    
    def generate_response(self, prompt: str) -> str:
        """Generate realistic responses based on prompt content"""
        
        if "analyze this design problem systematically" in prompt.lower():
            # Understanding phase response
            return '''
{
    "main_objective": "Create a parametric gear assembly with interlocking teeth and precise tolerances",
    "key_requirements": [
        "Two interlocking gears",
        "Precise tooth geometry",
        "Parametric design for different sizes",
        "Proper clearances and tolerances",
        "Assembly constraints"
    ],
    "constraints": [
        "FreeCAD geometric precision limits",
        "Computational complexity for tooth profiles",
        "Assembly interference checks required",
        "Performance optimization needed"
    ],
    "expected_outputs": [
        "Two gear objects with proper tooth profiles",
        "Assembly with correct positioning",
        "Parametric controls for gear ratios",
        "Validation of mesh quality"
    ],
    "complexity_level": "advanced",
    "domain_knowledge_needed": [
        "Gear geometry mathematics",
        "Involute tooth profiles",
        "FreeCAD Part Design workbench",
        "Parametric modeling techniques",
        "Assembly constraints"
    ],
    "potential_challenges": [
        "Complex involute curve calculations",
        "Precise tooth spacing and profiles",
        "Assembly interference detection",
        "Performance optimization for many teeth",
        "Parametric constraint management"
    ]
}
'''
        
        elif "create a detailed step-by-step implementation plan" in prompt.lower():
            # Breakdown phase response
            return '''
[
    {
        "description": "Initialize parametric document and setup variables",
        "purpose": "Create foundation for parametric gear design with configurable parameters",
        "freecad_operations": [
            "FreeCAD.newDocument()",
            "doc.addObject('Spreadsheet::Sheet')",
            "sheet.set('A1', 'gear1_teeth')",
            "sheet.set('A2', 'gear2_teeth')",
            "sheet.set('A3', 'module')"
        ],
        "dependencies": [],
        "validation_criteria": "Document created with parameter spreadsheet",
        "expected_result": "FreeCAD document with parametric controls ready",
        "error_handling": "Verify FreeCAD installation and document creation permissions"
    },
    {
        "description": "Calculate gear geometry parameters",
        "purpose": "Compute precise involute tooth profiles and gear dimensions",
        "freecad_operations": [
            "calculate_pitch_diameter()",
            "calculate_base_diameter()",
            "generate_involute_points()",
            "compute_tooth_spacing()"
        ],
        "dependencies": ["step_001"],
        "validation_criteria": "All geometric parameters calculated without mathematical errors",
        "expected_result": "Complete set of gear geometry parameters",
        "error_handling": "Validate mathematical results and check for degenerate cases"
    },
    {
        "description": "Create first gear tooth profile",
        "purpose": "Generate precise involute tooth profile for primary gear",
        "freecad_operations": [
            "Sketcher.createSketch()",
            "sketch.addGeometry(Part.LineSegment())",
            "sketch.addConstraint(Sketcher.Constraint())",
            "PartDesign.addObject('PartDesign::Pad')"
        ],
        "dependencies": ["step_001", "step_002"],
        "validation_criteria": "Tooth profile sketch is geometrically valid",
        "expected_result": "Parametric tooth profile ready for pattern",
        "error_handling": "Check sketch constraints and geometric validity"
    },
    {
        "description": "Create circular pattern for first gear",
        "purpose": "Replicate tooth profile around gear circumference",
        "freecad_operations": [
            "PartDesign.addObject('PartDesign::PolarPattern')",
            "pattern.Axis = (0,0,1)",
            "pattern.Angle = 360",
            "pattern.Occurrences = gear1_teeth"
        ],
        "dependencies": ["step_003"],
        "validation_criteria": "All teeth are properly positioned without interference",
        "expected_result": "Complete first gear with all teeth",
        "error_handling": "Verify pattern success and check for overlapping geometry"
    },
    {
        "description": "Create second gear with different tooth count",
        "purpose": "Generate meshing gear with proper gear ratio",
        "freecad_operations": [
            "create_gear_tooth_profile(gear2_teeth)",
            "PartDesign.addObject('PartDesign::PolarPattern')",
            "calculate_center_distance()",
            "position_second_gear()"
        ],
        "dependencies": ["step_004"],
        "validation_criteria": "Second gear meshes properly with first gear",
        "expected_result": "Two gears positioned for proper meshing",
        "error_handling": "Check gear mesh quality and interference"
    },
    {
        "description": "Create assembly constraints",
        "purpose": "Ensure proper gear interaction and rotation",
        "freecad_operations": [
            "Assembly.addConstraint('Coincident')",
            "Assembly.addConstraint('Parallel')",
            "Assembly.addConstraint('Distance')",
            "validate_assembly()"
        ],
        "dependencies": ["step_005"],
        "validation_criteria": "Gears rotate smoothly without interference",
        "expected_result": "Functional gear assembly with proper constraints",
        "error_handling": "Test rotation and check for binding or interference"
    }
]
'''
        
        elif "generate complete python code" in prompt.lower():
            # Implementation phase response
            return '''
{
    "code": "import FreeCAD\\nimport Part\\nimport math\\nfrom FreeCAD import Vector\\n\\ndef create_parametric_gear_assembly():\\n    \\"\\"\\"\\n    Create a parametric gear assembly with precise involute teeth\\n    \\"\\"\\"\\n    try:\\n        # Initialize document\\n        doc = FreeCAD.newDocument(\\"GearAssembly\\")\\n        \\n        # Setup parameters\\n        gear1_teeth = 20\\n        gear2_teeth = 15\\n        module = 2.0\\n        pressure_angle = 20.0\\n        \\n        # Calculate gear geometry\\n        pitch_diameter1 = gear1_teeth * module\\n        pitch_diameter2 = gear2_teeth * module\\n        center_distance = (pitch_diameter1 + pitch_diameter2) / 2\\n        \\n        # Create first gear\\n        gear1 = create_involute_gear(doc, gear1_teeth, module, pressure_angle, \\"Gear1\\")\\n        \\n        # Create second gear\\n        gear2 = create_involute_gear(doc, gear2_teeth, module, pressure_angle, \\"Gear2\\")\\n        \\n        # Position gears\\n        gear2.Placement.Base = Vector(center_distance, 0, 0)\\n        \\n        # Validate assembly\\n        doc.recompute()\\n        \\n        return {\\n            \\"status\\": \\"success\\",\\n            \\"gears\\": [gear1, gear2],\\n            \\"center_distance\\": center_distance,\\n            \\"gear_ratio\\": gear1_teeth / gear2_teeth\\n        }\\n        \\n    except Exception as e:\\n        return {\\"status\\": \\"error\\", \\"error\\": str(e)}\\n\\ndef create_involute_gear(doc, teeth, module, pressure_angle, name):\\n    \\"\\"\\"Create a single involute gear\\"\\"\\"\\n    # Simplified gear creation for demonstration\\n    pitch_radius = (teeth * module) / 2\\n    gear = Part.makeCylinder(pitch_radius, 5)\\n    gear_obj = doc.addObject(\\"Part::Feature\\", name)\\n    gear_obj.Shape = gear\\n    return gear_obj\\n\\nif __name__ == \\"__main__\\":\\n    result = create_parametric_gear_assembly()\\n    print(f\\"Gear assembly result: {result}\\")",
    "explanation": "This implementation creates a parametric gear assembly using FreeCAD's Python API. It calculates proper gear geometry including pitch diameters and center distances, creates two interlocking gears with different tooth counts, and positions them for proper meshing. The code includes error handling and validation to ensure robust operation.",
    "complexity_score": 0.85,
    "confidence_level": 0.92,
    "potential_issues": [
        "Simplified tooth profile - real involute curves would require more complex mathematics",
        "Basic gear positioning - production code would need more sophisticated assembly constraints",
        "Limited validation - should include gear mesh quality checks"
    ],
    "optimization_suggestions": [
        "Implement true involute tooth profiles using mathematical formulas",
        "Add comprehensive gear mesh validation",
        "Include backlash and tolerance calculations",
        "Add parametric controls through FreeCAD's property system"
    ]
}
'''
        
        elif "analyze the generated code for quality" in prompt.lower():
            # Validation phase response
            return '''
{
    "syntax_valid": true,
    "logic_valid": true,
    "freecad_compliance": true,
    "error_handling_adequate": true,
    "performance_acceptable": true,
    "issues_found": [
        "Simplified gear tooth geometry - using cylinders instead of proper involute profiles",
        "Missing assembly constraints for gear interaction",
        "Limited parameter validation for edge cases"
    ],
    "suggestions": [
        "Implement true involute tooth profile generation",
        "Add assembly workbench constraints for proper gear meshing",
        "Include comprehensive input parameter validation",
        "Add gear mesh quality analysis functions"
    ],
    "overall_quality_score": 0.78
}
'''
        
        elif "improve the code based on validation results" in prompt.lower():
            # Optimization phase response
            return '''
{
    "optimized_code": "import FreeCAD\\nimport Part\\nimport math\\nfrom FreeCAD import Vector\\nimport Sketcher\\nimport PartDesign\\n\\ndef create_advanced_gear_assembly():\\n    \\"\\"\\"\\n    Create an advanced parametric gear assembly with true involute teeth\\n    \\"\\"\\"\\n    try:\\n        # Validate inputs\\n        gear1_teeth = max(8, min(100, 20))  # Reasonable range\\n        gear2_teeth = max(8, min(100, 15))\\n        module = max(0.5, min(10.0, 2.0))\\n        pressure_angle = max(14.5, min(25.0, 20.0))\\n        \\n        # Initialize document\\n        doc = FreeCAD.newDocument(\\"AdvancedGearAssembly\\")\\n        \\n        # Calculate precise gear geometry\\n        pitch_diameter1 = gear1_teeth * module\\n        pitch_diameter2 = gear2_teeth * module\\n        base_diameter1 = pitch_diameter1 * math.cos(math.radians(pressure_angle))\\n        base_diameter2 = pitch_diameter2 * math.cos(math.radians(pressure_angle))\\n        center_distance = (pitch_diameter1 + pitch_diameter2) / 2\\n        \\n        # Create gears with proper involute profiles\\n        gear1 = create_true_involute_gear(doc, gear1_teeth, module, pressure_angle, \\"Gear1\\")\\n        gear2 = create_true_involute_gear(doc, gear2_teeth, module, pressure_angle, \\"Gear2\\")\\n        \\n        # Position gears with precise center distance\\n        gear2.Placement.Base = Vector(center_distance, 0, 0)\\n        \\n        # Add assembly constraints\\n        create_gear_assembly_constraints(doc, gear1, gear2, center_distance)\\n        \\n        # Validate gear mesh quality\\n        mesh_quality = validate_gear_mesh(gear1, gear2, center_distance)\\n        \\n        doc.recompute()\\n        \\n        return {\\n            \\"status\\": \\"success\\",\\n            \\"gears\\": [gear1, gear2],\\n            \\"center_distance\\": center_distance,\\n            \\"gear_ratio\\": gear1_teeth / gear2_teeth,\\n            \\"mesh_quality\\": mesh_quality,\\n            \\"parameters\\": {\\n                \\"gear1_teeth\\": gear1_teeth,\\n                \\"gear2_teeth\\": gear2_teeth,\\n                \\"module\\": module,\\n                \\"pressure_angle\\": pressure_angle\\n            }\\n        }\\n        \\n    except Exception as e:\\n        return {\\"status\\": \\"error\\", \\"error\\": str(e), \\"traceback\\": traceback.format_exc()}\\n\\ndef create_true_involute_gear(doc, teeth, module, pressure_angle, name):\\n    \\"\\"\\"Create gear with true involute tooth profiles\\"\\"\\"\\n    # Implementation would include proper involute mathematics\\n    # For demonstration, showing structure\\n    pitch_radius = (teeth * module) / 2\\n    addendum = module\\n    dedendum = 1.25 * module\\n    \\n    # Create gear body\\n    outer_radius = pitch_radius + addendum\\n    inner_radius = pitch_radius - dedendum\\n    \\n    gear_body = Part.makeCylinder(outer_radius, 10)\\n    gear_obj = doc.addObject(\\"Part::Feature\\", name)\\n    gear_obj.Shape = gear_body\\n    \\n    return gear_obj\\n\\ndef create_gear_assembly_constraints(doc, gear1, gear2, center_distance):\\n    \\"\\"\\"Add assembly constraints for proper gear interaction\\"\\"\\"\\n    # Assembly constraint implementation\\n    pass\\n\\ndef validate_gear_mesh(gear1, gear2, center_distance):\\n    \\"\\"\\"Validate gear mesh quality\\"\\"\\"\\n    return {\\"contact_ratio\\": 1.2, \\"interference\\": False, \\"backlash\\": 0.1}\\n\\nif __name__ == \\"__main__\\":\\n    result = create_advanced_gear_assembly()\\n    print(f\\"Advanced gear assembly result: {result}\\")",
    "improvements_made": [
        "Added comprehensive input parameter validation with reasonable ranges",
        "Implemented proper gear geometry calculations including base diameters",
        "Added gear mesh quality validation functions",
        "Included assembly constraint framework",
        "Enhanced error handling with traceback information",
        "Added detailed parameter tracking in results"
    ],
    "quality_improvement": 0.17
}
'''
        
        else:
            # Default response
            return "Generated response for prompt."


class PromptEngineeringDemo:
    """
    Comprehensive demonstration of the advanced prompt engineering system
    """
    
    def __init__(self):
        self.llm_client = MockLLMClient()
        self.enhanced_llm = EnhancedLLMIntegration(self.llm_client)
        
    async def run_comprehensive_demo(self):
        """Run comprehensive demonstration of enhanced prompt engineering"""
        
        print("🚀 Advanced Prompt Engineering System Demo")
        print("=" * 60)
        
        # Test cases with increasing complexity
        test_cases = [
            {
                'name': 'Simple Shape',
                'requirements': 'Create a simple box with dimensions 10x20x5',
                'expected_complexity': ProblemComplexity.SIMPLE
            },
            {
                'name': 'Mechanical Component',
                'requirements': 'Design a parametric gear assembly with 20 and 15 teeth, module 2.0, with proper involute profiles',
                'expected_complexity': ProblemComplexity.ADVANCED
            },
            {
                'name': 'Complex Assembly',
                'requirements': 'Create a complete robotic arm joint with servo motor mount, bearing housings, and articulated links',
                'expected_complexity': ProblemComplexity.EXPERT
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\\n{'='*20} Test Case {i}: {test_case['name']} {'='*20}")
            await self._run_single_test(test_case)
            
        print("\\n🎉 Demo completed! Advanced prompt engineering system demonstrated.")
        
    async def _run_single_test(self, test_case: Dict[str, Any]):
        """Run a single test case demonstration"""
        
        requirements = test_case['requirements']
        print(f"\\n📋 Requirements: {requirements}")
        print(f"🎯 Expected Complexity: {test_case['expected_complexity'].value}")
        
        try:
            # Generate enhanced code using the advanced system
            print("\\n🧠 Starting enhanced code generation...")
            start_time = asyncio.get_event_loop().time()
            
            result = self.enhanced_llm.generate_enhanced_freecad_code(
                requirements,
                {'demo_mode': True, 'test_case': test_case['name']}
            )
            
            end_time = asyncio.get_event_loop().time()
            generation_time = end_time - start_time
            
            # Display results
            self._display_generation_results(result, generation_time)
            
        except Exception as e:
            print(f"❌ Error in test case: {e}")
    
    def _display_generation_results(self, result: Dict[str, Any], generation_time: float):
        """Display the results of code generation"""
        
        print(f"\\n⏱️  Generation Time: {generation_time:.2f} seconds")
        print(f"🔧 Generation Method: {result.get('generation_method', 'enhanced_prompt_engineering')}")
        
        # Understanding phase results
        understanding = result.get('understanding', {})
        print(f"\\n📊 UNDERSTANDING PHASE:")
        print(f"   🎯 Main Objective: {understanding.get('main_objective', 'N/A')}")
        print(f"   📈 Complexity Level: {understanding.get('complexity_level', 'N/A')}")
        print(f"   ✅ Key Requirements: {len(understanding.get('key_requirements', []))} identified")
        print(f"   ⚠️  Potential Challenges: {len(understanding.get('potential_challenges', []))} identified")
        
        # Breakdown phase results
        breakdown = result.get('breakdown', [])
        print(f"\\n🔧 BREAKDOWN PHASE:")
        print(f"   📋 Implementation Steps: {len(breakdown)} steps planned")
        for i, step in enumerate(breakdown[:3], 1):  # Show first 3 steps
            print(f"   {i}. {step.get('description', 'N/A')}")
        if len(breakdown) > 3:
            print(f"   ... and {len(breakdown) - 3} more steps")
        
        # Implementation phase results
        implementation = result.get('implementation', {})
        print(f"\\n💻 IMPLEMENTATION PHASE:")
        code = implementation.get('code', '')
        print(f"   📝 Generated Code Length: {len(code)} characters")
        print(f"   🎯 Confidence Level: {implementation.get('confidence_level', 0.0):.1%}")
        print(f"   🔍 Complexity Score: {implementation.get('complexity_score', 0.0):.2f}")
        
        # Validation phase results
        validation = result.get('validation', {})
        print(f"\\n✅ VALIDATION PHASE:")
        print(f"   ✔️  Syntax Valid: {validation.get('syntax_valid', False)}")
        print(f"   ✔️  Logic Valid: {validation.get('logic_valid', False)}")
        print(f"   ✔️  FreeCAD Compliant: {validation.get('freecad_compliance', False)}")
        print(f"   📊 Overall Quality Score: {validation.get('overall_quality_score', 0.0):.1%}")
        
        issues = validation.get('issues_found', [])
        if issues:
            print(f"   ⚠️  Issues Found: {len(issues)}")
            for issue in issues[:2]:  # Show first 2 issues
                print(f"      - {issue}")
        
        # Optimization phase results
        optimization = result.get('optimization', {})
        if optimization.get('optimization_needed', False):
            print(f"\\n⚡ OPTIMIZATION PHASE:")
            improvements = optimization.get('improvements_made', [])
            print(f"   🔧 Improvements Made: {len(improvements)}")
            quality_improvement = optimization.get('quality_improvement', 0.0)
            print(f"   📈 Quality Improvement: +{quality_improvement:.1%}")
        
        # Quality metrics
        quality_metrics = result.get('quality_metrics', {})
        if quality_metrics:
            print(f"\\n📈 QUALITY METRICS:")
            print(f"   🎯 Average Quality: {quality_metrics.get('average_quality', 0.0):.1%}")
            print(f"   ✅ Success Rate: {quality_metrics.get('success_rate', 0.0):.1%}")
            print(f"   📊 Total Generations: {quality_metrics.get('total_generations', 0)}")
        
        # Show code sample
        final_code = result.get('final_code', '')
        if final_code:
            print(f"\\n💻 CODE SAMPLE (first 300 chars):")
            print("   " + "─" * 50)
            sample = final_code[:300].replace('\\n', '\\n   ')
            print(f"   {sample}")
            if len(final_code) > 300:
                print(f"   ... ({len(final_code) - 300} more characters)")
            print("   " + "─" * 50)


async def main():
    """Main demonstration function"""
    demo = PromptEngineeringDemo()
    await demo.run_comprehensive_demo()


if __name__ == "__main__":
    asyncio.run(main())

"""
Advanced LLM Prompt Engineering System for FreeCAD Code Generation
Implements a structured approach: Understand → Breakdown → Implement
"""

import json
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ProblemComplexity(Enum):
    """Problem complexity levels for different prompt strategies"""

    SIMPLE = "simple"  # Basic primitives
    MODERATE = "moderate"  # Shape combinations
    COMPLEX = "complex"  # Multi-step assemblies
    ADVANCED = "advanced"  # Parametric designs
    EXPERT = "expert"  # Complex mathematical shapes


class CodeGenerationPhase(Enum):
    """Phases of code generation process"""

    UNDERSTANDING = "understanding"
    BREAKDOWN = "breakdown"
    IMPLEMENTATION = "implementation"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"


@dataclass
class ProblemUnderstanding:
    """Structured problem understanding"""

    main_objective: str
    key_requirements: List[str]
    constraints: List[str]
    expected_outputs: List[str]
    complexity_level: ProblemComplexity
    domain_knowledge_needed: List[str]
    potential_challenges: List[str]


@dataclass
class ImplementationStep:
    """Detailed implementation step"""

    step_id: str
    description: str
    purpose: str
    freecad_operations: List[str]
    dependencies: List[str]
    validation_criteria: str
    expected_result: str
    error_handling: str
    code_snippet: Optional[str] = None


@dataclass
class GeneratedCode:
    """Generated code with metadata"""

    code: str
    explanation: str
    complexity_score: float
    confidence_level: float
    potential_issues: List[str]
    optimization_suggestions: List[str]


class AdvancedPromptEngine:
    """
    Advanced prompt engineering system for high-quality LLM code generation
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.problem_patterns = self._load_problem_patterns()
        self.code_templates = self._load_code_templates()
        self.validation_rules = self._load_validation_rules()

    def generate_enhanced_code(
        self, user_requirements: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate high-quality code using structured prompt engineering
        """
        print("🧠 Starting enhanced code generation...")

        # Phase 1: Problem Understanding
        print("  📊 Phase 1: Understanding the problem...")
        understanding = self._understand_problem(user_requirements, context)

        # Phase 2: Solution Breakdown
        print("  🔧 Phase 2: Breaking down into implementation steps...")
        breakdown = self._breakdown_solution(understanding, context)

        # Phase 3: Code Implementation
        print("  💻 Phase 3: Generating implementation code...")
        implementation = self._implement_solution(understanding, breakdown, context)

        # Phase 4: Code Validation
        print("  ✅ Phase 4: Validating generated code...")
        validation = self._validate_code(implementation, understanding)

        # Phase 5: Code Optimization
        print("  ⚡ Phase 5: Optimizing code quality...")
        optimization = self._optimize_code(implementation, validation)

        return {
            "understanding": understanding.__dict__,
            "breakdown": [step.__dict__ for step in breakdown],
            "implementation": implementation.__dict__,
            "validation": validation,
            "optimization": optimization,
            "final_code": optimization.get("optimized_code", implementation.code),
        }

    def _understand_problem(
        self, requirements: str, context: Dict[str, Any] = None
    ) -> ProblemUnderstanding:
        """
        Phase 1: Deep problem understanding using structured prompts
        """
        understanding_prompt = self._create_understanding_prompt(requirements, context)

        try:
            response = self.llm_client.generate_response(understanding_prompt)
            understanding_data = self._parse_understanding_response(response)

            return ProblemUnderstanding(
                main_objective=understanding_data.get("main_objective", ""),
                key_requirements=understanding_data.get("key_requirements", []),
                constraints=understanding_data.get("constraints", []),
                expected_outputs=understanding_data.get("expected_outputs", []),
                complexity_level=ProblemComplexity(
                    understanding_data.get("complexity_level", "moderate")
                ),
                domain_knowledge_needed=understanding_data.get(
                    "domain_knowledge_needed", []
                ),
                potential_challenges=understanding_data.get("potential_challenges", []),
            )
        except Exception as e:
            print(f"⚠️ Error in problem understanding: {e}")
            return self._create_fallback_understanding(requirements)

    def _breakdown_solution(
        self, understanding: ProblemUnderstanding, context: Dict[str, Any] = None
    ) -> List[ImplementationStep]:
        """
        Phase 2: Break down solution into detailed implementation steps
        """
        breakdown_prompt = self._create_breakdown_prompt(understanding, context)

        try:
            response = self.llm_client.generate_response(breakdown_prompt)
            steps_data = self._parse_breakdown_response(response)

            steps = []
            for i, step_data in enumerate(steps_data):
                step = ImplementationStep(
                    step_id=f"step_{i+1:03d}",
                    description=step_data.get("description", ""),
                    purpose=step_data.get("purpose", ""),
                    freecad_operations=step_data.get("freecad_operations", []),
                    dependencies=step_data.get("dependencies", []),
                    validation_criteria=step_data.get("validation_criteria", ""),
                    expected_result=step_data.get("expected_result", ""),
                    error_handling=step_data.get("error_handling", ""),
                )
                steps.append(step)

            return steps
        except Exception as e:
            print(f"⚠️ Error in solution breakdown: {e}")
            return self._create_fallback_breakdown(understanding)

    def _implement_solution(
        self,
        understanding: ProblemUnderstanding,
        breakdown: List[ImplementationStep],
        context: Dict[str, Any] = None,
    ) -> GeneratedCode:
        """
        Phase 3: Generate actual implementation code
        """
        implementation_prompt = self._create_implementation_prompt(
            understanding, breakdown, context
        )

        try:
            response = self.llm_client.generate_response(implementation_prompt)
            code_data = self._parse_implementation_response(response)

            return GeneratedCode(
                code=code_data.get("code", ""),
                explanation=code_data.get("explanation", ""),
                complexity_score=float(code_data.get("complexity_score", 0.5)),
                confidence_level=float(code_data.get("confidence_level", 0.7)),
                potential_issues=code_data.get("potential_issues", []),
                optimization_suggestions=code_data.get("optimization_suggestions", []),
            )
        except Exception as e:
            print(f"⚠️ Error in code implementation: {e}")
            return self._create_fallback_implementation(understanding, breakdown)

    def _create_understanding_prompt(
        self, requirements: str, context: Dict[str, Any] = None
    ) -> str:
        """
        Create a sophisticated prompt for problem understanding
        """
        context_info = self._format_context_info(context or {})

        prompt = f"""
You are an expert FreeCAD automation engineer and AI system. Your task is to deeply understand a design problem before solving it.

DESIGN REQUIREMENTS:
{requirements}

CURRENT CONTEXT:
{context_info}

Please analyze this design problem systematically and provide a detailed understanding in JSON format:

{{
    "main_objective": "Clear statement of the primary goal",
    "key_requirements": [
        "Specific requirement 1",
        "Specific requirement 2",
        "..."
    ],
    "constraints": [
        "Technical constraint 1",
        "Resource constraint 2",
        "..."
    ],
    "expected_outputs": [
        "Expected output 1",
        "Expected output 2",
        "..."
    ],
    "complexity_level": "simple|moderate|complex|advanced|expert",
    "domain_knowledge_needed": [
        "CAD modeling principles",
        "Geometric relationships",
        "..."
    ],
    "potential_challenges": [
        "Challenge 1 with reasoning",
        "Challenge 2 with reasoning",
        "..."
    ]
}}

ANALYSIS GUIDELINES:
1. **Main Objective**: Extract the core goal, not just surface requirements
2. **Key Requirements**: Break down functional and non-functional requirements
3. **Constraints**: Identify technical, resource, and design constraints
4. **Expected Outputs**: List concrete deliverables and success criteria
5. **Complexity Assessment**: Evaluate based on:
   - Number of geometric operations required
   - Interdependencies between components
   - Precision requirements
   - Mathematical complexity
6. **Domain Knowledge**: Identify required expertise areas
7. **Potential Challenges**: Anticipate problems and edge cases

Think step by step:
- What is the user really trying to achieve?
- What are the implicit requirements not explicitly stated?
- What could go wrong during implementation?
- What domain expertise is needed for success?

Provide your analysis in valid JSON format only.
"""
        return prompt

    def _create_breakdown_prompt(
        self, understanding: ProblemUnderstanding, context: Dict[str, Any] = None
    ) -> str:
        """
        Create a detailed breakdown prompt for implementation planning
        """
        context_info = self._format_context_info(context or {})

        prompt = f"""
You are an expert FreeCAD automation engineer. Based on the problem understanding, create a detailed implementation plan.

PROBLEM UNDERSTANDING:
- Main Objective: {understanding.main_objective}
- Complexity Level: {understanding.complexity_level.value}
- Key Requirements: {', '.join(understanding.key_requirements)}
- Constraints: {', '.join(understanding.constraints)}
- Potential Challenges: {', '.join(understanding.potential_challenges)}

CURRENT CONTEXT:
{context_info}

Create a detailed step-by-step implementation plan in JSON format:

[
    {{
        "description": "Clear description of what this step accomplishes",
        "purpose": "Why this step is necessary in the overall solution",
        "freecad_operations": [
            "Specific FreeCAD operation 1",
            "Specific FreeCAD operation 2",
            "..."
        ],
        "dependencies": [
            "step_001",
            "step_002"
        ],
        "validation_criteria": "How to verify this step succeeded",
        "expected_result": "What should exist after this step",
        "error_handling": "How to handle potential failures"
    }},
    {{
        "description": "Next step...",
        "..."
    }}
]

PLANNING GUIDELINES:
1. **Logical Sequence**: Order steps to build complexity gradually
2. **Dependency Management**: Clearly identify step dependencies
3. **FreeCAD Operations**: Use specific FreeCAD Python API calls
4. **Validation**: Define clear success criteria for each step
5. **Error Handling**: Plan for common failure scenarios
6. **Modularity**: Keep steps focused and cohesive

FREECAD OPERATION CATEGORIES:
- Document management: FreeCAD.newDocument(), doc.recompute()
- Primitive creation: Part.makeBox(), Part.makeCylinder(), Part.makeSphere()
- Boolean operations: Part.fuse(), Part.cut(), Part.common()
- Transformations: obj.Placement, obj.translate(), obj.rotate()
- Sketching: Sketcher workbench operations
- Part Design: PartDesign workbench operations
- Constraints: Distance, angle, parallel, perpendicular constraints

Consider the complexity level ({understanding.complexity_level.value}) when determining:
- Number of steps needed
- Level of detail required
- Validation complexity
- Error handling sophistication

Provide your implementation plan in valid JSON format only.
"""
        return prompt

    def _create_implementation_prompt(
        self,
        understanding: ProblemUnderstanding,
        breakdown: List[ImplementationStep],
        context: Dict[str, Any] = None,
    ) -> str:
        """
        Create a comprehensive implementation prompt for code generation
        """
        context_info = self._format_context_info(context or {})
        steps_summary = self._format_steps_summary(breakdown)

        prompt = f"""
You are an expert FreeCAD Python developer. Generate high-quality, production-ready code based on the analysis and implementation plan.

PROBLEM UNDERSTANDING:
- Main Objective: {understanding.main_objective}
- Complexity: {understanding.complexity_level.value}
- Key Requirements: {', '.join(understanding.key_requirements)}

IMPLEMENTATION PLAN:
{steps_summary}

CURRENT CONTEXT:
{context_info}

Generate complete Python code with the following JSON response format:

{{
    "code": "Complete Python code implementation",
    "explanation": "Detailed explanation of the implementation approach",
    "complexity_score": 0.8,
    "confidence_level": 0.9,
    "potential_issues": [
        "Potential issue 1",
        "Potential issue 2"
    ],
    "optimization_suggestions": [
        "Optimization suggestion 1",
        "Optimization suggestion 2"
    ]
}}

CODE GENERATION REQUIREMENTS:

1. **Complete Implementation**: Generate full, executable Python code
2. **FreeCAD Best Practices**: Follow FreeCAD Python API conventions
3. **Error Handling**: Include comprehensive error checking
4. **Documentation**: Add clear comments and docstrings
5. **Modularity**: Structure code in logical functions/classes
6. **Performance**: Consider efficiency and resource usage
7. **Maintainability**: Write clean, readable code

CODE STRUCTURE TEMPLATE:
```python
import FreeCAD
import Part
import Draft
# Other necessary imports

def main_implementation():
    '''
    Main function implementing the design requirements
    '''
    try:
        # Step 1: Document setup
        doc = FreeCAD.newDocument("GeneratedDesign")

        # Step 2-N: Implementation steps
        # ... (follow the implementation plan)

        # Final: Recompute and return results
        doc.recompute()
        return {{"status": "success", "objects": created_objects}}

    except Exception as e:
        return {{"status": "error", "error": str(e)}}

# Helper functions as needed
def create_component_1():
    '''Helper function for specific component'''
    pass

def validate_geometry(obj):
    '''Validate created geometry'''
    pass

if __name__ == "__main__":
    result = main_implementation()
    print(f"Implementation result: {{result}}")
```

QUALITY CRITERIA:
- Code should be executable without modification
- Include proper error handling and validation
- Follow Python and FreeCAD conventions
- Be well-documented with comments
- Handle edge cases appropriately
- Be optimized for the given complexity level

COMPLEXITY-SPECIFIC CONSIDERATIONS:
For {understanding.complexity_level.value} complexity:
- Use appropriate level of abstraction
- Include suitable error handling depth
- Consider performance implications
- Plan for maintainability needs

Provide your implementation in valid JSON format only, with complete executable code.
"""
        return prompt

    def _validate_code(
        self, implementation: GeneratedCode, understanding: ProblemUnderstanding
    ) -> Dict[str, Any]:
        """
        Phase 4: Validate generated code quality and correctness
        """
        validation_prompt = self._create_validation_prompt(
            implementation, understanding
        )

        try:
            response = self.llm_client.generate_response(validation_prompt)
            validation_data = self._parse_validation_response(response)

            return {
                "syntax_valid": validation_data.get("syntax_valid", False),
                "logic_valid": validation_data.get("logic_valid", False),
                "freecad_compliance": validation_data.get("freecad_compliance", False),
                "error_handling_adequate": validation_data.get(
                    "error_handling_adequate", False
                ),
                "performance_acceptable": validation_data.get(
                    "performance_acceptable", False
                ),
                "issues_found": validation_data.get("issues_found", []),
                "suggestions": validation_data.get("suggestions", []),
                "overall_quality_score": validation_data.get(
                    "overall_quality_score", 0.5
                ),
            }
        except Exception as e:
            print(f"⚠️ Error in code validation: {e}")
            return self._create_fallback_validation()

    def _optimize_code(
        self, implementation: GeneratedCode, validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 5: Optimize code based on validation results
        """
        if validation.get("overall_quality_score", 0) > 0.8:
            return {
                "optimization_needed": False,
                "optimized_code": implementation.code,
                "improvements_made": [],
            }

        optimization_prompt = self._create_optimization_prompt(
            implementation, validation
        )

        try:
            response = self.llm_client.generate_response(optimization_prompt)
            optimization_data = self._parse_optimization_response(response)

            return {
                "optimization_needed": True,
                "optimized_code": optimization_data.get(
                    "optimized_code", implementation.code
                ),
                "improvements_made": optimization_data.get("improvements_made", []),
                "quality_improvement": optimization_data.get(
                    "quality_improvement", 0.0
                ),
            }
        except Exception as e:
            print(f"⚠️ Error in code optimization: {e}")
            return {
                "optimization_needed": False,
                "optimized_code": implementation.code,
                "improvements_made": [],
                "error": str(e),
            }

    def _create_validation_prompt(
        self, implementation: GeneratedCode, understanding: ProblemUnderstanding
    ) -> str:
        """Create validation prompt for code quality assessment"""

        prompt = f"""
You are a senior FreeCAD code reviewer. Analyze the generated code for quality, correctness, and best practices.

ORIGINAL REQUIREMENTS:
- Objective: {understanding.main_objective}
- Complexity: {understanding.complexity_level.value}

GENERATED CODE:
```python
{implementation.code}
```

CODE EXPLANATION:
{implementation.explanation}

Perform comprehensive code review and provide analysis in JSON format:

{{
    "syntax_valid": true|false,
    "logic_valid": true|false,
    "freecad_compliance": true|false,
    "error_handling_adequate": true|false,
    "performance_acceptable": true|false,
    "issues_found": [
        "Issue 1 with specific location",
        "Issue 2 with specific location"
    ],
    "suggestions": [
        "Improvement suggestion 1",
        "Improvement suggestion 2"
    ],
    "overall_quality_score": 0.85
}}

VALIDATION CRITERIA:

1. **Syntax Validity**: Check for Python syntax errors
2. **Logic Validity**: Verify logical flow and correctness
3. **FreeCAD Compliance**: Ensure proper FreeCAD API usage
4. **Error Handling**: Assess exception handling adequacy
5. **Performance**: Evaluate efficiency and resource usage

Check for:
- Proper imports and FreeCAD API usage
- Logical sequence of operations
- Error handling and edge cases
- Code organization and readability
- Performance considerations
- Resource management
- Compliance with FreeCAD best practices

Provide detailed analysis in valid JSON format only.
"""
        return prompt

    def _create_optimization_prompt(
        self, implementation: GeneratedCode, validation: Dict[str, Any]
    ) -> str:
        """Create optimization prompt for code improvement"""

        issues = validation.get("issues_found", [])
        suggestions = validation.get("suggestions", [])

        prompt = f"""
You are a FreeCAD optimization expert. Improve the code based on validation results.

ORIGINAL CODE:
```python
{implementation.code}
```

VALIDATION ISSUES:
{chr(10).join(f"- {issue}" for issue in issues)}

IMPROVEMENT SUGGESTIONS:
{chr(10).join(f"- {suggestion}" for suggestion in suggestions)}

Generate optimized code with improvements in JSON format:

{{
    "optimized_code": "Improved Python code",
    "improvements_made": [
        "Specific improvement 1",
        "Specific improvement 2"
    ],
    "quality_improvement": 0.2
}}

OPTIMIZATION FOCUS:
1. Fix identified issues
2. Implement suggested improvements
3. Enhance error handling
4. Improve performance
5. Increase code readability
6. Add better documentation

Provide optimized code in valid JSON format only.
"""
        return prompt

    # Helper methods for parsing and formatting
    def _format_context_info(self, context: Dict[str, Any]) -> str:
        """Format context information for prompts"""
        if not context:
            return "No additional context provided."

        context_str = ""
        for key, value in context.items():
            context_str += f"- {key}: {value}\n"
        return context_str

    def _format_steps_summary(self, steps: List[ImplementationStep]) -> str:
        """Format implementation steps for prompts"""
        summary = ""
        for i, step in enumerate(steps, 1):
            summary += f"Step {i}: {step.description}\n"
            summary += f"  Purpose: {step.purpose}\n"
            summary += f"  Operations: {', '.join(step.freecad_operations)}\n\n"
        return summary

    def _parse_understanding_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for problem understanding"""
        try:
            # Extract JSON from response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._extract_understanding_from_text(response)
        except Exception as e:
            print(f"⚠️ Error parsing understanding response: {e}")
            return {}

    def _parse_breakdown_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response for solution breakdown"""
        try:
            # Extract JSON array from response
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._extract_breakdown_from_text(response)
        except Exception as e:
            print(f"⚠️ Error parsing breakdown response: {e}")
            return []

    def _parse_implementation_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for code implementation"""
        try:
            # Extract JSON from response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._extract_implementation_from_text(response)
        except Exception as e:
            print(f"⚠️ Error parsing implementation response: {e}")
            return {}

    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for code validation"""
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._extract_validation_from_text(response)
        except Exception as e:
            print(f"⚠️ Error parsing validation response: {e}")
            return {}

    def _parse_optimization_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for code optimization"""
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._extract_optimization_from_text(response)
        except Exception as e:
            print(f"⚠️ Error parsing optimization response: {e}")
            return {}

    # Fallback methods for error handling
    def _create_fallback_understanding(self, requirements: str) -> ProblemUnderstanding:
        """Create fallback understanding when LLM fails"""
        return ProblemUnderstanding(
            main_objective=f"Create design based on: {requirements}",
            key_requirements=[requirements],
            constraints=["FreeCAD compatibility", "Basic geometric constraints"],
            expected_outputs=["3D model", "FreeCAD document"],
            complexity_level=ProblemComplexity.MODERATE,
            domain_knowledge_needed=["CAD modeling", "FreeCAD Python API"],
            potential_challenges=["Geometric complexity", "API limitations"],
        )

    def _create_fallback_breakdown(
        self, understanding: ProblemUnderstanding
    ) -> List[ImplementationStep]:
        """Create fallback breakdown when LLM fails"""
        return [
            ImplementationStep(
                step_id="step_001",
                description="Initialize FreeCAD document",
                purpose="Setup workspace for modeling",
                freecad_operations=["FreeCAD.newDocument()"],
                dependencies=[],
                validation_criteria="Document created successfully",
                expected_result="Active FreeCAD document",
                error_handling="Check FreeCAD installation",
            ),
            ImplementationStep(
                step_id="step_002",
                description="Create basic geometry",
                purpose="Implement core design requirements",
                freecad_operations=["Part.makeBox()", "doc.addObject()"],
                dependencies=["step_001"],
                validation_criteria="Geometry objects created",
                expected_result="Basic 3D shapes in document",
                error_handling="Validate geometry parameters",
            ),
        ]

    def _create_fallback_implementation(
        self, understanding: ProblemUnderstanding, breakdown: List[ImplementationStep]
    ) -> GeneratedCode:
        """Create fallback implementation when LLM fails"""
        fallback_code = '''
import FreeCAD
import Part

def create_basic_shape():
    """Fallback implementation for basic shape creation"""
    try:
        doc = FreeCAD.newDocument("BasicShape")
        box = Part.makeBox(10, 10, 10)
        box_obj = doc.addObject("Part::Feature", "Box")
        box_obj.Shape = box
        doc.recompute()
        return {"status": "success", "objects": [box_obj]}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    result = create_basic_shape()
    print(f"Result: {result}")
'''

        return GeneratedCode(
            code=fallback_code,
            explanation="Fallback implementation for basic shape creation",
            complexity_score=0.3,
            confidence_level=0.6,
            potential_issues=["Limited functionality", "Basic error handling"],
            optimization_suggestions=[
                "Add more sophisticated geometry",
                "Enhance error handling",
            ],
        )

    def _create_fallback_validation(self) -> Dict[str, Any]:
        """Create fallback validation when LLM fails"""
        return {
            "syntax_valid": True,
            "logic_valid": True,
            "freecad_compliance": True,
            "error_handling_adequate": False,
            "performance_acceptable": True,
            "issues_found": ["Validation system unavailable"],
            "suggestions": ["Manual code review recommended"],
            "overall_quality_score": 0.5,
        }

    # Additional helper methods for text extraction when JSON parsing fails
    def _extract_understanding_from_text(self, text: str) -> Dict[str, Any]:
        """Extract understanding data from plain text response"""
        # Implementation for text-based extraction
        return {
            "main_objective": "Create design from requirements",
            "key_requirements": ["Basic functionality"],
            "constraints": ["FreeCAD compatibility"],
            "expected_outputs": ["3D model"],
            "complexity_level": "moderate",
            "domain_knowledge_needed": ["CAD modeling"],
            "potential_challenges": ["Implementation complexity"],
        }

    def _extract_breakdown_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract breakdown data from plain text response"""
        # Implementation for text-based extraction
        return [
            {
                "description": "Initialize document",
                "purpose": "Setup workspace",
                "freecad_operations": ["FreeCAD.newDocument()"],
                "dependencies": [],
                "validation_criteria": "Document created",
                "expected_result": "Active document",
                "error_handling": "Check FreeCAD",
            }
        ]

    def _extract_implementation_from_text(self, text: str) -> Dict[str, Any]:
        """Extract implementation data from plain text response"""
        # Extract code blocks from text
        code_blocks = re.findall(r"```python\n(.*?)\n```", text, re.DOTALL)
        code = code_blocks[0] if code_blocks else text

        return {
            "code": code,
            "explanation": "Extracted from text response",
            "complexity_score": 0.5,
            "confidence_level": 0.6,
            "potential_issues": ["Text extraction used"],
            "optimization_suggestions": ["Review extracted code"],
        }

    def _extract_validation_from_text(self, text: str) -> Dict[str, Any]:
        """Extract validation data from plain text response"""
        return {
            "syntax_valid": "error" not in text.lower(),
            "logic_valid": True,
            "freecad_compliance": "freecad" in text.lower(),
            "error_handling_adequate": "try" in text.lower(),
            "performance_acceptable": True,
            "issues_found": [],
            "suggestions": ["Manual review recommended"],
            "overall_quality_score": 0.6,
        }

    def _extract_optimization_from_text(self, text: str) -> Dict[str, Any]:
        """Extract optimization data from plain text response"""
        return {
            "optimized_code": text,
            "improvements_made": ["Text extraction optimization"],
            "quality_improvement": 0.1,
        }

    def _load_problem_patterns(self) -> Dict[str, Any]:
        """Load problem pattern recognition data"""
        return {
            "geometric_patterns": ["box", "cylinder", "sphere", "cone"],
            "assembly_patterns": ["combine", "join", "attach", "connect"],
            "architectural_patterns": ["building", "house", "tower", "structure"],
            "mechanical_patterns": ["gear", "shaft", "bearing", "assembly"],
        }

    def _load_code_templates(self) -> Dict[str, str]:
        """Load code templates for different patterns"""
        return {
            "basic_shape": """
import FreeCAD
import Part

def create_shape():
    doc = FreeCAD.newDocument()
    # Shape creation code here
    doc.recompute()
    return doc
""",
            "assembly": """
import FreeCAD
import Part

def create_assembly():
    doc = FreeCAD.newDocument()
    # Assembly creation code here
    doc.recompute()
    return doc
""",
        }

    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for code quality checking"""
        return {
            "required_imports": ["FreeCAD"],
            "required_patterns": ["doc.recompute()", "try:", "except:"],
            "forbidden_patterns": ["eval()", "exec()", "os.system()"],
            "best_practices": ["error handling", "documentation", "validation"],
        }


# Integration with existing EnhancedComplexShapeGenerator
class EnhancedLLMIntegration:
    """
    Integration layer for enhanced LLM code generation
    """

    def __init__(self, llm_client):
        self.prompt_engine = AdvancedPromptEngine(llm_client)
        self.code_quality_tracker = CodeQualityTracker()

    def generate_enhanced_freecad_code(
        self, requirements: str, session_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate high-quality FreeCAD code using advanced prompt engineering
        """
        print(f"🚀 Generating enhanced FreeCAD code for: {requirements}")

        # Use the advanced prompt engine
        result = self.prompt_engine.generate_enhanced_code(
            requirements, session_context
        )

        # Track code quality metrics
        self.code_quality_tracker.track_generation(result)

        # Return enhanced result with additional metadata
        return {
            **result,
            "generation_method": "enhanced_prompt_engineering",
            "quality_metrics": self.code_quality_tracker.get_latest_metrics(),
            "timestamp": time.time(),
        }


class CodeQualityTracker:
    """
    Tracks code quality metrics over time
    """

    def __init__(self):
        self.generation_history = []
        self.quality_trends = {}

    def track_generation(self, generation_result: Dict[str, Any]):
        """Track quality metrics for a generation"""
        quality_score = generation_result.get("validation", {}).get(
            "overall_quality_score", 0.5
        )
        complexity = generation_result.get("understanding", {}).get(
            "complexity_level", "moderate"
        )

        self.generation_history.append(
            {
                "timestamp": time.time(),
                "quality_score": quality_score,
                "complexity": complexity,
                "success": generation_result.get("implementation", {}).get(
                    "confidence_level", 0
                )
                > 0.7,
            }
        )

        # Update trends
        self._update_quality_trends()

    def get_latest_metrics(self) -> Dict[str, Any]:
        """Get latest quality metrics"""
        if not self.generation_history:
            return {
                "average_quality": 0.5,
                "success_rate": 0.5,
                "improvement_trend": 0.0,
            }

        recent_entries = self.generation_history[-10:]  # Last 10 generations

        return {
            "average_quality": sum(e["quality_score"] for e in recent_entries)
            / len(recent_entries),
            "success_rate": sum(1 for e in recent_entries if e["success"])
            / len(recent_entries),
            "improvement_trend": self._calculate_improvement_trend(),
            "total_generations": len(self.generation_history),
        }

    def _update_quality_trends(self):
        """Update quality trends analysis"""
        if len(self.generation_history) < 5:
            return

        # Calculate trends for different complexity levels
        for complexity in ["simple", "moderate", "complex", "advanced", "expert"]:
            relevant_entries = [
                e for e in self.generation_history if e["complexity"] == complexity
            ]
            if len(relevant_entries) >= 3:
                recent = relevant_entries[-3:]
                older = (
                    relevant_entries[-6:-3]
                    if len(relevant_entries) >= 6
                    else relevant_entries[:-3]
                )

                if older:
                    recent_avg = sum(e["quality_score"] for e in recent) / len(recent)
                    older_avg = sum(e["quality_score"] for e in older) / len(older)
                    self.quality_trends[complexity] = recent_avg - older_avg

    def _calculate_improvement_trend(self) -> float:
        """Calculate overall improvement trend"""
        if len(self.generation_history) < 4:
            return 0.0

        recent_half = self.generation_history[len(self.generation_history) // 2 :]
        older_half = self.generation_history[: len(self.generation_history) // 2]

        recent_avg = sum(e["quality_score"] for e in recent_half) / len(recent_half)
        older_avg = sum(e["quality_score"] for e in older_half) / len(older_half)

        return recent_avg - older_avg

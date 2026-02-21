"""
llm/providers/deepseek.py
=========================
DeepSeek R1 low-level HTTP client and data models, extracted from deepseek_client.py.

Import via:
    from ai_designer.llm.providers.deepseek import DeepSeekR1Client, DeepSeekConfig
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import requests
import websockets

logger = logging.getLogger(__name__)


class DeepSeekMode(Enum):
    """DeepSeek R1 operation modes for different complexity levels"""

    REASONING = "reasoning"  # Full reasoning mode for complex parts
    FAST = "fast"  # Fast mode for simple parts
    CREATIVE = "creative"  # Creative mode for innovative designs
    TECHNICAL = "technical"  # Technical mode for precision parts


@dataclass
class DeepSeekConfig:
    """Configuration for DeepSeek R1 local instance"""

    host: str = "localhost"
    port: int = 11434
    model_name: str = "deepseek-r1:14b"
    timeout: int = 300
    max_tokens: int = 8192
    temperature: float = 0.1
    top_p: float = 0.95
    reasoning_enabled: bool = True
    stream: bool = False


@dataclass
class ReasoningStep:
    """Individual reasoning step from DeepSeek R1"""

    step_id: int
    description: str
    code_snippet: Optional[str]
    reasoning: str
    confidence: float
    validation_status: str


@dataclass
class DeepSeekResponse:
    """Enhanced response from DeepSeek R1 with reasoning chain"""

    status: str
    generated_code: str
    reasoning_chain: List[ReasoningStep]
    confidence_score: float
    execution_time: float
    complexity_analysis: Dict[str, Any]
    optimization_suggestions: List[str]
    error_message: Optional[str] = None


class DeepSeekR1Client:
    """
    Client for interacting with locally running DeepSeek R1 model
    Specialized for complex FreeCAD part generation with reasoning capabilities
    """

    def __init__(self, config: Optional[DeepSeekConfig] = None):
        self.config = config or DeepSeekConfig()
        self.base_url = f"http://{self.config.host}:{self.config.port}"
        self.session = requests.Session()

        # Initialize connection
        self._verify_connection()

        # Performance tracking
        self.generation_history = []
        self.performance_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "average_response_time": 0.0,
            "average_confidence": 0.0,
        }

        logger.info(f"DeepSeek R1 Client initialized at {self.base_url}")

    def _verify_connection(self):
        """Verify connection to DeepSeek R1 local server"""
        try:
            # For Ollama, use the tags endpoint to verify connection
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check if our model is available
                models = [model["name"] for model in data.get("models", [])]
                if self.config.model_name in models:
                    logger.info(
                        f"✅ DeepSeek R1 connection verified - model {self.config.model_name} found"
                    )
                    return True
                else:
                    logger.warning(
                        f"⚠️ Model {self.config.model_name} not found. Available models: {models}"
                    )
                    return False
            else:
                logger.warning(
                    f"⚠️ DeepSeek R1 health check failed: {response.status_code}"
                )
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to connect to DeepSeek R1: {e}")
            raise ConnectionError(f"Cannot connect to DeepSeek R1 at {self.base_url}")

    def generate_complex_part(
        self,
        requirements: str,
        mode: DeepSeekMode = DeepSeekMode.REASONING,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> DeepSeekResponse:
        """
        Generate complex FreeCAD part using DeepSeek R1 with full reasoning chain

        Args:
            requirements: Natural language description of the part
            mode: Generation mode (reasoning, fast, creative, technical)
            context: Additional context (existing parts, materials, etc.)
            constraints: Design constraints (dimensions, tolerances, etc.)

        Returns:
            DeepSeekResponse with generated code and reasoning chain
        """
        start_time = time.time()
        self.performance_metrics["total_requests"] += 1

        try:
            # Prepare enhanced prompt for complex part generation
            prompt = self._build_complex_part_prompt(
                requirements, mode, context, constraints
            )

            # Make request to DeepSeek R1
            response = self._make_deepseek_request(prompt, mode)

            # Parse response and extract reasoning
            parsed_response = self._parse_deepseek_response(response)

            # Validate generated code
            validation_result = self._validate_generated_code(
                parsed_response.generated_code
            )

            # Update performance metrics
            execution_time = time.time() - start_time
            self._update_metrics(parsed_response, execution_time)

            # Store in history
            self._store_generation_history(
                requirements, parsed_response, execution_time
            )

            parsed_response.execution_time = execution_time

            logger.info(f"🎯 DeepSeek R1 generation completed in {execution_time:.2f}s")
            logger.info(f"   Confidence: {parsed_response.confidence_score:.2f}")
            logger.info(f"   Reasoning steps: {len(parsed_response.reasoning_chain)}")

            return parsed_response

        except Exception as e:
            logger.error(f"❌ DeepSeek R1 generation failed: {e}")
            return DeepSeekResponse(
                status="error",
                generated_code="",
                reasoning_chain=[],
                confidence_score=0.0,
                execution_time=time.time() - start_time,
                complexity_analysis={},
                optimization_suggestions=[],
                error_message=str(e),
            )

    def _analyze_requirement_complexity(self, requirements: str) -> str:
        """Analyze the complexity level of the requirement for adaptive prompting"""
        requirements_lower = requirements.lower()

        # Complex indicators
        complex_keywords = [
            "gear",
            "spring",
            "helical",
            "thread",
            "involute",
            "spiral",
            "assembly",
            "multiple parts",
            "complex curve",
            "organic shape",
            "parametric",
            "constraint",
            "pattern",
            "array",
        ]

        # Medium complexity indicators
        medium_keywords = [
            "hole",
            "cut",
            "boolean",
            "fillet",
            "chamfer",
            "bracket",
            "mount",
            "slot",
            "groove",
            "extrude",
            "revolve",
        ]

        # Basic shape indicators
        basic_keywords = [
            "cube",
            "box",
            "cylinder",
            "sphere",
            "cone",
            "torus",
            "simple",
            "basic",
            "primitive",
        ]

        if any(keyword in requirements_lower for keyword in complex_keywords):
            return "complex"
        elif any(keyword in requirements_lower for keyword in medium_keywords):
            return "medium"
        elif any(keyword in requirements_lower for keyword in basic_keywords):
            return "basic"
        else:
            return "medium"  # Default to medium complexity

    def _build_complex_part_prompt(
        self,
        requirements: str,
        mode: DeepSeekMode,
        context: Optional[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]],
    ) -> str:
        """Build optimized prompt for complex part generation with adaptive complexity"""

        # Analyze requirement complexity to adjust prompting strategy
        complexity_level = self._analyze_requirement_complexity(requirements)

        base_prompt = f"""You are an expert FreeCAD Python developer specializing in 3D part design.
You have deep knowledge of mechanical engineering, CAD principles, and advanced Python programming.

MODE: {mode.value.upper()}
COMPLEXITY LEVEL: {complexity_level.upper()}

TASK: Generate FreeCAD Python code for: {requirements}

REQUIREMENTS:
1. Create complete, executable FreeCAD Python code
2. **CRITICAL**: Always use the existing active document (App.ActiveDocument) - NEVER create new documents
3. Include proper error handling and validation
4. Add comprehensive comments explaining each step
5. Follow best practices for parametric design
6. Call doc.recompute() after creating objects to ensure proper updates
7. Use step-by-step approach for complex geometries

AVAILABLE FREECAD MODULES:
- FreeCAD (App, Base, Vector, Rotation, Placement)
- Part (primitives, boolean operations, complex shapes)
- PartDesign (sketches, pads, pockets, features)
- Draft (2D operations, wires, curves)
- Mesh (mesh operations)
- Path (CAM operations)

ADVANCED TECHNIQUES TO CONSIDER:
- Parametric constraints and relationships
- Complex boolean operations (fuse, cut, common)
- Sweep and loft operations for complex surfaces
- Pattern operations (linear, polar, rectangular)
- Fillet and chamfer operations
- Shell and thickness operations
- Multi-body assemblies"""

        # Add complexity-specific guidance
        if complexity_level == "basic":
            base_prompt += """

COMPLEXITY GUIDANCE - BASIC SHAPES:
- Focus on simple Part.makeXXX() functions
- Use basic boolean operations if needed
- Keep it simple and reliable
- Test each shape creation step"""

        elif complexity_level == "medium":
            base_prompt += """

COMPLEXITY GUIDANCE - MEDIUM COMPLEXITY:
- Combine basic shapes with boolean operations
- Use extrusion and revolution for custom profiles
- Build step-by-step: create profile, then extrude
- Add holes and cuts as separate operations"""

        elif complexity_level == "complex":
            base_prompt += """

COMPLEXITY GUIDANCE - COMPLEX SHAPES:
- Break down into simpler components
- Use 2D sketches as building blocks
- Consider approximations for very complex curves
- Test each step before proceeding
- For gears: use simplified tooth profiles or circular approximations
- For springs: use helical curves or simplified geometry"""

        if mode == DeepSeekMode.REASONING:
            base_prompt += (
                "\n\nPLEASE PROVIDE DETAILED REASONING FOR EACH DESIGN DECISION."
            )

        if context:
            try:
                # Convert any enum values to strings for JSON serialization
                serializable_context = {}
                for key, value in context.items():
                    if hasattr(value, "__dict__"):
                        serializable_context[key] = str(value)
                    elif isinstance(value, Enum):
                        serializable_context[key] = value.value
                    else:
                        serializable_context[key] = value
                base_prompt += (
                    f"\n\nCONTEXT:\n{json.dumps(serializable_context, indent=2)}"
                )
            except (TypeError, ValueError) as e:
                base_prompt += f"\n\nCONTEXT:\n{str(context)}"

        if constraints:
            try:
                # Convert any enum values to strings for JSON serialization
                serializable_constraints = {}
                for key, value in constraints.items():
                    if hasattr(value, "__dict__"):
                        serializable_constraints[key] = str(value)
                    elif isinstance(value, Enum):
                        serializable_constraints[key] = value.value
                    else:
                        serializable_constraints[key] = value
                base_prompt += f"\n\nCONSTRAINTS:\n{json.dumps(serializable_constraints, indent=2)}"
            except (TypeError, ValueError) as e:
                base_prompt += f"\n\nCONSTRAINTS:\n{str(constraints)}"

        base_prompt += """

CRITICAL FREECAD DOCUMENT PATTERN:
Follow this exact pattern for FreeCAD code:

```python
import FreeCAD as App
import Part
import math  # Use standard Python math, NOT FreeCAD.Math
# Other imports as needed

# ALWAYS use the existing active document - NEVER create new ones
doc = App.ActiveDocument
if not doc:
    print("❌ No active document available")
    exit()

# BASIC SHAPES (most reliable):
# Cylinder: Part.makeCylinder(radius, height)
cylinder_shape = Part.makeCylinder(10, 20)

# Box: Part.makeBox(length, width, height)
box_shape = Part.makeBox(10, 10, 10)

# Sphere: Part.makeSphere(radius)
sphere_shape = Part.makeSphere(10)

# Cone: Part.makeCone(radius1, radius2, height)
cone_shape = Part.makeCone(5, 10, 20)

# 2D SHAPES (for complex geometries):
# Circle: Part.makeCircle(radius) - simple form
circle = Part.makeCircle(10)

# Circle with position: Part.makeCircle(radius, center_vector)
circle_pos = Part.makeCircle(5, App.Vector(10, 0, 0))

# COMPLEX SHAPES - Build step by step:
# 1. Create 2D profile
circle = Part.makeCircle(10)
wire = Part.Wire([circle])
face = Part.Face(wire)

# 2. Extrude to 3D
solid = face.extrude(App.Vector(0, 0, 20))

# BOOLEAN OPERATIONS:
# Cut: shape1.cut(shape2)
box = Part.makeBox(20, 20, 20)
hole = Part.makeCylinder(5, 25)
result = box.cut(hole)

# Add object to the existing document
obj = doc.addObject("Part::Feature", "YourObjectName")
obj.Shape = solid  # or any shape variable

# Set placement if needed
obj.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

# Handle ViewObject safely (may not exist in headless mode)
try:
    if hasattr(obj, 'ViewObject') and obj.ViewObject:
        obj.ViewObject.ShapeColor = (0.0, 1.0, 0.0)
except Exception:
    pass  # Ignore ViewObject errors in headless mode

# ALWAYS recompute after creating objects
doc.recompute()

print(f"✅ {obj.Label} created successfully!")
```

IMPORTANT API USAGE:
- Part.makeCylinder(radius, height) - NOT makeCylinder(radius, height, vector)
- Part.makeBox(length, width, height) - NOT makeBox(length, width, height, vector)
- Part.makeCircle(radius) for simple circles - NO keyword arguments
- Use standard Python math module: math.pi, math.sin(), math.cos(), math.sqrt()
- NEVER use FreeCAD.Math - it doesn't exist, use standard Python math
- For complex shapes: build 2D profile first, then extrude/revolve
- Boolean operations: shape1.cut(shape2), shape1.fuse(shape2), shape1.common(shape2)
- Always use try/except blocks for complex operations
- Test with simple shapes first, then build complexity

COMMON ERROR PATTERNS TO AVOID:
❌ Part.makeCircle(radius=10) - NO keyword arguments
✅ Part.makeCircle(10) - Positional arguments only
❌ FreeCAD.Math.pi - Does not exist
✅ math.pi - Use standard Python math
❌ Creating new documents with App.newDocument()
✅ Using existing App.ActiveDocument

OUTPUT FORMAT:
1. Brief analysis of the requirements
2. Step-by-step approach explanation
3. Complete FreeCAD Python code
4. Validation and testing suggestions

Please generate production-ready code that creates the requested complex part."""

        return base_prompt

    def _make_deepseek_request(self, prompt: str, mode: DeepSeekMode) -> Dict[str, Any]:
        """Make request to DeepSeek R1 local server (Ollama-compatible)"""

        # Adjust parameters based on mode
        if mode == DeepSeekMode.REASONING:
            temperature = 0.1
            max_tokens = 8192
        elif mode == DeepSeekMode.FAST:
            temperature = 0.05
            max_tokens = 4096
        elif mode == DeepSeekMode.CREATIVE:
            temperature = 0.3
            max_tokens = 6144
        else:  # TECHNICAL
            temperature = 0.05
            max_tokens = 8192

        # Try Ollama-style API first (port 11434)
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": self.config.top_p,
                "num_predict": max_tokens,
            },
        }

        try:
            # Try Ollama generate endpoint
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                return response.json()

        except requests.exceptions.RequestException:
            pass

        # Fallback to OpenAI-compatible API
        openai_payload = {
            "model": self.config.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert FreeCAD developer specializing in complex 3D part design and manufacturing.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": self.config.top_p,
            "stream": self.config.stream,
        }

        response = self.session.post(
            f"{self.base_url}/v1/chat/completions",
            json=openai_payload,
            timeout=self.config.timeout,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code != 200:
            raise Exception(
                f"DeepSeek R1 request failed: {response.status_code} - {response.text}"
            )

        return response.json()

    def _parse_deepseek_response(self, response: Dict[str, Any]) -> DeepSeekResponse:
        """Parse DeepSeek R1 response and extract reasoning chain"""

        try:
            # Handle Ollama-style response
            if "response" in response:
                content = response["response"]
                reasoning_chain = []

                # For Ollama, we don't get structured reasoning, so we'll create basic steps
                reasoning_chain.append(
                    ReasoningStep(
                        step_id=0,
                        description="Generate FreeCAD code",
                        code_snippet=None,
                        reasoning="Generated using DeepSeek R1 via Ollama",
                        confidence=0.85,
                        validation_status="generated",
                    )
                )

            # Handle OpenAI-compatible response
            elif "choices" in response:
                choice = response["choices"][0]
                message = choice["message"]
                content = message["content"]

                # Extract reasoning chain if available
                reasoning_chain = []
                if "reasoning" in message:
                    reasoning_data = message["reasoning"]
                    for i, step in enumerate(reasoning_data.get("steps", [])):
                        reasoning_step = ReasoningStep(
                            step_id=i,
                            description=step.get("description", ""),
                            code_snippet=step.get("code", None),
                            reasoning=step.get("reasoning", ""),
                            confidence=step.get("confidence", 0.5),
                            validation_status=step.get("status", "unknown"),
                        )
                        reasoning_chain.append(reasoning_step)
            else:
                raise ValueError("Unknown response format")

            # Extract code from content
            generated_code = self._extract_code_from_content(content)

            # Calculate confidence based on various factors
            confidence_score = self._calculate_confidence_from_content(
                content, reasoning_chain
            )

            # Analyze complexity
            complexity_analysis = self._analyze_code_complexity(generated_code)

            # Generate optimization suggestions
            optimization_suggestions = self._generate_optimization_suggestions(
                generated_code, complexity_analysis
            )

            return DeepSeekResponse(
                status="success",
                generated_code=generated_code,
                reasoning_chain=reasoning_chain,
                confidence_score=confidence_score,
                execution_time=0.0,  # Will be set by caller
                complexity_analysis=complexity_analysis,
                optimization_suggestions=optimization_suggestions,
            )

        except Exception as e:
            logger.error(f"Failed to parse DeepSeek response: {e}")
            raise

    def _extract_code_from_content(self, content: str) -> str:
        """Extract Python code from response content"""

        # Look for code blocks
        if "```python" in content:
            start = content.find("```python") + 9
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()

        # Look for any code block
        if "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                code = content[start:end].strip()
                # Check if it looks like Python
                if any(
                    keyword in code for keyword in ["import", "def", "FreeCAD", "Part"]
                ):
                    return code

        # Fallback: try to find Python-like content
        lines = content.split("\n")
        code_lines = []
        in_code_section = False

        for line in lines:
            line = line.strip()
            if any(
                keyword in line
                for keyword in ["import FreeCAD", "import Part", "def ", "doc = "]
            ):
                in_code_section = True

            if in_code_section:
                code_lines.append(line)

                # Stop if we hit non-code content
                if (
                    line
                    and not line.startswith("#")
                    and not any(
                        char in line
                        for char in [
                            "=",
                            "(",
                            ")",
                            ".",
                            "import",
                            "def",
                            "if",
                            "for",
                            "try",
                        ]
                    )
                ):
                    if not any(
                        keyword in line for keyword in ["FreeCAD", "Part", "doc", "obj"]
                    ):
                        break

        return "\n".join(code_lines) if code_lines else content

    def _calculate_confidence_from_content(
        self, content: str, reasoning_chain: List[ReasoningStep]
    ) -> float:
        """Calculate confidence score from content and reasoning chain"""

        base_confidence = 0.7

        # Adjust based on content quality
        if len(content) > 500:  # Substantial response
            base_confidence += 0.05
        if "import FreeCAD" in content and "doc.recompute()" in content:
            base_confidence += 0.1
        if "def " in content:  # Has functions
            base_confidence += 0.05

        # Adjust based on reasoning quality
        if reasoning_chain:
            avg_reasoning_confidence = sum(
                step.confidence for step in reasoning_chain
            ) / len(reasoning_chain)
            base_confidence = (base_confidence + avg_reasoning_confidence) / 2

        return min(1.0, max(0.0, base_confidence))

    def _calculate_confidence(
        self, choice: Dict, reasoning_chain: List[ReasoningStep]
    ) -> float:
        """Calculate confidence score for the generated response"""

        base_confidence = 0.7

        # Adjust based on finish reason
        finish_reason = choice.get("finish_reason", "unknown")
        if finish_reason == "stop":
            base_confidence += 0.1
        elif finish_reason == "length":
            base_confidence -= 0.1

        # Adjust based on reasoning quality
        if reasoning_chain:
            avg_reasoning_confidence = sum(
                step.confidence for step in reasoning_chain
            ) / len(reasoning_chain)
            base_confidence = (base_confidence + avg_reasoning_confidence) / 2

        # Adjust based on response completeness
        if choice.get("message", {}).get("content", ""):
            content = choice["message"]["content"]
            if len(content) > 500:  # Substantial response
                base_confidence += 0.05
            if "import FreeCAD" in content and "doc.recompute()" in content:
                base_confidence += 0.1

        return min(1.0, max(0.0, base_confidence))

    def _analyze_code_complexity(self, code: str) -> Dict[str, Any]:
        """Analyze complexity of generated code"""

        lines = code.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # Count different types of operations
        imports = len([line for line in lines if "import" in line])
        function_defs = len([line for line in lines if "def " in line])
        objects_created = len([line for line in lines if ".addObject(" in line])
        boolean_ops = len(
            [
                line
                for line in lines
                if any(op in line for op in ["fuse", "cut", "common"])
            ]
        )
        advanced_features = len(
            [
                line
                for line in lines
                if any(
                    feature in line
                    for feature in ["Sketch", "Pad", "Pocket", "Fillet", "Chamfer"]
                )
            ]
        )

        # Calculate complexity score
        complexity_score = (
            len(non_empty_lines) * 0.1
            + objects_created * 0.5
            + boolean_ops * 1.0
            + advanced_features * 1.5
            + function_defs * 0.8
        )

        return {
            "line_count": len(non_empty_lines),
            "import_count": imports,
            "function_count": function_defs,
            "object_count": objects_created,
            "boolean_operation_count": boolean_ops,
            "advanced_feature_count": advanced_features,
            "complexity_score": min(10.0, complexity_score),
            "estimated_execution_time": complexity_score * 2,  # seconds
            "skill_level_required": self._determine_skill_level(complexity_score),
        }

    def _determine_skill_level(self, complexity_score: float) -> str:
        """Determine required skill level based on complexity"""
        if complexity_score < 2:
            return "beginner"
        elif complexity_score < 5:
            return "intermediate"
        elif complexity_score < 8:
            return "advanced"
        else:
            return "expert"

    def _generate_optimization_suggestions(
        self, code: str, complexity: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization suggestions for the code"""
        suggestions = []

        # Check for common optimization opportunities
        if complexity["object_count"] > 10:
            suggestions.append(
                "Consider grouping related objects for better organization"
            )

        if complexity["boolean_operation_count"] > 5:
            suggestions.append("Review boolean operations for potential simplification")

        if "doc.recompute()" not in code:
            suggestions.append("Add doc.recompute() to ensure proper model updates")

        if "try:" not in code:
            suggestions.append("Add error handling for more robust execution")

        # Check for performance improvements
        lines = code.split("\n")
        if len([line for line in lines if "for " in line]) > 3:
            suggestions.append("Consider vectorizing loops for better performance")

        # Check for best practices
        if not any("def " in line for line in lines):
            suggestions.append(
                "Consider organizing code into functions for reusability"
            )

        return suggestions

    def _validate_generated_code(self, code: str) -> Dict[str, Any]:
        """Validate the generated FreeCAD code"""
        validation_result = {
            "syntax_valid": False,
            "imports_valid": False,
            "freecad_valid": False,
            "executable": False,
            "issues": [],
        }

        try:
            # Basic syntax validation
            compile(code, "<string>", "exec")
            validation_result["syntax_valid"] = True
        except SyntaxError as e:
            validation_result["issues"].append(f"Syntax error: {e}")

        # Check for required imports
        if "import FreeCAD" in code or "import App" in code:
            validation_result["imports_valid"] = True
        else:
            validation_result["issues"].append("Missing FreeCAD import")

        # Check for FreeCAD-specific patterns
        freecad_patterns = ["newDocument", "addObject", "recompute", "ActiveDocument"]
        if any(pattern in code for pattern in freecad_patterns):
            validation_result["freecad_valid"] = True
        else:
            validation_result["issues"].append("No FreeCAD operations detected")

        # Overall executability assessment
        validation_result["executable"] = (
            validation_result["syntax_valid"]
            and validation_result["imports_valid"]
            and validation_result["freecad_valid"]
        )

        return validation_result

    def _update_metrics(self, response: DeepSeekResponse, execution_time: float):
        """Update performance metrics"""
        if response.status == "success":
            self.performance_metrics["successful_requests"] += 1

        # Update averages
        total = self.performance_metrics["total_requests"]

        self.performance_metrics["average_response_time"] = (
            self.performance_metrics["average_response_time"] * (total - 1)
            + execution_time
        ) / total

        self.performance_metrics["average_confidence"] = (
            self.performance_metrics["average_confidence"] * (total - 1)
            + response.confidence_score
        ) / total

    def _store_generation_history(
        self, requirements: str, response: DeepSeekResponse, execution_time: float
    ):
        """Store generation history for analysis"""
        history_entry = {
            "timestamp": time.time(),
            "requirements": requirements,
            "success": response.status == "success",
            "confidence": response.confidence_score,
            "execution_time": execution_time,
            "complexity_score": response.complexity_analysis.get("complexity_score", 0),
            "reasoning_steps": len(response.reasoning_chain),
        }

        self.generation_history.append(history_entry)

        # Keep only last 100 entries
        if len(self.generation_history) > 100:
            self.generation_history = self.generation_history[-100:]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        success_rate = 0.0
        if self.performance_metrics["total_requests"] > 0:
            success_rate = (
                self.performance_metrics["successful_requests"]
                / self.performance_metrics["total_requests"]
            )

        return {
            **self.performance_metrics,
            "success_rate": success_rate,
            "history_entries": len(self.generation_history),
        }

    def get_reasoning_insights(self) -> Dict[str, Any]:
        """Get insights from reasoning patterns"""
        if not self.generation_history:
            return {"insights": []}

        recent_entries = self.generation_history[-20:]  # Last 20 generations

        avg_reasoning_steps = sum(
            entry["reasoning_steps"] for entry in recent_entries
        ) / len(recent_entries)
        avg_complexity = sum(
            entry["complexity_score"] for entry in recent_entries
        ) / len(recent_entries)

        insights = []

        if avg_reasoning_steps > 5:
            insights.append("Model is using detailed reasoning for complex problems")

        if avg_complexity > 5:
            insights.append("Recent generations are increasingly complex")

        high_confidence_count = len(
            [e for e in recent_entries if e["confidence"] > 0.8]
        )
        if high_confidence_count / len(recent_entries) > 0.7:
            insights.append("Model shows high confidence in recent generations")

        return {
            "average_reasoning_steps": avg_reasoning_steps,
            "average_complexity": avg_complexity,
            "high_confidence_rate": high_confidence_count / len(recent_entries),
            "insights": insights,
        }

"""
DeepSeek R1 Local Client for FreeCAD Complex Part Generation
Integrates with locally running DeepSeek R1 model for advanced 3D design generation
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

    def _build_complex_part_prompt(
        self,
        requirements: str,
        mode: DeepSeekMode,
        context: Optional[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]],
    ) -> str:
        """Build optimized prompt for complex part generation"""

        base_prompt = f"""You are an expert FreeCAD Python developer specializing in complex 3D part design.
You have deep knowledge of mechanical engineering, CAD principles, and advanced Python programming.

MODE: {mode.value.upper()}

TASK: Generate FreeCAD Python code for: {requirements}

REQUIREMENTS:
1. Create complete, executable FreeCAD Python code
2. Use advanced FreeCAD features for complex geometries
3. Include proper error handling and validation
4. Add comprehensive comments explaining each step
5. Follow best practices for parametric design
6. Optimize for manufacturability when possible

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

        if mode == DeepSeekMode.REASONING:
            base_prompt += (
                "\n\nPLEASE PROVIDE DETAILED REASONING FOR EACH DESIGN DECISION."
            )

        if context:
            base_prompt += f"\n\nCONTEXT:\n{json.dumps(context, indent=2)}"

        if constraints:
            base_prompt += f"\n\nCONSTRAINTS:\n{json.dumps(constraints, indent=2)}"

        base_prompt += """

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


class DeepSeekIntegrationManager:
    """
    Manager class for integrating DeepSeek R1 with the existing FreeCAD system
    Provides seamless fallback and hybrid operation modes
    """

    def __init__(self, deepseek_client: DeepSeekR1Client, fallback_client=None):
        self.deepseek_client = deepseek_client
        self.fallback_client = fallback_client
        self.integration_metrics = {
            "deepseek_requests": 0,
            "fallback_requests": 0,
            "hybrid_requests": 0,
        }

        logger.info("DeepSeek Integration Manager initialized")

    def generate_command(self, nl_command: str, state=None, mode: str = "auto") -> str:
        """
        Generate FreeCAD command with intelligent mode selection

        Args:
            nl_command: Natural language command
            state: Current FreeCAD state
            mode: "deepseek", "fallback", "hybrid", or "auto"

        Returns:
            Generated FreeCAD Python code
        """

        if mode == "auto":
            mode = self._select_optimal_mode(nl_command, state)

        try:
            if mode == "deepseek":
                return self._generate_with_deepseek(nl_command, state)
            elif mode == "hybrid":
                return self._generate_hybrid(nl_command, state)
            else:  # fallback
                return self._generate_with_fallback(nl_command, state)

        except Exception as e:
            logger.warning(f"Generation failed with mode {mode}, trying fallback: {e}")
            return self._generate_with_fallback(nl_command, state)

    def _select_optimal_mode(self, nl_command: str, state) -> str:
        """Select optimal generation mode based on command complexity"""

        # Analyze command complexity
        complexity_indicators = [
            "complex",
            "advanced",
            "intricate",
            "assembly",
            "gear",
            "mechanism",
            "optimization",
            "parametric",
            "pattern",
            "array",
            "sweep",
            "loft",
        ]

        command_lower = nl_command.lower()
        complexity_score = sum(
            1 for indicator in complexity_indicators if indicator in command_lower
        )

        # Check if DeepSeek is available
        try:
            self.deepseek_client._verify_connection()
            deepseek_available = True
        except:
            deepseek_available = False

        # Decision logic
        if not deepseek_available:
            return "fallback"
        elif complexity_score >= 2:
            return "deepseek"
        elif complexity_score == 1:
            return "hybrid"
        else:
            return "fallback"

    def _generate_with_deepseek(self, nl_command: str, state) -> str:
        """Generate using DeepSeek R1"""
        self.integration_metrics["deepseek_requests"] += 1

        # Determine appropriate mode based on command
        if any(
            word in nl_command.lower()
            for word in ["creative", "innovative", "artistic"]
        ):
            mode = DeepSeekMode.CREATIVE
        elif any(
            word in nl_command.lower() for word in ["precise", "accurate", "technical"]
        ):
            mode = DeepSeekMode.TECHNICAL
        elif any(word in nl_command.lower() for word in ["quick", "fast", "simple"]):
            mode = DeepSeekMode.FAST
        else:
            mode = DeepSeekMode.REASONING

        # Prepare context
        context = {"freecad_state": state} if state else None

        # Generate with DeepSeek
        response = self.deepseek_client.generate_complex_part(
            requirements=nl_command, mode=mode, context=context
        )

        if response.status == "success":
            return response.generated_code
        else:
            raise Exception(f"DeepSeek generation failed: {response.error_message}")

    def _generate_with_fallback(self, nl_command: str, state) -> str:
        """Generate using fallback client"""
        self.integration_metrics["fallback_requests"] += 1

        if self.fallback_client:
            return self.fallback_client.generate_command(nl_command, state)
        else:
            # Emergency fallback
            return f"""
# Emergency fallback for: {nl_command}
import FreeCAD as App
import Part

doc = App.ActiveDocument or App.newDocument()
box = doc.addObject('Part::Box', 'EmergencyBox')
box.Length = 10
box.Width = 10
box.Height = 10
doc.recompute()
"""

    def _generate_hybrid(self, nl_command: str, state) -> str:
        """Generate using hybrid approach (DeepSeek + fallback validation)"""
        self.integration_metrics["hybrid_requests"] += 1

        try:
            # Try DeepSeek first
            deepseek_code = self._generate_with_deepseek(nl_command, state)

            # Validate with fallback if available
            if self.fallback_client:
                fallback_code = self._generate_with_fallback(nl_command, state)

                # Compare and potentially merge approaches
                return self._merge_solutions(deepseek_code, fallback_code, nl_command)
            else:
                return deepseek_code

        except Exception as e:
            logger.warning(f"Hybrid generation failed, using fallback: {e}")
            return self._generate_with_fallback(nl_command, state)

    def _merge_solutions(
        self, deepseek_code: str, fallback_code: str, nl_command: str
    ) -> str:
        """Intelligently merge solutions from different generators"""

        # For now, prefer DeepSeek for complex operations, fallback for simple ones
        if any(
            word in nl_command.lower() for word in ["complex", "advanced", "assembly"]
        ):
            return deepseek_code
        else:
            # Use fallback for simple operations
            return fallback_code

    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get integration performance metrics"""
        total_requests = sum(self.integration_metrics.values())

        return {
            **self.integration_metrics,
            "total_requests": total_requests,
            "deepseek_usage_rate": self.integration_metrics["deepseek_requests"]
            / max(1, total_requests),
            "fallback_usage_rate": self.integration_metrics["fallback_requests"]
            / max(1, total_requests),
            "hybrid_usage_rate": self.integration_metrics["hybrid_requests"]
            / max(1, total_requests),
            "deepseek_metrics": self.deepseek_client.get_performance_metrics(),
            "reasoning_insights": self.deepseek_client.get_reasoning_insights(),
        }

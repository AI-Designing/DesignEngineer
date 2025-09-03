"""
Enhanced Complex Shape Generator with Advanced AI Capabilities
Provides intelligent shape generation with quality prediction and optimization
"""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Import DeepSeek R1 integration
from ..llm.deepseek_client import (
    DeepSeekConfig,
    DeepSeekIntegrationManager,
    DeepSeekMode,
    DeepSeekR1Client,
    DeepSeekResponse,
)

# Import the advanced prompt engineering system
from .advanced_prompt_engine import EnhancedLLMIntegration, ProblemComplexity


class GenerationMode(Enum):
    """Enhanced generation modes for different use cases"""

    ADAPTIVE = "adaptive"
    PARALLEL = "parallel"
    INCREMENTAL = "incremental"
    TEMPLATE_BASED = "template_based"
    HYBRID = "hybrid"


class ComplexityLevel(Enum):
    """More granular complexity levels"""

    SIMPLE = 1
    BASIC = 2
    MODERATE = 3
    INTERMEDIATE = 4
    COMPLEX = 5
    ADVANCED = 6
    EXPERT = 7
    MASTER = 8
    ULTIMATE = 9
    IMPOSSIBLE = 10


@dataclass
class EnhancedGenerationStep:
    """Enhanced generation step with comprehensive metadata"""

    step_id: str
    description: str
    freecad_commands: List[str]
    dependencies: List[str]
    expected_objects: List[str]
    validation_criteria: Dict[str, Any]
    complexity_score: float
    estimated_time: float
    priority: int = 5  # 1-10, higher is more important
    parallelizable: bool = False
    fallback_commands: Optional[List[str]] = None
    quality_requirements: Optional[Dict[str, float]] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    success_probability: float = 0.8
    alternative_approaches: Optional[List[Dict]] = None


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics"""

    geometric_accuracy: float = 0.0
    design_consistency: float = 0.0
    aesthetic_quality: float = 0.0
    manufacturability: float = 0.0
    performance_score: float = 0.0
    overall_score: float = 0.0
    confidence_level: float = 0.0


@dataclass
class GenerationResult:
    """Enhanced generation result with comprehensive data"""

    status: str
    session_id: str
    generation_mode: str
    total_steps: int
    successful_steps: int
    failed_steps: int
    recovered_steps: int
    execution_time: float
    quality_metrics: QualityMetrics
    generated_objects: List[Dict]
    performance_data: Dict[str, Any]
    learned_patterns: List[Dict]
    recommendations: List[str]


class PatternLearningEngine:
    """AI engine for learning from generation patterns"""

    def __init__(self):
        self.pattern_database = {}
        self.success_patterns = []
        self.failure_patterns = []
        self.optimization_patterns = []

    def learn_from_generation(
        self,
        requirements: str,
        plan: List[EnhancedGenerationStep],
        result: GenerationResult,
    ):
        """Learn from a generation attempt"""
        pattern = {
            "requirements_hash": hash(requirements),
            "complexity_level": self._extract_complexity(requirements),
            "step_count": len(plan),
            "success_rate": (
                result.successful_steps / result.total_steps
                if result.total_steps > 0
                else 0
            ),
            "execution_time": result.execution_time,
            "quality_score": result.quality_metrics.overall_score,
            "generation_mode": result.generation_mode,
            "timestamp": time.time(),
        }

        if result.status == "success" and result.quality_metrics.overall_score > 0.8:
            self.success_patterns.append(pattern)
        elif result.status == "error" or result.quality_metrics.overall_score < 0.5:
            self.failure_patterns.append(pattern)

        # Store in database
        pattern_key = f"{pattern['complexity_level']}_{pattern['step_count']}"
        if pattern_key not in self.pattern_database:
            self.pattern_database[pattern_key] = []
        self.pattern_database[pattern_key].append(pattern)

    def find_similar_patterns(self, requirements: str) -> List[Dict]:
        """Find similar patterns from past generations"""
        complexity = self._extract_complexity(requirements)
        similar_patterns = []

        for pattern_key, patterns in self.pattern_database.items():
            for pattern in patterns:
                if abs(pattern["complexity_level"] - complexity) <= 1:
                    similarity_score = self._calculate_similarity(requirements, pattern)
                    if similarity_score > 0.6:
                        pattern["similarity_score"] = similarity_score
                        similar_patterns.append(pattern)

        # Sort by similarity and success rate
        similar_patterns.sort(
            key=lambda x: (x["similarity_score"], x.get("success_rate", 0)),
            reverse=True,
        )
        return similar_patterns[:5]  # Return top 5 similar patterns

    def get_optimization_suggestions(
        self, current_plan: List[EnhancedGenerationStep]
    ) -> List[Dict]:
        """Get optimization suggestions based on learned patterns"""
        suggestions = []

        # Analyze current plan
        plan_complexity = sum(step.complexity_score for step in current_plan)
        step_count = len(current_plan)

        # Find optimization patterns
        for pattern in self.optimization_patterns:
            if (
                abs(pattern["step_count"] - step_count) <= 2
                and abs(pattern["complexity_level"] - plan_complexity) <= 1
            ):
                suggestions.append(pattern["optimization"])

        return suggestions

    def _extract_complexity(self, requirements: str) -> int:
        """Extract complexity level from requirements"""
        # Simple heuristic - could be enhanced with NLP
        complexity_keywords = {
            "simple": 1,
            "basic": 2,
            "moderate": 3,
            "intermediate": 4,
            "complex": 5,
            "advanced": 6,
            "expert": 7,
            "master": 8,
            "ultimate": 9,
            "impossible": 10,
        }

        requirements_lower = requirements.lower()
        for keyword, level in complexity_keywords.items():
            if keyword in requirements_lower:
                return level

        # Default complexity based on length and keywords
        word_count = len(requirements.split())
        if word_count < 5:
            return 2
        elif word_count < 10:
            return 3
        elif word_count < 15:
            return 4
        else:
            return 5

    def _calculate_similarity(self, requirements: str, pattern: Dict) -> float:
        """Calculate similarity between current requirements and stored pattern"""
        # Simple similarity calculation - could be enhanced with semantic analysis
        current_hash = hash(requirements)
        pattern_hash = pattern["requirements_hash"]

        # For now, use a simple heuristic
        if current_hash == pattern_hash:
            return 1.0
        else:
            # Calculate based on complexity similarity
            complexity_similarity = (
                1.0
                - abs(
                    pattern["complexity_level"] - self._extract_complexity(requirements)
                )
                / 10.0
            )
            return max(0.0, complexity_similarity)


class QualityPredictor:
    """Predicts quality outcomes for generation steps"""

    def __init__(self):
        self.quality_models = {
            "geometric": self._geometric_quality_model,
            "aesthetic": self._aesthetic_quality_model,
            "performance": self._performance_quality_model,
        }
        self.historical_data = []

    def predict_step_quality(
        self, step: EnhancedGenerationStep, execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict quality outcome for a generation step"""

        # Base prediction on step complexity and success probability
        base_quality = min(
            1.0, step.success_probability * (1.0 - step.complexity_score / 10.0)
        )

        # Adjust based on context
        context_factor = self._analyze_context_factors(execution_context)
        adjusted_quality = base_quality * context_factor

        # Calculate risk level
        risk_level = 1.0 - adjusted_quality

        prediction = {
            "predicted_quality": adjusted_quality,
            "risk_level": risk_level,
            "confidence": 0.7,  # Default confidence
            "risk_factors": self._identify_risk_factors(step, execution_context),
            "mitigation_suggestions": self._suggest_mitigations(risk_level, step),
        }

        return prediction

    def predict_overall_quality(
        self, plan: List[EnhancedGenerationStep], execution_context: Dict[str, Any]
    ) -> QualityMetrics:
        """Predict overall quality for the entire generation plan"""

        step_predictions = [
            self.predict_step_quality(step, execution_context) for step in plan
        ]

        # Calculate weighted average based on step importance
        total_weight = sum(step.priority for step in plan)
        weighted_quality = (
            sum(
                pred["predicted_quality"] * step.priority
                for pred, step in zip(step_predictions, plan)
            )
            / total_weight
            if total_weight > 0
            else 0.5
        )

        # Calculate individual quality dimensions
        geometric_quality = self._predict_geometric_quality(plan, step_predictions)
        aesthetic_quality = self._predict_aesthetic_quality(plan, step_predictions)
        performance_quality = self._predict_performance_quality(plan, step_predictions)

        return QualityMetrics(
            geometric_accuracy=geometric_quality,
            design_consistency=weighted_quality,
            aesthetic_quality=aesthetic_quality,
            manufacturability=min(1.0, weighted_quality * 1.1),
            performance_score=performance_quality,
            overall_score=weighted_quality,
            confidence_level=self._calculate_confidence(step_predictions),
        )

    def _analyze_context_factors(self, context: Dict[str, Any]) -> float:
        """Analyze context factors that affect quality"""
        factor = 1.0

        # System load factor
        system_load = context.get("system_load", 0.5)
        if system_load > 0.8:
            factor *= 0.9
        elif system_load < 0.3:
            factor *= 1.1

        # Memory availability
        memory_usage = context.get("memory_usage", 0.5)
        if memory_usage > 0.9:
            factor *= 0.8

        # Previous step success rate
        prev_success_rate = context.get("previous_success_rate", 1.0)
        factor *= 0.5 + 0.5 * prev_success_rate

        return min(1.2, max(0.5, factor))

    def _identify_risk_factors(
        self, step: EnhancedGenerationStep, context: Dict[str, Any]
    ) -> List[str]:
        """Identify potential risk factors for a step"""
        risks = []

        if step.complexity_score > 7:
            risks.append("High complexity step")

        if step.success_probability < 0.6:
            risks.append("Low success probability")

        if len(step.dependencies) > 3:
            risks.append("Many dependencies")

        if not step.fallback_commands:
            risks.append("No fallback strategy")

        if context.get("system_load", 0) > 0.8:
            risks.append("High system load")

        return risks

    def _suggest_mitigations(
        self, risk_level: float, step: EnhancedGenerationStep
    ) -> List[str]:
        """Suggest mitigation strategies based on risk level"""
        mitigations = []

        if risk_level > 0.7:
            mitigations.append("Consider breaking step into smaller parts")
            mitigations.append("Add additional validation checkpoints")
            mitigations.append("Prepare alternative execution strategies")

        if risk_level > 0.5:
            mitigations.append("Increase monitoring frequency")
            mitigations.append("Pre-validate step dependencies")

        if not step.fallback_commands:
            mitigations.append("Define fallback commands")

        return mitigations

    def _predict_geometric_quality(
        self, plan: List[EnhancedGenerationStep], predictions: List[Dict]
    ) -> float:
        """Predict geometric quality specifically"""
        # Simple geometric quality prediction
        avg_prediction = sum(p["predicted_quality"] for p in predictions) / len(
            predictions
        )

        # Adjust based on geometric complexity
        geometric_steps = [s for s in plan if "geometric" in s.description.lower()]
        if geometric_steps:
            geometric_complexity = sum(
                s.complexity_score for s in geometric_steps
            ) / len(geometric_steps)
            return avg_prediction * (1.0 - geometric_complexity / 20.0)

        return avg_prediction

    def _predict_aesthetic_quality(self, plan: List, predictions: List[Dict]) -> float:
        """Predict aesthetic quality specifically"""
        # Simple aesthetic quality prediction
        return sum(p["predicted_quality"] for p in predictions) / len(predictions)

    def _predict_performance_quality(
        self, plan: List[EnhancedGenerationStep], predictions: List[Dict]
    ) -> float:
        """Predict performance quality specifically"""
        # Consider step count and complexity for performance
        total_complexity = sum(s.complexity_score for s in plan)
        step_count = len(plan)

        performance_factor = 1.0 - (total_complexity / (step_count * 10.0))
        avg_prediction = sum(p["predicted_quality"] for p in predictions) / len(
            predictions
        )

        return avg_prediction * max(0.3, performance_factor)

    def _calculate_confidence(self, predictions: List[Dict]) -> float:
        """Calculate confidence level for predictions"""
        if not predictions:
            return 0.5

        confidences = [p.get("confidence", 0.5) for p in predictions]
        return sum(confidences) / len(confidences)

    def _geometric_quality_model(
        self, step: EnhancedGenerationStep, context: Dict[str, Any]
    ) -> float:
        """Model for geometric quality prediction"""
        # Base quality on step complexity and type
        base_quality = 0.8

        # Adjust for complexity
        complexity_penalty = step.complexity_score / 10.0
        base_quality *= 1.0 - complexity_penalty * 0.3

        # Adjust for geometric operations
        if "sketch" in step.description.lower():
            base_quality *= 0.9  # Sketches generally reliable
        elif "extrude" in step.description.lower() or "pad" in step.description.lower():
            base_quality *= 0.85  # Extrusions moderately reliable
        elif (
            "fillet" in step.description.lower()
            or "chamfer" in step.description.lower()
        ):
            base_quality *= 0.8  # Feature operations more complex

        return max(0.1, min(1.0, base_quality))

    def _aesthetic_quality_model(
        self, step: EnhancedGenerationStep, context: Dict[str, Any]
    ) -> float:
        """Model for aesthetic quality prediction"""
        # Base aesthetic quality
        base_quality = 0.7

        # Adjust for aesthetic-related operations
        if any(
            term in step.description.lower()
            for term in ["fillet", "chamfer", "smooth", "round"]
        ):
            base_quality *= 1.2  # Aesthetic operations improve quality

        return max(0.1, min(1.0, base_quality))

    def _performance_quality_model(
        self, step: EnhancedGenerationStep, context: Dict[str, Any]
    ) -> float:
        """Model for performance quality prediction"""
        # Base performance quality
        base_quality = 0.8

        # Adjust for execution time estimates
        if step.estimated_duration > 30:  # Long operations
            base_quality *= 0.9
        elif step.estimated_duration > 60:  # Very long operations
            base_quality *= 0.8

        # Adjust for dependency complexity
        dependency_penalty = len(step.dependencies) * 0.05
        base_quality *= 1.0 - dependency_penalty

        return max(0.1, min(1.0, base_quality))


class EnhancedComplexShapeGenerator:
    """
    Next-generation complex shape generator with advanced AI capabilities
    """

    def __init__(
        self,
        llm_client,
        state_analyzer,
        command_executor,
        state_cache=None,
        websocket_manager=None,
        use_deepseek=True,
        deepseek_config=None,
    ):
        self.llm_client = llm_client
        self.state_analyzer = state_analyzer
        self.command_executor = command_executor
        self.state_cache = state_cache
        self.websocket_manager = websocket_manager

        # Initialize logger first
        self.logger = logging.getLogger(__name__)

        # Initialize DeepSeek R1 integration
        self.use_deepseek = use_deepseek
        self.deepseek_client = None
        self.deepseek_manager = None

        if use_deepseek:
            try:
                self.deepseek_client = DeepSeekR1Client(
                    deepseek_config or DeepSeekConfig()
                )
                self.deepseek_manager = DeepSeekIntegrationManager(
                    self.deepseek_client, fallback_client=llm_client
                )
                self.logger.info("✅ DeepSeek R1 integration enabled")
            except Exception as e:
                self.logger.warning(f"⚠️ DeepSeek R1 initialization failed: {e}")
                self.logger.info("📝 Falling back to standard LLM client")
                self.use_deepseek = False

        # Initialize advanced prompt engineering system
        self.enhanced_llm = EnhancedLLMIntegration(llm_client)

        # Enhanced AI components
        self.pattern_learning = PatternLearningEngine()
        self.quality_predictor = QualityPredictor()

        # Session tracking
        self.active_sessions = {}

        # Performance metrics
        self.performance_metrics = {
            "total_generations": 0,
            "successful_generations": 0,
            "average_quality_score": 0.0,
            "average_execution_time": 0.0,
            "pattern_learning_accuracy": 0.0,
            "deepseek_generations": 0,
            "fallback_generations": 0,
        }

    def generate_enhanced_complex_shape(
        self,
        user_requirements: str,
        session_id: str,
        generation_mode: GenerationMode = GenerationMode.ADAPTIVE,
        quality_targets: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GenerationResult:
        """
        Enhanced complex shape generation with AI-powered optimization
        Uses the advanced prompt engineering system for superior code quality
        """
        start_time = time.time()
        self.logger.info(f"Starting enhanced generation for session {session_id}")

        # Initialize session tracking
        session_context = {
            "start_time": start_time,
            "requirements": user_requirements,
            "mode": generation_mode,
            "quality_targets": quality_targets or {},
            "context": context or {},
        }
        self.active_sessions[session_id] = session_context

        try:
            # Step 1: Use advanced prompt engineering for code generation
            self.logger.info("Using advanced prompt engineering system...")
            enhanced_generation = self._generate_with_advanced_prompts(
                user_requirements, session_context
            )

            # Step 2: Intelligent requirement analysis (legacy for comparison)
            requirement_analysis = self._analyze_requirements_intelligently(
                user_requirements
            )

            # Step 2: Pattern-based optimization
            similar_patterns = self.pattern_learning.find_similar_patterns(
                user_requirements
            )

            # Step 3: Select optimal generation mode
            if generation_mode == GenerationMode.ADAPTIVE:
                generation_mode = self._select_optimal_mode(
                    requirement_analysis, similar_patterns
                )

            # Step 4: Generate enhanced plan
            enhanced_plan = self._generate_enhanced_plan(
                user_requirements, requirement_analysis, similar_patterns
            )

            # Step 5: Quality prediction and optimization
            predicted_quality = self.quality_predictor.predict_overall_quality(
                enhanced_plan, session_context["context"]
            )

            if quality_targets:
                enhanced_plan = self._optimize_plan_for_quality(
                    enhanced_plan, quality_targets
                )

            # Step 6: Execute with real-time monitoring
            execution_result = self._execute_enhanced_plan(
                enhanced_plan, session_id, generation_mode, predicted_quality
            )

            # Step 7: Calculate final metrics
            execution_time = time.time() - start_time
            final_quality = self._calculate_final_quality(execution_result)

            # Step 8: Learn from results
            generation_result = GenerationResult(
                status="success",
                session_id=session_id,
                generation_mode=generation_mode.value,
                total_steps=len(enhanced_plan),
                successful_steps=execution_result.get("successful_steps", 0),
                failed_steps=execution_result.get("failed_steps", 0),
                recovered_steps=execution_result.get("recovered_steps", 0),
                execution_time=execution_time,
                quality_metrics=final_quality,
                generated_objects=execution_result.get("generated_objects", []),
                performance_data=execution_result.get("performance_data", {}),
                learned_patterns=[],
                recommendations=self._generate_recommendations(execution_result),
            )

            # Learn from this generation
            self.pattern_learning.learn_from_generation(
                user_requirements, enhanced_plan, generation_result
            )

            # Update performance metrics
            self._update_performance_metrics(generation_result)

            # Send final update via WebSocket
            if self.websocket_manager:
                self._send_generation_complete(session_id, generation_result)

            return generation_result

        except Exception as e:
            self.logger.error(f"Enhanced generation failed: {str(e)}", exc_info=True)

            error_result = GenerationResult(
                status="error",
                session_id=session_id,
                generation_mode=(
                    generation_mode.value
                    if isinstance(generation_mode, GenerationMode)
                    else str(generation_mode)
                ),
                total_steps=0,
                successful_steps=0,
                failed_steps=1,
                recovered_steps=0,
                execution_time=time.time() - start_time,
                quality_metrics=QualityMetrics(),
                generated_objects=[],
                performance_data={},
                learned_patterns=[],
                recommendations=[f"Error occurred: {str(e)}"],
            )

            return error_result

        finally:
            # Clean up session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

    def _analyze_requirements_intelligently(self, requirements: str) -> Dict[str, Any]:
        """Enhanced requirement analysis with NLP and pattern recognition"""

        # Extract key entities and relationships
        entities = self._extract_entities(requirements)
        relationships = self._extract_relationships(requirements)

        # Analyze complexity
        complexity_score = self._calculate_complexity_score(requirements, entities)

        # Estimate resource requirements
        resource_estimate = self._estimate_resources(complexity_score, len(entities))

        # Identify potential challenges
        challenges = self._identify_challenges(requirements, entities, relationships)

        return {
            "entities": entities,
            "relationships": relationships,
            "complexity_score": complexity_score,
            "estimated_steps": max(3, len(entities) * 2),
            "estimated_time": complexity_score * 30,  # seconds
            "resource_estimate": resource_estimate,
            "challenges": challenges,
            "confidence": 0.8,
        }

    def _estimate_resources(
        self, complexity_score: float, entity_count: int
    ) -> Dict[str, Any]:
        """Estimate computational and time resources needed"""

        # Base estimates
        base_memory_mb = 50  # Base memory requirement
        base_time_seconds = 10  # Base execution time

        # Scale with complexity
        memory_mb = base_memory_mb + (complexity_score * 20) + (entity_count * 5)
        time_seconds = base_time_seconds + (complexity_score * 5) + (entity_count * 2)

        # CPU usage estimate (percentage)
        cpu_usage = min(90, 20 + (complexity_score * 10))

        return {
            "estimated_memory_mb": memory_mb,
            "estimated_time_seconds": time_seconds,
            "estimated_cpu_usage_percent": cpu_usage,
            "recommended_timeout": max(60, time_seconds * 2),
            "resource_level": (
                "low"
                if complexity_score < 3
                else "medium"
                if complexity_score < 7
                else "high"
            ),
        }

    def _extract_entities(self, requirements: str) -> List[Dict[str, Any]]:
        """Extract design entities from requirements"""
        entities = []

        # Common CAD entities
        cad_entities = {
            "box": {"type": "primitive", "complexity": 1},
            "cube": {"type": "primitive", "complexity": 1},
            "cylinder": {"type": "primitive", "complexity": 2},
            "sphere": {"type": "primitive", "complexity": 2},
            "cone": {"type": "primitive", "complexity": 2},
            "tower": {"type": "assembly", "complexity": 5},
            "building": {"type": "assembly", "complexity": 7},
            "house": {"type": "assembly", "complexity": 6},
            "gear": {"type": "mechanical", "complexity": 6},
            "shaft": {"type": "mechanical", "complexity": 3},
            "bearing": {"type": "mechanical", "complexity": 4},
        }

        requirements_lower = requirements.lower()
        for entity_name, entity_info in cad_entities.items():
            if entity_name in requirements_lower:
                entities.append(
                    {
                        "name": entity_name,
                        "type": entity_info["type"],
                        "complexity": entity_info["complexity"],
                    }
                )

        return entities

    def _extract_relationships(self, requirements: str) -> List[Dict[str, Any]]:
        """Extract relationships between entities"""
        relationships = []

        relationship_keywords = {
            "on top of": "stacked",
            "next to": "adjacent",
            "inside": "contained",
            "connected": "joined",
            "attached": "joined",
            "combined": "merged",
        }

        requirements_lower = requirements.lower()
        for keyword, relationship_type in relationship_keywords.items():
            if keyword in requirements_lower:
                relationships.append(
                    {
                        "type": relationship_type,
                        "keyword": keyword,
                        "complexity": (
                            2 if relationship_type in ["joined", "merged"] else 1
                        ),
                    }
                )

        return relationships

    def _calculate_complexity_score(
        self, requirements: str, entities: List[Dict]
    ) -> float:
        """Calculate overall complexity score"""
        if not entities:
            return 3.0  # Default moderate complexity

        # Base complexity from entities
        entity_complexity = sum(e["complexity"] for e in entities)

        # Adjust for requirement length and sophistication
        word_count = len(requirements.split())
        length_factor = min(2.0, word_count / 10.0)

        # Check for advanced keywords
        advanced_keywords = [
            "parametric",
            "optimized",
            "complex",
            "advanced",
            "intricate",
        ]
        advanced_count = sum(
            1 for keyword in advanced_keywords if keyword in requirements.lower()
        )
        advanced_factor = 1.0 + (advanced_count * 0.5)

        final_complexity = entity_complexity * length_factor * advanced_factor
        return min(10.0, max(1.0, final_complexity))

    def _select_optimal_mode(
        self, analysis: Dict[str, Any], patterns: List[Dict]
    ) -> GenerationMode:
        """Select optimal generation mode based on analysis and patterns"""
        complexity = analysis["complexity_score"]
        entity_count = len(analysis["entities"])

        # Check patterns for mode recommendations
        if patterns:
            successful_modes = [
                p.get("generation_mode")
                for p in patterns[:3]
                if p.get("success_rate", 0) > 0.8
            ]
            if successful_modes:
                mode_counts = {}
                for mode in successful_modes:
                    mode_counts[mode] = mode_counts.get(mode, 0) + 1
                best_mode = max(mode_counts.items(), key=lambda x: x[1])[0]
                try:
                    return GenerationMode(best_mode)
                except ValueError:
                    pass

        # Default mode selection logic
        if complexity >= 8 or entity_count > 5:
            return GenerationMode.PARALLEL
        elif complexity >= 6:
            return GenerationMode.INCREMENTAL
        elif entity_count > 3:
            return GenerationMode.TEMPLATE_BASED
        else:
            return GenerationMode.ADAPTIVE

    def _send_generation_complete(self, session_id: str, result: GenerationResult):
        """Send generation completion notification via WebSocket"""
        if self.websocket_manager:
            try:
                self.websocket_manager.send_user_notification(
                    f"Complex shape generation completed! Quality score: {result.quality_metrics.overall_score:.2f}",
                    "success",
                    session_id,
                )
            except Exception as e:
                self.logger.warning(f"Failed to send WebSocket notification: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics including DeepSeek stats"""
        base_metrics = {
            **self.performance_metrics,
            "active_sessions": len(self.active_sessions),
            "pattern_database_size": len(self.pattern_learning.pattern_database),
            "success_patterns": len(self.pattern_learning.success_patterns),
            "failure_patterns": len(self.pattern_learning.failure_patterns),
        }

        # Add DeepSeek metrics if available
        if self.use_deepseek and self.deepseek_manager:
            try:
                deepseek_metrics = self.deepseek_manager.get_integration_metrics()
                base_metrics["deepseek_integration"] = deepseek_metrics
                base_metrics["deepseek_available"] = True
            except Exception as e:
                self.logger.warning(f"Failed to get DeepSeek metrics: {e}")
                base_metrics["deepseek_available"] = False
        else:
            base_metrics["deepseek_available"] = False

        return base_metrics

    def get_deepseek_insights(self) -> Dict[str, Any]:
        """Get DeepSeek-specific insights and reasoning patterns"""
        if not (self.use_deepseek and self.deepseek_client):
            return {"available": False, "message": "DeepSeek R1 not available"}

        try:
            return {
                "available": True,
                "performance_metrics": self.deepseek_client.get_performance_metrics(),
                "reasoning_insights": self.deepseek_client.get_reasoning_insights(),
                "integration_stats": (
                    self.deepseek_manager.get_integration_metrics()
                    if self.deepseek_manager
                    else {}
                ),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def force_deepseek_mode(self, enable: bool = True):
        """Force enable or disable DeepSeek mode"""
        if enable and not self.use_deepseek:
            try:
                self.deepseek_client = DeepSeekR1Client()
                self.deepseek_manager = DeepSeekIntegrationManager(
                    self.deepseek_client, fallback_client=self.llm_client
                )
                self.use_deepseek = True
                self.logger.info("✅ DeepSeek R1 force-enabled")
            except Exception as e:
                self.logger.error(f"❌ Failed to force-enable DeepSeek: {e}")
        elif not enable:
            self.use_deepseek = False
            self.logger.info("🔄 DeepSeek R1 disabled, using fallback")

    def test_deepseek_connection(self) -> Dict[str, Any]:
        """Test DeepSeek R1 connection and capabilities"""
        if not self.deepseek_client:
            return {
                "status": "not_initialized",
                "message": "DeepSeek client not initialized",
            }

        try:
            # Test with a simple part generation
            test_response = self.deepseek_client.generate_complex_part(
                requirements="Create a simple test cube with 10mm sides",
                mode=DeepSeekMode.FAST,
                context={"test": True},
            )

            return {
                "status": "success",
                "connection": True,
                "test_generation": {
                    "confidence": test_response.confidence_score,
                    "execution_time": test_response.execution_time,
                    "reasoning_steps": len(test_response.reasoning_chain),
                    "code_generated": bool(test_response.generated_code),
                },
                "capabilities": {
                    "reasoning_mode": True,
                    "creative_mode": True,
                    "technical_mode": True,
                    "fast_mode": True,
                },
            }
        except Exception as e:
            return {"status": "error", "connection": False, "error": str(e)}

    def _generate_with_advanced_prompts(
        self, user_requirements: str, session_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate code using the advanced prompt engineering system with DeepSeek R1 integration
        This is the core improvement: structured understand -> breakdown -> implement approach
        """
        self.logger.info("🧠 Starting advanced prompt-based code generation...")

        # Try DeepSeek R1 first if available
        if self.use_deepseek and self.deepseek_manager:
            try:
                return self._generate_with_deepseek_r1(
                    user_requirements, session_context
                )
            except Exception as e:
                self.logger.warning(f"⚠️ DeepSeek generation failed, falling back: {e}")
                self.performance_metrics["fallback_generations"] += 1

        # Fallback to enhanced LLM integration
        return self._generate_with_enhanced_llm(user_requirements, session_context)

    def _generate_with_deepseek_r1(
        self, user_requirements: str, session_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate complex parts using DeepSeek R1 with full reasoning capabilities
        """
        self.logger.info("🚀 Using DeepSeek R1 for complex part generation...")
        self.performance_metrics["deepseek_generations"] += 1

        # Analyze complexity to choose appropriate DeepSeek mode
        complexity_analysis = self._analyze_requirements_intelligently(
            user_requirements
        )
        complexity_score = complexity_analysis["complexity_score"]

        # Select DeepSeek mode based on complexity and requirements
        if complexity_score >= 8:
            mode = DeepSeekMode.REASONING  # Full reasoning for complex parts
        elif any(
            word in user_requirements.lower()
            for word in ["creative", "artistic", "innovative"]
        ):
            mode = DeepSeekMode.CREATIVE
        elif any(
            word in user_requirements.lower()
            for word in ["precise", "technical", "engineering"]
        ):
            mode = DeepSeekMode.TECHNICAL
        elif complexity_score <= 3:
            mode = DeepSeekMode.FAST
        else:
            mode = DeepSeekMode.REASONING

        # Prepare enhanced context for DeepSeek
        deepseek_context = {
            "session_id": session_context.get("session_id"),
            "generation_mode": session_context.get("mode", "adaptive"),
            "quality_targets": session_context.get("quality_targets", {}),
            "freecad_state": session_context.get("context", {}),
            "complexity_analysis": complexity_analysis,
            "similar_patterns": self.pattern_learning.find_similar_patterns(
                user_requirements
            ),
            "performance_constraints": self._get_performance_constraints(),
        }

        # Add manufacturing and design constraints
        constraints = {
            "dimensional_accuracy": 0.1,  # mm
            "surface_finish": "standard",
            "material_considerations": True,
            "manufacturability": True,
            "assembly_requirements": "consider_tolerances",
        }

        # Generate with DeepSeek R1
        deepseek_response = self.deepseek_client.generate_complex_part(
            requirements=user_requirements,
            mode=mode,
            context=deepseek_context,
            constraints=constraints,
        )

        if deepseek_response.status == "success":
            self.logger.info(f"✅ DeepSeek R1 generation successful:")
            self.logger.info(f"   Mode: {mode.value}")
            self.logger.info(f"   Confidence: {deepseek_response.confidence_score:.2f}")
            self.logger.info(
                f"   Reasoning steps: {len(deepseek_response.reasoning_chain)}"
            )
            self.logger.info(
                f"   Complexity score: {deepseek_response.complexity_analysis.get('complexity_score', 0):.1f}"
            )

            # Convert DeepSeek response to expected format
            return self._convert_deepseek_to_standard_format(
                deepseek_response, user_requirements
            )
        else:
            self.logger.error(
                f"❌ DeepSeek generation failed: {deepseek_response.error_message}"
            )
            raise Exception(
                f"DeepSeek generation failed: {deepseek_response.error_message}"
            )

    def _convert_deepseek_to_standard_format(
        self, deepseek_response: DeepSeekResponse, requirements: str
    ) -> Dict[str, Any]:
        """
        Convert DeepSeek response to the standard format expected by the system
        """
        # Extract main objective from requirements or reasoning
        main_objective = requirements
        if deepseek_response.reasoning_chain:
            # Try to get more refined objective from reasoning
            for step in deepseek_response.reasoning_chain:
                if (
                    "objective" in step.description.lower()
                    or "goal" in step.description.lower()
                ):
                    main_objective = step.description
                    break

        # Convert reasoning chain to breakdown format
        breakdown = []
        for i, step in enumerate(deepseek_response.reasoning_chain):
            breakdown.append(
                {
                    "step_number": i + 1,
                    "description": step.description,
                    "purpose": step.reasoning,
                    "code_snippet": step.code_snippet,
                    "confidence": step.confidence,
                    "validation_status": step.validation_status,
                }
            )

        # If no reasoning chain, create basic breakdown
        if not breakdown:
            breakdown = [
                {
                    "step_number": 1,
                    "description": "Generate complex FreeCAD part",
                    "purpose": f"Create the requested part: {requirements}",
                    "code_snippet": None,
                    "confidence": deepseek_response.confidence_score,
                    "validation_status": "generated",
                }
            ]

        return {
            "understanding": {
                "main_objective": main_objective,
                "complexity_level": deepseek_response.complexity_analysis.get(
                    "skill_level_required", "intermediate"
                ),
                "estimated_time": deepseek_response.complexity_analysis.get(
                    "estimated_execution_time", 60
                ),
                "reasoning_quality": (
                    "high" if len(deepseek_response.reasoning_chain) > 3 else "standard"
                ),
            },
            "breakdown": breakdown,
            "implementation": {
                "code": deepseek_response.generated_code,
                "explanation": f"DeepSeek R1 generated solution with {len(deepseek_response.reasoning_chain)} reasoning steps",
                "confidence_level": deepseek_response.confidence_score,
                "complexity_analysis": deepseek_response.complexity_analysis,
                "optimization_suggestions": deepseek_response.optimization_suggestions,
            },
            "validation": {
                "overall_quality_score": deepseek_response.confidence_score,
                "syntax_valid": True,  # DeepSeek validation should handle this
                "freecad_compatible": True,
                "reasoning_chain_quality": len(deepseek_response.reasoning_chain)
                / 10.0,  # Normalize to 0-1
                "performance_prediction": deepseek_response.complexity_analysis,
            },
            "final_code": deepseek_response.generated_code,
            "generation_method": "deepseek_r1",
            "deepseek_metadata": {
                "execution_time": deepseek_response.execution_time,
                "reasoning_chain": deepseek_response.reasoning_chain,
                "optimization_suggestions": deepseek_response.optimization_suggestions,
            },
        }

    def _generate_with_enhanced_llm(
        self, user_requirements: str, session_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback generation using enhanced LLM integration
        """
        self.logger.info("🔄 Using enhanced LLM integration (fallback)...")

        # Prepare context for the enhanced LLM system
        enhanced_context = {
            "session_id": session_context.get("session_id"),
            "generation_mode": session_context.get("mode", "adaptive"),
            "quality_targets": session_context.get("quality_targets", {}),
            "previous_attempts": self._get_session_history(session_context),
            "available_tools": self._get_available_freecad_tools(),
            "performance_constraints": self._get_performance_constraints(),
            "user_preferences": session_context.get("context", {}),
        }

        # Use the enhanced LLM integration for superior code generation
        try:
            generation_result = self.enhanced_llm.generate_enhanced_freecad_code(
                user_requirements, enhanced_context
            )

            self.logger.info(f"✅ Enhanced LLM generation completed:")
            self.logger.info(
                f"   Understanding: {generation_result.get('understanding', {}).get('main_objective', 'N/A')}"
            )
            self.logger.info(
                f"   Breakdown steps: {len(generation_result.get('breakdown', []))}"
            )
            self.logger.info(
                f"   Quality score: {generation_result.get('validation', {}).get('overall_quality_score', 0.0):.2f}"
            )

            return generation_result

        except Exception as e:
            self.logger.error(f"❌ Enhanced LLM generation failed: {e}")
            # Final fallback to basic generation
            return self._generate_with_basic_prompts(
                user_requirements, enhanced_context
            )

    def _generate_with_basic_prompts(
        self, user_requirements: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback basic code generation method
        """
        self.logger.info("🔄 Using fallback basic prompt generation...")

        basic_prompt = f"""
Create FreeCAD Python code for: {user_requirements}

Requirements:
- Use FreeCAD Python API
- Include error handling
- Add documentation
- Ensure code is executable

Generate complete Python code that creates the requested shape in FreeCAD.
"""

        try:
            response = self.llm_client.generate_response(basic_prompt)

            # Extract code from response
            code_start = response.find("```python")
            code_end = response.find("```", code_start + 9)

            if code_start != -1 and code_end != -1:
                code = response[code_start + 9 : code_end].strip()
            else:
                code = response

            return {
                "understanding": {
                    "main_objective": user_requirements,
                    "complexity_level": "moderate",
                },
                "breakdown": [
                    {
                        "description": "Generate basic FreeCAD code",
                        "purpose": "Create requested shape",
                    }
                ],
                "implementation": {
                    "code": code,
                    "explanation": "Basic code generation",
                    "confidence_level": 0.6,
                },
                "validation": {"overall_quality_score": 0.5, "syntax_valid": True},
                "final_code": code,
                "generation_method": "basic_fallback",
            }

        except Exception as e:
            self.logger.error(f"❌ Basic prompt generation also failed: {e}")
            return self._create_emergency_fallback(user_requirements)

    def _create_emergency_fallback(self, user_requirements: str) -> Dict[str, Any]:
        """
        Emergency fallback when all generation methods fail
        """
        fallback_code = f'''
import FreeCAD
import Part

def create_emergency_shape():
    """
    Emergency fallback shape creation
    Requirements: {user_requirements}
    """
    try:
        doc = FreeCAD.newDocument("EmergencyShape")

        # Create a basic box as fallback
        box = Part.makeBox(10, 10, 10)
        box_obj = doc.addObject("Part::Feature", "EmergencyBox")
        box_obj.Shape = box

        doc.recompute()
        return {{"status": "success", "message": "Emergency fallback shape created"}}

    except Exception as e:
        return {{"status": "error", "error": str(e)}}

if __name__ == "__main__":
    result = create_emergency_shape()
    print(f"Emergency result: {{result}}")
'''

        return {
            "understanding": {
                "main_objective": f"Emergency fallback for: {user_requirements}",
                "complexity_level": "simple",
            },
            "breakdown": [
                {
                    "description": "Create emergency fallback shape",
                    "purpose": "Ensure system continues to function",
                }
            ],
            "implementation": {
                "code": fallback_code,
                "explanation": "Emergency fallback implementation",
                "confidence_level": 0.3,
            },
            "validation": {"overall_quality_score": 0.3, "syntax_valid": True},
            "final_code": fallback_code,
            "generation_method": "emergency_fallback",
        }

    def _get_session_history(
        self, session_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get historical data for the current session"""
        session_id = session_context.get("session_id")
        if not session_id:
            return []

        # Return recent attempts for this session
        history = []
        for entry in self.generation_history[-10:]:  # Last 10 attempts
            if entry.get("session_id") == session_id:
                history.append(
                    {
                        "requirements": entry.get("requirements"),
                        "success": entry.get("success", False),
                        "quality_score": entry.get("quality_score", 0.0),
                        "issues": entry.get("issues", []),
                    }
                )

        return history

    def _get_available_freecad_tools(self) -> List[str]:
        """Get list of available FreeCAD tools and operations"""
        return [
            "Part.makeBox()",
            "Part.makeCylinder()",
            "Part.makeSphere()",
            "Part.makeCone()",
            "Part.makeTorus()",
            "Part.makeWedge()",
            "Part.fuse()",
            "Part.cut()",
            "Part.common()",
            "Draft.makeWire()",
            "Draft.makeLine()",
            "Draft.makeCircle()",
            "Sketcher.Sketch",
            "PartDesign.Pad",
            "PartDesign.Pocket",
            "doc.addObject()",
            "doc.recompute()",
            "obj.Placement",
            "FreeCAD.Vector()",
            "FreeCAD.Rotation()",
            "FreeCAD.newDocument()",
        ]

    def _get_performance_constraints(self) -> Dict[str, Any]:
        """Get current performance constraints"""
        return {
            "max_execution_time": 300,  # 5 minutes
            "max_memory_usage": "1GB",
            "max_complexity_score": 0.9,
            "require_error_handling": True,
            "require_documentation": True,
            "target_success_rate": 0.95,
        }

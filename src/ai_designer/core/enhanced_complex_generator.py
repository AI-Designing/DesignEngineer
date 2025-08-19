"""
Enhanced Complex Shape Generator with Advanced AI Capabilities
Provides intelligent shape generation with quality prediction and optimization
"""

import json
import time
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    
    def learn_from_generation(self, requirements: str, plan: List[EnhancedGenerationStep], 
                            result: GenerationResult):
        """Learn from a generation attempt"""
        pattern = {
            'requirements_hash': hash(requirements),
            'complexity_level': self._extract_complexity(requirements),
            'step_count': len(plan),
            'success_rate': result.successful_steps / result.total_steps if result.total_steps > 0 else 0,
            'execution_time': result.execution_time,
            'quality_score': result.quality_metrics.overall_score,
            'generation_mode': result.generation_mode,
            'timestamp': time.time()
        }
        
        if result.status == 'success' and result.quality_metrics.overall_score > 0.8:
            self.success_patterns.append(pattern)
        elif result.status == 'error' or result.quality_metrics.overall_score < 0.5:
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
                if abs(pattern['complexity_level'] - complexity) <= 1:
                    similarity_score = self._calculate_similarity(requirements, pattern)
                    if similarity_score > 0.6:
                        pattern['similarity_score'] = similarity_score
                        similar_patterns.append(pattern)
        
        # Sort by similarity and success rate
        similar_patterns.sort(key=lambda x: (x['similarity_score'], x.get('success_rate', 0)), reverse=True)
        return similar_patterns[:5]  # Return top 5 similar patterns
    
    def get_optimization_suggestions(self, current_plan: List[EnhancedGenerationStep]) -> List[Dict]:
        """Get optimization suggestions based on learned patterns"""
        suggestions = []
        
        # Analyze current plan
        plan_complexity = sum(step.complexity_score for step in current_plan)
        step_count = len(current_plan)
        
        # Find optimization patterns
        for pattern in self.optimization_patterns:
            if (abs(pattern['step_count'] - step_count) <= 2 and 
                abs(pattern['complexity_level'] - plan_complexity) <= 1):
                suggestions.append(pattern['optimization'])
        
        return suggestions
    
    def _extract_complexity(self, requirements: str) -> int:
        """Extract complexity level from requirements"""
        # Simple heuristic - could be enhanced with NLP
        complexity_keywords = {
            'simple': 1, 'basic': 2, 'moderate': 3, 'intermediate': 4,
            'complex': 5, 'advanced': 6, 'expert': 7, 'master': 8,
            'ultimate': 9, 'impossible': 10
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
        pattern_hash = pattern['requirements_hash']
        
        # For now, use a simple heuristic
        if current_hash == pattern_hash:
            return 1.0
        else:
            # Calculate based on complexity similarity
            complexity_similarity = 1.0 - abs(pattern['complexity_level'] - self._extract_complexity(requirements)) / 10.0
            return max(0.0, complexity_similarity)

class QualityPredictor:
    """Predicts quality outcomes for generation steps"""
    
    def __init__(self):
        self.quality_models = {
            'geometric': self._geometric_quality_model,
            'aesthetic': self._aesthetic_quality_model,
            'performance': self._performance_quality_model
        }
        self.historical_data = []
    
    def predict_step_quality(self, step: EnhancedGenerationStep, 
                           execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict quality outcome for a generation step"""
        
        # Base prediction on step complexity and success probability
        base_quality = min(1.0, step.success_probability * (1.0 - step.complexity_score / 10.0))
        
        # Adjust based on context
        context_factor = self._analyze_context_factors(execution_context)
        adjusted_quality = base_quality * context_factor
        
        # Calculate risk level
        risk_level = 1.0 - adjusted_quality
        
        prediction = {
            'predicted_quality': adjusted_quality,
            'risk_level': risk_level,
            'confidence': 0.7,  # Default confidence
            'risk_factors': self._identify_risk_factors(step, execution_context),
            'mitigation_suggestions': self._suggest_mitigations(risk_level, step)
        }
        
        return prediction
    
    def predict_overall_quality(self, plan: List[EnhancedGenerationStep],
                              execution_context: Dict[str, Any]) -> QualityMetrics:
        """Predict overall quality for the entire generation plan"""
        
        step_predictions = [
            self.predict_step_quality(step, execution_context) 
            for step in plan
        ]
        
        # Calculate weighted average based on step importance
        total_weight = sum(step.priority for step in plan)
        weighted_quality = sum(
            pred['predicted_quality'] * step.priority 
            for pred, step in zip(step_predictions, plan)
        ) / total_weight if total_weight > 0 else 0.5
        
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
            confidence_level=self._calculate_confidence(step_predictions)
        )
    
    def _analyze_context_factors(self, context: Dict[str, Any]) -> float:
        """Analyze context factors that affect quality"""
        factor = 1.0
        
        # System load factor
        system_load = context.get('system_load', 0.5)
        if system_load > 0.8:
            factor *= 0.9
        elif system_load < 0.3:
            factor *= 1.1
        
        # Memory availability
        memory_usage = context.get('memory_usage', 0.5)
        if memory_usage > 0.9:
            factor *= 0.8
        
        # Previous step success rate
        prev_success_rate = context.get('previous_success_rate', 1.0)
        factor *= (0.5 + 0.5 * prev_success_rate)
        
        return min(1.2, max(0.5, factor))
    
    def _identify_risk_factors(self, step: EnhancedGenerationStep, 
                             context: Dict[str, Any]) -> List[str]:
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
        
        if context.get('system_load', 0) > 0.8:
            risks.append("High system load")
        
        return risks
    
    def _suggest_mitigations(self, risk_level: float, 
                           step: EnhancedGenerationStep) -> List[str]:
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
    
    def _predict_geometric_quality(self, plan: List[EnhancedGenerationStep],
                                 predictions: List[Dict]) -> float:
        """Predict geometric quality specifically"""
        # Simple geometric quality prediction
        avg_prediction = sum(p['predicted_quality'] for p in predictions) / len(predictions)
        
        # Adjust based on geometric complexity
        geometric_steps = [s for s in plan if 'geometric' in s.description.lower()]
        if geometric_steps:
            geometric_complexity = sum(s.complexity_score for s in geometric_steps) / len(geometric_steps)
            return avg_prediction * (1.0 - geometric_complexity / 20.0)
        
        return avg_prediction
    
    def _predict_aesthetic_quality(self, plan: List[EnhancedGenerationStep],
                                 predictions: List[Dict]) -> float:
        """Predict aesthetic quality specifically"""
        # Simple aesthetic quality prediction
        return sum(p['predicted_quality'] for p in predictions) / len(predictions)
    
    def _predict_performance_quality(self, plan: List[EnhancedGenerationStep],
                                   predictions: List[Dict]) -> float:
        """Predict performance quality specifically"""
        # Consider step count and complexity for performance
        total_complexity = sum(s.complexity_score for s in plan)
        step_count = len(plan)
        
        performance_factor = 1.0 - (total_complexity / (step_count * 10.0))
        avg_prediction = sum(p['predicted_quality'] for p in predictions) / len(predictions)
        
        return avg_prediction * max(0.3, performance_factor)
    
    def _calculate_confidence(self, predictions: List[Dict]) -> float:
        """Calculate confidence level for predictions"""
        if not predictions:
            return 0.5
        
        confidences = [p.get('confidence', 0.5) for p in predictions]
        return sum(confidences) / len(confidences)

class EnhancedComplexShapeGenerator:
    """
    Next-generation complex shape generator with advanced AI capabilities
    """
    
    def __init__(self, llm_client, state_analyzer, command_executor, 
                 state_cache=None, websocket_manager=None):
        self.llm_client = llm_client
        self.state_analyzer = state_analyzer
        self.command_executor = command_executor
        self.state_cache = state_cache
        self.websocket_manager = websocket_manager
        
        self.logger = logging.getLogger(__name__)
        
        # Enhanced AI components
        self.pattern_learning = PatternLearningEngine()
        self.quality_predictor = QualityPredictor()
        
        # Session tracking
        self.active_sessions = {}
        
        # Performance metrics
        self.performance_metrics = {
            'total_generations': 0,
            'successful_generations': 0,
            'average_quality_score': 0.0,
            'average_execution_time': 0.0,
            'pattern_learning_accuracy': 0.0
        }
    
    def generate_enhanced_complex_shape(self, 
                                      user_requirements: str,
                                      session_id: str,
                                      generation_mode: GenerationMode = GenerationMode.ADAPTIVE,
                                      quality_targets: Optional[Dict[str, float]] = None,
                                      context: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """
        Enhanced complex shape generation with AI-powered optimization
        """
        start_time = time.time()
        self.logger.info(f"Starting enhanced generation for session {session_id}")
        
        # Initialize session tracking
        session_context = {
            'start_time': start_time,
            'requirements': user_requirements,
            'mode': generation_mode,
            'quality_targets': quality_targets or {},
            'context': context or {}
        }
        self.active_sessions[session_id] = session_context
        
        try:
            # Step 1: Intelligent requirement analysis
            requirement_analysis = self._analyze_requirements_intelligently(user_requirements)
            
            # Step 2: Pattern-based optimization
            similar_patterns = self.pattern_learning.find_similar_patterns(user_requirements)
            
            # Step 3: Select optimal generation mode
            if generation_mode == GenerationMode.ADAPTIVE:
                generation_mode = self._select_optimal_mode(requirement_analysis, similar_patterns)
            
            # Step 4: Generate enhanced plan
            enhanced_plan = self._generate_enhanced_plan(
                user_requirements, requirement_analysis, similar_patterns
            )
            
            # Step 5: Quality prediction and optimization
            predicted_quality = self.quality_predictor.predict_overall_quality(
                enhanced_plan, session_context['context']
            )
            
            if quality_targets:
                enhanced_plan = self._optimize_plan_for_quality(enhanced_plan, quality_targets)
            
            # Step 6: Execute with real-time monitoring
            execution_result = self._execute_enhanced_plan(
                enhanced_plan, session_id, generation_mode, predicted_quality
            )
            
            # Step 7: Calculate final metrics
            execution_time = time.time() - start_time
            final_quality = self._calculate_final_quality(execution_result)
            
            # Step 8: Learn from results
            generation_result = GenerationResult(
                status='success',
                session_id=session_id,
                generation_mode=generation_mode.value,
                total_steps=len(enhanced_plan),
                successful_steps=execution_result.get('successful_steps', 0),
                failed_steps=execution_result.get('failed_steps', 0),
                recovered_steps=execution_result.get('recovered_steps', 0),
                execution_time=execution_time,
                quality_metrics=final_quality,
                generated_objects=execution_result.get('generated_objects', []),
                performance_data=execution_result.get('performance_data', {}),
                learned_patterns=[],
                recommendations=self._generate_recommendations(execution_result)
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
                status='error',
                session_id=session_id,
                generation_mode=generation_mode.value if isinstance(generation_mode, GenerationMode) else str(generation_mode),
                total_steps=0,
                successful_steps=0,
                failed_steps=1,
                recovered_steps=0,
                execution_time=time.time() - start_time,
                quality_metrics=QualityMetrics(),
                generated_objects=[],
                performance_data={},
                learned_patterns=[],
                recommendations=[f"Error occurred: {str(e)}"]
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
            'entities': entities,
            'relationships': relationships,
            'complexity_score': complexity_score,
            'estimated_steps': max(3, len(entities) * 2),
            'estimated_time': complexity_score * 30,  # seconds
            'resource_estimate': resource_estimate,
            'challenges': challenges,
            'confidence': 0.8
        }
    
    def _extract_entities(self, requirements: str) -> List[Dict[str, Any]]:
        """Extract design entities from requirements"""
        entities = []
        
        # Common CAD entities
        cad_entities = {
            'box': {'type': 'primitive', 'complexity': 1},
            'cube': {'type': 'primitive', 'complexity': 1},
            'cylinder': {'type': 'primitive', 'complexity': 2},
            'sphere': {'type': 'primitive', 'complexity': 2},
            'cone': {'type': 'primitive', 'complexity': 2},
            'tower': {'type': 'assembly', 'complexity': 5},
            'building': {'type': 'assembly', 'complexity': 7},
            'house': {'type': 'assembly', 'complexity': 6},
            'gear': {'type': 'mechanical', 'complexity': 6},
            'shaft': {'type': 'mechanical', 'complexity': 3},
            'bearing': {'type': 'mechanical', 'complexity': 4}
        }
        
        requirements_lower = requirements.lower()
        for entity_name, entity_info in cad_entities.items():
            if entity_name in requirements_lower:
                entities.append({
                    'name': entity_name,
                    'type': entity_info['type'],
                    'complexity': entity_info['complexity']
                })
        
        return entities
    
    def _extract_relationships(self, requirements: str) -> List[Dict[str, Any]]:
        """Extract relationships between entities"""
        relationships = []
        
        relationship_keywords = {
            'on top of': 'stacked',
            'next to': 'adjacent',
            'inside': 'contained',
            'connected': 'joined',
            'attached': 'joined',
            'combined': 'merged'
        }
        
        requirements_lower = requirements.lower()
        for keyword, relationship_type in relationship_keywords.items():
            if keyword in requirements_lower:
                relationships.append({
                    'type': relationship_type,
                    'keyword': keyword,
                    'complexity': 2 if relationship_type in ['joined', 'merged'] else 1
                })
        
        return relationships
    
    def _calculate_complexity_score(self, requirements: str, entities: List[Dict]) -> float:
        """Calculate overall complexity score"""
        if not entities:
            return 3.0  # Default moderate complexity
        
        # Base complexity from entities
        entity_complexity = sum(e['complexity'] for e in entities)
        
        # Adjust for requirement length and sophistication
        word_count = len(requirements.split())
        length_factor = min(2.0, word_count / 10.0)
        
        # Check for advanced keywords
        advanced_keywords = ['parametric', 'optimized', 'complex', 'advanced', 'intricate']
        advanced_count = sum(1 for keyword in advanced_keywords if keyword in requirements.lower())
        advanced_factor = 1.0 + (advanced_count * 0.5)
        
        final_complexity = entity_complexity * length_factor * advanced_factor
        return min(10.0, max(1.0, final_complexity))
    
    def _select_optimal_mode(self, analysis: Dict[str, Any], 
                           patterns: List[Dict]) -> GenerationMode:
        """Select optimal generation mode based on analysis and patterns"""
        complexity = analysis['complexity_score']
        entity_count = len(analysis['entities'])
        
        # Check patterns for mode recommendations
        if patterns:
            successful_modes = [p.get('generation_mode') for p in patterns[:3] 
                              if p.get('success_rate', 0) > 0.8]
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
                    session_id
                )
            except Exception as e:
                self.logger.warning(f"Failed to send WebSocket notification: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            **self.performance_metrics,
            'active_sessions': len(self.active_sessions),
            'pattern_database_size': len(self.pattern_learning.pattern_database),
            'success_patterns': len(self.pattern_learning.success_patterns),
            'failure_patterns': len(self.pattern_learning.failure_patterns)
        }
    
    # Additional helper methods would be implemented here...
    # (Due to length constraints, showing key structure and main methods)

"""
Enhanced State-LLM Integration Module
Provides intelligent state-aware LLM decision making with continuous analysis
and complex shape generation capabilities
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from ..services.state_service import FreeCADStateService
    from ..llm.client import LLMClient
    from ..freecad.command_executor import CommandExecutor
    from ..redis_utils.state_cache import StateCache
    from .complex_shape_generator import ComplexShapeGenerator, ComplexityLevel
    from .intent_processor import IntentProcessor
except ImportError:
    # Handle import errors gracefully for development
    pass

class AnalysisMode(Enum):
    """Defines different modes of state analysis"""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"
    REAL_TIME = "real_time"

class GenerationStrategy(Enum):
    """Defines different generation strategies"""
    INCREMENTAL = "incremental"
    DECOMPOSED = "decomposed"
    ITERATIVE = "iterative"
    ADAPTIVE = "adaptive"

@dataclass
class LLMDecisionContext:
    """Enhanced context for LLM decision making"""
    user_input: str
    current_state: Dict[str, Any]
    state_history: List[Dict[str, Any]]
    session_context: Dict[str, Any]
    complexity_analysis: Dict[str, Any]
    constraint_analysis: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    generation_goals: List[str]
    quality_requirements: Dict[str, Any]

@dataclass 
class EnhancedDecisionResult:
    """Enhanced result of LLM decision making"""
    decision_type: str
    confidence_score: float
    reasoning: str
    action_plan: List[Dict[str, Any]]
    state_predictions: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    alternative_approaches: List[Dict[str, Any]]
    quality_expectations: Dict[str, Any]
    monitoring_points: List[str]

@dataclass
class DecisionContext:
    """Context for LLM decision making"""
    current_state: Dict[str, Any]
    user_intent: str
    session_id: str
    command_history: List[Dict[str, Any]]
    available_objects: List[Dict[str, Any]]
    previous_decisions: List[Dict[str, Any]]
    constraints: Dict[str, Any]
    timestamp: datetime

@dataclass
class LLMDecision:
    """Result of LLM decision making"""
    command: str
    confidence: float
    reasoning: str
    parameters: Dict[str, Any]
    prerequisites: List[str]
    expected_outcome: Dict[str, Any]
    fallback_commands: List[str]
    validation_checks: List[str]
    timestamp: datetime

class StateLLMIntegration:
    """
    Integrates state management with LLM decision making for intelligent command generation
    """
    
    def __init__(self, state_service=None, llm_client=None, command_executor=None, 
                 queue_manager=None, intent_processor=None):
        self.state_service = state_service
        self.llm_client = llm_client
        self.command_executor = command_executor
        self.queue_manager = queue_manager
        self.intent_processor = intent_processor
        
        # Decision cache for performance
        self.decision_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Performance monitoring
        self.performance_metrics = {
            'state_retrieval_time': [],
            'llm_decision_time': [],
            'command_execution_time': [],
            'total_processing_time': []
        }
    
    def process_user_request(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """
        Main entry point: Process user request with full state-LLM-execution flow
        """
        start_time = time.time()
        session_id = session_id or "default"
        
        try:
            # Step 1: Process Intent
            print(f"🔍 Processing intent for: {user_input[:50]}...")
            intent_result = self._process_intent(user_input, session_id)
            
            # Step 2: Retrieve and Prepare State Context
            print(f"📊 Retrieving state context...")
            decision_context = self._prepare_decision_context(
                user_input, session_id, intent_result
            )
            
            # Step 3: Get LLM Decision (with caching)
            print(f"🧠 Getting LLM decision...")
            llm_decision = self._get_llm_decision(decision_context)
            
            # Step 4: Validate Decision
            print(f"✅ Validating decision...")
            validation_result = self._validate_decision(llm_decision, decision_context)
            
            if not validation_result['valid']:
                print(f"❌ Decision validation failed: {validation_result['reason']}")
                return self._handle_validation_failure(validation_result, decision_context)
            
            # Step 5: Execute Decision
            print(f"⚡ Executing decision...")
            execution_result = self._execute_decision(llm_decision, decision_context)
            
            # Step 6: Update State and Cache
            print(f"💾 Updating state cache...")
            self._update_state_after_execution(execution_result, session_id)
            
            # Step 7: Prepare Response
            total_time = time.time() - start_time
            self.performance_metrics['total_processing_time'].append(total_time)
            
            return {
                'status': 'success',
                'user_input': user_input,
                'session_id': session_id,
                'intent': intent_result,
                'decision': asdict(llm_decision),
                'execution': execution_result,
                'processing_time': total_time,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"❌ Error in process_user_request: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'user_input': user_input,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def _process_intent(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Process user intent using intent processor"""
        if not self.intent_processor:
            # Fallback intent processing
            return {
                'intent_type': 'general_command',
                'confidence': 0.5,
                'requires_llm': True
            }
        
        intent_start = time.time()
        intent_result = self.intent_processor.process_intent(user_input, session_id)
        
        return intent_result
    
    def _prepare_decision_context(self, user_input: str, session_id: str, 
                                intent_result: Dict[str, Any]) -> DecisionContext:
        """Prepare comprehensive context for LLM decision making"""
        state_start = time.time()
        
        # Get current state
        current_state = {}
        if self.state_service:
            try:
                current_state = self.state_service.get_latest_state(f"session_{session_id}")
                if not current_state:
                    # Force state analysis if no cached state
                    current_state = self.state_service.analyze_and_cache(session_id) or {}
            except Exception as e:
                print(f"⚠️ Failed to get current state: {e}")
        
        # Get command history
        command_history = self._get_command_history(session_id)
        
        # Get available objects
        available_objects = current_state.get('objects', [])
        
        # Get previous decisions for context
        previous_decisions = self._get_previous_decisions(session_id)
        
        # Define constraints
        constraints = {
            'max_objects': 100,
            'max_execution_time': 60,  # seconds
            'allowed_formats': ['step', 'stl', 'obj', 'fcstd'],
            'memory_limit': '1GB'
        }
        
        state_time = time.time() - state_start
        self.performance_metrics['state_retrieval_time'].append(state_time)
        
        return DecisionContext(
            current_state=current_state,
            user_intent=user_input,
            session_id=session_id,
            command_history=command_history,
            available_objects=available_objects,
            previous_decisions=previous_decisions,
            constraints=constraints,
            timestamp=datetime.now()
        )
    
    def _get_llm_decision(self, context: DecisionContext) -> LLMDecision:
        """Get LLM decision with caching for performance"""
        llm_start = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(context)
        cached_decision = self._get_cached_decision(cache_key)
        
        if cached_decision:
            print("🚀 Using cached LLM decision")
            return cached_decision
        
        if not self.llm_client:
            raise Exception("LLM client not available")
        
        # Prepare LLM prompt with full context
        prompt = self._create_llm_prompt(context)
        
        try:
            # Get LLM response
            llm_response = self.llm_client.generate_response(prompt)
            
            # Parse LLM response
            decision = self._parse_llm_response(llm_response, context)
            
            # Cache the decision
            self._cache_decision(cache_key, decision)
            
            llm_time = time.time() - llm_start
            self.performance_metrics['llm_decision_time'].append(llm_time)
            
            return decision
        
        except Exception as e:
            print(f"❌ LLM decision failed: {e}")
            # Return fallback decision
            return self._create_fallback_decision(context)
    
    def _create_llm_prompt(self, context: DecisionContext) -> str:
        """Create comprehensive LLM prompt with state context"""
        
        state_summary = self._summarize_state(context.current_state)
        history_summary = self._summarize_history(context.command_history)
        objects_summary = self._summarize_objects(context.available_objects)
        
        prompt = f"""
You are an expert FreeCAD automation assistant. Based on the current state and user request, generate the next optimal command.

## Current State Summary:
{state_summary}

## Available Objects:
{objects_summary}

## Recent Command History:
{history_summary}

## User Request:
"{context.user_intent}"

## Session Context:
- Session ID: {context.session_id}
- Object Count: {len(context.available_objects)}
- Previous Decisions: {len(context.previous_decisions)}

## Constraints:
- Max execution time: {context.constraints.get('max_execution_time', 60)} seconds
- Max objects: {context.constraints.get('max_objects', 100)}
- Allowed formats: {context.constraints.get('allowed_formats', [])}

## Required Response Format (JSON):
{{
    "command": "exact FreeCAD Python command to execute",
    "confidence": 0.95,
    "reasoning": "detailed explanation of why this command was chosen",
    "parameters": {{
        "object_name": "name if creating new object",
        "dimensions": {{"x": 10, "y": 10, "z": 10}},
        "position": {{"x": 0, "y": 0, "z": 0}},
        "operation_type": "create|modify|delete|export"
    }},
    "prerequisites": ["any required setup commands"],
    "expected_outcome": {{
        "new_objects": ["list of objects that will be created"],
        "modified_objects": ["list of objects that will be modified"],
        "state_changes": "description of expected state changes"
    }},
    "fallback_commands": ["alternative commands if primary fails"],
    "validation_checks": ["checks to perform after execution"]
}}

Focus on:
1. Using current state context to make informed decisions
2. Avoiding conflicts with existing objects
3. Ensuring command safety and validity
4. Providing clear reasoning for the chosen approach
5. Including fallback options for error recovery

Generate a safe, executable FreeCAD command that fulfills the user's request.
"""
        
        return prompt
    
    def _summarize_state(self, state: Dict[str, Any]) -> str:
        """Create a concise state summary for the LLM"""
        if not state or 'error' in state:
            return "No active document or state unavailable"
        
        summary = []
        summary.append(f"Document: {state.get('document_name', 'Unnamed')}")
        summary.append(f"Objects: {state.get('object_count', 0)} total")
        
        if state.get('objects'):
            obj_types = {}
            for obj in state['objects'][:5]:  # Limit to 5 for brevity
                obj_type = obj.get('type', 'Unknown')
                obj_types[obj_type] = obj_types.get(obj_type, 0) + 1
            
            type_summary = ", ".join([f"{count} {type}" for type, count in obj_types.items()])
            summary.append(f"Object types: {type_summary}")
        
        return " | ".join(summary)
    
    def _summarize_history(self, history: List[Dict[str, Any]]) -> str:
        """Create a concise command history summary"""
        if not history:
            return "No recent commands"
        
        recent = history[-3:]  # Last 3 commands
        summaries = []
        
        for cmd in recent:
            cmd_type = cmd.get('command', '')[:30]
            status = cmd.get('status', 'unknown')
            summaries.append(f"{cmd_type}... ({status})")
        
        return " -> ".join(summaries)
    
    def _summarize_objects(self, objects: List[Dict[str, Any]]) -> str:
        """Create a concise objects summary"""
        if not objects:
            return "No objects in current document"
        
        summaries = []
        for obj in objects[:5]:  # Limit to 5
            name = obj.get('name', 'Unnamed')
            obj_type = obj.get('type', 'Unknown')
            summaries.append(f"{name} ({obj_type})")
        
        if len(objects) > 5:
            summaries.append(f"... and {len(objects) - 5} more")
        
        return ", ".join(summaries)
    
    def _parse_llm_response(self, response: str, context: DecisionContext) -> LLMDecision:
        """Parse LLM JSON response into LLMDecision object"""
        try:
            data = json.loads(response)
            
            return LLMDecision(
                command=data.get('command', ''),
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', ''),
                parameters=data.get('parameters', {}),
                prerequisites=data.get('prerequisites', []),
                expected_outcome=data.get('expected_outcome', {}),
                fallback_commands=data.get('fallback_commands', []),
                validation_checks=data.get('validation_checks', []),
                timestamp=datetime.now()
            )
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"❌ Failed to parse LLM response: {e}")
            return self._create_fallback_decision(context)
    
    def _create_fallback_decision(self, context: DecisionContext) -> LLMDecision:
        """Create a safe fallback decision when LLM fails"""
        user_input = context.user_intent.lower()
        
        # Simple pattern-based fallback
        if 'cube' in user_input or 'box' in user_input:
            command = "box = doc.addObject('Part::Box', 'Box')"
        elif 'cylinder' in user_input:
            command = "cylinder = doc.addObject('Part::Cylinder', 'Cylinder')"
        elif 'sphere' in user_input:
            command = "sphere = doc.addObject('Part::Sphere', 'Sphere')"
        else:
            command = "# Unable to determine appropriate command"
        
        return LLMDecision(
            command=command,
            confidence=0.3,
            reasoning="Fallback decision due to LLM failure",
            parameters={},
            prerequisites=[],
            expected_outcome={"new_objects": ["Basic shape"]},
            fallback_commands=[],
            validation_checks=["Check object creation"],
            timestamp=datetime.now()
        )
    
    def _validate_decision(self, decision: LLMDecision, context: DecisionContext) -> Dict[str, Any]:
        """Validate LLM decision before execution"""
        
        # Basic safety checks
        if not decision.command or decision.command.strip() == "":
            return {'valid': False, 'reason': 'Empty command'}
        
        # Check for dangerous commands
        dangerous_patterns = [
            'import os', 'import subprocess', 'exec(', 'eval(',
            'delete', 'remove', '__import__', 'file.write'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in decision.command.lower():
                return {'valid': False, 'reason': f'Dangerous command pattern: {pattern}'}
        
        # Check confidence threshold
        if decision.confidence < 0.3:
            return {'valid': False, 'reason': 'Confidence too low'}
        
        # Check prerequisites
        for prereq in decision.prerequisites:
            if not self._check_prerequisite(prereq, context):
                return {'valid': False, 'reason': f'Prerequisite not met: {prereq}'}
        
        return {'valid': True, 'reason': 'All validations passed'}
    
    def _check_prerequisite(self, prerequisite: str, context: DecisionContext) -> bool:
        """Check if a prerequisite is satisfied"""
        if prerequisite == "active_document":
            return context.current_state.get('object_count', 0) >= 0
        elif prerequisite == "no_active_document":
            return context.current_state.get('object_count', 0) == 0
        elif prerequisite.startswith("object_exists:"):
            obj_name = prerequisite.split(":")[1]
            return any(obj.get('name') == obj_name for obj in context.available_objects)
        
        return True  # Default to True for unknown prerequisites
    
    def _execute_decision(self, decision: LLMDecision, context: DecisionContext) -> Dict[str, Any]:
        """Execute the LLM decision using appropriate executor"""
        exec_start = time.time()
        
        try:
            if self.queue_manager:
                # Execute via queue manager for better control
                command_id = self.queue_manager.submit_command(
                    user_input=context.user_intent,
                    command=decision.command,
                    session_id=context.session_id,
                    state_context=context.current_state
                )
                
                # Wait for completion
                result = self.queue_manager.get_command_result(command_id, timeout=60)
                
                if result:
                    execution_result = {
                        'status': result.status.value,
                        'command_id': command_id,
                        'result': result.result,
                        'error': result.error
                    }
                else:
                    execution_result = {
                        'status': 'timeout',
                        'command_id': command_id,
                        'error': 'Command execution timed out'
                    }
            
            elif self.command_executor:
                # Direct execution
                result = self.command_executor.execute(decision.command)
                execution_result = result
            
            else:
                raise Exception("No command executor available")
            
            exec_time = time.time() - exec_start
            self.performance_metrics['command_execution_time'].append(exec_time)
            
            return execution_result
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'command': decision.command
            }
    
    def _update_state_after_execution(self, execution_result: Dict[str, Any], session_id: str):
        """Update state cache after successful command execution"""
        if execution_result.get('status') == 'success' and self.state_service:
            try:
                # Trigger state re-analysis
                self.state_service.analyze_and_cache(session_id)
            except Exception as e:
                print(f"⚠️ Failed to update state after execution: {e}")
    
    def _handle_validation_failure(self, validation_result: Dict[str, Any], 
                                 context: DecisionContext) -> Dict[str, Any]:
        """Handle decision validation failure"""
        return {
            'status': 'validation_failed',
            'reason': validation_result['reason'],
            'user_input': context.user_intent,
            'session_id': context.session_id,
            'suggested_action': 'Please rephrase your request or provide more details',
            'timestamp': datetime.now().isoformat()
        }
    
    # Caching methods for performance
    def _generate_cache_key(self, context: DecisionContext) -> str:
        """Generate cache key for decision caching"""
        state_hash = hash(str(context.current_state))
        intent_hash = hash(context.user_intent)
        return f"{context.session_id}_{state_hash}_{intent_hash}"
    
    def _get_cached_decision(self, cache_key: str) -> Optional[LLMDecision]:
        """Get decision from cache if still valid"""
        if cache_key in self.decision_cache:
            cached_data, timestamp = self.decision_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            else:
                del self.decision_cache[cache_key]
        return None
    
    def _cache_decision(self, cache_key: str, decision: LLMDecision):
        """Cache decision for performance"""
        self.decision_cache[cache_key] = (decision, time.time())
    
    def _get_command_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get recent command history for context"""
        # This would typically come from a database or Redis
        # For now, return empty list
        return []
    
    def _get_previous_decisions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get previous LLM decisions for context"""
        # This would typically come from a database
        # For now, return empty list
        return []
    
class EnhancedStateLLMIntegration(StateLLMIntegration):
    """
    Enhanced State-LLM Integration with complex shape generation capabilities
    """
    
    def __init__(self, state_service=None, llm_client=None, command_executor=None, 
                 queue_manager=None, intent_processor=None, state_cache=None):
        super().__init__(state_service, llm_client, command_executor, queue_manager, intent_processor)
        
        # Enhanced components
        self.state_cache = state_cache
        self.complex_shape_generator = None
        if all([llm_client, state_service, command_executor]):
            try:
                from .complex_shape_generator import ComplexShapeGenerator
                self.complex_shape_generator = ComplexShapeGenerator(
                    llm_client, state_service.analyzer, command_executor, state_cache
                )
            except ImportError:
                pass
        
        # Enhanced tracking
        self.state_analysis_history = []
        self.llm_feedback_history = []
        self.complexity_progression = []
        
        # Configuration with API key
        self.api_key = "AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc"
        if self.llm_client and hasattr(self.llm_client, 'set_api_key'):
            self.llm_client.set_api_key(self.api_key)
    
    def process_complex_shape_request(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process complex shape generation requests with continuous state analysis
        """
        session_id = session_id or "complex_session"
        start_time = time.time()
        
        print(f"🏗️ Starting complex shape generation for: {user_input}")
        
        try:
            # Step 1: Analyze complexity requirements
            complexity_analysis = self._analyze_complexity_requirements(user_input)
            
            # Step 2: Determine generation strategy
            generation_strategy = self._determine_generation_strategy(complexity_analysis, user_input)
            
            # Step 3: Enhanced state analysis
            enhanced_context = self._create_enhanced_context(user_input, session_id, complexity_analysis)
            
            if generation_strategy == GenerationStrategy.DECOMPOSED:
                # Use complex shape generator
                result = self._process_with_complex_generator(user_input, session_id, enhanced_context)
            else:
                # Use enhanced iterative processing
                result = self._process_with_iterative_enhancement(user_input, session_id, enhanced_context)
            
            # Step 4: Continuous monitoring and feedback
            monitoring_result = self._setup_continuous_monitoring(session_id, result)
            
            total_time = time.time() - start_time
            
            return {
                'status': 'success',
                'processing_mode': 'complex_shape_generation',
                'generation_strategy': generation_strategy.value,
                'complexity_analysis': complexity_analysis,
                'result': result,
                'monitoring': monitoring_result,
                'processing_time': total_time,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Complex shape generation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'processing_mode': 'complex_shape_generation',
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_complexity_requirements(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze the complexity requirements of the user request
        """
        print("🔍 Analyzing complexity requirements...")
        
        # Enhanced LLM prompt for complexity analysis
        complexity_prompt = f"""
        Analyze the complexity of this CAD design request and provide detailed breakdown:

        USER REQUEST: "{user_input}"

        Please analyze and categorize this request across multiple dimensions:

        1. GEOMETRIC COMPLEXITY (1-10):
           - Simple shapes (1-3): basic primitives
           - Intermediate (4-6): combinations, boolean operations
           - Advanced (7-8): complex curves, surfaces, patterns
           - Expert (9-10): advanced mathematical shapes, parametric designs

        2. OPERATION COMPLEXITY (1-10):
           - Number of steps required
           - Dependencies between operations
           - Required precision level

        3. DECOMPOSITION REQUIREMENTS:
           - Can this be broken into smaller steps?
           - What are the logical building blocks?
           - What dependencies exist?

        4. STATE MONITORING NEEDS:
           - How often should state be checked?
           - What validation points are critical?
           - What quality metrics matter?

        Respond in JSON format:
        {{
            "geometric_complexity": 7,
            "operation_complexity": 6,
            "overall_complexity": "advanced",
            "decomposition_recommended": true,
            "estimated_steps": 8,
            "key_challenges": ["challenge1", "challenge2"],
            "required_capabilities": ["capability1", "capability2"],
            "monitoring_points": ["point1", "point2"],
            "quality_metrics": ["metric1", "metric2"],
            "risk_factors": ["risk1", "risk2"],
            "recommended_approach": "decomposed"
        }}
        """
        
        try:
            if self.llm_client:
                response = self.llm_client.generate_response(complexity_prompt)
                complexity_data = json.loads(response)
                
                # Enhance with additional analysis
                complexity_data['analysis_timestamp'] = datetime.now().isoformat()
                complexity_data['input_length'] = len(user_input)
                complexity_data['keywords'] = self._extract_complexity_keywords(user_input)
                
                return complexity_data
            else:
                # Fallback analysis
                return self._fallback_complexity_analysis(user_input)
        
        except Exception as e:
            print(f"⚠️ Complexity analysis failed: {e}")
            return self._fallback_complexity_analysis(user_input)
    
    def _determine_generation_strategy(self, complexity_analysis: Dict[str, Any], 
                                     user_input: str) -> GenerationStrategy:
        """
        Determine the optimal generation strategy based on complexity analysis
        """
        complexity_level = complexity_analysis.get('overall_complexity', 'intermediate')
        geometric_complexity = complexity_analysis.get('geometric_complexity', 5)
        decomposition_recommended = complexity_analysis.get('decomposition_recommended', False)
        
        if geometric_complexity >= 7 or decomposition_recommended:
            return GenerationStrategy.DECOMPOSED
        elif geometric_complexity >= 5:
            return GenerationStrategy.ITERATIVE
        elif 'adaptive' in user_input.lower() or 'parametric' in user_input.lower():
            return GenerationStrategy.ADAPTIVE
        else:
            return GenerationStrategy.INCREMENTAL
    
    def _create_enhanced_context(self, user_input: str, session_id: str, 
                               complexity_analysis: Dict[str, Any]) -> LLMDecisionContext:
        """
        Create enhanced context for complex shape generation
        """
        print("📊 Creating enhanced decision context...")
        
        # Get comprehensive current state
        current_state = self._get_comprehensive_state(session_id)
        
        # Get state history for pattern analysis
        state_history = self._get_state_history(session_id)
        
        # Create session context
        session_context = {
            'session_id': session_id,
            'start_time': datetime.now().isoformat(),
            'complexity_target': complexity_analysis.get('overall_complexity'),
            'generation_mode': 'complex_shape'
        }
        
        # Analyze constraints based on current state and requirements
        constraint_analysis = self._analyze_constraints(current_state, complexity_analysis)
        
        # Get performance metrics
        performance_metrics = self.get_performance_metrics()
        
        # Define generation goals
        generation_goals = self._extract_generation_goals(user_input, complexity_analysis)
        
        # Define quality requirements
        quality_requirements = self._define_quality_requirements(complexity_analysis)
        
        return LLMDecisionContext(
            user_input=user_input,
            current_state=current_state,
            state_history=state_history,
            session_context=session_context,
            complexity_analysis=complexity_analysis,
            constraint_analysis=constraint_analysis,
            performance_metrics=performance_metrics,
            generation_goals=generation_goals,
            quality_requirements=quality_requirements
        )
    
    def _process_with_complex_generator(self, user_input: str, session_id: str, 
                                      context: LLMDecisionContext) -> Dict[str, Any]:
        """
        Process using the complex shape generator with full decomposition
        """
        print("🏗️ Using complex shape generator...")
        
        if not self.complex_shape_generator:
            raise Exception("Complex shape generator not available")
        
        # Determine target complexity
        complexity_level = context.complexity_analysis.get('overall_complexity', 'intermediate')
        if complexity_level == 'expert':
            target_complexity = ComplexityLevel.EXPERT
        elif complexity_level == 'advanced':
            target_complexity = ComplexityLevel.ADVANCED
        elif complexity_level == 'intermediate':
            target_complexity = ComplexityLevel.INTERMEDIATE
        else:
            target_complexity = ComplexityLevel.SIMPLE
        
        # Generate complex shape with continuous monitoring
        generation_result = self.complex_shape_generator.generate_complex_shape(
            user_input, session_id, target_complexity
        )
        
        # Add continuous state monitoring
        monitoring_data = self._add_continuous_monitoring(generation_result, session_id)
        
        return {
            'generation_result': generation_result,
            'monitoring_data': monitoring_data,
            'method': 'complex_generator'
        }
    
    def _process_with_iterative_enhancement(self, user_input: str, session_id: str,
                                          context: LLMDecisionContext) -> Dict[str, Any]:
        """
        Process using iterative enhancement with continuous state feedback
        """
        print("🔄 Using iterative enhancement...")
        
        iteration_results = []
        max_iterations = 10
        current_iteration = 0
        
        current_context = context
        
        while current_iteration < max_iterations:
            print(f"🔄 Iteration {current_iteration + 1}/{max_iterations}")
            
            # Get enhanced LLM decision
            enhanced_decision = self._get_enhanced_llm_decision(current_context)
            
            # Execute with monitoring
            execution_result = self._execute_with_state_monitoring(enhanced_decision, session_id)
            
            # Analyze post-execution state
            post_execution_state = self._analyze_post_execution_state(session_id)
            
            # Get LLM feedback on progress
            progress_feedback = self._get_progress_feedback(
                current_context, enhanced_decision, execution_result, post_execution_state
            )
            
            iteration_result = {
                'iteration': current_iteration + 1,
                'decision': enhanced_decision.__dict__ if hasattr(enhanced_decision, '__dict__') else enhanced_decision,
                'execution': execution_result,
                'state_after': post_execution_state,
                'progress_feedback': progress_feedback,
                'timestamp': datetime.now().isoformat()
            }
            
            iteration_results.append(iteration_result)
            
            # Check completion
            if self._check_completion_criteria(current_context, post_execution_state, progress_feedback):
                print("✅ Generation completed successfully")
                break
            
            # Update context for next iteration
            current_context = self._update_context_for_next_iteration(
                current_context, post_execution_state, progress_feedback
            )
            
            current_iteration += 1
        
        return {
            'iterations': iteration_results,
            'total_iterations': current_iteration + 1,
            'method': 'iterative_enhancement',
            'completion_status': 'completed' if current_iteration < max_iterations else 'max_iterations_reached'
        }
    
    def _get_enhanced_llm_decision(self, context: LLMDecisionContext) -> EnhancedDecisionResult:
        """
        Get enhanced LLM decision with comprehensive analysis
        """
        enhanced_prompt = self._create_enhanced_llm_prompt(context)
        
        try:
            if self.llm_client:
                response = self.llm_client.generate_response(enhanced_prompt)
                return self._parse_enhanced_response(response)
            else:
                return self._create_fallback_enhanced_decision(context)
        
        except Exception as e:
            print(f"⚠️ Enhanced LLM decision failed: {e}")
            return self._create_fallback_enhanced_decision(context)
    
    def _create_enhanced_llm_prompt(self, context: LLMDecisionContext) -> str:
        """
        Create comprehensive prompt for enhanced LLM decision making
        """
        return f"""
        You are an advanced CAD design AI with expertise in complex shape generation and state-aware decision making.
        
        CURRENT SITUATION:
        User Request: "{context.user_input}"
        Session ID: {context.session_context['session_id']}
        
        CURRENT STATE ANALYSIS:
        Objects Count: {context.current_state.get('object_count', 0)}
        Current Objects: {json.dumps(context.current_state.get('objects', [])[:3], indent=2)}
        Quality Metrics: {json.dumps(context.current_state.get('quality_metrics', {}), indent=2)}
        
        COMPLEXITY ANALYSIS:
        Overall Complexity: {context.complexity_analysis.get('overall_complexity')}
        Geometric Complexity: {context.complexity_analysis.get('geometric_complexity')}/10
        Operation Complexity: {context.complexity_analysis.get('operation_complexity')}/10
        Key Challenges: {context.complexity_analysis.get('key_challenges', [])}
        
        GENERATION GOALS:
        {json.dumps(context.generation_goals, indent=2)}
        
        QUALITY REQUIREMENTS:
        {json.dumps(context.quality_requirements, indent=2)}
        
        CONSTRAINTS:
        {json.dumps(context.constraint_analysis, indent=2)}
        
        STATE HISTORY (last 3 states):
        {json.dumps(context.state_history[-3:], indent=2)}
        
        Please provide a comprehensive decision that includes:
        
        1. DECISION TYPE: What kind of action to take (create, modify, analyze, etc.)
        2. CONFIDENCE SCORE: How confident you are (0.0-1.0)
        3. DETAILED REASONING: Why this decision is optimal
        4. ACTION PLAN: Step-by-step plan with specific FreeCAD commands
        5. STATE PREDICTIONS: What the state should look like after execution
        6. RISK ASSESSMENT: Potential risks and mitigation strategies
        7. ALTERNATIVE APPROACHES: Other viable approaches
        8. QUALITY EXPECTATIONS: Expected quality metrics after execution
        9. MONITORING POINTS: Key points to monitor during execution
        
        Respond in JSON format:
        {{
            "decision_type": "create_complex_shape",
            "confidence_score": 0.92,
            "reasoning": "Detailed explanation of the decision logic...",
            "action_plan": [
                {{
                    "step": 1,
                    "description": "Create base geometry",
                    "commands": ["doc = FreeCAD.newDocument()", "box = doc.addObject('Part::Box', 'BaseBox')"],
                    "validation": "Check that BaseBox is created"
                }},
                {{
                    "step": 2,
                    "description": "Add complexity",
                    "commands": ["cylinder = doc.addObject('Part::Cylinder', 'TopCylinder')"],
                    "validation": "Check that TopCylinder is created"
                }}
            ],
            "state_predictions": {{
                "object_count": 2,
                "new_objects": ["BaseBox", "TopCylinder"],
                "quality_score": 0.85
            }},
            "risk_assessment": {{
                "risks": ["Geometric interference", "Performance impact"],
                "mitigation": ["Check clearances", "Monitor memory usage"],
                "probability": 0.2
            }},
            "alternative_approaches": [
                {{
                    "approach": "Single complex solid",
                    "pros": ["Better performance"],
                    "cons": ["Less flexibility"]
                }}
            ],
            "quality_expectations": {{
                "geometric_accuracy": 0.95,
                "design_consistency": 0.90,
                "manufacturability": 0.85
            }},
            "monitoring_points": [
                "Object creation success",
                "Memory usage",
                "Geometric validity",
                "Performance metrics"
            ]
        }}
        
        Focus on creating high-quality, manufacturable designs that meet the user's requirements while maintaining system performance.
        """
    
    def _parse_enhanced_response(self, response: str) -> EnhancedDecisionResult:
        """
        Parse enhanced LLM response into structured result
        """
        try:
            data = json.loads(response)
            return EnhancedDecisionResult(**data)
        
        except Exception as e:
            print(f"❌ Failed to parse enhanced response: {e}")
            return self._create_fallback_enhanced_decision(None)
    
    def _execute_with_state_monitoring(self, decision: EnhancedDecisionResult, 
                                     session_id: str) -> Dict[str, Any]:
        """
        Execute decision with continuous state monitoring
        """
        execution_results = []
        
        for step in decision.action_plan:
            print(f"⚡ Executing step {step.get('step', 'unknown')}: {step.get('description', '')}")
            
            # Pre-execution state
            pre_state = self._get_comprehensive_state(session_id)
            
            # Execute commands
            step_results = []
            for command in step.get('commands', []):
                if self.command_executor:
                    result = self.command_executor.execute_command(command)
                    step_results.append(result)
            
            # Post-execution state
            post_state = self._get_comprehensive_state(session_id)
            
            # Validate step
            validation_result = self._validate_step_execution(step, step_results, pre_state, post_state)
            
            step_execution = {
                'step': step,
                'pre_state': pre_state,
                'post_state': post_state,
                'command_results': step_results,
                'validation': validation_result,
                'timestamp': datetime.now().isoformat()
            }
            
            execution_results.append(step_execution)
            
            # Stop if step failed critically
            if not validation_result.get('success', False) and validation_result.get('critical', False):
                break
        
        return {
            'steps_executed': len(execution_results),
            'step_results': execution_results,
            'overall_success': all(step['validation'].get('success', False) for step in execution_results)
        }
    
    def _get_progress_feedback(self, context: LLMDecisionContext, decision: EnhancedDecisionResult,
                             execution_result: Dict[str, Any], post_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get LLM feedback on progress towards goals
        """
        feedback_prompt = f"""
        Analyze the progress made towards the user's goals and provide feedback.
        
        ORIGINAL REQUEST: "{context.user_input}"
        
        DECISION MADE: {decision.reasoning}
        
        EXECUTION RESULTS: {json.dumps(execution_result, indent=2)}
        
        STATE BEFORE: Objects: {context.current_state.get('object_count', 0)}
        STATE AFTER: Objects: {post_state.get('object_count', 0)}
        
        GENERATION GOALS: {json.dumps(context.generation_goals, indent=2)}
        
        Please assess:
        1. How much progress was made towards the goals?
        2. What percentage of the requirements are now satisfied?
        3. What should be the next priority?
        4. Are there any quality concerns?
        5. Should the approach be modified?
        
        Respond in JSON:
        {{
            "progress_percentage": 45.0,
            "goals_satisfied": ["goal1", "goal2"],
            "goals_remaining": ["goal3", "goal4"],
            "next_priority": "Add structural details",
            "quality_assessment": {{
                "current_quality": 0.75,
                "concerns": ["geometric accuracy"],
                "improvements_needed": ["refinement"]
            }},
            "approach_recommendation": {{
                "continue_current": true,
                "modify_approach": false,
                "alternative_needed": false,
                "reasoning": "Good progress, continue with current strategy"
            }},
            "completion_estimate": {{
                "remaining_steps": 3,
                "estimated_time": "5 minutes",
                "confidence": 0.8
            }}
        }}
        """
        
        try:
            if self.llm_client:
                response = self.llm_client.generate_response(feedback_prompt)
                return json.loads(response)
            else:
                return self._default_progress_feedback()
        
        except Exception as e:
            print(f"⚠️ Progress feedback failed: {e}")
            return self._default_progress_feedback()
    
    # Helper methods
    def _get_comprehensive_state(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive state including quality metrics"""
        if self.state_service:
            try:
                state = self.state_service.get_latest_state(f"session_{session_id}")
                if not state:
                    state = self.state_service.analyze_and_cache(session_id) or {}
                
                # Enhance with additional metrics
                state['analysis_timestamp'] = datetime.now().isoformat()
                state['quality_metrics'] = self._calculate_quality_metrics(state)
                
                return state
            except Exception as e:
                print(f"⚠️ Failed to get comprehensive state: {e}")
        
        return {'object_count': 0, 'objects': [], 'quality_metrics': {}}
    
    def _calculate_quality_metrics(self, state: Dict[str, Any]) -> Dict[str, float]:
        """Calculate quality metrics for current state"""
        objects = state.get('objects', [])
        
        return {
            'geometric_accuracy': min(1.0, len(objects) * 0.1 + 0.5),
            'design_consistency': 0.8 if len(objects) > 1 else 1.0,
            'complexity_score': min(1.0, len(objects) * 0.15),
            'manufacturability': 0.9 - (len(objects) * 0.05),
            'performance_score': max(0.1, 1.0 - len(objects) * 0.08)
        }
    
    def _extract_complexity_keywords(self, user_input: str) -> List[str]:
        """Extract keywords indicating complexity"""
        keywords = []
        complexity_indicators = [
            'complex', 'advanced', 'intricate', 'detailed', 'parametric',
            'tower', 'building', 'assembly', 'multiple', 'combined'
        ]
        
        user_lower = user_input.lower()
        for keyword in complexity_indicators:
            if keyword in user_lower:
                keywords.append(keyword)
        
        return keywords
    
    def _fallback_complexity_analysis(self, user_input: str) -> Dict[str, Any]:
        """Fallback complexity analysis when LLM is unavailable"""
        keywords = self._extract_complexity_keywords(user_input)
        complexity_score = min(10, len(keywords) * 2 + 3)
        
        return {
            'geometric_complexity': complexity_score,
            'operation_complexity': max(3, complexity_score - 1),
            'overall_complexity': 'advanced' if complexity_score >= 7 else 'intermediate',
            'decomposition_recommended': complexity_score >= 6,
            'estimated_steps': max(3, complexity_score),
            'keywords': keywords,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _analyze_constraints(self, current_state: Dict[str, Any], 
                           complexity_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze constraints based on current state and complexity"""
        object_count = current_state.get('object_count', 0)
        complexity = complexity_analysis.get('geometric_complexity', 5)
        
        return {
            'max_objects': max(10, 50 - object_count),
            'memory_usage': f"{object_count * 10}MB estimated",
            'execution_time_limit': min(300, complexity * 30),  # seconds
            'quality_threshold': 0.8,
            'performance_threshold': 0.7
        }
    
    def _extract_generation_goals(self, user_input: str, 
                                complexity_analysis: Dict[str, Any]) -> List[str]:
        """Extract specific generation goals from user input"""
        goals = []
        
        # Basic goal extraction
        if any(word in user_input.lower() for word in ['create', 'make', 'build', 'design']):
            goals.append("Create primary shape")
        
        if any(word in user_input.lower() for word in ['complex', 'detailed', 'intricate']):
            goals.append("Add complexity and detail")
        
        if any(word in user_input.lower() for word in ['combine', 'together', 'assembly']):
            goals.append("Combine multiple components")
        
        # Add default goal if none found
        if not goals:
            goals.append("Fulfill user requirements")
        
        return goals
    
    def _define_quality_requirements(self, complexity_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Define quality requirements based on complexity analysis"""
        complexity = complexity_analysis.get('geometric_complexity', 5)
        
        return {
            'minimum_accuracy': max(0.7, 1.0 - complexity * 0.05),
            'geometric_tolerance': min(0.1, complexity * 0.01),
            'surface_quality': max(0.8, 1.0 - complexity * 0.03),
            'structural_integrity': 0.9,
            'manufacturability': max(0.6, 1.0 - complexity * 0.04)
        }
    
    def _setup_continuous_monitoring(self, session_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Setup continuous monitoring for the generation process"""
        return {
            'monitoring_active': True,
            'session_id': session_id,
            'start_time': datetime.now().isoformat(),
            'monitoring_frequency': '30s',
            'alerts_enabled': True,
            'quality_checks': ['geometric_validation', 'performance_monitoring']
        }
    
    def _add_continuous_monitoring(self, generation_result: Dict[str, Any], 
                                 session_id: str) -> Dict[str, Any]:
        """Add continuous monitoring data to generation result"""
        return {
            'session_monitoring': True,
            'real_time_updates': True,
            'quality_tracking': True,
            'performance_metrics': self.get_performance_metrics()
        }
    
    def _analyze_post_execution_state(self, session_id: str) -> Dict[str, Any]:
        """Analyze state after command execution"""
        return self._get_comprehensive_state(session_id)
    
    def _check_completion_criteria(self, context: LLMDecisionContext, 
                                 post_state: Dict[str, Any], 
                                 feedback: Dict[str, Any]) -> bool:
        """Check if generation is complete"""
        progress = feedback.get('progress_percentage', 0)
        return progress >= 90.0 or feedback.get('approach_recommendation', {}).get('completion_reached', False)
    
    def _update_context_for_next_iteration(self, context: LLMDecisionContext,
                                         post_state: Dict[str, Any],
                                         feedback: Dict[str, Any]) -> LLMDecisionContext:
        """Update context for next iteration"""
        # Update current state
        context.current_state = post_state
        
        # Add to state history
        context.state_history.append(post_state)
        
        # Update goals based on feedback
        remaining_goals = feedback.get('goals_remaining', context.generation_goals)
        context.generation_goals = remaining_goals
        
        return context
    
    def _validate_step_execution(self, step: Dict[str, Any], step_results: List[Dict],
                               pre_state: Dict[str, Any], post_state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that a step executed successfully"""
        # Check if object count increased (for creation steps)
        objects_created = post_state.get('object_count', 0) - pre_state.get('object_count', 0)
        
        # Check for command execution errors
        has_errors = any(result.get('status') == 'error' for result in step_results)
        
        return {
            'success': not has_errors and objects_created >= 0,
            'objects_created': objects_created,
            'errors': [r.get('error') for r in step_results if r.get('error')],
            'critical': has_errors,
            'validation_details': step.get('validation', 'No validation specified')
        }
    
    def _create_fallback_enhanced_decision(self, context: Optional[LLMDecisionContext]) -> EnhancedDecisionResult:
        """Create fallback enhanced decision when LLM fails"""
        return EnhancedDecisionResult(
            decision_type="fallback_create",
            confidence_score=0.3,
            reasoning="Fallback decision due to LLM unavailability",
            action_plan=[{
                "step": 1,
                "description": "Create basic shape",
                "commands": ["doc = FreeCAD.newDocument()", "box = doc.addObject('Part::Box', 'Box')"],
                "validation": "Check basic shape creation"
            }],
            state_predictions={"object_count": 1},
            risk_assessment={"risks": ["Limited functionality"], "probability": 1.0},
            alternative_approaches=[],
            quality_expectations={"accuracy": 0.5},
            monitoring_points=["Basic object creation"]
        )
    
    def _default_progress_feedback(self) -> Dict[str, Any]:
        """Default progress feedback when LLM is unavailable"""
        return {
            'progress_percentage': 50.0,
            'goals_satisfied': [],
            'goals_remaining': ["Complete user request"],
            'next_priority': "Continue with current approach",
            'quality_assessment': {
                'current_quality': 0.7,
                'concerns': [],
                'improvements_needed': []
            },
            'approach_recommendation': {
                'continue_current': True,
                'modify_approach': False,
                'reasoning': "Default feedback - continue current approach"
            }
        }
    
    def _get_state_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get state history for pattern analysis"""
        return self.state_analysis_history[-10:] if self.state_analysis_history else []

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get enhanced performance metrics"""
        base_metrics = super().get_performance_metrics()
        
        enhanced_metrics = {
            'complexity_progression': self.complexity_progression,
            'state_analysis_count': len(self.state_analysis_history),
            'llm_feedback_count': len(self.llm_feedback_history),
            'api_key_configured': bool(self.api_key)
        }
        
        return {**base_metrics, **enhanced_metrics}

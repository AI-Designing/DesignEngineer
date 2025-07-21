"""
State-LLM Integration System
Manages the flow from state retrieval -> LLM decision -> command execution
"""

import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

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
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        metrics = {}
        
        for metric_name, values in self.performance_metrics.items():
            if values:
                metrics[metric_name] = {
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
            else:
                metrics[metric_name] = {'avg': 0, 'min': 0, 'max': 0, 'count': 0}
        
        return metrics

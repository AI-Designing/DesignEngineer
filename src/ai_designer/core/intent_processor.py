"""
Intent Processing Layer
Processes user input and determines the appropriate action based on current state
"""

import json
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

class IntentProcessor:
    """
    Processes user intents and determines appropriate actions based on current state.
    This is the first layer after user input in the architecture.
    """
    
    def __init__(self, state_service=None, llm_client=None):
        self.state_service = state_service
        self.llm_client = llm_client
        
        # Intent patterns for quick classification
        self.intent_patterns = {
            'create_object': [
                r'create.*(?:box|cube|cylinder|sphere|cone|torus)',
                r'make.*(?:box|cube|cylinder|sphere|cone|torus)',
                r'add.*(?:box|cube|cylinder|sphere|cone|torus)',
                r'new.*(?:box|cube|cylinder|sphere|cone|torus)'
            ],
            'modify_object': [
                r'move.*', r'rotate.*', r'scale.*', r'resize.*',
                r'change.*(?:size|position|orientation)',
                r'modify.*', r'edit.*', r'update.*'
            ],
            'analyze_state': [
                r'analyze.*', r'check.*state', r'what.*current',
                r'show.*state', r'status.*', r'examine.*'
            ],
            'save_export': [
                r'save.*', r'export.*', r'output.*',
                r'write.*file', r'generate.*file'
            ],
            'delete_object': [
                r'delete.*', r'remove.*', r'clear.*'
            ],
            'query_info': [
                r'what.*', r'how.*', r'show.*objects',
                r'list.*', r'info.*', r'help.*'
            ]
        }
    
    def process_intent(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process user intent and return structured action plan
        
        Args:
            user_input: Natural language input from user
            session_id: Optional session identifier
            
        Returns:
            Dict containing:
            - intent_type: Classified intent
            - confidence: Classification confidence
            - context: Current state context
            - action_plan: Suggested actions
            - requires_llm: Whether LLM processing is needed
        """
        
        # Step 1: Get current state for context
        current_state = self._get_current_state(session_id)
        
        # Step 2: Classify intent
        intent_classification = self._classify_intent(user_input)
        
        # Step 3: Analyze context and determine complexity
        context_analysis = self._analyze_context(user_input, current_state)
        
        # Step 4: Create action plan
        action_plan = self._create_action_plan(
            user_input, 
            intent_classification, 
            context_analysis
        )
        
        return {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'session_id': session_id,
            'intent_type': intent_classification['type'],
            'confidence': intent_classification['confidence'],
            'context': context_analysis,
            'action_plan': action_plan,
            'requires_llm': action_plan['requires_llm'],
            'state_snapshot': current_state
        }
    
    def _get_current_state(self, session_id: str = None) -> Dict[str, Any]:
        """Retrieve current FreeCAD state"""
        if not self.state_service:
            return {'error': 'State service not available'}
        
        try:
            # Get latest cached state
            state_key = f"session_{session_id}" if session_id else None
            cached_state = self.state_service.get_latest_state(state_key)
            
            if cached_state:
                return cached_state
            
            # If no cached state, analyze current document
            current_analysis = self.state_service.analyze_and_cache()
            return current_analysis if current_analysis else {}
            
        except Exception as e:
            return {'error': f'Failed to retrieve state: {e}'}
    
    def _classify_intent(self, user_input: str) -> Dict[str, Any]:
        """Classify user intent using pattern matching"""
        user_input_lower = user_input.lower()
        
        intent_scores = {}
        
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            matched_patterns = []
            
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    score += 1
                    matched_patterns.append(pattern)
            
            if score > 0:
                intent_scores[intent_type] = {
                    'score': score,
                    'patterns': matched_patterns
                }
        
        # Determine best match
        if intent_scores:
            best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x]['score'])
            max_score = intent_scores[best_intent]['score']
            confidence = min(max_score / len(self.intent_patterns[best_intent]), 1.0)
            
            return {
                'type': best_intent,
                'confidence': confidence,
                'all_scores': intent_scores
            }
        
        # Fallback to general intent
        return {
            'type': 'general_command',
            'confidence': 0.5,
            'all_scores': {}
        }
    
    def _analyze_context(self, user_input: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current context to determine action complexity"""
        
        context = {
            'has_active_document': False,
            'object_count': 0,
            'objects_present': [],
            'needs_new_document': False,
            'complexity_level': 'simple',
            'dependencies': [],
            'potential_conflicts': []
        }
        
        if 'error' not in current_state:
            # Analyze document state
            analysis = current_state.get('analysis', {})
            context['has_active_document'] = current_state.get('object_count', 0) > 0
            context['object_count'] = current_state.get('object_count', 0)
            context['objects_present'] = [
                obj['name'] for obj in current_state.get('objects', [])
            ]
            
            # Determine if we need a new document
            if not context['has_active_document'] and 'create' in user_input.lower():
                context['needs_new_document'] = True
            
            # Analyze complexity based on state
            if context['object_count'] > 5:
                context['complexity_level'] = 'complex'
            elif context['object_count'] > 2:
                context['complexity_level'] = 'moderate'
            
            # Check for potential dependencies
            if 'modify' in user_input.lower() or 'move' in user_input.lower():
                if context['object_count'] > 1:
                    context['dependencies'] = context['objects_present']
        
        return context
    
    def _create_action_plan(self, user_input: str, intent: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed action plan based on intent and context"""
        
        action_plan = {
            'primary_action': intent['type'],
            'steps': [],
            'requires_llm': False,
            'estimated_complexity': context['complexity_level'],
            'prerequisites': [],
            'expected_outcomes': []
        }
        
        intent_type = intent['type']
        
        if intent_type == 'create_object':
            action_plan['steps'] = self._plan_object_creation(user_input, context)
            action_plan['requires_llm'] = intent['confidence'] < 0.8
            
        elif intent_type == 'modify_object':
            action_plan['steps'] = self._plan_object_modification(user_input, context)
            action_plan['requires_llm'] = True  # Modifications usually need LLM
            
        elif intent_type == 'analyze_state':
            action_plan['steps'] = [
                {'action': 'retrieve_current_state', 'priority': 1},
                {'action': 'format_state_report', 'priority': 2},
                {'action': 'present_to_user', 'priority': 3}
            ]
            action_plan['requires_llm'] = False
            
        elif intent_type == 'save_export':
            action_plan['steps'] = self._plan_save_export(user_input, context)
            action_plan['requires_llm'] = 'export' in user_input.lower()
            
        elif intent_type == 'query_info':
            action_plan['steps'] = [
                {'action': 'analyze_query', 'priority': 1},
                {'action': 'retrieve_relevant_info', 'priority': 2},
                {'action': 'format_response', 'priority': 3}
            ]
            action_plan['requires_llm'] = True
            
        else:  # general_command
            action_plan['steps'] = [
                {'action': 'full_llm_processing', 'priority': 1},
                {'action': 'validate_command', 'priority': 2},
                {'action': 'execute_with_monitoring', 'priority': 3}
            ]
            action_plan['requires_llm'] = True
        
        # Add prerequisites
        if context['needs_new_document']:
            action_plan['prerequisites'].append('create_new_document')
        
        if not context['has_active_document'] and intent_type != 'analyze_state':
            action_plan['prerequisites'].append('ensure_active_document')
        
        return action_plan
    
    def _plan_object_creation(self, user_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan steps for object creation"""
        steps = []
        
        if context['needs_new_document']:
            steps.append({'action': 'create_new_document', 'priority': 1})
        
        # Check if dimensions are specified
        if re.search(r'\d+', user_input):
            steps.append({'action': 'parse_dimensions', 'priority': 2})
            steps.append({'action': 'create_object_with_dimensions', 'priority': 3})
        else:
            steps.append({'action': 'create_object_default', 'priority': 2})
        
        steps.extend([
            {'action': 'validate_creation', 'priority': 4},
            {'action': 'auto_save', 'priority': 5},
            {'action': 'update_state_cache', 'priority': 6}
        ])
        
        return steps
    
    def _plan_object_modification(self, user_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan steps for object modification"""
        return [
            {'action': 'identify_target_objects', 'priority': 1},
            {'action': 'analyze_modification_request', 'priority': 2},
            {'action': 'validate_modification_safety', 'priority': 3},
            {'action': 'execute_modification', 'priority': 4},
            {'action': 'verify_result', 'priority': 5},
            {'action': 'update_state_cache', 'priority': 6}
        ]
    
    def _plan_save_export(self, user_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan steps for save/export operations"""
        steps = []
        
        if 'export' in user_input.lower():
            steps.extend([
                {'action': 'determine_export_format', 'priority': 1},
                {'action': 'validate_objects_for_export', 'priority': 2},
                {'action': 'execute_export', 'priority': 3}
            ])
        else:
            steps.extend([
                {'action': 'determine_save_location', 'priority': 1},
                {'action': 'execute_save', 'priority': 2}
            ])
        
        steps.append({'action': 'confirm_operation', 'priority': len(steps) + 1})
        return steps

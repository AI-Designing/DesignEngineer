"""
State-Driven Command Processor
Handles complex natural language commands by breaking them down into steps
and using Redis state for intelligent decision making.
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

class StateAwareCommandProcessor:
    """
    Enhanced command processor that uses Redis state to break down complex
    natural language commands into multiple executable steps.
    """
    
    def __init__(self, llm_client, state_cache, api_client, command_executor):
        self.llm_client = llm_client
        self.state_cache = state_cache
        self.api_client = api_client
        self.command_executor = command_executor
        self.session_id = f"session_{int(time.time())}"
        
    def process_complex_command(self, nl_command: str) -> Dict[str, Any]:
        """
        Main entry point: Process complex natural language command using state-driven approach
        
        Flow:
        1. Get current state from Redis
        2. Use LLM to break down command into steps
        3. Execute each step, updating state after each
        4. Use updated state to inform next step decisions
        """
        print(f"🧠 Processing complex command: {nl_command}")
        
        try:
            # Step 1: Get current state from Redis
            current_state = self._get_current_state()
            print(f"📊 Current state retrieved: {len(current_state.get('objects', []))} objects")
            
            # Step 2: Use LLM to break down the command into steps
            task_breakdown = self._decompose_task(nl_command, current_state)
            
            if not task_breakdown or 'error' in task_breakdown:
                return {"status": "error", "message": "Failed to decompose task"}
            
            print(f"📋 Task broken down into {len(task_breakdown['steps'])} steps")
            
            # Step 3: Execute each step with state updates
            return self._execute_step_sequence(task_breakdown, nl_command)
            
        except Exception as e:
            print(f"❌ Error in complex command processing: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_current_state(self) -> Dict[str, Any]:
        """Get the current FreeCAD document state and any cached state from Redis"""
        try:
            # Get live state from FreeCAD
            live_state = self.api_client.get_document_state()
            
            # Get cached state from Redis
            cached_states = self.state_cache.list_states(session_id=self.session_id)
            latest_cached_state = {}
            
            if cached_states:
                # Get the most recent state
                latest_key = max(cached_states)
                latest_cached_state = self.state_cache.retrieve_state(latest_key) or {}
            
            # Combine live and cached state
            combined_state = {
                "live_state": live_state,
                "cached_state": latest_cached_state,
                "objects": live_state.get("objects", []),
                "object_count": live_state.get("object_count", 0),
                "document_name": live_state.get("document_name", "Unknown"),
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id
            }
            
            return combined_state
            
        except Exception as e:
            print(f"⚠️ Error getting current state: {e}")
            return {"objects": [], "object_count": 0, "error": str(e)}
    
    def _decompose_task(self, nl_command: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to break down complex natural language command into executable steps
        """
        print("🔧 Decomposing task with LLM...")
        
        try:
            # Create a detailed prompt for task decomposition
            decomposition_prompt = f"""
You are a FreeCAD automation expert. Break down the following user request into a sequence of executable steps.

User Request: "{nl_command}"

Current FreeCAD State:
- Objects in document: {current_state.get('object_count', 0)}
- Object list: {[obj.get('name', 'Unknown') for obj in current_state.get('objects', [])]}
- Document: {current_state.get('document_name', 'Unknown')}

Instructions:
1. Analyze the user request and current state
2. Break the request into logical, sequential steps
3. Each step should be a single, specific FreeCAD operation
4. Consider object positioning, sizing, and relationships
5. If objects need to be combined, plan the positioning first
6. Return ONLY a JSON object with this exact structure:

{{
    "total_steps": <number>,
    "analysis": "<brief analysis of what needs to be done>",
    "steps": [
        {{
            "step_number": 1,
            "description": "<what this step does>",
            "action_type": "<create|modify|position|combine>",
            "target_object": "<object name or type>",
            "details": {{
                "object_type": "<Part::Box|Part::Cylinder|Part::Cone|Part::Sphere|Part::Torus|etc>",
                "parameters": {{"param1": "value1", "param2": "value2"}},
                "positioning": {{"x": 0, "y": 0, "z": 0, "explanation": "why positioned here"}}
            }}
        }}
    ]
}}

Example for "create a cone and cylinder together":
{{
    "total_steps": 3,
    "analysis": "Create a cylinder as base, create a cone positioned on top, then optionally combine them",
    "steps": [
        {{
            "step_number": 1,
            "description": "Create a base cylinder",
            "action_type": "create",
            "target_object": "Cylinder",
            "details": {{
                "object_type": "Part::Cylinder",
                "parameters": {{"radius": 5, "height": 10}},
                "positioning": {{"x": 0, "y": 0, "z": 0, "explanation": "base position"}}
            }}
        }},
        {{
            "step_number": 2,
            "description": "Create a cone on top of cylinder",
            "action_type": "create",
            "target_object": "Cone",
            "details": {{
                "object_type": "Part::Cone", 
                "parameters": {{"radius1": 5, "radius2": 0, "height": 8}},
                "positioning": {{"x": 0, "y": 0, "z": 10, "explanation": "positioned on top of cylinder"}}
            }}
        }},
        {{
            "step_number": 3,
            "description": "Combine cylinder and cone",
            "action_type": "combine",
            "target_object": "Fusion",
            "details": {{
                "object_type": "Part::MultiFuse",
                "parameters": {{"shapes": ["Cylinder", "Cone"]}},
                "positioning": {{"x": 0, "y": 0, "z": 0, "explanation": "fusion combines at original positions"}}
            }}
        }}
    ]
}}
"""
            
            # Use LLM to decompose the task
            response = self.llm_client.llm.invoke(decomposition_prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            print(f"🤖 LLM decomposition response: {response_text[:200]}...")
            
            # Try to parse JSON response
            try:
                # Clean the response - remove any markdown formatting
                clean_response = response_text.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]
                elif clean_response.startswith('```'):
                    clean_response = clean_response[3:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
                
                task_breakdown = json.loads(clean_response.strip())
                
                # Validate the structure
                if not all(key in task_breakdown for key in ['total_steps', 'analysis', 'steps']):
                    raise ValueError("Invalid task breakdown structure")
                
                print(f"✅ Task successfully decomposed: {task_breakdown['analysis']}")
                return task_breakdown
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse LLM response as JSON: {e}")
                print(f"Raw response: {response_text}")
                return {"error": "Invalid JSON response from LLM"}
                
        except Exception as e:
            print(f"❌ Error in task decomposition: {e}")
            return {"error": str(e)}
    
    def _execute_step_sequence(self, task_breakdown: Dict[str, Any], original_command: str) -> Dict[str, Any]:
        """
        Execute the sequence of steps, updating state after each step
        """
        print(f"🚀 Executing {task_breakdown['total_steps']} steps...")
        
        results = []
        execution_state = {
            "original_command": original_command,
            "task_analysis": task_breakdown['analysis'],
            "total_steps": task_breakdown['total_steps'],
            "completed_steps": 0,
            "failed_steps": 0,
            "created_objects": [],
            "start_time": datetime.now().isoformat()
        }
        
        for step in task_breakdown['steps']:
            step_number = step['step_number']
            step_description = step['description']
            
            print(f"\n🔄 Step {step_number}/{task_breakdown['total_steps']}: {step_description}")
            
            try:
                # Get current state before this step
                current_state = self._get_current_state()
                
                # Generate FreeCAD command for this step
                freecad_command = self._generate_step_command(step, current_state)
                
                if freecad_command:
                    print(f"📝 Generated command: {freecad_command[:100]}...")
                    
                    # Execute the command
                    execution_result = self.command_executor.execute(freecad_command)
                    
                    if execution_result.get("status") == "success":
                        print(f"✅ Step {step_number} completed successfully")
                        execution_state["completed_steps"] += 1
                        
                        # Update state in Redis
                        updated_state = self._get_current_state()
                        state_key = self.state_cache.cache_state(
                            updated_state,
                            session_id=self.session_id,
                            document_name=updated_state.get("document_name")
                        )
                        
                        # Track created objects
                        if step['action_type'] == 'create':
                            target_object = step['target_object']
                            execution_state["created_objects"].append({
                                "name": target_object,
                                "step": step_number,
                                "type": step['details'].get('object_type', 'Unknown')
                            })
                        
                        results.append({
                            "step": step_number,
                            "status": "success",
                            "description": step_description,
                            "command": freecad_command,
                            "state_key": state_key
                        })
                        
                    else:
                        print(f"❌ Step {step_number} failed: {execution_result.get('message', 'Unknown error')}")
                        execution_state["failed_steps"] += 1
                        results.append({
                            "step": step_number,
                            "status": "failed",
                            "description": step_description,
                            "error": execution_result.get('message', 'Unknown error')
                        })
                        
                else:
                    print(f"❌ Step {step_number} failed: Could not generate command")
                    execution_state["failed_steps"] += 1
                    results.append({
                        "step": step_number,
                        "status": "failed",
                        "description": step_description,
                        "error": "Could not generate FreeCAD command"
                    })
                
            except Exception as e:
                print(f"❌ Step {step_number} failed with exception: {e}")
                execution_state["failed_steps"] += 1
                results.append({
                    "step": step_number,
                    "status": "failed",
                    "description": step_description,
                    "error": str(e)
                })
        
        # Final summary
        execution_state["end_time"] = datetime.now().isoformat()
        execution_state["overall_status"] = "success" if execution_state["failed_steps"] == 0 else "partial"
        
        print(f"\n🎯 Execution Summary:")
        print(f"   ✅ Completed: {execution_state['completed_steps']}/{execution_state['total_steps']}")
        print(f"   ❌ Failed: {execution_state['failed_steps']}")
        print(f"   📦 Objects created: {len(execution_state['created_objects'])}")
        
        return {
            "status": execution_state["overall_status"],
            "execution_state": execution_state,
            "step_results": results,
            "summary": f"Completed {execution_state['completed_steps']}/{execution_state['total_steps']} steps"
        }
    
    def _generate_step_command(self, step: Dict[str, Any], current_state: Dict[str, Any]) -> Optional[str]:
        """
        Generate a specific FreeCAD command for a single step using current state context
        """
        try:
            action_type = step['action_type']
            target_object = step['target_object']
            details = step['details']
            
            print(f"🔨 Generating command for step: {step.get('description', 'Unknown')}")
            print(f"   Action: {action_type}, Target: {target_object}")
            print(f"   Details: {details}")
            
            # Create a simple, direct command based on action type
            if action_type == 'create':
                object_type = details.get('object_type', '')
                parameters = details.get('parameters', {})
                positioning = details.get('positioning', {})
                
                # Generate direct FreeCAD command based on object type
                if 'Cylinder' in object_type:
                    radius = parameters.get('radius', 5)
                    height = parameters.get('height', 10)
                    command = f"""cylinder = doc.addObject('Part::Cylinder', '{target_object}')
cylinder.Radius = {radius}
cylinder.Height = {height}"""
                    
                elif 'Cone' in object_type:
                    radius1 = parameters.get('radius1', 5)
                    radius2 = parameters.get('radius2', 0)
                    height = parameters.get('height', 8)
                    command = f"""cone = doc.addObject('Part::Cone', '{target_object}')
cone.Radius1 = {radius1}
cone.Radius2 = {radius2}
cone.Height = {height}"""
                    
                elif 'Box' in object_type:
                    length = parameters.get('length', 10)
                    width = parameters.get('width', 10)
                    height = parameters.get('height', 10)
                    command = f"""box = doc.addObject('Part::Box', '{target_object}')
box.Length = {length}
box.Width = {width}
box.Height = {height}"""
                    
                elif 'Sphere' in object_type:
                    radius = parameters.get('radius', 10)
                    command = f"""sphere = doc.addObject('Part::Sphere', '{target_object}')
sphere.Radius = {radius}"""
                    
                else:
                    # Fallback to LLM generation
                    print(f"⚠️ Unknown object type {object_type}, using LLM fallback")
                    return self._llm_generate_fallback(step, current_state)
                
                # Add positioning if specified
                if positioning.get('x', 0) != 0 or positioning.get('y', 0) != 0 or positioning.get('z', 0) != 0:
                    x, y, z = positioning.get('x', 0), positioning.get('y', 0), positioning.get('z', 0)
                    var_name = target_object.lower()
                    command += f"""
{var_name}.Placement = App.Placement(App.Vector({x},{y},{z}), App.Rotation())"""
                
                # Always end with recompute
                command += "\ndoc.recompute()"
                
                return command
                
            elif action_type == 'combine':
                # Handle fusion/combination
                shapes = parameters.get('shapes', [])
                if len(shapes) >= 2:
                    shapes_str = ', '.join([f"doc.getObject('{shape}')" for shape in shapes])
                    command = f"""fusion = doc.addObject('Part::MultiFuse', '{target_object}')
fusion.Shapes = [{shapes_str}]
doc.recompute()"""
                    return command
                else:
                    print(f"⚠️ Insufficient shapes for combination: {shapes}")
                    return None
            
            else:
                # Fallback to LLM for complex operations
                print(f"⚠️ Unsupported action type {action_type}, using LLM fallback")
                return self._llm_generate_fallback(step, current_state)
                
        except Exception as e:
            print(f"❌ Error generating step command: {e}")
            print(f"   Step data: {step}")
            return None
            
    def _llm_generate_fallback(self, step: Dict[str, Any], current_state: Dict[str, Any]) -> Optional[str]:
        """Fallback to LLM generation with simpler prompt"""
        try:
            simple_prompt = f"Create FreeCAD Python code to: {step.get('description', 'unknown task')}"
            return self.llm_client.generate_command(simple_prompt, current_state)
        except Exception as e:
            print(f"❌ LLM fallback failed: {e}")
            return None

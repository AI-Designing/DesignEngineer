"""
Enhanced State-Aware Command Generator
Generates commands with full state context and decision-making capability
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class StateAwareCommandGenerator:
    """
    Generates FreeCAD commands with full state awareness and context
    """

    def __init__(self, llm_client=None, state_service=None):
        self.llm_client = llm_client
        self.state_service = state_service

        # Enhanced prompt templates with state awareness
        self.prompt_templates = {
            "create_object": self._get_create_object_prompt(),
            "modify_object": self._get_modify_object_prompt(),
            "analyze_and_decide": self._get_analysis_prompt(),
            "next_step": self._get_next_step_prompt(),
            "complete_component": self._get_component_completion_prompt(),
        }

    def generate_command_with_state(
        self, user_input: str, intent_data: Dict[str, Any], session_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate command with full state context and next-step planning

        Args:
            user_input: User's natural language input
            intent_data: Processed intent information
            session_id: Session identifier for state tracking

        Returns:
            Dict containing:
            - command: Generated FreeCAD command
            - next_steps: Suggested next steps
            - state_changes: Expected state changes
            - decision_reasoning: Why this command was chosen
        """

        # Get comprehensive state context
        state_context = self._get_comprehensive_state(session_id)

        # Determine the appropriate prompt template
        intent_type = intent_data.get("intent_type", "general_command")
        action_plan = intent_data.get("action_plan", {})

        # Generate command based on complexity and context
        if action_plan.get("requires_llm", True):
            result = self._generate_with_llm(user_input, intent_data, state_context)
        else:
            result = self._generate_with_rules(user_input, intent_data, state_context)

        # Add decision metadata
        result["generation_metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "intent_type": intent_type,
            "state_snapshot_id": state_context.get("id"),
            "decision_method": "llm" if action_plan.get("requires_llm") else "rules",
            "confidence": intent_data.get("confidence", 0.5),
        }

        return result

    def _get_comprehensive_state(self, session_id: str = None) -> Dict[str, Any]:
        """Get comprehensive state including history and context"""
        state_context = {
            "current_state": {},
            "recent_history": [],
            "session_context": {},
            "capabilities": {},
            "constraints": {},
        }

        if self.state_service:
            try:
                # Get current state
                current_state = self.state_service.get_latest_state(session_id)
                if current_state:
                    state_context["current_state"] = current_state

                # Get command history
                history = self.state_service.get_command_history(session_id, limit=5)
                if history:
                    state_context["recent_history"] = history

                # Get session context
                session_data = self.state_service.get_session_context(session_id)
                if session_data:
                    state_context["session_context"] = session_data

            except Exception as e:
                print(f"Warning: Failed to get comprehensive state: {e}")

        # Add current capabilities and constraints
        state_context["capabilities"] = self._get_current_capabilities(
            state_context["current_state"]
        )
        state_context["constraints"] = self._get_current_constraints(
            state_context["current_state"]
        )

        return state_context

    def _generate_with_llm(
        self,
        user_input: str,
        intent_data: Dict[str, Any],
        state_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate command using LLM with full state context"""
        if not self.llm_client:
            return {"error": "LLM client not available"}

        try:
            # Select appropriate prompt template
            intent_type = intent_data.get("intent_type", "general_command")
            prompt_template = self.prompt_templates.get(
                intent_type, self.prompt_templates["analyze_and_decide"]
            )

            # Prepare state context for LLM
            formatted_state = self._format_state_for_llm(state_context)

            # Generate command with state awareness
            prompt = prompt_template.format(
                user_input=user_input,
                state_context=formatted_state,
                intent_data=json.dumps(intent_data, indent=2),
                session_context=json.dumps(
                    state_context.get("session_context", {}), indent=2
                ),
            )

            # Get LLM response
            response = self.llm_client.generate_command(prompt)

            # Parse and structure the response
            return self._parse_llm_response(response, intent_data, state_context)

        except Exception as e:
            return {"error": f"LLM generation failed: {e}"}

    def _generate_with_rules(
        self,
        user_input: str,
        intent_data: Dict[str, Any],
        state_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate command using rule-based approach"""
        intent_type = intent_data.get("intent_type")
        current_state = state_context.get("current_state", {})

        result = {
            "command": "",
            "next_steps": [],
            "state_changes": {},
            "decision_reasoning": "",
            "confidence": 0.8,
        }

        if intent_type == "create_object":
            result = self._generate_create_object_command(user_input, current_state)
        elif intent_type == "analyze_state":
            result = self._generate_analyze_command(current_state)
        elif intent_type == "save_export":
            result = self._generate_save_command(user_input, current_state)
        else:
            # Fallback to LLM for complex cases
            return self._generate_with_llm(user_input, intent_data, state_context)

        return result

    def _generate_create_object_command(
        self, user_input: str, current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate object creation command with state awareness"""
        user_lower = user_input.lower()

        # Determine if we need a new document
        object_count = current_state.get("object_count", 0)
        needs_document = object_count == 0

        # Extract object type and dimensions
        if "box" in user_lower or "cube" in user_lower:
            obj_type = "box"
            dimensions = self._extract_box_dimensions(user_input)
        elif "cylinder" in user_lower:
            obj_type = "cylinder"
            dimensions = self._extract_cylinder_dimensions(user_input)
        elif "sphere" in user_lower:
            obj_type = "sphere"
            dimensions = self._extract_sphere_dimensions(user_input)
        else:
            obj_type = "box"  # Default
            dimensions = {"length": 10, "width": 10, "height": 10}

        # Generate command
        if needs_document:
            command = "doc = App.newDocument('NewDesign')\n"
        else:
            command = ""

        if obj_type == "box":
            command += f"box = doc.addObject('Part::Box', 'Box')\n"
            command += f"box.Length = {dimensions.get('length', 10)}\n"
            command += f"box.Width = {dimensions.get('width', 10)}\n"
            command += f"box.Height = {dimensions.get('height', 10)}\n"
        elif obj_type == "cylinder":
            command += f"cylinder = doc.addObject('Part::Cylinder', 'Cylinder')\n"
            command += f"cylinder.Radius = {dimensions.get('radius', 5)}\n"
            command += f"cylinder.Height = {dimensions.get('height', 20)}\n"
        elif obj_type == "sphere":
            command += f"sphere = doc.addObject('Part::Sphere', 'Sphere')\n"
            command += f"sphere.Radius = {dimensions.get('radius', 10)}\n"

        command += "doc.recompute()"

        return {
            "command": command,
            "next_steps": [
                "modify_object_properties",
                "add_constraints",
                "create_additional_features",
            ],
            "state_changes": {
                "new_objects": [f"{obj_type.title()}"],
                "object_count_change": +1,
                "document_modified": True,
            },
            "decision_reasoning": f"Created {obj_type} based on user request with state-aware document handling",
            "confidence": 0.9,
        }

    def _generate_analyze_command(
        self, current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate state analysis command"""
        return {
            "command": 'print("Current document analysis:")\nfor obj in doc.Objects:\n    print(f"Object: {obj.Name}, Type: {obj.TypeId}")',
            "next_steps": [
                "review_analysis_results",
                "plan_next_modeling_step",
                "optimize_current_design",
            ],
            "state_changes": {"analysis_performed": True},
            "decision_reasoning": "Providing comprehensive document analysis",
            "confidence": 1.0,
        }

    def _generate_save_command(
        self, user_input: str, current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate save/export command with state awareness"""

        if "export" in user_input.lower():
            if "stl" in user_input.lower():
                command = """
objects = [obj for obj in doc.Objects if hasattr(obj, 'Shape')]
if objects:
    import Mesh
    Mesh.export(objects, "export.stl")
    print("STL exported successfully")
else:
    print("No objects to export")
"""
                return {
                    "command": command,
                    "next_steps": ["verify_export", "share_file"],
                    "state_changes": {"file_exported": True},
                    "decision_reasoning": "Exporting to STL format based on request",
                    "confidence": 0.9,
                }

        # Default save
        command = 'doc.saveAs("design.FCStd")\nprint("Document saved successfully")'

        return {
            "command": command,
            "next_steps": ["continue_modeling", "backup_file"],
            "state_changes": {"document_saved": True},
            "decision_reasoning": "Saving document to preserve current state",
            "confidence": 0.95,
        }

    def _format_state_for_llm(self, state_context: Dict[str, Any]) -> str:
        """Format state context for LLM consumption"""
        formatted_parts = []

        # Current state
        current_state = state_context.get("current_state", {})
        if current_state:
            formatted_parts.append("CURRENT STATE:")
            formatted_parts.append(
                f"- Document has {current_state.get('object_count', 0)} objects"
            )

            objects = current_state.get("objects", [])
            if objects:
                formatted_parts.append("- Objects present:")
                for obj in objects[:5]:  # Limit to first 5
                    formatted_parts.append(
                        f"  * {obj.get('name', 'Unknown')} ({obj.get('type', 'Unknown')})"
                    )

        # Recent history
        history = state_context.get("recent_history", [])
        if history:
            formatted_parts.append("\nRECENT ACTIONS:")
            for i, action in enumerate(history[-3:], 1):  # Last 3 actions
                formatted_parts.append(
                    f"{i}. {action.get('command', 'Unknown action')}"
                )

        # Capabilities and constraints
        capabilities = state_context.get("capabilities", {})
        if capabilities:
            formatted_parts.append("\nCURRENT CAPABILITIES:")
            for capability, status in capabilities.items():
                formatted_parts.append(f"- {capability}: {'✓' if status else '✗'}")

        constraints = state_context.get("constraints", {})
        if constraints:
            formatted_parts.append("\nCONSTRAINTS:")
            for constraint, value in constraints.items():
                formatted_parts.append(f"- {constraint}: {value}")

        return (
            "\\n".join(formatted_parts)
            if formatted_parts
            else "No state information available"
        )

    def _parse_llm_response(
        self, response: str, intent_data: Dict[str, Any], state_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse and structure LLM response"""

        # For now, treat the response as the command
        # In a more sophisticated implementation, we could parse structured responses

        return {
            "command": response.strip(),
            "next_steps": self._suggest_next_steps(intent_data, state_context),
            "state_changes": self._predict_state_changes(response, state_context),
            "decision_reasoning": f'Generated using LLM based on {intent_data.get("intent_type", "general")} intent',
            "confidence": intent_data.get("confidence", 0.7),
        }

    def _suggest_next_steps(
        self, intent_data: Dict[str, Any], state_context: Dict[str, Any]
    ) -> List[str]:
        """Suggest logical next steps based on current action and state"""
        intent_type = intent_data.get("intent_type")

        if intent_type == "create_object":
            return ["modify_properties", "add_constraints", "create_related_objects"]
        elif intent_type == "modify_object":
            return ["verify_changes", "add_more_features", "save_progress"]
        elif intent_type == "analyze_state":
            return ["plan_next_action", "optimize_design", "review_requirements"]
        else:
            return ["analyze_result", "continue_workflow", "save_progress"]

    def _predict_state_changes(
        self, command: str, state_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict state changes from command"""
        changes = {}

        command_lower = command.lower()

        if "addobject" in command_lower:
            changes["object_count_change"] = +1
            changes["document_modified"] = True

        if "newdocument" in command_lower:
            changes["new_document"] = True
            changes["object_count"] = 0

        if "saveas" in command_lower or "save(" in command_lower:
            changes["document_saved"] = True

        if "export" in command_lower:
            changes["file_exported"] = True

        return changes

    def _get_current_capabilities(
        self, current_state: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Determine current system capabilities based on state"""
        return {
            "can_create_objects": True,
            "can_modify_objects": current_state.get("object_count", 0) > 0,
            "can_save_document": current_state.get("object_count", 0) > 0,
            "can_export_files": current_state.get("object_count", 0) > 0,
            "has_active_document": current_state.get("object_count", 0) >= 0,
        }

    def _get_current_constraints(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Determine current constraints based on state"""
        return {
            "max_objects_recommended": 50,
            "current_object_count": current_state.get("object_count", 0),
            "memory_usage": "normal",  # Could be enhanced with actual monitoring
            "processing_capability": "full",
        }

    # Helper methods for dimension extraction
    def _extract_box_dimensions(self, text: str) -> Dict[str, float]:
        """Extract box dimensions from text"""
        import re

        dimensions = {"length": 10, "width": 10, "height": 10}

        # Look for patterns like "10x10x10"
        pattern = r"(\\d+(?:\\.\\d+)?)\\s*(?:x|\\*|by)\\s*(\\d+(?:\\.\\d+)?)\\s*(?:x|\\*|by)\\s*(\\d+(?:\\.\\d+)?)"
        match = re.search(pattern, text)
        if match:
            dimensions["length"] = float(match.group(1))
            dimensions["width"] = float(match.group(2))
            dimensions["height"] = float(match.group(3))

        return dimensions

    def _extract_cylinder_dimensions(self, text: str) -> Dict[str, float]:
        """Extract cylinder dimensions from text"""
        import re

        dimensions = {"radius": 5, "height": 20}

        # Look for radius and height patterns
        radius_match = re.search(r"radius\\s*(\\d+(?:\\.\\d+)?)", text)
        height_match = re.search(r"height\\s*(\\d+(?:\\.\\d+)?)", text)

        if radius_match:
            dimensions["radius"] = float(radius_match.group(1))
        if height_match:
            dimensions["height"] = float(height_match.group(1))

        return dimensions

    def _extract_sphere_dimensions(self, text: str) -> Dict[str, float]:
        """Extract sphere dimensions from text"""
        import re

        dimensions = {"radius": 10}

        radius_match = re.search(r"radius\\s*(\\d+(?:\\.\\d+)?)", text)
        if radius_match:
            dimensions["radius"] = float(radius_match.group(1))

        return dimensions

    # Prompt templates
    def _get_create_object_prompt(self) -> str:
        return """
You are an expert FreeCAD Python scripter with full awareness of the current design state.

USER REQUEST: {user_input}

CURRENT STATE CONTEXT:
{state_context}

INTENT ANALYSIS:
{intent_data}

SESSION CONTEXT:
{session_context}

Based on the current state and user request, generate a FreeCAD Python command that:
1. Takes into account the existing objects and document state
2. Creates appropriate objects with proper naming to avoid conflicts
3. Uses reasonable dimensions if not specified
4. Ensures proper document structure

IMPORTANT:
- Only output the Python code, no explanations
- Consider existing objects when naming new ones
- Use proper FreeCAD scripting patterns
- Include doc.recompute() at the end
- If no document exists, create one first

Generate the command:
"""

    def _get_modify_object_prompt(self) -> str:
        return """
You are an expert FreeCAD Python scripter modifying existing objects.

USER REQUEST: {user_input}

CURRENT STATE CONTEXT:
{state_context}

INTENT ANALYSIS:
{intent_data}

Generate a modification command that:
1. Identifies the correct objects to modify
2. Applies the requested changes safely
3. Maintains design integrity
4. Updates the document properly

Only output the Python code:
"""

    def _get_analysis_prompt(self) -> str:
        return """
You are analyzing a FreeCAD design state to make intelligent decisions.

USER REQUEST: {user_input}

CURRENT STATE CONTEXT:
{state_context}

Provide a comprehensive analysis and generate appropriate action commands.
Focus on understanding the current state and suggesting the best next steps.

Output only the Python code for analysis:
"""

    def _get_next_step_prompt(self) -> str:
        return """
Based on the current design state, suggest the next logical step in the design process.

CURRENT STATE: {state_context}
USER CONTEXT: {user_input}

Generate a command that moves the design forward logically:
"""

    def _get_component_completion_prompt(self) -> str:
        return """
You are working on completing a design component. Analyze the current state and generate
commands to complete the component effectively.

CURRENT STATE: {state_context}
USER GOAL: {user_input}

Generate commands to complete the component:
"""

import re
import json
from typing import Dict, Any, Optional

class CommandExecutor:
    def __init__(self, api_client=None, state_manager=None):
        self.api_client = api_client
        self.state_manager = state_manager
        self.command_history = []

    def execute(self, command):
        """Execute a FreeCAD command"""
        if not self.api_client:
            raise ValueError("API client not initialized")
            
        if self.validate_command(command):
            # Add to history
            self.command_history.append(command)
            
            # Execute the command
            response = self.api_client.execute_command(command)
            
            # Update state if state manager is available
            if self.state_manager and response.get("status") == "success":
                try:
                    current_state = self.api_client.get_document_state()
                    self.state_manager.update_state(current_state)
                except Exception as e:
                    print(f"Warning: Failed to update state: {e}")
            
            return response
        else:
            raise ValueError("Invalid command")

    def execute_natural_language(self, nl_command: str) -> Dict[str, Any]:
        """Convert natural language to FreeCAD command and execute"""
        freecad_command = self.parse_natural_language(nl_command)
        if freecad_command:
            return self.execute(freecad_command)
        else:
            return {"status": "error", "message": "Could not parse natural language command"}

    def parse_natural_language(self, nl_command: str) -> Optional[str]:
        """Basic natural language parsing (can be enhanced with LLM later)"""
        nl_command = nl_command.lower().strip()
        
        # Box creation patterns
        if "create" in nl_command and "box" in nl_command:
            # Extract dimensions if provided
            dimensions = self._extract_dimensions(nl_command)
            return self._generate_box_command(**dimensions)
        
        # Cylinder creation patterns
        elif "create" in nl_command and "cylinder" in nl_command:
            dimensions = self._extract_cylinder_dimensions(nl_command)
            return self._generate_cylinder_command(**dimensions)
        
        # Sphere creation patterns
        elif "create" in nl_command and "sphere" in nl_command:
            radius = self._extract_sphere_radius(nl_command)
            return self._generate_sphere_command(radius)
        
        # Save document
        elif "save" in nl_command and "document" in nl_command:
            filename = self._extract_filename(nl_command, "fcstd")
            return f'doc.saveAs("{filename}")'
        
        # Export STL
        elif "export" in nl_command and "stl" in nl_command:
            filename = self._extract_filename(nl_command, "stl")
            return f'''
objects = [obj for obj in doc.Objects]
if objects:
    import Mesh
    Mesh.export(objects, "{filename}")
    print("STL exported successfully")
'''
        
        return None

    def _extract_dimensions(self, text: str) -> Dict[str, float]:
        """Extract box dimensions from text"""
        dimensions = {"length": 10, "width": 10, "height": 10, "name": "Box"}
        
        # Look for patterns like "10x10x10", "length 15", etc.
        dimension_pattern = r'(\d+(?:\.\d+)?)\s*(?:x|\*|by)\s*(\d+(?:\.\d+)?)\s*(?:x|\*|by)\s*(\d+(?:\.\d+)?)'
        match = re.search(dimension_pattern, text)
        if match:
            dimensions["length"] = float(match.group(1))
            dimensions["width"] = float(match.group(2))
            dimensions["height"] = float(match.group(3))
        
        return dimensions

    def _extract_cylinder_dimensions(self, text: str) -> Dict[str, float]:
        """Extract cylinder dimensions from text"""
        dimensions = {"radius": 5, "height": 10, "name": "Cylinder"}
        
        # Look for radius and height
        radius_match = re.search(r'radius\s*(\d+(?:\.\d+)?)', text)
        height_match = re.search(r'height\s*(\d+(?:\.\d+)?)', text)
        
        if radius_match:
            dimensions["radius"] = float(radius_match.group(1))
        if height_match:
            dimensions["height"] = float(height_match.group(1))
        
        return dimensions

    def _extract_sphere_radius(self, text: str) -> float:
        """Extract sphere radius from text"""
        radius_match = re.search(r'radius\s*(\d+(?:\.\d+)?)', text)
        return float(radius_match.group(1)) if radius_match else 5.0

    def _extract_filename(self, text: str, extension: str) -> str:
        """Extract filename from text"""
        # Look for filename patterns
        filename_match = re.search(r'(?:as|to|file)\s+([^\s]+)', text)
        if filename_match:
            filename = filename_match.group(1)
            if not filename.endswith(f'.{extension}'):
                filename += f'.{extension}'
            return filename
        return f"output.{extension}"

    def _generate_box_command(self, length=10, width=10, height=10, name="Box"):
        """Generate FreeCAD command to create a box"""
        return f'''
box = doc.addObject("Part::Box", "{name}")
box.Length = {length}
box.Width = {width}
box.Height = {height}
doc.recompute()
print("Box created: {name}")
'''

    def _generate_cylinder_command(self, radius=5, height=10, name="Cylinder"):
        """Generate FreeCAD command to create a cylinder"""
        return f'''
cylinder = doc.addObject("Part::Cylinder", "{name}")
cylinder.Radius = {radius}
cylinder.Height = {height}
doc.recompute()
print("Cylinder created: {name}")
'''

    def _generate_sphere_command(self, radius=5, name="Sphere"):
        """Generate FreeCAD command to create a sphere"""
        return f'''
sphere = doc.addObject("Part::Sphere", "{name}")
sphere.Radius = {radius}
doc.recompute()
print("Sphere created: {name}")
'''

    def validate_command(self, command):
        """Validate if the command is safe to execute"""
        dangerous_keywords = [
            'import os', 'import subprocess', 'exec(', 'eval(', '__import__',
            'open(', 'file(', 'input(', 'raw_input(', 'execfile(',
            'reload(', 'compile(', 'globals()', 'locals()'
        ]
        
        command_lower = command.lower()
        for keyword in dangerous_keywords:
            if keyword in command_lower:
                return False
        
        return True

    def get_state(self):
        """Get current FreeCAD state"""
        if self.api_client:
            return self.api_client.get_document_state()
        return {}

    def get_command_history(self):
        """Get command execution history"""
        return self.command_history.copy()

    # Enhanced predefined commands
    def create_box(self, length=10, width=10, height=10, name="Box"):
        """Create a box in FreeCAD"""
        command = self._generate_box_command(length, width, height, name)
        return self.execute(command)

    def create_cylinder(self, radius=5, height=10, name="Cylinder"):
        """Create a cylinder in FreeCAD"""
        command = self._generate_cylinder_command(radius, height, name)
        return self.execute(command)

    def create_sphere(self, radius=5, name="Sphere"):
        """Create a sphere in FreeCAD"""
        command = self._generate_sphere_command(radius, name)
        return self.execute(command)
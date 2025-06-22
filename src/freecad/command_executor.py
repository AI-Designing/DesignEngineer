class CommandExecutor:
    def __init__(self, api_client=None, state_manager=None):
        self.api_client = api_client
        self.state_manager = state_manager

    def execute(self, command):
        """Execute a FreeCAD command"""
        if not self.api_client:
            raise ValueError("API client not initialized")
            
        if self.validate_command(command):
            response = self.api_client.execute_command(command)
            
            # Update state if state manager is available
            if self.state_manager and response.get("status") == "success":
                current_state = self.api_client.get_document_state()
                self.state_manager.update_state(current_state)
            
            return response
        else:
            raise ValueError("Invalid command")

    def validate_command(self, command):
        """Validate if the command is safe to execute"""
        # Basic validation - extend this as needed
        dangerous_keywords = ['import os', 'import subprocess', 'exec(', 'eval(', '__import__']
        
        for keyword in dangerous_keywords:
            if keyword in command.lower():
                return False
        
        return True

    def get_state(self):
        """Get current FreeCAD state"""
        if self.api_client:
            return self.api_client.get_document_state()
        return {}

    # Predefined common FreeCAD commands
    def create_box(self, length=10, width=10, height=10, name="Box"):
        """Create a box in FreeCAD"""
        command = f"""
import Part
box = FreeCAD.ActiveDocument.addObject("Part::Box", "{name}")
box.Length = {length}
box.Width = {width}
box.Height = {height}
"""
        return self.execute(command)

    def create_cylinder(self, radius=5, height=10, name="Cylinder"):
        """Create a cylinder in FreeCAD"""
        command = f"""
import Part
cylinder = FreeCAD.ActiveDocument.addObject("Part::Cylinder", "{name}")
cylinder.Radius = {radius}
cylinder.Height = {height}
"""
        return self.execute(command)

    def create_sphere(self, radius=5, name="Sphere"):
        """Create a sphere in FreeCAD"""
        command = f"""
import Part
sphere = FreeCAD.ActiveDocument.addObject("Part::Sphere", "{name}")
sphere.Radius = {radius}
"""
        return self.execute(command)
import re
import json
import os
from typing import Dict, Any, Optional
from .state_manager import FreeCADStateAnalyzer
from llm.client import LLMClient

class CommandExecutor:
    def __init__(self, api_client=None, state_manager=None, auto_save=True, llm_provider="openai", llm_api_key=None, auto_open_gui=True):
        self.api_client = api_client
        self.state_manager = state_manager
        self.state_analyzer = FreeCADStateAnalyzer(api_client)
        self.command_history = []
        self.auto_save = auto_save
        self.auto_open_gui = auto_open_gui  # New option to control GUI opening
        self.save_counter = 0
        self.last_saved_path = None
        # llm_provider: 'openai' or 'google', llm_api_key: API key for the provider
        self.llm_client = LLMClient(api_key=llm_api_key, provider=llm_provider)

    def execute(self, command):
        """Execute a FreeCAD command"""
        if not self.api_client:
            raise ValueError("API client not initialized")
            
        if self.validate_command(command):
            # Add to history
            self.command_history.append(command)
            
            # Execute the command
            response = self.api_client.execute_command(command)
            
            # Auto-save if command was successful and auto-save is enabled
            if self.auto_save and response.get("status") == "success":
                save_result = self._auto_save_document()
                if save_result:
                    print(f"\n💾 Document auto-saved to: {save_result}")
                    self.last_saved_path = save_result
                    
                    # Auto-open in GUI if enabled
                    if self.auto_open_gui:
                        print("🖥️  Opening document in FreeCAD GUI...")
                        gui_result = self.api_client.open_in_freecad_gui(save_result)
                        if gui_result.get("status") == "success":
                            print("✅ Document opened in FreeCAD GUI with objects visible")
                        else:
                            print(f"⚠️  Could not open in GUI: {gui_result.get('message', 'Unknown error')}")
                            # Try manual GUI opening as fallback
                            gui_result = self.api_client.open_current_document_in_gui()
                            if gui_result.get("status") == "success":
                                print("✅ Document opened in FreeCAD GUI (fallback method)")
                            else:
                                print(f"❌ GUI opening failed: {gui_result.get('message', 'Unknown error')}")
            
            # Update state if state manager is available
            if self.state_manager and response.get("status") == "success":
                try:
                    current_state = self.api_client.get_document_state()
                    # Add file location to state
                    current_state["last_saved_path"] = self.last_saved_path
                    self.state_manager.update_state(current_state)
                except Exception as e:
                    print(f"Warning: Failed to update state: {e}")
            
            # Perform state analysis after successful command execution
            if response.get("status") == "success":
                try:
                    analysis = self.state_analyzer.analyze_document_state()
                    if "analysis" in analysis:
                        print("\n" + "="*50)
                        print("📊 Post-Command State Analysis")
                        print("="*50)
                        self.state_analyzer.print_analysis_results(analysis)
                except Exception as e:
                    print(f"Warning: State analysis failed: {e}")
            
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
        """Enhanced: Use rules, then LLM if rules fail"""
        nl_command = nl_command.lower().strip()
        # Rule-based parsing
        if "create" in nl_command and "box" in nl_command:
            dimensions = self._extract_dimensions(nl_command)
            # Create a new dict with correct types
            box_args = {
                "length": int(dimensions["length"]),
                "width": int(dimensions["width"]),
                "height": int(dimensions["height"]),
                "name": str(dimensions["name"])
            }
            return self._generate_box_command(**box_args)
        elif "create" in nl_command and "cylinder" in nl_command:
            dimensions = self._extract_cylinder_dimensions(nl_command)
            cyl_args = {
                "radius": int(dimensions["radius"]),
                "height": int(dimensions["height"]),
                "name": str(dimensions["name"])
            }
            return self._generate_cylinder_command(**cyl_args)
        elif "create" in nl_command and "sphere" in nl_command:
            radius = int(self._extract_sphere_radius(nl_command))
            return self._generate_sphere_command(radius)
        elif "save" in nl_command and "document" in nl_command:
            filename = self._extract_filename(nl_command, "fcstd")
            return f'doc.saveAs("{filename}")'
        elif "export" in nl_command and "stl" in nl_command:
            filename = self._extract_filename(nl_command, "stl")
            return f'''
objects = [obj for obj in doc.Objects]
if objects:
    import Mesh
    Mesh.export(objects, "{filename}")
    print("STL exported successfully")
'''
        # If no rule matched, use LLM
        if self.llm_client:
            # Optionally, pass current state for context
            try:
                state = self.api_client.get_document_state() if self.api_client else None
                return self.llm_client.generate_command(nl_command, state)
            except Exception as e:
                print(f"[CommandExecutor] Error getting state or generating command: {e}")
                # Fall back to generating without state
                try:
                    return self.llm_client.generate_command(nl_command, None)
                except Exception as fallback_error:
                    print(f"[CommandExecutor] Fallback also failed: {fallback_error}")
                    return None
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

    def _auto_save_document(self):
        """Auto-save the document with incremental naming"""
        try:
            # Generate auto-save filename
            self.save_counter += 1
            timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"freecad_auto_save_{timestamp}_{self.save_counter:03d}.FCStd"
            
            # Save in outputs directory
            outputs_dir = os.path.join(os.getcwd(), "outputs")
            if not os.path.exists(outputs_dir):
                os.makedirs(outputs_dir)
            save_path = os.path.join(outputs_dir, filename)
            
            # Save the document
            if self.api_client:
                result = self.api_client.save_document(save_path)
            else:
                print("Warning: api_client is not initialized.")
                return None
            if result.get("status") == "success":
                # Return the actual saved path from the API response
                return result.get("saved_path", save_path)
            else:
                print(f"Warning: Auto-save failed: {result.get('message', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"Warning: Auto-save failed: {e}")
            return None

    def manual_save(self, filename=None):
        """Manually save the document with optional custom filename"""
        try:
            outputs_dir = os.path.join(os.getcwd(), "outputs")
            if not os.path.exists(outputs_dir):
                os.makedirs(outputs_dir)
            if filename:
                # Use provided filename
                if not filename.endswith('.FCStd'):
                    filename += '.FCStd'
                save_path = os.path.join(outputs_dir, os.path.basename(filename))
            else:
                # Generate default filename
                timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"freecad_manual_save_{timestamp}.FCStd"
                save_path = os.path.join(outputs_dir, filename)
            
            if self.api_client:
                result = self.api_client.save_document(save_path)
            else:
                print("Warning: api_client is not initialized.")
                return None
            if result.get("status") == "success":
                actual_path = result.get("saved_path", save_path)
                self.last_saved_path = actual_path
                print(f"✅ Document saved to: {actual_path}")
                return actual_path
            else:
                print(f"❌ Save failed: {result.get('message', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"❌ Save failed: {e}")
            return None

    def get_save_info(self):
        """Get information about saved files"""
        info = {
            "last_saved_path": self.last_saved_path,
            "save_counter": self.save_counter,
            "auto_save_enabled": self.auto_save
        }
        return info

    # Enhanced predefined commands
    def create_box(self, length=10, width=10, height=10, name="Box"):
        """Create a box in FreeCAD"""
        # Ensure types are correct
        length = int(float(length))
        width = int(float(width))
        height = int(float(height))
        name = str(name)
        command = self._generate_box_command(length, width, height, name)
        return self.execute(command)

    def create_cylinder(self, radius=5, height=10, name="Cylinder"):
        """Create a cylinder in FreeCAD"""
        radius = int(float(radius))
        height = int(float(height))
        name = str(name)
        command = self._generate_cylinder_command(radius, height, name)
        return self.execute(command)

    def create_sphere(self, radius=5, name="Sphere"):
        """Create a sphere in FreeCAD"""
        radius = int(float(radius))
        name = str(name)
        command = self._generate_sphere_command(radius, name)
        return self.execute(command)

    def set_auto_open_gui(self, enabled: bool):
        """Enable or disable automatic GUI opening after command execution"""
        self.auto_open_gui = enabled
        status = "enabled" if enabled else "disabled"
        print(f"🖥️  Auto-open GUI {status}")
    
    def open_current_in_gui(self):
        """Manually open the current document in FreeCAD GUI"""
        if self.api_client:
            return self.api_client.open_current_document_in_gui()
        else:
            return {"status": "error", "message": "No API client available"}
import sys
import os
import subprocess
import tempfile
import json

# Add FreeCAD paths
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/lib/")
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/Mod")

try:
    import FreeCAD
    import FreeCADGui
    import Part
    import Mesh
except ImportError as e:
    print(f"Warning: FreeCAD modules not available: {e}")
    FreeCAD = None

class FreeCADAPIClient:
    def __init__(self, use_headless=True):
        self.connection = None
        self.document = None
        self.use_headless = use_headless
        self.freecad_executable = "freecadcmd" if use_headless else "freecad"

    def connect(self):
        """Connect to FreeCAD and create/open a document"""
        try:
            if FreeCAD is None:
                # Use subprocess approach if FreeCAD not directly importable
                return self._connect_via_subprocess()
            
            # Direct import approach
            if not hasattr(FreeCAD, 'ActiveDocument') or FreeCAD.ActiveDocument is None:
                self.document = FreeCAD.newDocument("AutomationDoc")
                print("Connected to FreeCAD and created new document")
            else:
                self.document = FreeCAD.ActiveDocument
                print("Connected to existing FreeCAD document")
            
            self.connection = True
            return True
        except Exception as e:
            print(f"Failed to connect to FreeCAD: {e}")
            return False

    def _connect_via_subprocess(self):
        """Test connection via subprocess"""
        test_script = """
import FreeCAD
doc = FreeCAD.newDocument("TestDoc")
print("SUCCESS: FreeCAD connection established")
"""
        return self._execute_via_subprocess(test_script)

    def execute_command(self, command):
        """Execute a FreeCAD command/script"""
        if FreeCAD and self.connection:
            return self._execute_direct(command)
        else:
            return self._execute_via_subprocess(command)

    def _execute_direct(self, command):
        """Execute command directly using imported FreeCAD"""
        if not self.connection:
            raise ConnectionError("Not connected to FreeCAD")
        
        try:
            # Create a local environment for command execution
            local_env = {
                'FreeCAD': FreeCAD,
                'Part': Part,
                'Mesh': Mesh,
                'doc': self.document,
                'App': FreeCAD,
            }
            
            # Execute the command
            exec(command, local_env)
            
            # Recompute the document
            if self.document:
                self.document.recompute()
            
            return {"status": "success", "message": f"Command executed: {command}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to execute command: {e}"}

    def _execute_via_subprocess(self, command):
        """Execute command via freecadcmd subprocess"""
        try:
            # Create a temporary Python script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(f"""
import sys
import os
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/lib/")
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/Mod")

try:
    import FreeCAD
    import Part
    import Mesh
    
    # Create or get document
    if not hasattr(FreeCAD, 'ActiveDocument') or FreeCAD.ActiveDocument is None:
        doc = FreeCAD.newDocument("AutomationDoc")
    else:
        doc = FreeCAD.ActiveDocument
    
    # Execute user command
{command}
    
    # Recompute
    doc.recompute()
    
    print("SUCCESS: Command executed successfully")
    
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
""")
                temp_file_path = temp_file.name

            # Execute with freecadcmd
            result = subprocess.run(
                [self.freecad_executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up
            os.unlink(temp_file_path)
            
            if result.returncode == 0:
                return {"status": "success", "message": result.stdout, "command": command}
            else:
                return {"status": "error", "message": result.stderr, "command": command}
                
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command execution timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Subprocess execution failed: {e}"}

    def execute_script_file(self, script_path):
        """Execute a FreeCAD script file"""
        try:
            result = subprocess.run(
                [self.freecad_executable, script_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"status": "success", "message": result.stdout}
            else:
                return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": f"Script execution failed: {e}"}

    def get_document_objects(self):
        """Get all objects in the current document"""
        if FreeCAD and self.document:
            return [obj.Name for obj in self.document.Objects]
        
        # Use subprocess to get objects
        command = """
for obj in doc.Objects:
    print(f"OBJECT: {obj.Name}")
"""
        result = self._execute_via_subprocess(command)
        if result["status"] == "success":
            objects = []
            for line in result["message"].split('\n'):
                if line.startswith("OBJECT: "):
                    objects.append(line.replace("OBJECT: ", "").strip())
            return objects
        return []

    def get_document_state(self):
        """Get current state of the FreeCAD document"""
        if FreeCAD and self.document:
            objects_info = []
            for obj in self.document.Objects:
                obj_info = {
                    "name": obj.Name,
                    "type": obj.TypeId,
                    "label": obj.Label
                }
                objects_info.append(obj_info)
            
            return {
                "active_document": self.document.Name,
                "objects": objects_info,
                "object_count": len(self.document.Objects)
            }
        
        # Use subprocess to get state
        command = """
import json
state = {
    "active_document": doc.Name,
    "objects": [{"name": obj.Name, "type": obj.TypeId, "label": obj.Label} for obj in doc.Objects],
    "object_count": len(doc.Objects)
}
print(f"STATE: {json.dumps(state)}")
"""
        result = self._execute_via_subprocess(command)
        if result["status"] == "success":
            for line in result["message"].split('\n'):
                if line.startswith("STATE: "):
                    try:
                        return json.loads(line.replace("STATE: ", ""))
                    except json.JSONDecodeError:
                        pass
        
        return {"objects": [], "active_document": None}

    def save_document(self, file_path):
        """Save the current document"""
        command = f"""
import os
save_path = os.path.expanduser("{file_path}")
doc.saveAs(save_path)
print(f"Document saved to: {{save_path}}")
"""
        return self._execute_via_subprocess(command)

    def export_stl(self, objects, file_path):
        """Export objects to STL format"""
        command = f"""
import os
export_path = os.path.expanduser("{file_path}")
objects_to_export = [doc.getObject(name) for name in {objects} if doc.getObject(name)]
if objects_to_export:
    import Mesh
    Mesh.export(objects_to_export, export_path)
    print(f"STL exported to: {{export_path}}")
else:
    print("No valid objects found for export")
"""
        return self._execute_via_subprocess(command)
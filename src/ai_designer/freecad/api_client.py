import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..core.sandbox import (
    SafeScriptExecutor,
    ScriptExecutionError,
    ScriptValidationError,
)

# Add FreeCAD paths
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/lib/")
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/Mod")

try:
    import FreeCAD
    import FreeCADGui
    import Mesh
    import Part
except ImportError as e:
    print(f"Warning: FreeCAD modules not available: {e}")
    FreeCAD = None


class FreeCADAPIClient:
    def __init__(self, use_headless=True):
        self.connection = None
        self.document = None
        self.use_headless = use_headless
        self.freecad_executable = "freecadcmd" if use_headless else "freecad"
        self.freecad_gui_executable = "freecad"  # GUI executable
        self.last_saved_document = None

    def connect(self):
        """Connect to FreeCAD and create/open a document"""
        try:
            if FreeCAD is None:
                # Use subprocess approach if FreeCAD not directly importable
                return self._connect_via_subprocess()

            # Direct import approach
            if not hasattr(FreeCAD, "ActiveDocument") or FreeCAD.ActiveDocument is None:
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
        """Execute command using safe sandbox (no direct exec())"""
        from ..sandbox import ScriptSandbox

        if not self.connection:
            raise ConnectionError("Not connected to FreeCAD")

        try:
            # Create sandbox with FreeCAD environment
            sandbox = ScriptSandbox(
                timeout=60,
                strict_validation=True,
                use_subprocess=False,  # FreeCAD needs inline execution
            )

            # Prepare FreeCAD environment
            freecad_env = {
                "FreeCAD": FreeCAD,
                "Part": Part,
                "doc": self.document,
                "App": FreeCAD,
            }

            # Execute script safely with validation
            result = sandbox.execute_freecad_script(
                script=command, freecad_env=freecad_env
            )

            if result.success:
                return {
                    "status": "success",
                    "message": "Command executed successfully",
                    "output": result.output,
                    "execution_time": result.execution_time,
                }
            else:
                return {
                    "status": "error",
                    "message": result.error_message or "Execution failed",
                    "stderr": result.stderr,
                }

        except ScriptValidationError as e:
            return {"status": "error", "message": f"Script validation failed: {e}"}
        except ScriptExecutionError as e:
            return {"status": "error", "message": f"Script execution failed: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to execute command: {e}"}

    def _execute_via_subprocess(self, command):
        """Execute command via freecadcmd subprocess"""
        try:
            # Create a temporary Python script
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(
                    f"""
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
"""
                )
                temp_file_path = temp_file.name

            # Execute with freecadcmd
            result = subprocess.run(
                [self.freecad_executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Clean up
            os.unlink(temp_file_path)

            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": result.stdout,
                    "command": command,
                }
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
                timeout=60,
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
            for line in result["message"].split("\n"):
                if line.startswith("OBJECT: "):
                    objects.append(line.replace("OBJECT: ", "").strip())
            return objects
        return []

    def get_document_state(self):
        """Get current state of the FreeCAD document"""
        if FreeCAD and self.document:
            objects_info = []
            for obj in self.document.Objects:
                obj_info = {"name": obj.Name, "type": obj.TypeId, "label": obj.Label}
                objects_info.append(obj_info)

            return {
                "active_document": self.document.Name,
                "objects": objects_info,
                "object_count": len(self.document.Objects),
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
            for line in result["message"].split("\n"):
                if line.startswith("STATE: "):
                    try:
                        return json.loads(line.replace("STATE: ", ""))
                    except json.JSONDecodeError:
                        pass

        return {"objects": [], "active_document": None}

    def save_document(self, file_path):
        """Save the current document"""
        # If FreeCAD and self.document are available, save directly
        if FreeCAD and self.document:
            try:
                save_path = os.path.expanduser(file_path)
                save_path = os.path.abspath(save_path)
                self.document.saveAs(save_path)
                print(f"SAVED_TO: {save_path}")
                print(f"Document saved to: {save_path}")
                self.last_saved_document = save_path
                return {
                    "status": "success",
                    "saved_path": save_path,
                    "message": f"Document saved to: {save_path}",
                }
            except Exception as e:
                print(f"Error saving document: {e}")
                return {"status": "error", "message": f"Failed to save document: {e}"}
        # Otherwise, use subprocess fallback
        command = f"""
import os
save_path = os.path.expanduser(\"{file_path}\")
save_path = os.path.abspath(save_path)
doc.saveAs(save_path)
print(f\"SAVED_TO: {{save_path}}\")
print(f\"Document saved to: {{save_path}}\")
"""
        result = self._execute_via_subprocess(command)
        # Extract the saved path from the output
        if result.get("status") == "success":
            for line in result["message"].split("\n"):
                if line.startswith("SAVED_TO: "):
                    saved_path = line.replace("SAVED_TO: ", "").strip()
                    result["saved_path"] = saved_path
                    self.last_saved_document = (
                        saved_path  # Store the saved document path
                    )
                    break
        return result

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

    def get_file_info(self):
        """Get information about file paths and current working directory"""
        command = """
import os
cwd = os.getcwd()
home = os.path.expanduser("~")
print(f"CURRENT_DIR: {cwd}")
print(f"HOME_DIR: {home}")
print(f"DOCUMENT_NAME: {doc.Name}")
if hasattr(doc, 'FileName') and doc.FileName:
    print(f"DOCUMENT_PATH: {doc.FileName}")
else:
    print("DOCUMENT_PATH: Not saved yet")
"""
        return self._execute_via_subprocess(command)

    def open_in_freecad_gui(self, file_path=None):
        """Open the document in FreeCAD GUI with objects visible"""
        if not file_path:
            file_path = self.last_saved_document

        print(f"[DEBUG] Attempting to open in GUI:")
        print(f"[DEBUG] - file_path parameter: {file_path}")
        print(f"[DEBUG] - last_saved_document: {self.last_saved_document}")

        if not file_path:
            print("❌ No file path provided and no last saved document")
            return {"status": "error", "message": "No valid document path"}

        if not os.path.exists(file_path):
            print(f"❌ File does not exist: {file_path}")
            return {"status": "error", "message": f"File does not exist: {file_path}"}

        try:
            print(f"🖥️  Opening document in FreeCAD GUI: {file_path}")

            # Create a script to open the document and fit all objects in view
            script_content = f"""
import FreeCAD
import FreeCADGui
import time

# Open the document
doc = FreeCAD.openDocument(r"{file_path}")
FreeCAD.setActiveDocument(doc.Name)

# Give some time for the document to load
time.sleep(1)

# Show all objects and fit them in view
if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
    # Make sure all objects are visible
    for obj in doc.Objects:
        if hasattr(obj, 'ViewObject') and obj.ViewObject:
            obj.ViewObject.Visibility = True

    # Fit all objects in view
    FreeCADGui.SendMsgToActiveView("ViewFit")

    # Switch to a good default view (isometric)
    FreeCADGui.ActiveDocument.activeView().viewIsometric()

    print("SUCCESS: Document opened in FreeCAD GUI with objects visible")
else:
    print("WARNING: GUI not available")
"""

            # Write the script to a temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(script_content)
                temp_script_path = temp_file.name

            # Launch FreeCAD GUI with the script
            result = subprocess.Popen(
                [self.freecad_gui_executable, temp_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Give FreeCAD time to start
            time.sleep(2)

            # Clean up the temporary script
            try:
                os.unlink(temp_script_path)
            except:
                pass

            print("✅ FreeCAD GUI launched successfully")
            return {
                "status": "success",
                "message": f"Document opened in FreeCAD GUI: {file_path}",
                "process_id": result.pid,
            }

        except Exception as e:
            print(f"❌ Failed to open document in FreeCAD GUI: {e}")
            return {"status": "error", "message": f"Failed to open in GUI: {e}"}

    def open_current_document_in_gui(self):
        """Open the current document in FreeCAD GUI"""
        if not self.last_saved_document:
            print("⚠️  No saved document to open. Creating temporary save...")

            # Create a temporary save
            import time

            temp_filename = f"temp_freecad_view_{int(time.time())}.FCStd"
            temp_path = os.path.join(os.getcwd(), temp_filename)

            save_result = self.save_document(temp_path)
            if save_result.get("status") == "success":
                return self.open_in_freecad_gui(temp_path)
            else:
                return {
                    "status": "error",
                    "message": "Failed to save document for GUI viewing",
                }

        return self.open_in_freecad_gui(self.last_saved_document)

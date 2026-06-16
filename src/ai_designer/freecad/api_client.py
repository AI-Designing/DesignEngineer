import atexit
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from ..sandbox import SafeScriptExecutor, ScriptExecutionError, ScriptValidationError
from .path_resolver import get_freecad_executable, setup_freecad_paths

# Setup FreeCAD paths from environment/config
try:
    setup_freecad_paths()
except Exception as e:
    print(f"Warning: Could not setup FreeCAD paths: {e}")

try:
    import FreeCAD
    import FreeCADGui
    import Mesh
    import Part
except ImportError as e:
    print(f"Warning: FreeCAD modules not available: {e}")
    FreeCAD = None


# ---------------------------------------------------------------------------
# Xvfb virtual display — shared across all FreeCADAPIClient instances so we
# only start one server per process.
# ---------------------------------------------------------------------------
_xvfb_process: subprocess.Popen = None
_xvfb_display: str = ":99"


def _ensure_xvfb() -> str:
    """Start Xvfb :99 if not already running.  Returns the DISPLAY string."""
    global _xvfb_process, _xvfb_display
    if _xvfb_process and _xvfb_process.poll() is None:
        return _xvfb_display  # already running

    # Find an available display number
    for n in range(99, 110):
        display = f":{n}"
        lock = f"/tmp/.X{n}-lock"
        if not os.path.exists(lock):
            _xvfb_display = display
            break

    try:
        _xvfb_process = subprocess.Popen(
            ["Xvfb", _xvfb_display, "-screen", "0", "1024x768x24"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)  # give Xvfb time to bind to the socket
        atexit.register(_stop_xvfb)
    except FileNotFoundError:
        print("Warning: Xvfb not found — FreeCAD subprocess may hang without a display")
    return _xvfb_display


def _stop_xvfb():
    if _xvfb_process and _xvfb_process.poll() is None:
        _xvfb_process.terminate()


class FreeCADAPIClient:
    def __init__(self, use_headless=True):
        self.connection = None
        self.document = None
        self.use_headless = use_headless
        # Prefer FREECAD_PATH env var (set in Docker), then auto-detect via path_resolver
        _env_path = os.getenv("FREECAD_PATH") or os.getenv("FREECADCMD_PATH")
        if _env_path and os.path.exists(_env_path):
            self.freecad_executable = _env_path
        else:
            if _env_path:
                print(
                    f"Warning: FREECAD_PATH={_env_path!r} does not exist, falling back to auto-detect"
                )
            try:
                self.freecad_executable = get_freecad_executable()
            except Exception:
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

    def execute_command(self, command, save_path=None, document_path=None):
        """Execute a FreeCAD command/script, optionally saving the document
        in the same subprocess so state is preserved.

        Args:
            command: FreeCAD Python body (indented by the subprocess wrapper).
            save_path: If set, document is saved inside the same subprocess run.
            document_path: If set, load this ``.FCStd`` checkpoint before running
                ``command`` (subprocess or in-process). Required for multi-step
                subprocess workflows where each step is a separate process.
        """
        if FreeCAD and self.connection:
            if document_path:
                abs_p = os.path.abspath(os.path.expanduser(document_path))
                if not os.path.isfile(abs_p):
                    return {
                        "status": "error",
                        "message": f"Checkpoint document not found: {abs_p}",
                    }
                try:
                    doc = FreeCAD.openDocument(abs_p)
                    if doc is None:
                        return {
                            "status": "error",
                            "message": f"FreeCAD failed to open document: {abs_p}",
                        }
                    self.document = doc
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to open checkpoint document: {e}",
                    }
            result = self._execute_direct(command)
            # Save directly when FreeCAD is in-process
            if save_path and result.get("status") == "success":
                save_result = self.save_document(save_path)
                if save_result.get("status") == "success":
                    result["saved_path"] = save_result.get("saved_path", save_path)
            return result
        else:
            return self._execute_via_subprocess(
                command, save_path=save_path, document_path=document_path
            )

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

    def _execute_via_subprocess(self, command, save_path=None, document_path=None):
        """Execute command via FreeCAD AppImage in console mode (-c).

        Uses -c (console/headless) mode so FreeCAD never opens a GUI window,
        meaning no Xvfb virtual display is required and stdout works normally.
        A sentinel file is still used for success detection because os._exit(0)
        does not flush stdout buffers.

        When save_path is provided the document is saved inside the same
        subprocess so no state is lost between calls.

        When document_path is provided, that ``.FCStd`` is opened before user
        code runs so multi-step workflows can chain across subprocess boundaries.
        """
        save_path_abs = (
            os.path.abspath(os.path.expanduser(save_path)) if save_path else None
        )
        doc_path_abs = (
            os.path.abspath(os.path.expanduser(document_path))
            if document_path
            else None
        )

        # Console mode doesn't need a display, but we set DISPLAY as a fallback
        # in case any FreeCAD module tries to probe it during import.
        display = _ensure_xvfb()
        # Build optional save block (4-space indented to match the try block)
        if save_path_abs:
            _save_block = f"""
    # Auto-save within the same subprocess so state is preserved
    import os as _os
    _save_dir = _os.path.dirname({repr(save_path_abs)})
    if _save_dir:
        _os.makedirs(_save_dir, exist_ok=True)
    doc.saveAs({repr(save_path_abs)})
    print("SAVED_TO: " + {repr(save_path_abs)})
"""
        else:
            _save_block = ""

        if doc_path_abs:
            _doc_init = f"""
    import os as _os
    _checkpoint = {repr(doc_path_abs)}
    if not _os.path.isfile(_checkpoint):
        raise FileNotFoundError("Checkpoint document not found: " + _checkpoint)
    doc = FreeCAD.openDocument(_checkpoint)
    if doc is None:
        raise RuntimeError("FreeCAD.openDocument returned None for: " + _checkpoint)
    FreeCAD.setActiveDocument(doc.Name)
"""
        else:
            _doc_init = """
    # Create or get document (fresh process → usually new document)
    if not hasattr(FreeCAD, 'ActiveDocument') or FreeCAD.ActiveDocument is None:
        doc = FreeCAD.newDocument("AutomationDoc")
    else:
        doc = FreeCAD.ActiveDocument
"""

        # Indent every non-empty line of the command to 4 spaces so it sits
        # correctly inside the try block in the generated script.
        indented_command = "\n".join(
            ("    " + line) if line.strip() else "" for line in command.split("\n")
        )

        sentinel_path = f"/tmp/freecad_ok_{uuid.uuid4().hex}"

        try:
            # Create a temporary Python script
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(
                    f"""import os
import sys

try:
    import FreeCAD
    import FreeCAD as App
    import Part
    import Mesh
{_doc_init}
    # Execute user command
{indented_command}

    # Recompute
    doc.recompute()
{_save_block}
    # Write sentinel so the caller can detect success (stdout is swallowed in GUI mode)
    open("{sentinel_path}", "w").write("ok")

except Exception as e:
    import traceback
    traceback.print_exc()
    # os._exit bypasses sys.exit interception so FreeCAD won't log a spurious
    # 'Exception while processing file' error
    os._exit(1)

# os._exit(0) avoids FreeCAD catching SystemExit and reporting a false error
os._exit(0)
"""
                )
                temp_file_path = temp_file.name

            # -c / --console = headless console mode: no GUI window, stdout works,
            # and FreeCAD won't misinterpret the .py file as a model to "open".
            # The script is passed as a positional argument after the flag.
            env = {**os.environ, "DISPLAY": display}
            result = subprocess.run(
                [self.freecad_executable, "-c", temp_file_path],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )

            # Clean up temp script AFTER subprocess finishes (blocking call above)
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

            # Success = sentinel file written by the script (stdout is empty in GUI mode)
            if os.path.exists(sentinel_path):
                os.unlink(sentinel_path)
                out = {
                    "status": "success",
                    "message": (result.stdout or "").strip()
                    or "Command executed successfully",
                    "command": command,
                    "stdout": result.stdout or "",
                    "stderr": result.stderr or "",
                }
                if save_path_abs:
                    out["saved_path"] = save_path_abs
                    self.last_saved_document = save_path_abs
                return out
            else:
                # Collect any error output for diagnostics
                err_msg = (
                    result.stderr
                    or result.stdout
                    or "Script failed — no output captured"
                ).strip()
                return {"status": "error", "message": err_msg, "command": command}

        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command execution timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Subprocess execution failed: {e}"}

    def execute_script_file(self, script_path):
        """Execute a FreeCAD script file"""
        try:
            display = _ensure_xvfb()
            env = {**os.environ, "DISPLAY": display}
            # Console mode: -c runs the script headlessly without opening a GUI window
            result = subprocess.run(
                [self.freecad_executable, "-c", script_path],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )

            if result.returncode == 0:
                return {"status": "success", "message": result.stdout}
            else:
                return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": f"Script execution failed: {e}"}

    def get_document_objects(self, document_path=None):
        """Get all objects in the current document.

        In subprocess mode, ``document_path`` may point to a saved ``.FCStd``
        so state reflects that file instead of an empty new document.
        """
        if FreeCAD and self.document:
            return [obj.Name for obj in self.document.Objects]

        # Use subprocess to get objects
        command = """
for obj in doc.Objects:
    print(f"OBJECT: {obj.Name}")
"""
        result = self._execute_via_subprocess(command, document_path=document_path)
        if result["status"] == "success":
            objects = []
            blob = result.get("stdout") or result.get("message") or ""
            for line in blob.split("\n"):
                if line.startswith("OBJECT: "):
                    objects.append(line.replace("OBJECT: ", "").strip())
            return objects
        return []

    def get_document_state(self, document_path=None):
        """Get current state of the FreeCAD document.

        When running headless via subprocess, pass ``document_path`` to read
        state from a checkpoint ``.FCStd`` (multi-step workflows).
        """
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
        result = self._execute_via_subprocess(command, document_path=document_path)
        if result["status"] == "success":
            blob = result.get("stdout") or result.get("message") or ""
            for line in blob.split("\n"):
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

            # Launch FreeCAD GUI with the script as a positional arg.
            # GUI mode (no -c) so the window stays open for the user to inspect.
            # Xvfb is already running via _ensure_xvfb() called above.
            result = subprocess.Popen(
                [self.freecad_gui_executable, temp_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Give FreeCAD enough time to start and fully read+execute the script
            # before we remove the temp file (Popen is non-blocking, so we must wait)
            time.sleep(8)

            # Clean up the temporary script only after FreeCAD has had time to read it
            try:
                os.unlink(temp_script_path)
            except OSError:
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

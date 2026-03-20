"""
Persistent GUI Client for FreeCAD
Maintains a continuous connection to FreeCAD GUI with real-time updates
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, Optional


class PersistentFreeCADGUI:
    """
    Manages a persistent FreeCAD GUI connection that stays open
    and updates in real-time as commands are executed
    """

    def __init__(self, websocket_manager=None):
        self.freecad_gui_executable = os.getenv("FREECAD_PATH", "freecad")
        self._module_dir = None
        self.gui_process = None
        self.gui_script_path = None
        self.websocket_manager = websocket_manager
        self.session_id = f"freecad_gui_{int(time.time())}"
        self.is_running = False
        self.communication_port = self._find_free_port()
        self.socket_server = None
        self.socket_thread = None
        self.pid_file = "/tmp/freecad_persistent_gui.pid"

    def check_existing_gui(self) -> bool:
        """Check if there's already a persistent GUI running"""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r") as f:
                    data = json.load(f)
                    pid = data.get("pid")
                    port = data.get("port")

                if pid and self._is_process_running(pid):
                    # Try to connect to the existing GUI
                    if self._test_connection(port):
                        print(
                            f"🔗 Found existing persistent GUI (PID: {pid}, Port: {port})"
                        )

                        # Create a mock process object that returns None for poll()
                        class MockProcess:
                            def __init__(self, pid):
                                self.pid = pid

                            def poll(self):
                                return None  # Process is still running

                            def terminate(self):
                                pass

                            def kill(self):
                                pass

                            def wait(self, timeout=None):
                                pass

                        self.gui_process = MockProcess(pid)
                        self.communication_port = port
                        self.is_running = True
                        return True
                    else:
                        print(
                            f"⚠️  Existing GUI process found but not responding, will restart"
                        )
                        # Clean up stale PID file
                        os.remove(self.pid_file)
            except Exception as e:
                print(f"⚠️  Error checking existing GUI: {e}")
                # Clean up potentially corrupted PID file
                try:
                    os.remove(self.pid_file)
                except:
                    pass

        return False

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running"""
        try:
            # Check if process exists and is not a zombie
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _test_connection(self, port: int) -> bool:
        """Test if we can connect to the persistent GUI"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            return result == 0
        except:
            return False

    def _save_gui_info(self):
        """Save persistent GUI info to file"""
        try:
            info = {
                "pid": self.gui_process.pid,
                "port": self.communication_port,
                "session_id": self.session_id,
                "started_at": time.time(),
            }
            with open(self.pid_file, "w") as f:
                json.dump(info, f)
        except Exception as e:
            print(f"⚠️  Could not save GUI info: {e}")

    def _find_free_port(self) -> int:
        """Find a free port for communication"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def _get_freecad_user_dir(self) -> str:
        """Return the FreeCAD user config directory (where Mod/ lives)."""
        for candidate in [
            os.path.expanduser("~/.local/share/FreeCAD"),
            os.path.expanduser("~/.FreeCAD"),
        ]:
            if os.path.isdir(candidate):
                return candidate
        return os.path.expanduser("~/.local/share/FreeCAD")

    def _install_freecad_module(self) -> None:
        """Install the AIDesignerBridge InitGui.py into FreeCAD's Mod directory.

        FreeCAD automatically loads InitGui.py from every directory under
        <UserAppDataDir>/Mod/ when the GUI starts.  This avoids passing a .py
        file as a positional argument to the AppImage (which causes the
        "Unknown file" error).

        The bridge opens a TCP socket on self.communication_port and handles
        four command types: execute_script, update_view, open_document, refresh.
        It uses direct exec() — no external ai_designer imports needed.
        """
        user_dir = self._get_freecad_user_dir()
        mod_dir = os.path.join(user_dir, "Mod", "AIDesignerBridge")
        os.makedirs(mod_dir, exist_ok=True)
        init_path = os.path.join(mod_dir, "InitGui.py")
        port = self.communication_port

        # Use __PORT__ as a safe placeholder so we never fight with .format()
        # on the f-string-like content of the generated script.
        bridge_template = (
            "# AIDesignerBridge — auto-loaded by FreeCAD GUI on startup\n"
            "import socket, json, threading, time, os\n"
            "\n"
            "_BRIDGE_PORT = __PORT__\n"
            "\n"
            "class _Bridge:\n"
            "    def __init__(self):\n"
            "        self.server_socket = None\n"
            "        self.running = False\n"
            "\n"
            "    def start(self):\n"
            "        try:\n"
            "            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            "            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
            "            self.server_socket.settimeout(1.0)\n"
            "            self.server_socket.bind(('127.0.0.1', _BRIDGE_PORT))\n"
            "            self.server_socket.listen(5)\n"
            "            self.running = True\n"
            "            print('AIDesignerBridge: listening on port ' + str(_BRIDGE_PORT))\n"
            "            threading.Thread(target=self._serve, daemon=True).start()\n"
            "        except Exception as e:\n"
            "            print('AIDesignerBridge: failed to start: ' + str(e))\n"
            "\n"
            "    def _serve(self):\n"
            "        while self.running:\n"
            "            try:\n"
            "                sock, _ = self.server_socket.accept()\n"
            "                threading.Thread(target=self._handle, args=(sock,), daemon=True).start()\n"
            "            except socket.timeout:\n"
            "                continue\n"
            "            except Exception as e:\n"
            "                if self.running:\n"
            "                    print('AIDesignerBridge: accept error: ' + str(e))\n"
            "                break\n"
            "\n"
            "    def _handle(self, sock):\n"
            "        try:\n"
            "            while True:\n"
            "                data = sock.recv(65536)\n"
            "                if not data:\n"
            "                    break\n"
            "                try:\n"
            "                    msg = json.loads(data.decode('utf-8'))\n"
            "                    self._dispatch(msg)\n"
            "                    sock.send(json.dumps({'status': 'executed', 'timestamp': time.time()}).encode())\n"
            "                except json.JSONDecodeError:\n"
            "                    sock.send(json.dumps({'status': 'error', 'message': 'Invalid JSON'}).encode())\n"
            "                except Exception as e:\n"
            "                    sock.send(json.dumps({'status': 'error', 'message': str(e)}).encode())\n"
            "        except Exception:\n"
            "            pass\n"
            "        finally:\n"
            "            sock.close()\n"
            "\n"
            "    def _dispatch(self, msg):\n"
            "        t = msg.get('type', '')\n"
            "        if t == 'execute_script':\n"
            "            self._execute_script(msg.get('script', ''))\n"
            "        elif t == 'update_view':\n"
            "            self._update_view()\n"
            "        elif t == 'open_document':\n"
            "            self._open_document(msg.get('path', ''))\n"
            "        elif t == 'refresh':\n"
            "            self._refresh()\n"
            "\n"
            "    def _execute_script(self, script):\n"
            "        import FreeCAD, FreeCADGui\n"
            "        doc = FreeCAD.ActiveDocument\n"
            "        if not doc:\n"
            "            doc = FreeCAD.newDocument('AutomationDoc')\n"
            "            FreeCAD.setActiveDocument(doc.Name)\n"
            "        ns = {'FreeCAD': FreeCAD, 'App': FreeCAD, 'Gui': FreeCADGui, 'doc': doc}\n"
            "        exec(compile(script, '<bridge>', 'exec'), ns)\n"
            "        doc.recompute()\n"
            "        FreeCADGui.updateGui()\n"
            "        for obj in doc.Objects:\n"
            "            if hasattr(obj, 'ViewObject') and obj.ViewObject:\n"
            "                obj.ViewObject.Visibility = True\n"
            "        FreeCADGui.SendMsgToActiveView('ViewFit')\n"
            "\n"
            "    def _update_view(self):\n"
            "        import FreeCAD, FreeCADGui\n"
            "        doc = FreeCAD.ActiveDocument\n"
            "        if doc:\n"
            "            doc.recompute()\n"
            "        FreeCADGui.updateGui()\n"
            "        FreeCADGui.SendMsgToActiveView('ViewFit')\n"
            "\n"
            "    def _open_document(self, path):\n"
            "        import FreeCAD, FreeCADGui\n"
            "        if path and os.path.exists(path):\n"
            "            FreeCAD.openDocument(path)\n"
            "            FreeCADGui.updateGui()\n"
            "            FreeCADGui.SendMsgToActiveView('ViewFit')\n"
            "\n"
            "    def _refresh(self):\n"
            "        import FreeCAD, FreeCADGui\n"
            "        doc = FreeCAD.ActiveDocument\n"
            "        if doc:\n"
            "            doc.recompute()\n"
            "        FreeCADGui.updateGui()\n"
            "\n"
            "_bridge = _Bridge()\n"
            "_bridge.start()\n"
        )
        bridge_content = bridge_template.replace("__PORT__", str(port))
        with open(init_path, "w") as f:
            f.write(bridge_content)
        print(f"✅ AIDesignerBridge installed at: {init_path}")
        self._module_dir = mod_dir

    def start_persistent_gui(self, initial_document_path: str = None) -> bool:
        """Start persistent FreeCAD GUI that stays open"""
        try:
            # First check if there's already a persistent GUI running
            if self.check_existing_gui():
                print("✅ Using existing persistent FreeCAD GUI")
                if self.websocket_manager:
                    self.websocket_manager.send_user_notification(
                        f"Connected to existing persistent FreeCAD GUI on port {self.communication_port}",
                        "success",
                        self.session_id,
                    )
                return True

            print("🖥️  Starting new persistent FreeCAD GUI...")

            # Install the AIDesignerBridge module into FreeCAD's Mod directory.
            # FreeCAD auto-loads InitGui.py on GUI startup — no .py positional arg needed.
            self._install_freecad_module()

            # Launch FreeCAD GUI without a .py positional argument.
            # Passing a .py file as a positional arg to the AppImage causes
            # "Unknown file: /tmp/xxx.py" errors.
            self.gui_process = subprocess.Popen(
                [self.freecad_gui_executable],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Poll until the bridge socket accepts connections (up to 30 s)
            print("⏳ Waiting for FreeCAD GUI and bridge to initialise...")
            connected = False
            for _ in range(60):
                time.sleep(0.5)
                if self.gui_process.poll() is not None:
                    print("❌ FreeCAD GUI process exited unexpectedly")
                    return False
                if self._test_connection(self.communication_port):
                    connected = True
                    break

            if not connected:
                print("❌ Timed out waiting for FreeCAD bridge to start")
                return False

            self.is_running = True
            self._save_gui_info()
            print(f"✅ Persistent FreeCAD GUI started (PID: {self.gui_process.pid})")
            print(f"🔗 Communication port: {self.communication_port}")

            if initial_document_path:
                self.open_document_in_gui(initial_document_path)

            if self.websocket_manager:
                self.websocket_manager.send_user_notification(
                    f"Persistent FreeCAD GUI started on port {self.communication_port}",
                    "success",
                    self.session_id,
                )

            return True

        except Exception as e:
            print(f"❌ Error starting persistent GUI: {e}")
            return False

    def _create_persistent_script(self, initial_document_path: str = None):
        """Create the persistent FreeCAD script"""
        script_content = f'''
import FreeCAD
import FreeCADGui
import time
import socket
import json
import threading
import sys
import traceback

# Configuration
COMMUNICATION_PORT = {self.communication_port}
SESSION_ID = "{self.session_id}"

class SimpleFreeCADSocketServer:
    """Simple socket server to receive commands from CLI"""

    def __init__(self):
        self.server_socket = None
        self.running = False
        self.clients = []

    def start_server(self):
        """Start the socket server"""
        try:
            print(f"🔗 Starting FreeCAD socket server on port {{COMMUNICATION_PORT}}")

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', COMMUNICATION_PORT))
            self.server_socket.listen(5)
            self.running = True

            print(f"✅ FreeCAD GUI listening on port {{COMMUNICATION_PORT}}")

            # Accept connections in a separate thread
            server_thread = threading.Thread(target=self.accept_connections, daemon=True)
            server_thread.start()

            return True

        except Exception as e:
            print(f"❌ Failed to start socket server: {{e}}")
            traceback.print_exc()
            return False

    def accept_connections(self):
        """Accept incoming connections"""
        while self.running:
            try:
                if not self.server_socket:
                    break

                client_socket, addr = self.server_socket.accept()
                print(f"👤 Client connected from {{addr}}")

                self.clients.append(client_socket)

                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                client_thread.start()

            except Exception as e:
                if self.running:
                    print(f"❌ Error accepting connection: {{e}}")
                    traceback.print_exc()
                break

    def handle_client(self, client_socket):
        """Handle commands from a client"""
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break

                try:
                    message = json.loads(data.decode('utf-8'))
                    print(f"📨 Received command: {{message.get('type', 'unknown')}}")

                    self.process_command(message)

                    # Send acknowledgment
                    response = {{"status": "executed", "timestamp": time.time()}}
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    print(f"✅ Command processed and response sent")

                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON received")
                    error_response = {{"status": "error", "message": "Invalid JSON"}}
                    client_socket.send(json.dumps(error_response).encode('utf-8'))

                except Exception as e:
                    print(f"❌ Error processing command: {{e}}")
                    traceback.print_exc()
                    error_response = {{"status": "error", "message": str(e)}}
                    try:
                        client_socket.send(json.dumps(error_response).encode('utf-8'))
                    except:
                        pass

        except Exception as e:
            print(f"❌ Error handling client: {{e}}")
            traceback.print_exc()

        finally:
            try:
                client_socket.close()
            except:
                pass
            if client_socket in self.clients:
                self.clients.remove(client_socket)

    def process_command(self, message):
        """Process command from CLI"""
        command_type = message.get('type', 'unknown')

        try:
            if command_type == 'execute_script':
                script = message.get('script', '')
                print(f"🔧 Executing script: {{script[:100]}}...")
                self.execute_freecad_script(script)

            elif command_type == 'update_view':
                print("🔄 Updating view...")
                self.update_view()

            elif command_type == 'open_document':
                doc_path = message.get('path', '')
                print(f"📁 Opening document: {{doc_path}}")
                self.open_document(doc_path)

            elif command_type == 'refresh':
                print("🔄 Refreshing GUI...")
                self.refresh_gui()

            else:
                print(f"⚠️  Unknown command type: {{command_type}}")

        except Exception as e:
            print(f"❌ Error processing {{command_type}}: {{e}}")
            traceback.print_exc()
            raise

    def start_server(self):
        """Start the socket server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', COMMUNICATION_PORT))
            self.server_socket.listen(5)
            self.running = True

            print(f"🔗 FreeCAD GUI listening on port {{COMMUNICATION_PORT}}")

            # Accept connections in a separate thread
            threading.Thread(target=self.accept_connections, daemon=True).start()

        except Exception as e:
            print(f"❌ Failed to start socket server: {{e}}")

    def accept_connections(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"👤 Client connected from {{addr}}")

                self.clients.append(client_socket)

                # Handle client in separate thread
                threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,),
                    daemon=True
                ).start()

            except Exception as e:
                if self.running:
                    print(f"❌ Error accepting connection: {{e}}")

    def handle_client(self, client_socket):
        """Handle commands from a client"""
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break

                try:
                    message = json.loads(data.decode('utf-8'))
                    self.process_command(message)

                    # Send acknowledgment
                    response = {{"status": "executed", "timestamp": time.time()}}
                    client_socket.send(json.dumps(response).encode('utf-8'))

                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON received")

                except Exception as e:
                    print(f"❌ Error processing command: {{e}}")

        except Exception as e:
            print(f"❌ Error handling client: {{e}}")

        finally:
            client_socket.close()
            if client_socket in self.clients:
                self.clients.remove(client_socket)

    def process_command(self, message):
        """Process command from CLI"""
        command_type = message.get('type', 'unknown')

        if command_type == 'execute_script':
            script = message.get('script', '')
            self.execute_freecad_script(script)

        elif command_type == 'update_view':
            self.update_view()

        elif command_type == 'open_document':
            doc_path = message.get('path', '')
            self.open_document(doc_path)

        elif command_type == 'refresh':
            self.refresh_gui()

    def execute_freecad_script(self, script):
        """Execute FreeCAD script in GUI context"""
        try:
            # Get or create the active document - don't create new ones
            doc = FreeCAD.ActiveDocument
            if not doc:
                doc = FreeCAD.newDocument("AutomationDoc")
                FreeCAD.setActiveDocument(doc.Name)
                print("📄 Created new automation document")
            else:
                print(f"📄 Using existing document: {{doc.Name}}")

            # Execute the script in the context of the existing document
            # Use safe sandbox with validation (replaces dangerous exec())
            try:
                from ai_designer.sandbox import ScriptSandbox

                # Create sandbox for FreeCAD scripts
                sandbox = ScriptSandbox(
                    timeout=60,
                    strict_validation=True,
                    use_subprocess=False  # GUI requires inline execution
                )

                # Prepare FreeCAD environment
                freecad_env = {{
                    'FreeCAD': FreeCAD,
                    'doc': doc,
                    'App': FreeCAD,
                    'Gui': FreeCADGui if 'FreeCADGui' in globals() else None
                }}

                # Execute validated script with sandbox
                result = sandbox.execute_freecad_script(script, freecad_env)

                if not result.success:
                    raise ValueError(f"Script execution failed: {{result.error}}")

            except Exception as e:
                import logging
                logging.error(f"Script execution failed: {{e}}")
                raise ValueError(f"Script error: {{e}}")
            doc.recompute()
            FreeCADGui.updateGui()

            # Make sure all objects in the document are visible
            for obj in doc.Objects:
                if hasattr(obj, 'ViewObject') and obj.ViewObject:
                    obj.ViewObject.Visibility = True

            # Fit view to show all objects in the SAME window
            if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
                FreeCADGui.SendMsgToActiveView("ViewFit")
                print(f"🔄 View updated - Document now has {{len(doc.Objects)}} objects")

            print(f"✅ Script executed successfully in existing document")

        except Exception as e:
            print(f"❌ Error executing script: {{e}}")
            import traceback
            traceback.print_exc()

    def update_view(self):
        """Update the 3D view"""
        try:
            doc = FreeCAD.ActiveDocument
            if doc and hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
                # Make sure all objects are visible
                for obj in doc.Objects:
                    if hasattr(obj, 'ViewObject') and obj.ViewObject:
                        obj.ViewObject.Visibility = True

                # Recompute and update
                doc.recompute()
                FreeCADGui.updateGui()

                # Fit view to show all objects
                FreeCADGui.SendMsgToActiveView("ViewFit")
                print(f"🔄 View updated - showing {{len(doc.Objects)}} objects")
            else:
                print("⚠️  No active document or GUI available for view update")

        except Exception as e:
            print(f"❌ Error updating view: {{e}}")

    def open_document(self, doc_path):
        """Open a document"""
        try:
            if doc_path and os.path.exists(doc_path):
                FreeCAD.openDocument(doc_path)
                FreeCAD.setActiveDocument(os.path.basename(doc_path).replace('.FCStd', ''))
                self.update_view()
                print(f"📁 Opened document: {{doc_path}}")

        except Exception as e:
            print(f"❌ Error opening document: {{e}}")

    def refresh_gui(self):
        """Refresh the entire GUI"""
        try:
            doc = FreeCAD.ActiveDocument
            if doc:
                doc.recompute()
            FreeCADGui.updateGui()
            print("🔄 GUI refreshed")

        except Exception as e:
            print(f"❌ Error refreshing GUI: {{e}}")

# Initialize FreeCAD GUI
print("🚀 Starting persistent FreeCAD GUI...")

# Create or open document
if "{initial_document_path}" and "{initial_document_path}" != "None":
    try:
        doc = FreeCAD.openDocument("{initial_document_path}")
        print(f"📁 Opened initial document: {initial_document_path}")
    except:
        doc = FreeCAD.newDocument("AutomationDoc")
        print("📄 Created new document")
else:
    doc = FreeCAD.newDocument("AutomationDoc")
    print("📄 Created new document")

FreeCAD.setActiveDocument(doc.Name)

# Set up the view
if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
    FreeCADGui.ActiveDocument.activeView().viewIsometric()
    FreeCADGui.SendMsgToActiveView("ViewFit")

# Start socket server
print("🚀 Starting socket server...")
socket_server = SimpleFreeCADSocketServer()
server_started = socket_server.start_server()

if server_started:
    print("✅ Persistent FreeCAD GUI ready for real-time updates")
    print(f"🔗 Session ID: {{SESSION_ID}}")
    print(f"📡 Socket server listening on port {{COMMUNICATION_PORT}}")
    print("�🖥️  GUI will stay open and update automatically")
else:
    print("❌ Failed to start socket server")
    print("⚠️  GUI will run but won't accept remote commands")

# Keep the script running
print("🔄 GUI script running, waiting for commands...")
'''

        # Write script to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            self.gui_script_path = f.name

    def _start_socket_server(self):
        """Start socket server for receiving CLI commands"""

        def server_thread():
            try:
                self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # We'll connect TO the FreeCAD GUI, not serve from here
                pass
            except Exception as e:
                print(f"❌ Socket server error: {e}")

        self.socket_thread = threading.Thread(target=server_thread, daemon=True)
        self.socket_thread.start()

    def send_command_to_gui(self, command: Dict[str, Any]) -> bool:
        """Send command to the persistent FreeCAD GUI"""
        try:
            # Connect to FreeCAD GUI socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect(("localhost", self.communication_port))

            # Send command
            message = json.dumps(command).encode("utf-8")
            client_socket.send(message)

            # Wait for response
            response_data = client_socket.recv(4096)
            response = json.loads(response_data.decode("utf-8"))

            client_socket.close()

            if response.get("status") == "executed":
                if self.websocket_manager:
                    self.websocket_manager.send_user_notification(
                        f"Command executed in GUI: {command.get('type', 'unknown')}",
                        "success",
                        self.session_id,
                    )
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ Failed to send command to GUI: {e}")
            if self.websocket_manager:
                self.websocket_manager.send_error(
                    f"GUI communication error: {str(e)}", session_id=self.session_id
                )
            return False

    def execute_script_in_gui(self, script: str) -> bool:
        """Execute a FreeCAD script in the persistent GUI"""
        return self.send_command_to_gui(
            {"type": "execute_script", "script": script, "timestamp": time.time()}
        )

    def update_gui_view(self) -> bool:
        """Update the GUI view to show latest changes"""
        return self.send_command_to_gui(
            {"type": "update_view", "timestamp": time.time()}
        )

    def open_document_in_gui(self, doc_path: str) -> bool:
        """Open a document in the persistent GUI"""
        return self.send_command_to_gui(
            {"type": "open_document", "path": doc_path, "timestamp": time.time()}
        )

    def refresh_gui(self) -> bool:
        """Refresh the GUI"""
        return self.send_command_to_gui({"type": "refresh", "timestamp": time.time()})

    def is_gui_running(self) -> bool:
        """Check if the GUI is still running"""
        if not self.gui_process:
            return False

        return self.gui_process.poll() is None

    def stop_gui(self):
        """Stop the persistent GUI"""
        try:
            if self.gui_process and self.is_gui_running():
                print("🛑 Stopping persistent FreeCAD GUI...")
                self.gui_process.terminate()

                # Wait for graceful shutdown
                try:
                    self.gui_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("⚠️  Force killing FreeCAD GUI...")
                    self.gui_process.kill()

                self.is_running = False
                print("✅ Persistent FreeCAD GUI stopped")

                if self.websocket_manager:
                    self.websocket_manager.send_user_notification(
                        "Persistent FreeCAD GUI stopped", "info", self.session_id
                    )

            # Clean up script file
            if self.gui_script_path and os.path.exists(self.gui_script_path):
                os.unlink(self.gui_script_path)

            # Clean up PID file
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)

        except Exception as e:
            print(f"❌ Error stopping GUI: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get status of the persistent GUI"""
        return {
            "running": self.is_gui_running(),
            "pid": self.gui_process.pid if self.gui_process else None,
            "session_id": self.session_id,
            "communication_port": self.communication_port,
            "script_path": self.gui_script_path,
        }

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_gui()

    def send_update_signal(self):
        """
        Send update signal to the persistent FreeCAD GUI
        Triggers a refresh/recompute of the current document
        """
        try:
            if not self.is_running:
                print("⚠️ Persistent GUI not running, cannot send update signal")
                return False

            # Send recompute command to update the GUI
            update_command = (
                "App.ActiveDocument.recompute() if App.ActiveDocument else None"
            )
            result = self._send_command_to_gui(update_command)

            if result.get("status") == "success":
                print("✅ GUI update signal sent successfully")
                return True
            else:
                print(
                    f"⚠️ GUI update signal failed: {result.get('message', 'Unknown error')}"
                )
                return False

        except Exception as e:
            print(f"❌ Failed to send GUI update signal: {e}")
            return False

    def _send_command_to_gui(self, command):
        """
        Send a command to the persistent GUI via socket communication
        """
        try:
            if not self.communication_port:
                return {"status": "error", "message": "No communication port available"}

            # Create a simple socket client to send command
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5.0)  # 5 second timeout
                sock.connect(("localhost", self.communication_port))

                # Send command
                command_data = {"command": command, "type": "execute"}
                message = json.dumps(command_data) + "\n"
                sock.sendall(message.encode())

                # Get response
                response_data = sock.recv(4096).decode()
                if response_data:
                    response = json.loads(response_data.strip())
                    return response
                else:
                    return {"status": "error", "message": "No response from GUI"}

        except ConnectionRefusedError:
            return {
                "status": "error",
                "message": "GUI not responding on communication port",
            }
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid response format: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Communication error: {e}"}

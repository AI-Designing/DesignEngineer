#!/usr/bin/env python3
"""
Simple FreeCAD GUI launcher that stays open and accepts real-time updates
"""

import os
import signal
import subprocess
import tempfile
import time


def create_simple_gui_script():
    """Create a simple FreeCAD script that keeps the GUI open"""
    script_content = """
import FreeCAD
import FreeCADGui
import time
import sys

print("🚀 Starting Simple Persistent FreeCAD GUI...")

# Create or get active document
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")
    print("📄 Created new document: AutomationDoc")

FreeCAD.setActiveDocument(doc.Name)

# Set up the 3D view
try:
    if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
        FreeCADGui.ActiveDocument.activeView().viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
        print("🔄 View initialized")
except:
    print("⚠️  Could not set up view")

print("✅ FreeCAD GUI ready and persistent")
print("🖥️  GUI will stay open - you can now send commands")
print("📝 Document:", doc.Name)
print("🔄 Waiting for external commands...")

# Keep the GUI alive and responsive
while True:
    try:
        # Process GUI events
        FreeCADGui.updateGui()

        # Small delay to prevent excessive CPU usage
        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\\n👋 GUI stopped by user")
        break
    except Exception as e:
        print(f"⚠️  GUI error: {e}")
        time.sleep(1)

print("🛑 FreeCAD GUI shutting down...")
"""
    return script_content


def start_persistent_freecad_gui():
    """Start FreeCAD GUI that stays open"""
    print("🖥️  Starting Persistent FreeCAD GUI...")

    # Create the GUI script
    script_content = create_simple_gui_script()

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        # Start FreeCAD with the persistent script
        process = subprocess.Popen(
            ["freecad", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,  # Create new process group
        )

        print(f"✅ FreeCAD GUI started (PID: {process.pid})")
        print(f"📝 Script: {script_path}")

        # Wait a moment for startup
        time.sleep(3)

        # Check if still running
        if process.poll() is None:
            print("✅ GUI is running and persistent")
            return process, script_path
        else:
            stdout, stderr = process.communicate()
            print("❌ GUI failed to start")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return None, script_path

    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
        return None, script_path


def test_gui_with_commands(process):
    """Test the GUI by opening existing files"""
    print("\\n🧪 Testing GUI with existing files...")

    # Get list of recent files
    outputs_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs"
    )
    if os.path.exists(outputs_dir):
        files = [f for f in os.listdir(outputs_dir) if f.endswith(".FCStd")]
        if files:
            latest_file = sorted(files)[-1]
            file_path = os.path.join(outputs_dir, latest_file)

            print(f"📂 Found file: {latest_file}")
            print(f"💡 To open this file in the GUI, use FreeCAD's File > Open menu")
            print(f"📁 File location: {file_path}")
            return file_path

    return None


def main():
    """Main function"""
    print("🚀 FreeCAD Persistent GUI Launcher")
    print("=" * 50)

    # Start the persistent GUI
    process, script_path = start_persistent_freecad_gui()

    if process:
        try:
            print("\\n🎯 GUI is now running!")
            print("✅ You can now:")
            print("   1. See the FreeCAD window open")
            print("   2. Run commands from another terminal")
            print("   3. Watch real-time updates")

            # Test with existing files
            test_file = test_gui_with_commands(process)

            print("\\n⌨️  Press Ctrl+C to stop the GUI")

            # Wait for process or user interrupt
            while process.poll() is None:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\\n🛑 Stopping GUI...")

            # Terminate the process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing GUI...")
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except Exception as e:
                print(f"⚠️  Error stopping: {e}")

        finally:
            # Cleanup
            if os.path.exists(script_path):
                os.unlink(script_path)
            print("✅ Cleanup completed")

    else:
        print("❌ Failed to start persistent GUI")
        if os.path.exists(script_path):
            os.unlink(script_path)


if __name__ == "__main__":
    main()

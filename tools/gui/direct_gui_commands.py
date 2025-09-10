#!/usr/bin/env python3
"""
Direct FreeCAD GUI Command Sender
Sends commands directly to the running FreeCAD GUI session via socket
"""

import json
import socket
import time


def send_command_to_freecad_gui(script, port=60543):
    """Send a command directly to the FreeCAD GUI via socket"""
    try:
        print(f"📡 Connecting to FreeCAD GUI on port {port}...")

        # Connect to FreeCAD GUI
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10)
        client_socket.connect(("localhost", port))

        print("✅ Connected to FreeCAD GUI!")

        # Prepare command
        command = {"type": "execute_script", "script": script, "timestamp": time.time()}

        # Send command
        message = json.dumps(command).encode("utf-8")
        client_socket.send(message)
        print("📤 Command sent!")

        # Wait for response
        response_data = client_socket.recv(4096)
        response = json.loads(response_data.decode("utf-8"))

        print(f"📥 Response: {response}")

        client_socket.close()

        if response.get("status") == "executed":
            print("✅ Command executed successfully in GUI!")
            return True
        else:
            print("❌ Command execution failed")
            return False

    except ConnectionRefusedError:
        print("❌ Cannot connect to FreeCAD GUI")
        print("💡 Make sure the persistent GUI is running")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def create_box_in_gui():
    """Create a box in the persistent GUI"""
    script = """
# Create box in the SAME document
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create box
box = doc.addObject("Part::Box", "RealTimeBox")
box.Length = 25
box.Width = 20
box.Height = 15
box.Placement.Base = FreeCAD.Vector(0, 0, 0)

# Set color to red for visibility
if hasattr(box, 'ViewObject'):
    box.ViewObject.ShapeColor = (1.0, 0.0, 0.0)  # Red

doc.recompute()
print(f"✅ Box created! Document now has {len(doc.Objects)} objects")

# Update view
import FreeCADGui
if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
    FreeCADGui.SendMsgToActiveView("ViewFit")
"""

    print("🔧 Creating Red Box in persistent GUI...")
    return send_command_to_freecad_gui(script)


def create_cylinder_in_gui():
    """Create a cylinder in the persistent GUI"""
    script = """
# Create cylinder in the SAME document
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create cylinder
cylinder = doc.addObject("Part::Cylinder", "RealTimeCylinder")
cylinder.Radius = 10
cylinder.Height = 25
cylinder.Placement.Base = FreeCAD.Vector(40, 0, 0)

# Set color to blue for visibility
if hasattr(cylinder, 'ViewObject'):
    cylinder.ViewObject.ShapeColor = (0.0, 0.0, 1.0)  # Blue

doc.recompute()
print(f"✅ Cylinder created! Document now has {len(doc.Objects)} objects")

# Update view
import FreeCADGui
if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
    FreeCADGui.SendMsgToActiveView("ViewFit")
"""

    print("🔧 Creating Blue Cylinder in persistent GUI...")
    return send_command_to_freecad_gui(script)


def create_sphere_in_gui():
    """Create a sphere in the persistent GUI"""
    script = """
# Create sphere in the SAME document
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create sphere
sphere = doc.addObject("Part::Sphere", "RealTimeSphere")
sphere.Radius = 15
sphere.Placement.Base = FreeCAD.Vector(-40, 0, 0)

# Set color to green for visibility
if hasattr(sphere, 'ViewObject'):
    sphere.ViewObject.ShapeColor = (0.0, 1.0, 0.0)  # Green

doc.recompute()
print(f"✅ Sphere created! Document now has {len(doc.Objects)} objects")

# Update view
import FreeCADGui
if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
    FreeCADGui.SendMsgToActiveView("ViewFit")
"""

    print("🔧 Creating Green Sphere in persistent GUI...")
    return send_command_to_freecad_gui(script)


def create_cone_in_gui():
    """Create a cone in the persistent GUI"""
    script = """
# Create cone in the SAME document
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create cone
cone = doc.addObject("Part::Cone", "RealTimeCone")
cone.Radius1 = 12
cone.Radius2 = 3
cone.Height = 20
cone.Placement.Base = FreeCAD.Vector(0, 40, 0)

# Set color to yellow for visibility
if hasattr(cone, 'ViewObject'):
    cone.ViewObject.ShapeColor = (1.0, 1.0, 0.0)  # Yellow

doc.recompute()
print(f"✅ Cone created! Document now has {len(doc.Objects)} objects")

# Update view
import FreeCADGui
if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
    FreeCADGui.SendMsgToActiveView("ViewFit")
"""

    print("🔧 Creating Yellow Cone in persistent GUI...")
    return send_command_to_freecad_gui(script)


def show_all_objects():
    """Show all objects in the document"""
    script = """
# Show all objects in the document
doc = FreeCAD.ActiveDocument
if doc:
    print(f"📊 Document: {doc.Name}")
    print(f"📦 Total objects: {len(doc.Objects)}")
    print("🏗️  Objects in document:")
    for i, obj in enumerate(doc.Objects, 1):
        print(f"  {i}. {obj.Label} ({obj.TypeId})")

    # Update view to show all
    import FreeCADGui
    if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
        FreeCADGui.SendMsgToActiveView("ViewFit")
        print("🔄 View updated to show all objects")
else:
    print("❌ No active document")
"""

    print("📊 Checking all objects in GUI...")
    return send_command_to_freecad_gui(script)


def main():
    """Main demonstration"""
    print("🚀 Direct FreeCAD GUI Real-Time Demo")
    print("=" * 50)
    print("💡 This sends commands directly to the persistent FreeCAD GUI")
    print("✅ Objects will appear in the SAME document window")

    commands = [
        ("Red Box", create_box_in_gui),
        ("Blue Cylinder", create_cylinder_in_gui),
        ("Green Sphere", create_sphere_in_gui),
        ("Yellow Cone", create_cone_in_gui),
        ("Show All Objects", show_all_objects),
    ]

    for i, (name, func) in enumerate(commands, 1):
        print(f"\n🎯 Step {i}/{len(commands)}: {name}")

        success = func()

        if success:
            print(f"✅ {name} completed successfully!")
        else:
            print(f"❌ {name} failed")

        if i < len(commands):
            print("⏱️  Waiting 3 seconds before next command...")
            time.sleep(3)

    print(f"\n🎉 Demo completed!")
    print("💡 Check the FreeCAD GUI window - you should see all colorful objects!")
    print("🔄 The objects are in the SAME document and visible in real-time")


if __name__ == "__main__":
    main()

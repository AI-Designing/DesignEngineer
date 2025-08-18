#!/usr/bin/env python3
"""
Test real-time FreeCAD commands with visible GUI updates
"""

import subprocess
import time
import tempfile
import os

def create_freecad_command_script(command_description, objects_to_create):
    """Create a FreeCAD script for specific commands"""
    
    scripts = {
        "box": '''
import FreeCAD
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create box
box = doc.addObject("Part::Box", "Box")
box.Length = 20
box.Width = 15  
box.Height = 10
box.Placement.Base = FreeCAD.Vector(0, 0, 0)
doc.recompute()
print("✅ Box created!")
''',
        
        "cylinder": '''
import FreeCAD
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create cylinder
cylinder = doc.addObject("Part::Cylinder", "Cylinder")
cylinder.Radius = 8
cylinder.Height = 20
cylinder.Placement.Base = FreeCAD.Vector(30, 0, 0)
doc.recompute()
print("✅ Cylinder created!")
''',
        
        "sphere": '''
import FreeCAD
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create sphere
sphere = doc.addObject("Part::Sphere", "Sphere")
sphere.Radius = 12
sphere.Placement.Base = FreeCAD.Vector(-30, 0, 0)
doc.recompute()
print("✅ Sphere created!")
''',
        
        "cone": '''
import FreeCAD
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create cone
cone = doc.addObject("Part::Cone", "Cone")
cone.Radius1 = 10
cone.Radius2 = 2
cone.Height = 15
cone.Placement.Base = FreeCAD.Vector(0, 30, 0)
doc.recompute()
print("✅ Cone created!")
''',
        
        "multiple": '''
import FreeCAD
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("AutomationDoc")

# Create multiple objects
objects_created = []

# Box
box = doc.addObject("Part::Box", "MultiBox")
box.Length = 10
box.Width = 10
box.Height = 5
box.Placement.Base = FreeCAD.Vector(0, 0, 0)
objects_created.append("Box")

# Cylinder  
cylinder = doc.addObject("Part::Cylinder", "MultiCylinder")
cylinder.Radius = 5
cylinder.Height = 15
cylinder.Placement.Base = FreeCAD.Vector(20, 0, 0)
objects_created.append("Cylinder")

# Sphere
sphere = doc.addObject("Part::Sphere", "MultiSphere")
sphere.Radius = 7
sphere.Placement.Base = FreeCAD.Vector(-20, 0, 0)
objects_created.append("Sphere")

doc.recompute()
print(f"✅ Created {len(objects_created)} objects: {', '.join(objects_created)}")
'''
    }
    
    return scripts.get(command_description, scripts["box"])

def execute_freecad_script_directly(script_content, description):
    """Execute FreeCAD script directly and return to GUI"""
    print(f"🔧 Executing: {description}")
    
    # Write script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    try:
        # Execute with FreeCAD in batch mode, then return to GUI
        result = subprocess.run([
            'freecad', '--console',
            script_path
        ], 
        capture_output=True, 
        text=True, 
        timeout=30
        )
        
        print(f"📤 Return code: {result.returncode}")
        if result.stdout:
            print(f"📋 Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"⚠️  Errors: {result.stderr.strip()}")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(script_path):
            os.unlink(script_path)

def test_real_time_commands():
    """Test a series of real-time FreeCAD commands"""
    print("🚀 Testing Real-Time FreeCAD Commands")
    print("=" * 50)
    
    commands = [
        ("box", "Creating a box"),
        ("cylinder", "Creating a cylinder"), 
        ("sphere", "Creating a sphere"),
        ("cone", "Creating a cone"),
        ("multiple", "Creating multiple objects")
    ]
    
    print("💡 Make sure FreeCAD GUI is open to see real-time updates!")
    print("📝 You can open existing files in the GUI to see accumulated objects")
    
    for i, (cmd_type, description) in enumerate(commands, 1):
        print(f"\\n🎯 Step {i}/{len(commands)}: {description}")
        
        # Generate script
        script = create_freecad_command_script(cmd_type, [])
        
        # Execute
        success = execute_freecad_script_directly(script, description)
        
        if success:
            print(f"✅ {description} completed")
        else:
            print(f"❌ {description} failed")
        
        # Wait between commands for visibility
        if i < len(commands):
            print("⏱️  Waiting 3 seconds...")
            time.sleep(3)
    
    # Show files location
    outputs_dir = "/home/vansh5632/DesignEng/freecad-llm-automation/outputs"
    if os.path.exists(outputs_dir):
        files = [f for f in os.listdir(outputs_dir) if f.endswith('.FCStd')]
        if files:
            latest_file = sorted(files)[-1]
            file_path = os.path.join(outputs_dir, latest_file)
            print(f"\\n📁 Latest file: {file_path}")
            print(f"💡 Open this file in FreeCAD GUI to see all objects!")

def open_existing_file_in_gui():
    """Helper to open an existing file in GUI"""
    outputs_dir = "/home/vansh5632/DesignEng/freecad-llm-automation/outputs"
    if os.path.exists(outputs_dir):
        files = [f for f in os.listdir(outputs_dir) if f.endswith('.FCStd')]
        if files:
            latest_file = sorted(files)[-1]
            file_path = os.path.join(outputs_dir, latest_file)
            
            print(f"🔍 Opening file in GUI: {latest_file}")
            
            script_content = f'''
import FreeCAD
import FreeCADGui

# Open the file
doc = FreeCAD.openDocument("{file_path}")
FreeCAD.setActiveDocument(doc.Name)

# Update view
if hasattr(FreeCADGui, 'ActiveDocument') and FreeCADGui.ActiveDocument:
    FreeCADGui.ActiveDocument.activeView().viewIsometric()
    FreeCADGui.SendMsgToActiveView("ViewFit")

print(f"📁 Opened: {{doc.Name}}")
print(f"📊 Objects: {{len(doc.Objects)}}")
for obj in doc.Objects:
    print(f"  - {{obj.Label}} ({{obj.TypeId}})")
'''
            
            return execute_freecad_script_directly(script_content, f"Opening {latest_file}")
    
    return False

def main():
    """Main function"""
    print("🎯 FreeCAD Real-Time Command Tester")
    print("=" * 50)
    
    choice = input("Choose test:\n1. Test real-time commands\n2. Open existing file in GUI\n3. Both\nChoice (1-3): ").strip()
    
    if choice == "1":
        test_real_time_commands()
    elif choice == "2":
        open_existing_file_in_gui()
    elif choice == "3":
        test_real_time_commands()
        print("\\n" + "="*30)
        open_existing_file_in_gui()
    else:
        print("✅ Running all tests...")
        test_real_time_commands()
        print("\\n" + "="*30)
        open_existing_file_in_gui()

if __name__ == "__main__":
    main()

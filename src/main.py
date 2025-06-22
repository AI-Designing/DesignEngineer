import sys
import os
import subprocess
import time
from freecad.api_client import FreeCADAPIClient
from freecad.command_executor import CommandExecutor
import FreeCAD
import Part

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    """
    Main function to establish connection with FreeCAD API and execute commands
    """
    try:
        # Initialize the API client
        print("Initializing FreeCAD API client...")
        api_client = FreeCADAPIClient()
        
        # Start FreeCAD application
        print("Starting FreeCAD application...")
        freecad_process = subprocess.Popen(['freecad'])
        
        # Wait a moment for FreeCAD to start
        time.sleep(3)
        
        # Establish connection
        print("Establishing connection to FreeCAD...")
        if api_client.connect():
            print("✓ Successfully connected to FreeCAD API")
            
            # Initialize command executor
            command_executor = CommandExecutor(api_client)
            
            # Execute a simple test command
            print("Executing test command...")
            test_command = "print('Hello from FreeCAD!')"
            result = command_executor.execute(test_command)
            
            print(f"Command result: {result}")
            
            # Execute commands step by step
            print("Creating a simple box...")
            
            # Step 1: Create document and box
            step1 = "doc = FreeCAD.newDocument('TestDocument'); box = doc.addObject('Part::Box', 'TestBox'); box.Length = 10; box.Width = 10; box.Height = 10; doc.recompute(); print('Box created successfully!')"
            result1 = command_executor.execute(step1)
            print(f"Step 1 result: {result1}")
            
            # Step 2: Save document
            step2 = "import os; doc = FreeCAD.getDocument('TestDocument'); save_path = os.path.expanduser('~/test_box.FCStd'); doc.saveAs(save_path); print(f'Document saved to: {save_path}')"
            result2 = command_executor.execute(step2)
            print(f"Step 2 result: {result2}")
            
            # Step 3: Export STEP file
            step3 = "import Part; import os; doc = FreeCAD.getDocument('TestDocument'); box = doc.getObject('TestBox'); step_path = os.path.expanduser('~/test_box.step'); Part.export([box], step_path); print(f'STEP file exported to: {step_path}')"
            result3 = command_executor.execute(step3)
            print(f"Step 3 result: {result3}")
            
        else:
            print("✗ Failed to connect to FreeCAD API")
            
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # Clean up
        try:
            api_client.disconnect()
            print("Disconnected from FreeCAD API")
        except:
            pass

if __name__ == "__main__":
    main()
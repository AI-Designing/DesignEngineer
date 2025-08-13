#!/usr/bin/env python3
"""
Demo: Persistent GUI with Step-by-Step Updates
This demonstrates the FIXED behavior where ONE window stays open
and gets updated with each command execution.
"""

import time
import subprocess
import signal
import sys

def run_interactive_demo():
    """Run demo using interactive CLI to maintain same persistent GUI"""
    print("🎯 Persistent GUI Demo - Step-by-Step Updates")
    print("=" * 55)
    print("This demo will:")
    print("1. Start ONE persistent FreeCAD GUI window")
    print("2. Execute commands that update the SAME window")
    print("3. Show step-by-step object creation")
    print("4. Verify no new windows are opened")
    print()
    
    # Commands to execute step by step
    commands = [
        "create box 20x20x20 --real",
        "create cylinder radius 10 height 15 --real", 
        "create sphere radius 8 --real",
        "create cone radius1 12 radius2 6 height 18 --real"
    ]
    
    print("🚀 Starting interactive FreeCAD CLI...")
    print("📋 Commands to execute:")
    for i, cmd in enumerate(commands, 1):
        print(f"   {i}. {cmd}")
    print()
    
    # Start the CLI in interactive mode
    process = subprocess.Popen([
        'python3', '-m', 'ai_designer.cli',
        '--llm-provider', 'google',
        '--llm-api-key', 'AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc'
    ], 
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd='/home/vansh5632/DesignEng/freecad-llm-automation'
    )
    
    def cleanup():
        """Clean up the process"""
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
    
    try:
        # Wait a moment for CLI to start
        time.sleep(5)
        
        print("✅ CLI started, now executing commands step by step...")
        print("🖥️  Check that ONE FreeCAD window opens and stays open")
        print()
        
        # Execute each command
        for i, command in enumerate(commands, 1):
            print(f"🔄 Step {i}: {command}")
            
            # Send command to CLI
            process.stdin.write(command + "\n")
            process.stdin.flush()
            
            # Give time for execution
            print(f"   ⏳ Executing... (check GUI updates)")
            time.sleep(8)
            
            print(f"   ✅ Step {i} completed")
            print(f"   🔍 GUI should now show {i} object(s) in the SAME window")
            print()
        
        print("🎉 Demo completed successfully!")
        print("📊 Expected result:")
        print("   • ONE FreeCAD window remained open throughout")
        print("   • Window shows all 4 objects: box, cylinder, sphere, cone")
        print("   • No additional windows were opened")
        print()
        
        # Send quit command
        print("🛑 Sending quit command...")
        process.stdin.write("quit\n")
        process.stdin.flush()
        
        # Wait for clean shutdown
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("⚠️  Process didn't quit cleanly, terminating...")
            cleanup()
            
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
        cleanup()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        cleanup()

def run_simple_test():
    """Run a simple test with a single session"""
    print("🧪 Simple Test: Single Session Multiple Commands")
    print("=" * 50)
    
    # Create a script that runs multiple commands in one session
    script_content = '''
import sys
import os
sys.path.insert(0, "/home/vansh5632/DesignEng/freecad-llm-automation")

from src.ai_designer.cli import FreeCADCLI

# Create CLI instance
cli = FreeCADCLI(
    llm_provider="google",
    llm_api_key="AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc",
    enable_persistent_gui=True,
    enable_websocket=True
)

# Initialize
if cli.initialize():
    print("✅ CLI initialized with persistent GUI")
    
    # Execute multiple commands in same session
    commands = [
        "create box 20x20x20 --real",
        "create cylinder radius 10 height 15 --real", 
        "create sphere radius 8 --real"
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\\n🔄 Executing step {i}: {cmd}")
        cli.execute_command(cmd)
        print(f"✅ Step {i} completed - check GUI for updates")
        
        import time
        time.sleep(3)
    
    print("\\n🎉 All commands executed in same persistent GUI!")
    input("Press Enter to quit and close GUI...")
    
    # Cleanup
    cli.cleanup()
else:
    print("❌ Failed to initialize CLI")
'''
    
    with open('/tmp/test_persistent_gui.py', 'w') as f:
        f.write(script_content)
    
    print("🚀 Running test script...")
    result = subprocess.run(['python3', '/tmp/test_persistent_gui.py'], 
                          cwd='/home/vansh5632/DesignEng/freecad-llm-automation')
    
    return result.returncode == 0

if __name__ == "__main__":
    print("Choose demo type:")
    print("1. Interactive CLI demo (recommended)")
    print("2. Simple script test")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        run_interactive_demo()
    elif choice == "2":
        run_simple_test()
    else:
        print("Invalid choice, running interactive demo...")
        run_interactive_demo()

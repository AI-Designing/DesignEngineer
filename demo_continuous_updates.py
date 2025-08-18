#!/usr/bin/env python3
"""
Demonstrate real-time FreeCAD GUI updates with continuous commands
"""

import subprocess
import time
import os

def run_freecad_command(command):
    """Run a single FreeCAD command with real execution"""
    print(f"🔧 Executing: {command}")
    
    cmd = [
        "/home/vansh5632/DesignEng/freecad-llm-automation/venv/bin/python",
        "-m", "ai_designer.cli",
        "--llm-provider", "google",
        "--llm-api-key", "AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc",
        "--command", command
    ]
    
    env = os.environ.copy()
    env["GOOGLE_API_KEY"] = "AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc"
    
    try:
        result = subprocess.run(
            cmd,
            cwd="/home/vansh5632/DesignEng/freecad-llm-automation",
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ Command completed successfully")
            # Extract key information from output
            lines = result.stdout.split('\n')
            for line in lines:
                if "REAL EXECUTION SUCCESS" in line:
                    print(f"🎯 {line}")
                elif "Document auto-saved to:" in line:
                    print(f"💾 {line}")
                elif "Objects:" in line and "📊" in line:
                    print(f"📊 {line}")
        else:
            print(f"❌ Command failed (return code: {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error executing command: {e}")
        return False

def demonstrate_continuous_updates():
    """Demonstrate continuous real-time updates"""
    print("🚀 Real-Time FreeCAD GUI Updates Demonstration")
    print("=" * 60)
    print("💡 Make sure you can see the FreeCAD GUI window!")
    print("👀 Watch as objects appear in real-time!")
    print()
    
    # List of commands to execute with real flag
    commands = [
        "create box 20x15x10 --real",
        "create cylinder radius 8 height 20 --real",
        "create sphere radius 12 --real",
        "create cone radius 10 height 15 --real"
    ]
    
    success_count = 0
    
    for i, command in enumerate(commands, 1):
        print(f"\n{'='*50}")
        print(f"🎯 Step {i}/{len(commands)}: {command}")
        print('='*50)
        
        success = run_freecad_command(command)
        
        if success:
            success_count += 1
            print(f"✅ Step {i} completed - Objects should now be visible in GUI!")
        else:
            print(f"❌ Step {i} failed")
        
        # Wait between commands for visibility
        if i < len(commands):
            print(f"\n⏱️  Waiting 5 seconds before next command...")
            for j in range(5, 0, -1):
                print(f"   {j}...", end=" ", flush=True)
                time.sleep(1)
            print("▶️ Next!")
    
    print(f"\n🎉 DEMONSTRATION COMPLETE!")
    print(f"✅ Successful commands: {success_count}/{len(commands)}")
    
    # Check created files
    outputs_dir = "/home/vansh5632/DesignEng/freecad-llm-automation/outputs"
    if os.path.exists(outputs_dir):
        files = [f for f in os.listdir(outputs_dir) if f.endswith('.FCStd')]
        recent_files = sorted([f for f in files if '20250818_19' in f])[-4:]  # Last 4 today
        
        print(f"\n📁 Files created during demonstration:")
        for file in recent_files:
            file_path = os.path.join(outputs_dir, file)
            file_size = os.path.getsize(file_path)
            print(f"  📄 {file} ({file_size} bytes)")
    
    print(f"\n💡 Tips:")
    print(f"   • Open any of these files in FreeCAD GUI to see the objects")
    print(f"   • Use File > Open in FreeCAD GUI")
    print(f"   • All objects should be visible and properly positioned")

if __name__ == "__main__":
    demonstrate_continuous_updates()

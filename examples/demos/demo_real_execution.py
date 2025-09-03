#!/usr/bin/env python3
"""
Demo script showing real FreeCAD object creation with continuous updates
"""

import os
import subprocess
import sys
import time


def main():
    print("🚀 FreeCAD Real Execution Demo")
    print("=" * 50)

    # Get the project directory
    project_dir = "/home/vansh5632/DesignEng/freecad-llm-automation"
    python_path = f"{project_dir}/venv/bin/python"
    api_key = "AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc"

    # List of commands to execute (with --real flag for actual object creation)
    commands = [
        "create box 10x20x30 --real",
        "create cylinder radius 5 height 15 --real",
        "create sphere radius 8 --real",
        "create cone radius 6 height 12 --real",
    ]

    print("📋 Commands to execute:")
    for i, cmd in enumerate(commands, 1):
        print(f"  {i}. {cmd}")

    print(f"\n🔧 Starting CLI in interactive mode...")
    print("💡 Note: Use '--real' flag to actually create FreeCAD objects!")
    print("💡 Without '--real', commands show workflow analysis only")

    # Create a batch script to execute multiple commands
    batch_script = f"""
# FreeCAD Real Execution Batch
echo "🎯 DEMO: Creating multiple objects with real execution"

echo "📦 Step 1: Creating a box..."
echo "create box 10x20x30 --real"

echo "📦 Step 2: Creating a cylinder..."
echo "create cylinder radius 5 height 15 --real"

echo "📦 Step 3: Creating a sphere..."
echo "create sphere radius 8 --real"

echo "📦 Step 4: Creating a cone..."
echo "create cone radius 6 height 12 --real"

echo "📊 Step 5: Checking state..."
echo "state"

echo "💾 Step 6: Saving info..."
echo "saveinfo"

echo "🖥️ Step 7: Opening in GUI..."
echo "gui"

echo "✅ Demo completed!"
echo "quit"
"""

    # Execute the CLI with the batch commands
    try:
        # Write batch commands to stdin
        process = subprocess.Popen(
            [
                python_path,
                "-m",
                "ai_designer.cli",
                "--llm-provider",
                "google",
                "--llm-api-key",
                api_key,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=project_dir,
        )

        # Send commands
        commands_text = "\n".join(
            [
                "create box 10x20x30 --real",
                "create cylinder radius 5 height 15 --real",
                "create sphere radius 8 --real",
                "state",
                "saveinfo",
                "quit",
            ]
        )

        stdout, stderr = process.communicate(input=commands_text, timeout=60)

        print("📋 Execution Output:")
        print("-" * 30)
        print(stdout)

        if stderr:
            print("⚠️ Errors:")
            print(stderr)

        print("✅ Demo execution completed!")

        # Check for created files
        outputs_dir = f"{project_dir}/outputs"
        if os.path.exists(outputs_dir):
            files = [f for f in os.listdir(outputs_dir) if f.endswith(".FCStd")]
            latest_files = sorted(files)[-3:]  # Get last 3 files

            print(f"\n📁 Created Files:")
            for file in latest_files:
                file_path = os.path.join(outputs_dir, file)
                file_size = os.path.getsize(file_path)
                print(f"  📄 {file} ({file_size} bytes)")

    except subprocess.TimeoutExpired:
        print("⏰ Command timed out")
        process.kill()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

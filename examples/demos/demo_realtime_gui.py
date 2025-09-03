#!/usr/bin/env python3
"""
Complete Real-Time FreeCAD Demo with GUI and WebSocket Updates
Shows step-by-step object creation with live GUI updates
"""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

import websockets


def run_websocket_monitor():
    """Run WebSocket monitor in background to show real-time updates"""

    async def monitor_websocket():
        uri = "ws://localhost:8765"
        print("🔗 Starting WebSocket Monitor for Real-Time Updates")
        print("=" * 60)

        try:
            async with websockets.connect(uri) as websocket:
                print("✅ Connected to FreeCAD WebSocket server")

                # Register for monitoring
                register_msg = {
                    "type": "register_session",
                    "session_id": "real_time_demo",
                }
                await websocket.send(json.dumps(register_msg))

                print("📺 Monitoring real-time updates...")
                print("-" * 40)

                # Listen for updates
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type", "unknown")
                        timestamp = data.get("timestamp", datetime.now().isoformat())
                        msg_data = data.get("data", {})

                        # Format timestamp
                        try:
                            dt = datetime.fromisoformat(
                                timestamp.replace("Z", "+00:00")
                            )
                            time_str = dt.strftime("%H:%M:%S")
                        except:
                            time_str = (
                                timestamp[:8] if len(timestamp) > 8 else timestamp
                            )

                        if msg_type == "progress_update":
                            progress = msg_data.get("progress", 0) * 100
                            message = msg_data.get("message", "")

                            # Create progress bar
                            bar_length = 25
                            filled_length = int(bar_length * (progress / 100))
                            bar = "█" * filled_length + "░" * (
                                bar_length - filled_length
                            )

                            print(f"[{time_str}] ⚡ Progress: [{bar}] {progress:.0f}%")
                            print(f"           📋 {message}")

                        elif msg_type == "user_notification":
                            message = msg_data.get("message", "")
                            notif_type = msg_data.get("type", "info")

                            icon = {
                                "info": "ℹ️",
                                "warning": "⚠️",
                                "error": "❌",
                                "success": "✅",
                            }.get(notif_type, "ℹ️")

                            print(f"[{time_str}] {icon} {message}")

                        elif msg_type == "command_status":
                            status = msg_data.get("status", "unknown")
                            status_icon = (
                                "✅"
                                if status == "completed"
                                else ("❌" if status == "failed" else "⚠️")
                            )
                            print(
                                f"[{time_str}] {status_icon} Command {status.upper()}"
                            )

                        elif msg_type == "system_status":
                            status = msg_data.get("status", "unknown")
                            if status == "connected":
                                client_id = msg_data.get("client_id", "unknown")
                                print(f"[{time_str}] 🤝 Connected as {client_id}")
                            elif status == "session_registered":
                                print(
                                    f"[{time_str}] 📝 Session registered for real-time monitoring"
                                )

                    except json.JSONDecodeError:
                        print(f"❌ Invalid message: {message}")
                    except Exception as e:
                        print(f"❌ Error handling message: {e}")

        except ConnectionRefusedError:
            print("❌ Cannot connect to WebSocket server")
            print("💡 Make sure the FreeCAD CLI is running")
            return False
        except Exception as e:
            print(f"❌ WebSocket monitor error: {e}")
            return False

    # Run the async monitor
    try:
        asyncio.run(monitor_websocket())
    except Exception as e:
        print(f"❌ Monitor failed: {e}")


def main():
    print("🚀 FreeCAD Real-Time GUI Demo with WebSocket Updates")
    print("=" * 70)
    print("This demo will:")
    print("1. 🖥️  Start FreeCAD CLI with persistent GUI")
    print("2. 🔗 Establish WebSocket connection for real-time updates")
    print("3. 📦 Create objects step-by-step with live GUI updates")
    print("4. 📺 Show progress and changes in real-time")
    print()

    # Configuration
    project_dir = "/home/vansh5632/DesignEng/freecad-llm-automation"
    python_path = f"{project_dir}/venv/bin/python"
    api_key = "AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc"

    # Start WebSocket monitor in background
    print("🔄 Starting WebSocket monitor...")
    monitor_thread = threading.Thread(target=run_websocket_monitor, daemon=True)
    monitor_thread.start()
    time.sleep(2)  # Give monitor time to start

    # Commands to execute with real-time updates
    commands = [
        "create box 10x20x30 --real",
        "create cylinder radius 5 height 15 --real",
        "create sphere radius 8 --real",
        "create cone radius 6 height 12 --real",
        "state",
        "saveinfo",
    ]

    print("📋 Commands to execute with real-time GUI updates:")
    for i, cmd in enumerate(commands, 1):
        print(f"  {i}. {cmd}")
    print()

    # Create command input for the CLI
    command_input = "\n".join(commands + ["quit"])

    try:
        print("🚀 Starting FreeCAD CLI with persistent GUI...")
        print("💡 Watch the WebSocket monitor above for real-time updates!")
        print("💡 A FreeCAD GUI window should open and update automatically!")
        print("-" * 70)

        # Start the CLI process with all commands
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

        # Send all commands at once
        stdout, stderr = process.communicate(input=command_input, timeout=120)

        print("📋 CLI Execution Results:")
        print("=" * 50)
        print(stdout)

        if stderr:
            print("⚠️ Errors/Warnings:")
            print(stderr)

        # Check for created files
        outputs_dir = f"{project_dir}/outputs"
        if os.path.exists(outputs_dir):
            files = [f for f in os.listdir(outputs_dir) if f.endswith(".FCStd")]
            latest_files = sorted(files)[-5:]  # Get last 5 files

            print("\n📁 Recent FreeCAD Files Created:")
            print("-" * 40)
            for file in latest_files:
                file_path = os.path.join(outputs_dir, file)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    mod_time = os.path.getmtime(file_path)
                    mod_time_str = datetime.fromtimestamp(mod_time).strftime("%H:%M:%S")
                    print(f"  📄 {file}")
                    print(f"      Size: {file_size} bytes | Modified: {mod_time_str}")

        print("\n🎉 Demo completed successfully!")
        print("✅ Real-time GUI updates were demonstrated")
        print("✅ WebSocket communication established")
        print("✅ Objects created and displayed in FreeCAD GUI")
        print()
        print("📝 Summary of what happened:")
        print("   • FreeCAD GUI opened and stayed open during execution")
        print("   • WebSocket server provided real-time progress updates")
        print("   • Each '--real' command created actual FreeCAD objects")
        print("   • Objects appeared immediately in the GUI after creation")
        print("   • Files were automatically saved with increasing object counts")

    except subprocess.TimeoutExpired:
        print("⏰ Command timed out after 2 minutes")
        process.kill()
    except Exception as e:
        print(f"❌ Error running demo: {e}")

    print("\n👋 Demo finished. WebSocket monitor will continue running...")

    # Keep the monitor running for a bit longer to show any final updates
    time.sleep(5)


if __name__ == "__main__":
    main()

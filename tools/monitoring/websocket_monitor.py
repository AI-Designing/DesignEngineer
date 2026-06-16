#!/usr/bin/env python3
"""
Simple WebSocket Monitor for FreeCAD Real-time Updates
Shows live progress and command execution status
"""

import asyncio
import json
import sys
from datetime import datetime

import websockets


class SimpleWebSocketMonitor:
    def __init__(self):
        self.uri = "ws://localhost:8765"
        self.session_id = "monitor_session"

    async def connect_and_monitor(self):
        """Connect to WebSocket server and monitor updates"""
        print("🔗 FreeCAD Real-time Monitor")
        print("=" * 40)
        print(f"📡 Connecting to: {self.uri}")

        try:
            async with websockets.connect(self.uri) as websocket:
                print("✅ Connected to FreeCAD automation system")

                # Register for session
                register_msg = {
                    "type": "register_session",
                    "session_id": self.session_id,
                }

                await websocket.send(json.dumps(register_msg))
                print(f"📝 Registered for session: {self.session_id}")
                print("-" * 40)
                print("📺 Live Updates:")
                print()

                # Listen for messages
                async for message in websocket:
                    await self.handle_message(message)

        except ConnectionRefusedError:
            print("❌ Cannot connect - is the FreeCAD CLI running?")
            print("💡 Start API: uvicorn ai_designer.api.app:app --port 8000")

        except Exception as e:
            print(f"❌ Connection error: {e}")

    async def handle_message(self, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            timestamp = data.get("timestamp", datetime.now().isoformat())
            msg_data = data.get("data", {})

            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp[:8] if len(timestamp) > 8 else timestamp

            if msg_type == "system_status":
                status = msg_data.get("status", "unknown")
                if status == "connected":
                    client_id = msg_data.get("client_id", "unknown")
                    print(f"[{time_str}] 🤝 Connected as {client_id}")
                elif status == "session_registered":
                    print(f"[{time_str}] 📝 Session registered successfully")
                elif status != "pong":
                    active_conn = msg_data.get("active_connections", 0)
                    print(f"[{time_str}] 📊 Active connections: {active_conn}")

            elif msg_type == "progress_update":
                command_id = msg_data.get("command_id", "unknown")[:8]
                progress = msg_data.get("progress", 0) * 100
                status = msg_data.get("status", "unknown")
                message = msg_data.get("message", "")

                # Create progress bar
                bar_length = 20
                filled_length = int(bar_length * (progress / 100))
                bar = "█" * filled_length + "░" * (bar_length - filled_length)

                print(f"[{time_str}] ⚡ Progress: [{bar}] {progress:.0f}%")
                print(f"           📋 {message}")
                if progress >= 100:
                    print()

            elif msg_type == "command_status":
                command_id = msg_data.get("command_id", "unknown")[:8]
                status = msg_data.get("status", "unknown")

                status_icon = (
                    "✅"
                    if status == "completed"
                    else ("❌" if status == "failed" else "⚠️")
                )
                print(f"[{time_str}] {status_icon} Command {status.upper()}")
                print()

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

            elif msg_type == "state_change":
                state = msg_data.get("state", {})
                object_count = state.get("object_count", 0)
                print(f"[{time_str}] 🔄 Document updated - Objects: {object_count}")

            elif msg_type == "error":
                error = msg_data.get("error", "Unknown error")
                print(f"[{time_str}] ❌ Error: {error}")

        except json.JSONDecodeError:
            print(f"❌ Invalid message: {message}")
        except Exception as e:
            print(f"❌ Error handling message: {e}")


async def main():
    """Main function"""
    monitor = SimpleWebSocketMonitor()

    while True:
        try:
            await monitor.connect_and_monitor()
            print("\n🔄 Connection lost, retrying in 5 seconds...")
            await asyncio.sleep(5)

        except KeyboardInterrupt:
            print("\n👋 Monitor stopped by user")
            break

        except Exception as e:
            print(f"\n💥 Unexpected error: {e}")
            print("🔄 Retrying in 10 seconds...")
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)

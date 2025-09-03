"""
WebSocket Client for Testing Real-time Features
Connects to the FreeCAD automation system and displays live updates
"""

import asyncio
import json
from datetime import datetime

import websockets


async def websocket_client():
    """
    Connect to the WebSocket server and display real-time updates
    """
    uri = "ws://localhost:8765"

    print("🌐 Connecting to FreeCAD Automation WebSocket...")
    print(f"📡 URI: {uri}")
    print("=" * 50)

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")

            # Register for a session
            session_id = "demo_session"
            register_msg = {"type": "register_session", "session_id": session_id}

            await websocket.send(json.dumps(register_msg))
            print(f"📝 Registered for session: {session_id}")
            print("-" * 50)
            print("📺 Live Updates:")
            print()

            # Listen for messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await handle_message(data)

                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON received: {message}")

                except Exception as e:
                    print(f"❌ Error handling message: {e}")

    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused - is the server running?")
        print("💡 Start the server with: python enhanced_main.py")

    except Exception as e:
        print(f"❌ Connection error: {e}")


async def handle_message(data: dict):
    """Handle incoming WebSocket message"""
    msg_type = data.get("type", "unknown")
    timestamp = data.get("timestamp", datetime.now().isoformat())
    msg_data = data.get("data", {})

    # Format timestamp
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M:%S")
    except:
        time_str = timestamp

    if msg_type == "system_status":
        status = msg_data.get("status", "unknown")
        if status == "connected":
            client_id = msg_data.get("client_id", "unknown")
            print(f"[{time_str}] 🤝 Connected as {client_id}")

        elif status == "session_registered":
            session_id = msg_data.get("session_id", "unknown")
            print(f"[{time_str}] 📝 Session registered: {session_id}")

        elif status == "pong":
            print(f"[{time_str}] 💓 Pong received")

        else:
            active_conn = msg_data.get("active_connections", 0)
            messages_sent = msg_data.get("messages_sent", 0)
            print(
                f"[{time_str}] 📊 System status - Connections: {active_conn}, Messages: {messages_sent}"
            )

    elif msg_type == "progress_update":
        command_id = msg_data.get("command_id", "unknown")[:8]
        progress = msg_data.get("progress", 0) * 100
        status = msg_data.get("status", "unknown")
        message = msg_data.get("message", "")
        estimated_remaining = msg_data.get("estimated_remaining")

        progress_bar = create_progress_bar(progress / 100)

        print(f"[{time_str}] ⚡ Command {command_id} - {status}")
        print(f"              {progress_bar} {progress:.1f}%")
        if message:
            print(f"              📝 {message}")
        if estimated_remaining:
            print(f"              ⏱️ ETA: {estimated_remaining}s")
        print()

    elif msg_type == "command_status":
        command_id = msg_data.get("command_id", "unknown")[:8]
        status = msg_data.get("status", "unknown")
        result = msg_data.get("result", {})

        status_icon = (
            "✅" if status == "completed" else ("❌" if status == "failed" else "⚠️")
        )

        print(f"[{time_str}] {status_icon} Command {command_id} - {status}")
        if result:
            print(f"              📋 Result: {str(result)[:100]}...")
        print()

    elif msg_type == "state_change":
        state = msg_data.get("state", {})
        checkpoint = state.get("checkpoint", False)
        object_count = state.get("object_count", 0)

        if checkpoint:
            print(f"[{time_str}] 📊 State checkpoint - Objects: {object_count}")
        else:
            print(f"[{time_str}] 🔄 State changed - Objects: {object_count}")
        print()

    elif msg_type == "error":
        error = msg_data.get("error", "Unknown error")
        details = msg_data.get("details", {})

        print(f"[{time_str}] ❌ Error: {error}")
        if details:
            print(f"              📋 Details: {details}")
        print()

    elif msg_type == "user_notification":
        message = msg_data.get("message", "")
        notif_type = msg_data.get("type", "info")

        icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}.get(
            notif_type, "ℹ️"
        )

        print(f"[{time_str}] {icon} {message}")
        print()

    else:
        print(f"[{time_str}] 📨 Unknown message type: {msg_type}")
        print(f"              📋 Data: {msg_data}")
        print()


def create_progress_bar(progress: float, width: int = 20) -> str:
    """Create a visual progress bar"""
    filled = int(progress * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"


async def main():
    """Main function"""
    print("🎮 FreeCAD WebSocket Client")
    print("🔗 Real-time updates viewer")
    print()

    while True:
        try:
            await websocket_client()
            print("\n🔄 Connection lost, retrying in 5 seconds...")
            await asyncio.sleep(5)

        except KeyboardInterrupt:
            print("\n👋 Client stopped by user")
            break

        except Exception as e:
            print(f"\n💥 Unexpected error: {e}")
            print("🔄 Retrying in 10 seconds...")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())

"""
Display / output module for the FreeCAD CLI.

Extracted from the monolithic cli.py.  All functions here are pure display
helpers — they accept state as arguments and print to stdout.  None of these
functions have side-effects beyond printing.
"""

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Workflow results
# ---------------------------------------------------------------------------


def display_workflow_results(result: Dict[str, Any], original_command: str) -> None:
    """Print the outcome of a multi-step workflow execution.

    Args:
        result: Dict returned by ``CommandExecutor`` or the workflow orchestrator.
        original_command: The original natural-language command for context.
    """
    status = result.get("status", "unknown")
    message = result.get("message", "")
    steps = result.get("steps", [])

    print(f"\n📋 Workflow Results for: '{original_command[:60]}'")
    print("=" * 60)
    print(f"Status: {'✅' if status == 'success' else '❌'} {status.upper()}")
    if message:
        print(f"Message: {message}")

    if steps:
        print(f"\nSteps executed ({len(steps)}):")
        for i, step in enumerate(steps, 1):
            step_status = step.get("status", "?")
            step_msg = step.get("message", step.get("command", ""))
            icon = (
                "✅"
                if step_status == "success"
                else "⚠️"
                if step_status == "warning"
                else "❌"
            )
            print(f"  {icon} Step {i}: {step_msg[:70]}")


# ---------------------------------------------------------------------------
# State display
# ---------------------------------------------------------------------------


def show_state(state: Dict[str, Any]) -> None:
    """Print a human-readable summary of the current FreeCAD document state.

    Args:
        state: State dict from ``CommandExecutor.get_state()``.
    """
    print("\nCurrent FreeCAD State:")
    print(f"Document: {state.get('active_document', 'None')}")
    print(f"Objects: {state.get('object_count', 0)}")
    for obj in state.get("objects", []):
        print(f"  - {obj['name']} ({obj['type']})")


# ---------------------------------------------------------------------------
# WebSocket / GUI status
# ---------------------------------------------------------------------------


def show_websocket_status(
    enable_websocket: bool,
    websocket_manager: Any,
    session_id: str,
) -> None:
    """Print WebSocket server status.

    Args:
        enable_websocket: Whether the WS feature is enabled.
        websocket_manager: ``WebSocketManager`` instance (may be ``None``).
        session_id: Current session identifier.
    """
    print("\n🌐 WebSocket Server Status:")
    print("=" * 40)

    if not enable_websocket or not websocket_manager:
        print("❌ WebSocket server is disabled")
        return

    stats = websocket_manager.get_stats()
    print(f"Status: {'🟢 Running' if stats['running'] else '🔴 Stopped'}")
    print(f"Active connections: {stats['active_connections']}")
    print(f"Total connections: {stats['total_connections']}")
    print(f"Messages sent: {stats['messages_sent']}")
    print(f"Messages received: {stats['messages_received']}")
    print(f"Session count: {stats['session_count']}")

    if stats.get("uptime_seconds"):
        uptime_s = stats["uptime_seconds"]
        uptime_str = f"{uptime_s/60:.1f}m" if uptime_s > 60 else f"{uptime_s:.1f}s"
        print(f"Uptime: {uptime_str}")

    print(f"🔗 Connection URL: ws://localhost:8765")
    print(f"📱 Session ID: {session_id}")


def show_persistent_gui_status(
    enable_persistent_gui: bool,
    persistent_gui: Any,
) -> None:
    """Print persistent GUI status.

    Args:
        enable_persistent_gui: Whether the feature is enabled.
        persistent_gui: ``PersistentFreeCADGUI`` instance (may be ``None``).
    """
    print("\n🖥️  Persistent GUI Status:")
    print("=" * 40)

    if not enable_persistent_gui or not persistent_gui:
        print("❌ Persistent GUI is disabled")
        return

    status = persistent_gui.get_status()
    print(f"Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
    if status.get("pid"):
        print(f"Process ID: {status['pid']}")
    print(f"Communication port: {status['communication_port']}")
    print(f"Session ID: {status['session_id']}")

    if status["running"]:
        print("✅ GUI is ready for real-time updates")
        print("💡 Use '--real' flag with commands to see live updates")
    else:
        print("⚠️  GUI is not running - try restarting with 'restart-gui'")


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

HELP_TEXT = """\
🚀 FreeCAD LLM CLI - Unified LLM System with Auto-Provider Selection

🧠 LLM Provider Management:
  llm-status          Show current LLM provider status
  switch-provider     Switch to deepseek | google | auto

🎯 Command Execution:
  create <desc>       Natural language shape creation
  unified <desc>      Use unified LLM manager
  deepseek <desc>     DeepSeek R1 reasoning (complex parts)
  script <path>       Execute a Python script file
  complex <desc>      Multi-step complex shape workflow

📊 State & Information:
  state               Show current document state
  analyze [file]      Comprehensive state analysis
  history             Show command history
  fileinfo            Show file paths
  saveinfo            Show save information
  websocket / ws      WebSocket server status
  persistent-gui      Persistent GUI status

🔧 GUI Control:
  restart-gui         Restart persistent FreeCAD GUI
  stop-gui            Stop persistent GUI

⚡ Other:
  help                Show this message
  quit / exit         Exit the CLI
"""


def show_help() -> None:
    """Print the CLI help message."""
    print(HELP_TEXT)

"""
Session state management for the FreeCAD CLI.

Extracted from the monolithic cli.py to separate session-tracking concerns
(command history, context, session metadata) from the main CLI orchestration logic.
"""

import time
from typing import Any, Dict, List, Optional


class SessionManager:
    """Manages per-session state: history, context, and metadata.

    This class owns all mutable session data that does not depend on FreeCAD
    or LLM connections, keeping the main CLI class focused on orchestration.
    """

    def __init__(self) -> None:
        self.session_id: str = f"cli_session_{int(time.time())}"
        self.command_history: List[str] = []
        self.context: Dict[str, Any] = {}
        self.current_doc_path: Optional[str] = None
        self.metadata: Dict[str, Any] = {
            "started_at": time.time(),
            "commands_executed": 0,
            "commands_succeeded": 0,
        }

    def record_command(self, command: str, success: bool = True) -> None:
        """Add *command* to history and update metadata counts."""
        self.command_history.append(command)
        self.metadata["commands_executed"] += 1
        if success:
            self.metadata["commands_succeeded"] += 1

    def show_history(self, limit: int = 10) -> None:
        """Print the last *limit* executed commands."""
        history = self.command_history[-limit:]
        print(f"\nCommand History ({len(self.command_history)} total, showing last {len(history)}):")
        for i, cmd in enumerate(history, 1):
            print(f"{i:2d}. {cmd[:80]}{'...' if len(cmd) > 80 else ''}")

    def set_context(self, key: str, value: Any) -> None:
        """Store an arbitrary context value under *key*."""
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a context value."""
        return self.context.get(key, default)

    def get_summary(self) -> Dict[str, Any]:
        """Return a snapshot of session metadata."""
        elapsed = time.time() - self.metadata["started_at"]
        return {
            "session_id": self.session_id,
            "elapsed_seconds": elapsed,
            "commands_executed": self.metadata["commands_executed"],
            "commands_succeeded": self.metadata["commands_succeeded"],
            "current_doc_path": self.current_doc_path,
        }

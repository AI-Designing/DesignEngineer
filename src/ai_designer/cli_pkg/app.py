"""
FreeCADCLIApp — the trimmed application class for the FreeCAD LLM CLI.

This file contains only lifecycle concerns:
  __init__, initialize(), interactive_mode(), cleanup(), _start_websocket_server()

All command execution is delegated to CommandRunner (commands.py).
All display output is delegated to display.py.
Session management is delegated to SessionManager (session.py).
"""

import asyncio
import os
import sys
import threading
import time
from typing import Any, Dict, Optional

from .commands import CommandRunner
from .display import (
    show_help,
    show_persistent_gui_status,
    show_state,
    show_websocket_status,
)
from .session import SessionManager

try:
    from ai_designer.freecad.api_client import FreeCADAPIClient
    from ai_designer.freecad.command_executor import CommandExecutor
    from ai_designer.freecad.persistent_gui_client import PersistentFreeCADGUI
    from ai_designer.freecad.state_manager import FreeCADStateAnalyzer
    from ai_designer.llm.deepseek_client import DeepSeekR1Client
    from ai_designer.llm.unified_manager import LLMProvider, UnifiedLLMManager
    from ai_designer.realtime.websocket_manager import ProgressTracker, WebSocketManager
    from ai_designer.redis_utils.client import RedisClient
    from ai_designer.redis_utils.state_cache import StateCache
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    sys.path.insert(0, parent_dir)
    from ai_designer.freecad.api_client import FreeCADAPIClient
    from ai_designer.freecad.command_executor import CommandExecutor
    from ai_designer.freecad.persistent_gui_client import PersistentFreeCADGUI
    from ai_designer.freecad.state_manager import FreeCADStateAnalyzer
    from ai_designer.llm.deepseek_client import DeepSeekR1Client
    from ai_designer.llm.unified_manager import LLMProvider, UnifiedLLMManager
    from ai_designer.realtime.websocket_manager import ProgressTracker, WebSocketManager
    from ai_designer.redis_utils.client import RedisClient
    from ai_designer.redis_utils.state_cache import StateCache


class FreeCADCLIApp:
    """
    Trimmed application class — owns only lifecycle + state.

    Runtime commands are delegated to ``CommandRunner``.
    """

    def __init__(
        self,
        use_headless: bool = True,
        llm_provider: str = "auto",
        llm_api_key: Optional[str] = None,
        auto_open_gui: bool = True,
        enable_websocket: bool = True,
        enable_persistent_gui: bool = True,
        deepseek_enabled: bool = False,
        deepseek_mode: str = "reasoning",
        deepseek_port: int = 11434,
    ) -> None:
        self.api_client = FreeCADAPIClient(use_headless=use_headless)
        self.command_executor: Optional[Any] = None
        self.state_cache: Optional[Any] = None
        self.state_analyzer: Optional[Any] = None

        # LLM configuration
        self.llm_provider_name = llm_provider
        self.llm_api_key = llm_api_key
        self.auto_open_gui = auto_open_gui
        self.unified_llm_manager: Optional[UnifiedLLMManager] = None

        # Legacy DeepSeek
        self.deepseek_enabled = deepseek_enabled
        self.deepseek_mode = deepseek_mode
        self.deepseek_port = deepseek_port
        self.deepseek_client: Optional[DeepSeekR1Client] = None

        # Real-time / GUI
        self.enable_websocket = enable_websocket
        self.enable_persistent_gui = enable_persistent_gui
        self.websocket_manager: Optional[WebSocketManager] = None
        self.progress_tracker: Optional[ProgressTracker] = None
        self.persistent_gui: Optional[PersistentFreeCADGUI] = None
        self.websocket_thread: Optional[threading.Thread] = None

        # Session
        self.session = SessionManager()

        # Redis
        try:
            redis_client = RedisClient()
            if redis_client.connect():
                self.state_cache = StateCache(redis_client)
                print("✓ Redis connection established for state caching")
        except Exception as e:
            print(f"Warning: Redis not available: {e}")

        # WebSocket
        if self.enable_websocket:
            try:
                self.websocket_manager = WebSocketManager()
                self.progress_tracker = ProgressTracker(self.websocket_manager)
                print("✓ WebSocket manager initialized")
            except Exception as e:
                print(f"Warning: WebSocket not available: {e}")
                self.enable_websocket = False

        # Persistent GUI
        if self.enable_persistent_gui:
            try:
                self.persistent_gui = PersistentFreeCADGUI(self.websocket_manager)
                print("✓ Persistent GUI client initialized")
            except Exception as e:
                print(f"Warning: Persistent GUI not available: {e}")
                self.enable_persistent_gui = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """Initialize FreeCAD connection, LLM managers, and optional services."""
        print("Initializing FreeCAD CLI...")

        # Unified LLM Manager
        print("🧠 Initializing Unified LLM Manager...")
        try:
            llm_config = {
                "google_api_key": self.llm_api_key or os.getenv("GOOGLE_API_KEY"),
                "deepseek_host": "localhost",
                "deepseek_port": self.deepseek_port,
                "deepseek_model": "deepseek-r1:14b",
                "deepseek_timeout": 300,
                "gemini_model": "gemini-1.5-flash",
            }
            self.unified_llm_manager = UnifiedLLMManager(config=llm_config)

            if self.deepseek_enabled:
                self.unified_llm_manager.set_active_provider(LLMProvider.DEEPSEEK_R1)
            elif self.llm_provider_name == "google":
                self.unified_llm_manager.set_active_provider(LLMProvider.GOOGLE_GEMINI)
            else:
                self.unified_llm_manager.set_active_provider(LLMProvider.AUTO)

            print("✅ Unified LLM Manager ready")
            status = self.unified_llm_manager.get_provider_status()
            for provider, info in status["providers"].items():
                icon = "✅" if info["available"] else "❌"
                print(
                    f"   {icon} {provider}: {'Available' if info['available'] else 'Unavailable'}"
                )

        except Exception as e:
            print(f"⚠️  Unified LLM Manager initialization failed: {e}")
            self.unified_llm_manager = None

        # Legacy DeepSeek
        if self.deepseek_enabled:
            try:
                from ai_designer.llm.deepseek_client import DeepSeekConfig

                config = DeepSeekConfig(
                    host="localhost", port=self.deepseek_port, timeout=300
                )
                self.deepseek_client = DeepSeekR1Client(config=config)
                print("✅ Legacy DeepSeek R1 client ready")
            except Exception as e:
                print(f"⚠️  Legacy DeepSeek R1 initialization failed: {e}")
                self.deepseek_enabled = False

        # WebSocket server
        if self.enable_websocket and self.websocket_manager:
            self._start_websocket_server()

        if not self.api_client.connect():
            print("✗ Failed to connect to FreeCAD")
            return False

        print("✓ FreeCAD connection established")

        # Persistent GUI
        if self.enable_persistent_gui and self.persistent_gui:
            if self.persistent_gui.start_persistent_gui():
                print("✅ Persistent GUI ready for real-time updates")
                if self.websocket_manager:
                    self.websocket_manager.send_user_notification(
                        "FreeCAD CLI initialized with persistent GUI and WebSocket server",
                        "success",
                        self.session.session_id,
                    )
            else:
                print(
                    "⚠️  Persistent GUI failed to start, falling back to standard mode"
                )
                self.enable_persistent_gui = False

        # CommandExecutor
        self.command_executor = CommandExecutor(
            self.api_client,
            self.state_cache,
            llm_provider=self.llm_provider_name,
            llm_api_key=self.llm_api_key,
            auto_open_gui=self.auto_open_gui,
            persistent_gui=(
                self.persistent_gui if self.enable_persistent_gui else None
            ),
        )
        self.state_analyzer = FreeCADStateAnalyzer(self.api_client)

        return True

    def cleanup(self) -> None:
        """Release resources on shutdown."""
        print("🧹 Cleaning up resources...")

        if self.enable_persistent_gui and self.persistent_gui:
            if self.persistent_gui.is_gui_running():
                print("🛑 Stopping persistent GUI...")
                self.persistent_gui.stop_gui()

        if self.enable_websocket and self.websocket_manager:
            if self.websocket_manager.running:
                print("🛑 Stopping WebSocket server...")
                try:
                    if self.websocket_thread and self.websocket_thread.is_alive():
                        asyncio.run_coroutine_threadsafe(
                            self.websocket_manager.stop_server(),
                            asyncio.get_event_loop(),
                        )
                except Exception:
                    pass

        print("✅ Cleanup completed")

    def _start_websocket_server(self) -> None:
        """Start the WebSocket server in a daemon thread."""

        def _run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.websocket_manager.start_server())
                loop.run_forever()
            except Exception as e:
                print(f"❌ WebSocket server error: {e}")
            finally:
                loop.close()

        self.websocket_thread = threading.Thread(target=_run, daemon=True)
        self.websocket_thread.start()
        time.sleep(1)
        print("✅ WebSocket server started on ws://localhost:8765")

    # ------------------------------------------------------------------
    # Interactive mode
    # ------------------------------------------------------------------

    def interactive_mode(self) -> None:
        """Enter the read-eval-print loop."""
        if not self.initialize():
            return

        runner = self._make_runner()

        print("\nFreeCAD Interactive Mode")
        print("Type 'help' for commands, 'quit' to exit")
        print("=" * 50)

        while True:
            try:
                user_input = input("FreeCAD> ").strip()
                if not user_input:
                    continue

                cmd_lower = user_input.lower()

                if cmd_lower in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break

                elif cmd_lower == "help":
                    show_help()

                elif cmd_lower == "state":
                    if self.command_executor:
                        show_state(self.command_executor.get_state())

                elif cmd_lower in ("llm-status", "llm", "providers"):
                    self._show_llm_status()

                elif cmd_lower.startswith(("switch-provider ", "provider ")):
                    provider = user_input.split(" ", 1)[1].strip()
                    self._switch_llm_provider(provider)

                elif cmd_lower.startswith("unified "):
                    body = user_input[8:].strip()
                    if " --mode " in body:
                        parts = body.split(" --mode ")
                        runner.execute_unified_command(
                            parts[0].strip(), parts[1].strip()
                        )
                    else:
                        runner.execute_unified_command(body)

                elif cmd_lower == "analyze":
                    runner.analyze_state()

                elif cmd_lower.startswith("analyze "):
                    runner.analyze_state(user_input[8:].strip())

                elif cmd_lower == "history":
                    self.session.show_history()

                elif cmd_lower.startswith("script "):
                    runner.execute_script(user_input[7:].strip())

                elif cmd_lower in ("fileinfo", "files", "location"):
                    self._show_file_info()

                elif cmd_lower in ("saveinfo", "saves", "autosave"):
                    self._show_save_info()

                elif cmd_lower.startswith("save "):
                    fn = user_input[5:].strip()
                    (
                        self.command_executor.manual_save(fn)
                        if fn
                        else self.command_executor.manual_save()
                    )

                elif cmd_lower in ("gui", "open", "view"):
                    result = self.command_executor.open_current_in_gui()
                    if result.get("status") == "success":
                        print("✅ Document opened in FreeCAD GUI")
                    else:
                        print(
                            f"❌ Failed to open in GUI: {result.get('message', 'Unknown error')}"
                        )

                elif cmd_lower in ("gui-on", "auto-gui-on"):
                    self.command_executor.set_auto_open_gui(True)

                elif cmd_lower in ("gui-off", "auto-gui-off"):
                    self.command_executor.set_auto_open_gui(False)

                elif cmd_lower in ("websocket", "ws", "realtime"):
                    show_websocket_status(
                        self.enable_websocket,
                        self.websocket_manager,
                        self.session.session_id,
                    )

                elif cmd_lower in ("persistent-gui", "pgui", "gui-status"):
                    show_persistent_gui_status(
                        self.enable_persistent_gui, self.persistent_gui
                    )

                elif cmd_lower in ("start-websocket", "ws-start"):
                    if self.enable_websocket and self.websocket_manager:
                        if not self.websocket_manager.running:
                            self._start_websocket_server()
                        else:
                            print("⚠️  WebSocket server is already running")
                    else:
                        print("❌ WebSocket server is not available")

                elif cmd_lower in ("stop-gui", "gui-stop"):
                    if self.enable_persistent_gui and self.persistent_gui:
                        if self.persistent_gui.is_gui_running():
                            self.persistent_gui.stop_gui()
                        else:
                            print("⚠️  Persistent GUI is not running")
                    else:
                        print("❌ Persistent GUI is not available")

                elif cmd_lower in ("restart-gui", "gui-restart"):
                    if self.enable_persistent_gui and self.persistent_gui:
                        print("🔄 Restarting persistent GUI...")
                        if self.persistent_gui.is_gui_running():
                            self.persistent_gui.stop_gui()
                            time.sleep(2)
                        if self.persistent_gui.start_persistent_gui():
                            print("✅ Persistent GUI restarted successfully")
                        else:
                            print("❌ Failed to restart persistent GUI")
                    else:
                        print("❌ Persistent GUI is not available")

                elif cmd_lower.startswith("deepseek "):
                    deepseek_cmd = user_input[9:].strip()
                    if self.deepseek_enabled:
                        runner.execute_deepseek_command(deepseek_cmd)
                    else:
                        print(
                            "❌ DeepSeek R1 is not enabled. Use --deepseek-enabled flag."
                        )

                elif self.deepseek_enabled and any(
                    kw in cmd_lower
                    for kw in (
                        "gear",
                        "complex",
                        "bracket",
                        "assembly",
                        "housing",
                        "detailed",
                    )
                ):
                    print(
                        f"🧠 Complex command detected - using DeepSeek R1: {user_input}"
                    )
                    runner.execute_deepseek_command(user_input)

                else:
                    self.session.record_command(user_input)
                    runner.execute_command(user_input)

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break

        self.cleanup()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _make_runner(self) -> CommandRunner:
        """Construct a CommandRunner from this app's current state."""
        return CommandRunner(
            command_executor=self.command_executor,
            api_client=self.api_client,
            state_analyzer=self.state_analyzer,
            state_cache=self.state_cache,
            unified_llm_manager=self.unified_llm_manager,
            deepseek_client=self.deepseek_client,
            persistent_gui=self.persistent_gui,
            websocket_manager=self.websocket_manager,
            progress_tracker=self.progress_tracker,
            enable_persistent_gui=self.enable_persistent_gui,
            deepseek_enabled=self.deepseek_enabled,
            session_id=self.session.session_id,
        )

    def _switch_llm_provider(self, provider_name: str) -> bool:
        if not self.unified_llm_manager:
            print("❌ Unified LLM Manager not initialized")
            return False
        mapping = {
            "auto": LLMProvider.AUTO,
            "deepseek": LLMProvider.DEEPSEEK_R1,
            "google": LLMProvider.GOOGLE_GEMINI,
        }
        provider = mapping.get(provider_name.lower())
        if not provider:
            print(f"❌ Unknown provider: {provider_name}")
            return False
        ok = self.unified_llm_manager.set_active_provider(provider)
        if ok:
            print(f"✅ Switched to LLM provider: {provider_name}")
        else:
            print(f"❌ Failed to switch to provider: {provider_name}")
        return ok

    def _show_llm_status(self) -> None:
        if not self.unified_llm_manager:
            print("❌ Unified LLM Manager not initialized")
            return
        print("\n🧠 LLM Provider Status")
        print("=" * 50)
        status = self.unified_llm_manager.get_provider_status()
        print(f"Active Provider: {status['active_provider']}")
        print("\nAvailable Providers:")
        for provider, info in status["providers"].items():
            icon = "✅" if info["available"] else "❌"
            type_info = f"({info['type']})" if info.get("type") else ""
            print(f"  {icon} {provider} {type_info}")
            if not info["available"] and info.get("error"):
                print(f"      Error: {info['error']}")

        perf = self.unified_llm_manager.get_performance_summary()
        if perf["total_generations"] > 0:
            print(
                f"\nPerformance Summary (last {perf['total_generations']} generations):"
            )
            for prov, usage in perf["provider_usage"].items():
                if usage > 0:
                    success_rate = perf["success_rates"][prov] * 100
                    avg_time = perf["average_times"][prov]
                    print(
                        f"  {prov}: {usage} requests, {success_rate:.1f}% success, {avg_time:.1f}s avg"
                    )

    def _show_file_info(self) -> None:
        print("\nFile Location Information:")
        print("=" * 30)
        try:
            result = self.api_client.get_file_info()
            if result["status"] == "success":
                for line in result["message"].split("\n"):
                    if line.startswith("CURRENT_DIR: "):
                        print(f"Working Directory: {line.replace('CURRENT_DIR: ', '')}")
                    elif line.startswith("HOME_DIR: "):
                        print(f"Home Directory: {line.replace('HOME_DIR: ', '')}")
                    elif line.startswith("DOCUMENT_NAME: "):
                        print(f"Document Name: {line.replace('DOCUMENT_NAME: ', '')}")
                    elif line.startswith("DOCUMENT_PATH: "):
                        path = line.replace("DOCUMENT_PATH: ", "")
                        if path == "Not saved yet":
                            print(f"Document Status: {path}")
                        else:
                            print(f"Document Path: {path}")
            else:
                print(f"Error getting file info: {result['message']}")
        except Exception as e:
            print(f"Error: {e}")

    def _show_save_info(self) -> None:
        if not self.command_executor:
            print("❌ Command executor not initialized")
            return
        import datetime

        save_info = self.command_executor.get_save_info()
        print("\n💾 File Save Information:")
        print("=" * 40)
        print(
            f"Auto-save enabled: {'✅ Yes' if save_info['auto_save_enabled'] else '❌ No'}"
        )
        print(f"Save counter: {save_info['save_counter']}")
        if save_info["last_saved_path"]:
            print(f"Last saved to: {save_info['last_saved_path']}")
            if os.path.exists(save_info["last_saved_path"]):
                import os as _os

                file_size = _os.path.getsize(save_info["last_saved_path"])
                mod_time = datetime.datetime.fromtimestamp(
                    _os.path.getmtime(save_info["last_saved_path"])
                ).strftime("%Y-%m-%d %H:%M:%S")
                print(f"File size: {file_size} bytes")
                print(f"Last modified: {mod_time}")
            else:
                print("⚠️  File no longer exists at saved location")
        else:
            print("No files saved yet")

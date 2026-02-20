"""
Command-execution module for the FreeCAD CLI.

Extracted from the monolithic cli.py.  ``CommandRunner`` encapsulates all
command-dispatching logic that was previously methods on ``FreeCADCLI``.
"""

import asyncio
import datetime
import os
import time
import traceback
from typing import Any, Dict, List, Optional


class CommandRunner:
    """Handles dispatching CLI text commands to the appropriate back-end."""

    def __init__(
        self,
        command_executor: Any,
        api_client: Any,
        state_analyzer: Any,
        state_cache: Any,
        unified_llm_manager: Any,
        deepseek_client: Any,
        persistent_gui: Any,
        websocket_manager: Any,
        progress_tracker: Any,
        enable_persistent_gui: bool,
        deepseek_enabled: bool,
        session_id: str,
    ) -> None:
        self.command_executor = command_executor
        self.api_client = api_client
        self.state_analyzer = state_analyzer
        self.state_cache = state_cache
        self.unified_llm_manager = unified_llm_manager
        self.deepseek_client = deepseek_client
        self.persistent_gui = persistent_gui
        self.websocket_manager = websocket_manager
        self.progress_tracker = progress_tracker
        self.enable_persistent_gui = enable_persistent_gui
        self.deepseek_enabled = deepseek_enabled
        self.session_id = session_id

    # ------------------------------------------------------------------
    # Public command methods
    # ------------------------------------------------------------------

    def execute_command(self, command: str) -> None:
        """Execute a natural-language FreeCAD command with Phase 2/3 workflows."""
        command_id = f"cmd_{int(time.time() * 1000)}"

        try:
            print(f"🧠 Processing with Phase 2 & 3 workflows: {command}")

            if self.progress_tracker:
                self.progress_tracker.start_tracking(command_id, 5, self.session_id)

            if "--real" in command:
                self._execute_real(command, command_id)
            elif (
                hasattr(self.command_executor, "state_aware_processor")
                and self.command_executor.state_aware_processor
            ):
                self._execute_state_aware(command, command_id)
            else:
                self._execute_basic(command, command_id)

        except Exception as e:
            print(f"✗ Exception: {e}")
            if self.progress_tracker:
                self.progress_tracker.fail_tracking(command_id, str(e))
            traceback.print_exc()

    def execute_script(self, script_path: str) -> None:
        """Execute a FreeCAD Python script file."""
        if not os.path.exists(script_path):
            print(f"✗ Script file not found: {script_path}")
            return
        try:
            result = self.api_client.execute_script_file(script_path)
            if result["status"] == "success":
                print(f"✓ Script executed: {script_path}")
                print(result["message"])
            else:
                print(f"✗ Script failed: {result['message']}")
        except Exception as e:
            print(f"✗ Exception executing script: {e}")

    def execute_complex_shape(self, description: str) -> List[Dict]:
        """Execute a multi-step complex shape creation."""
        print(f"🔄 Creating complex shape: {description}")

        complex_prompts = {
            "cone and cylinder": [
                "create a cylinder with radius 5 and height 10",
                "create a cone with radius 3 and height 8 positioned on top of the cylinder",
                "fuse the cylinder and cone together",
            ],
            "tower": [
                "create a cylinder base with radius 8 and height 5",
                "create a smaller cylinder with radius 6 and height 10 on top",
                "create a cone roof with radius 6 and height 6 on top",
                "fuse all parts together",
            ],
            "rocket": [
                "create a cylinder body with radius 4 and height 20",
                "create a cone nose with radius 4 and height 8 on top",
                "create 4 small cylinders as fins with radius 1 and height 6",
                "position fins around the base",
                "fuse body and nose together",
            ],
            "complex structure": [
                "create a box base 20x20x5",
                "create a cylinder pillar radius 3 height 15 at each corner",
                "create a cone roof radius 8 height 5 in the center",
                "fuse all components together",
            ],
        }

        desc_lower = description.lower()
        if "cone" in desc_lower and "cylinder" in desc_lower:
            commands = complex_prompts["cone and cylinder"]
        elif "tower" in desc_lower:
            commands = complex_prompts["tower"]
        elif "rocket" in desc_lower:
            commands = complex_prompts["rocket"]
        elif "complex" in desc_lower or "structure" in desc_lower:
            commands = complex_prompts["complex structure"]
        else:
            commands = [f"create a complex shape: {description}"]

        results = []
        for i, cmd in enumerate(commands, 1):
            print(f"  Step {i}/{len(commands)}: {cmd}")
            try:
                if cmd.startswith("!"):
                    result = self.command_executor.execute(cmd[1:])
                else:
                    result = self.command_executor.execute_natural_language(cmd)

                if result["status"] == "success":
                    print(f"    ✓ {result['message']}")
                    results.append(result)
                else:
                    print(f"    ✗ Error: {result['message']}")
            except Exception as e:
                print(f"    ✗ Exception: {e}")

        print(
            f"✅ Complex shape creation completed with {len(results)} successful operations"
        )
        return results

    def execute_deepseek_command(self, command: str) -> None:
        """Execute command using the DeepSeek R1 reasoning model."""
        if not self.deepseek_enabled or not self.deepseek_client:
            print("❌ DeepSeek R1 is not enabled or not initialized")
            print("🔄 Falling back to standard processing...")
            return self.execute_command(command)

        command_id = f"deepseek_cmd_{int(time.time() * 1000)}"
        self._use_direct_deepseek_api(command, "reasoning", command_id)

    def analyze_state(self, doc_path: Optional[str] = None) -> None:
        """Run comprehensive FreeCAD state analysis."""
        if not self.state_analyzer:
            print("✗ State analyzer not available")
            return

        print("🔄 Analyzing FreeCAD document state...")
        try:
            analysis = self.state_analyzer.analyze_document_state(doc_path)
            self.state_analyzer.print_analysis_results(analysis)

            if self.state_cache and "analysis" in analysis:
                self.state_cache.cache_state(analysis, "last_analysis")
                print("\n💾 Analysis results cached")
        except Exception as e:
            print(f"✗ Analysis failed: {e}")

    def execute_unified_command(self, command: str, mode: str = "standard") -> None:
        """Execute command via the unified LLM manager."""
        try:
            from ai_designer.llm.unified_manager import (  # noqa: F401
                GenerationMode,
                LLMRequest,
            )
        except ImportError:
            from ai_designer.llm.unified_manager import (  # noqa: F811
                GenerationMode,
                LLMRequest,
            )

        if not self.unified_llm_manager:
            print(
                "❌ Unified LLM Manager not initialized, falling back to legacy execution"
            )
            return self.execute_command(command)

        print(f"🧠 Processing with Unified LLM Manager: {command}")

        mode_mapping = {
            "fast": GenerationMode.FAST,
            "standard": GenerationMode.STANDARD,
            "complex": GenerationMode.COMPLEX,
            "creative": GenerationMode.CREATIVE,
            "technical": GenerationMode.TECHNICAL,
        }
        generation_mode = mode_mapping.get(mode.lower(), GenerationMode.STANDARD)

        current_state = None
        if self.state_analyzer:
            try:
                current_state = self.state_analyzer.get_current_state()
            except Exception as e:
                print(f"⚠️ Could not get current state: {e}")

        request = LLMRequest(
            command=command,
            state=current_state,
            mode=generation_mode,
            context={"session_id": self.session_id},
        )

        try:
            response = self.unified_llm_manager.generate_command(request)

            if response.status == "success":
                print("✅ Code generation successful!")
                print(f"   Provider: {response.provider.value}")
                print(f"   Confidence: {response.confidence_score:.2f}")
                print(f"   Generation time: {response.execution_time:.1f}s")

                code_preview = (
                    response.generated_code[:300] + "..."
                    if len(response.generated_code) > 300
                    else response.generated_code
                )
                print(f"\n📝 Generated Code:\n{code_preview}")

                if self.command_executor and response.generated_code:
                    self._execute_generated_code(
                        response.generated_code,
                        f"unified_{int(time.time() * 1000)}",
                        response.provider.value,
                    )
                    self._maybe_notify_ws(f"Command executed: {command}")

                if response.optimization_suggestions:
                    print("\n💡 Optimization Suggestions:")
                    for s in response.optimization_suggestions[:3]:
                        print(f"   • {s}")
            else:
                print(f"❌ Code generation failed: {response.error_message}")

        except Exception as e:
            print(f"❌ Unified command execution failed: {e}")
            print("🔄 Falling back to legacy execution method...")
            return self.execute_command(command)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _execute_real(self, command: str, command_id: str) -> None:
        """Handle --real flag commands that directly create FreeCAD objects."""
        print("🔧 REAL EXECUTION MODE: Creating actual FreeCAD objects...")
        clean_command = command.replace("--real", "").strip()

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                command_id, 1, "Generating FreeCAD code..."
            )

        if clean_command.startswith("!"):
            result = self.command_executor.execute(clean_command[1:])
        else:
            result = self.command_executor.execute_natural_language(clean_command)

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                command_id, 3, "Executing in FreeCAD..."
            )

        if (
            self.enable_persistent_gui
            and self.persistent_gui
            and self.persistent_gui.is_gui_running()
        ):
            if result and result.get("status") == "success":
                freecad_script = result.get("command", "")
                if freecad_script:
                    print("📡 Sending real-time update to persistent GUI...")
                    gui_ok = self.persistent_gui.execute_script_in_gui(freecad_script)
                    if gui_ok:
                        print("✅ Command executed in persistent GUI")
                        self.persistent_gui.update_gui_view()
                    else:
                        print("⚠️  GUI update failed, but command executed")

        if self.progress_tracker:
            self.progress_tracker.update_progress(command_id, 4, "Updating views...")

        if result and result.get("status") == "success":
            print(
                f"✅ REAL EXECUTION SUCCESS: {result.get('message', 'Command executed successfully')}"
            )
            print(
                f"📁 File saved: {result.get('saved_path', 'Check outputs/ directory')}"
            )
            result["execution_type"] = "REAL_FREECAD"
            if self.progress_tracker:
                self.progress_tracker.complete_tracking(
                    command_id, True, "Command completed successfully"
                )
        else:
            msg = (
                result.get("message", "Execution failed")
                if result
                else "Execution failed"
            )
            print(f"❌ REAL EXECUTION FAILED: {msg}")
            if result:
                result["execution_type"] = "REAL_FREECAD"
            if self.progress_tracker:
                self.progress_tracker.fail_tracking(command_id, msg)

    def _execute_state_aware(self, command: str, command_id: str) -> None:
        """Use StateAwareCommandProcessor for advanced Phase 2/3 workflows."""
        from .display import display_workflow_results

        print("🎯 Using advanced State-Aware Processing (Phase 2 & 3)")

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                command_id, 1, "Analyzing workflow strategy..."
            )

        result = self.command_executor.state_aware_processor.process_complex_command(
            command
        )

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                command_id, 3, "Processing workflow steps..."
            )

        display_workflow_results(result, command)

        if self.progress_tracker:
            status = result.get("status", "unknown")
            if status == "success":
                self.progress_tracker.complete_tracking(
                    command_id, True, "Workflow analysis completed"
                )
            else:
                self.progress_tracker.fail_tracking(
                    command_id, result.get("error", "Workflow failed")
                )

    def _execute_basic(self, command: str, command_id: str) -> None:
        """Fall back to basic command processing."""
        print("⚠️ Falling back to basic processing")

        if self.progress_tracker:
            self.progress_tracker.update_progress(
                command_id, 1, "Basic command processing..."
            )

        if command.startswith("!"):
            result = self.command_executor.execute(command[1:])
        else:
            result = self.command_executor.execute_natural_language(command)

        if result["status"] == "success":
            print(f"✓ {result['message']}")
            if self.progress_tracker:
                self.progress_tracker.complete_tracking(
                    command_id, True, "Basic command completed"
                )
        else:
            print(f"✗ Error: {result['message']}")
            if self.progress_tracker:
                self.progress_tracker.fail_tracking(command_id, result["message"])

    def _use_direct_deepseek_api(
        self, command: str, mode: str, command_id: str
    ) -> None:
        """Use direct DeepSeek R1 API call."""
        try:
            if self.progress_tracker:
                self.progress_tracker.update_progress(
                    command_id, 2, "Sending request to DeepSeek R1..."
                )

            print(
                "🔄 Attempting DeepSeek R1 API call (may take up to 2 minutes for 14b model)..."
            )

            original_timeout = self.deepseek_client.config.timeout
            self.deepseek_client.config.timeout = 300

            response = asyncio.run(
                self.deepseek_client.generate_complex_part(
                    prompt=command, mode=mode, enable_reasoning=True
                )
            )

            self.deepseek_client.config.timeout = original_timeout

            if response and response.success:
                if response.reasoning:
                    reasoning_preview = (
                        response.reasoning[:500] + "..."
                        if len(response.reasoning) > 500
                        else response.reasoning
                    )
                    print(
                        f"\n🧠 DeepSeek R1 Reasoning:\n{'=' * 50}\n{reasoning_preview}\n{'=' * 50}"
                    )

                if response.freecad_code:
                    self._execute_generated_code(
                        response.freecad_code, command_id, "Direct API"
                    )
                else:
                    print("⚠️  No FreeCAD code generated from direct API")
                    if self.progress_tracker:
                        self.progress_tracker.fail_tracking(
                            command_id, "No FreeCAD code generated"
                        )
            else:
                error_msg = (
                    response.error if response else "No response from DeepSeek R1"
                )
                print(f"❌ DeepSeek R1 API failed: {error_msg}")
                if self.progress_tracker:
                    self.progress_tracker.fail_tracking(command_id, error_msg)

        except Exception as e:
            print(f"❌ Direct API exception: {e}")
            if self.progress_tracker:
                self.progress_tracker.fail_tracking(command_id, str(e))

    def _execute_generated_code(
        self, freecad_code: str, command_id: str, source: str
    ) -> None:
        """Execute generated FreeCAD Python code and update GUI."""
        try:
            print(f"\n🔧 Generated FreeCAD Code from {source}:")
            print(
                freecad_code[:300] + "..." if len(freecad_code) > 300 else freecad_code
            )

            if self.progress_tracker:
                self.progress_tracker.update_progress(
                    command_id, 5, "Executing in FreeCAD..."
                )

            exec_result = self.command_executor.execute(freecad_code)

            if exec_result.get("status") == "success":
                print(
                    f"✅ {source} SUCCESS: {exec_result.get('message', 'Code executed successfully')}"
                )

                if (
                    self.enable_persistent_gui
                    and self.persistent_gui
                    and self.persistent_gui.is_gui_running()
                ):
                    print("📡 Sending to persistent GUI...")
                    gui_ok = self.persistent_gui.execute_script_in_gui(freecad_code)
                    if gui_ok:
                        print("✅ Real-time GUI update completed")
                        self.persistent_gui.update_gui_view()

                if self.progress_tracker:
                    self.progress_tracker.complete_tracking(
                        command_id, True, f"{source} completed successfully"
                    )
            else:
                msg = exec_result.get("message", "Execution failed")
                print(f"❌ FreeCAD execution failed: {msg}")
                if self.progress_tracker:
                    self.progress_tracker.fail_tracking(
                        command_id, f"FreeCAD execution failed: {msg}"
                    )

        except Exception as e:
            self._save_generated_code_fallback(freecad_code, source)
            print(f"❌ Code execution exception: {e}")
            if self.progress_tracker:
                self.progress_tracker.fail_tracking(command_id, str(e))

    def _save_generated_code_fallback(self, freecad_code: str, source: str) -> None:
        """Save generated code to disk when execution fails."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            code_file = f"outputs/generated_code_{timestamp}.py"
            os.makedirs("outputs", exist_ok=True)
            with open(code_file, "w") as f:
                f.write(f"# Generated by {source} at {timestamp}\n")
                f.write(freecad_code)
            print(f"📁 Generated code saved to: {code_file}")
        except Exception as save_e:
            print(f"⚠️ Could not save generated code: {save_e}")

    def _maybe_notify_ws(self, message: str) -> None:
        """Send a notification via WebSocket if available."""
        if self.websocket_manager:
            try:
                self.websocket_manager.send_user_notification(
                    message, "success", self.session_id
                )
            except Exception as ws_e:
                print(f"⚠️ WebSocket update failed: {ws_e}")

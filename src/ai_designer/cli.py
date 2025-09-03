#!/usr/bin/env python3
import sys
import os
import argparse
import asyncio
import threading
import time

# Fix imports to use relative paths
try:
    from .freecad.api_client import FreeCADAPIClient
    from .freecad.command_executor import CommandExecutor
    from .freecad.state_manager import FreeCADStateAnalyzer
    from .freecad.persistent_gui_client import PersistentFreeCADGUI
    from .redis_utils.client import RedisClient
    from .redis_utils.state_cache import StateCache
    from .realtime.websocket_manager import WebSocketManager, ProgressTracker
    from .llm.deepseek_client import DeepSeekR1Client, DeepSeekIntegrationManager, DeepSeekMode
    from .core.enhanced_complex_generator import EnhancedComplexShapeGenerator
except ImportError:
    # Fallback for when running as script
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    from ai_designer.freecad.api_client import FreeCADAPIClient
    from ai_designer.freecad.command_executor import CommandExecutor
    from ai_designer.freecad.state_manager import FreeCADStateAnalyzer
    from ai_designer.freecad.persistent_gui_client import PersistentFreeCADGUI
    from ai_designer.redis_utils.client import RedisClient
    from ai_designer.redis_utils.state_cache import StateCache
    from ai_designer.realtime.websocket_manager import WebSocketManager, ProgressTracker
    from ai_designer.llm.deepseek_client import DeepSeekR1Client, DeepSeekIntegrationManager, DeepSeekMode
    from ai_designer.core.enhanced_complex_generator import EnhancedComplexShapeGenerator
    from ai_designer.core.enhanced_complex_generator import EnhancedComplexShapeGenerator

class FreeCADCLI:
    def __init__(self, use_headless=True, llm_provider="openai", llm_api_key=None, auto_open_gui=True, enable_websocket=True, enable_persistent_gui=True, deepseek_enabled=False, deepseek_mode="reasoning", deepseek_port=11434):
        self.api_client = FreeCADAPIClient(use_headless=use_headless)
        self.command_executor = None
        self.state_cache = None
        self.state_analyzer = None
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.auto_open_gui = auto_open_gui
        
        # DeepSeek R1 configuration
        self.deepseek_enabled = deepseek_enabled
        self.deepseek_mode = deepseek_mode
        self.deepseek_port = deepseek_port
        self.deepseek_client = None
        self.enhanced_generator = None
        
        # WebSocket and real-time features
        self.enable_websocket = enable_websocket
        self.enable_persistent_gui = enable_persistent_gui
        self.websocket_manager = None
        self.progress_tracker = None
        self.persistent_gui = None
        self.websocket_thread = None
        self.session_id = f"cli_session_{int(time.time())}"
        
        # Try to initialize Redis for state management
        try:
            redis_client = RedisClient()
            if redis_client.connect():
                self.state_cache = StateCache(redis_client)
                print("✓ Redis connection established for state caching")
        except Exception as e:
            print(f"Warning: Redis not available: {e}")
        
        # Initialize WebSocket server if enabled
        if self.enable_websocket:
            try:
                self.websocket_manager = WebSocketManager()
                self.progress_tracker = ProgressTracker(self.websocket_manager)
                print("✓ WebSocket manager initialized")
            except Exception as e:
                print(f"Warning: WebSocket not available: {e}")
                self.enable_websocket = False
        
        # Initialize persistent GUI if enabled
        if self.enable_persistent_gui:
            try:
                self.persistent_gui = PersistentFreeCADGUI(self.websocket_manager)
                print("✓ Persistent GUI client initialized")
            except Exception as e:
                print(f"Warning: Persistent GUI not available: {e}")
                self.enable_persistent_gui = False

    def initialize(self):
        """Initialize FreeCAD connection and command executor"""
        print("Initializing FreeCAD CLI...")
        
        # Initialize DeepSeek R1 if enabled
        if self.deepseek_enabled:
            try:
                print(f"🧠 Initializing DeepSeek R1 client on port {self.deepseek_port}...")
                from ai_designer.llm.deepseek_client import DeepSeekConfig
                config = DeepSeekConfig(
                    host="localhost",
                    port=self.deepseek_port,
                    timeout=120
                )
                self.deepseek_client = DeepSeekR1Client(config=config)
                print("✅ DeepSeek R1 client ready")
            except Exception as e:
                print(f"⚠️  DeepSeek R1 initialization failed: {e}")
                print("Continuing with standard LLM providers...")
                self.deepseek_enabled = False
        
        # Start WebSocket server if enabled
        if self.enable_websocket and self.websocket_manager:
            self._start_websocket_server()
        
        if self.api_client.connect():
            print("✓ FreeCAD connection established")
            
            # Start persistent GUI if enabled BEFORE creating CommandExecutor
            if self.enable_persistent_gui and self.persistent_gui:
                print("🖥️  Starting persistent FreeCAD GUI...")
                if self.persistent_gui.start_persistent_gui():
                    print("✅ Persistent GUI ready for real-time updates")
                    if self.websocket_manager:
                        self.websocket_manager.send_user_notification(
                            "FreeCAD CLI initialized with persistent GUI and WebSocket server",
                            "success",
                            self.session_id
                        )
                else:
                    print("⚠️  Persistent GUI failed to start, falling back to standard mode")
                    self.enable_persistent_gui = False
            
            # Create CommandExecutor with persistent GUI reference
            self.command_executor = CommandExecutor(
                self.api_client, 
                self.state_cache, 
                llm_provider=self.llm_provider, 
                llm_api_key=self.llm_api_key,
                auto_open_gui=self.auto_open_gui,
                persistent_gui=self.persistent_gui if self.enable_persistent_gui else None
            )
            self.state_analyzer = FreeCADStateAnalyzer(self.api_client)
            
            # Initialize enhanced generator with DeepSeek after command executor is ready
            if self.deepseek_enabled and self.deepseek_client:
                try:
                    print("🔧 Initializing Enhanced Complex Generator with DeepSeek R1...")
                    from ai_designer.llm.deepseek_client import DeepSeekConfig
                    config = DeepSeekConfig(
                        host="localhost",
                        port=self.deepseek_port,
                        timeout=120
                    )
                    self.enhanced_generator = EnhancedComplexShapeGenerator(
                        llm_client=None,  # Will use DeepSeek
                        state_analyzer=self.state_analyzer,
                        command_executor=self.command_executor,
                        state_cache=self.state_cache,
                        websocket_manager=self.websocket_manager,
                        use_deepseek=True,
                        deepseek_config=config
                    )
                    print("✅ Enhanced Complex Generator with DeepSeek R1 ready")
                except Exception as e:
                    print(f"⚠️  Enhanced generator initialization failed: {e}")
                    self.enhanced_generator = None
            
            return True
        else:
            print("✗ Failed to connect to FreeCAD")
            return False
    
    def _start_websocket_server(self):
        """Start the WebSocket server in a separate thread"""
        def start_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.websocket_manager.start_server())
                loop.run_forever()
            except Exception as e:
                print(f"❌ WebSocket server error: {e}")
            finally:
                loop.close()
        
        self.websocket_thread = threading.Thread(target=start_server, daemon=True)
        self.websocket_thread.start()
        
        # Give server time to start
        time.sleep(1)
        print("✅ WebSocket server started on ws://localhost:8765")

    def interactive_mode(self):
        """Start interactive command mode"""
        if not self.initialize():
            return
        
        print("\nFreeCAD Interactive Mode")
        print("Type 'help' for commands, 'quit' to exit")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("FreeCAD> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    self.show_help()
                
                elif user_input.lower() == 'state':
                    self.show_state()
                
                elif user_input.lower() == 'analyze':
                    self.analyze_state()
                
                elif user_input.startswith('analyze '):
                    doc_path = user_input[8:].strip()
                    self.analyze_state(doc_path)
                
                elif user_input.lower() == 'history':
                    self.show_history()
                
                elif user_input.startswith('script '):
                    script_path = user_input[7:].strip()
                    self.execute_script(script_path)
                
                elif user_input.lower() in ['fileinfo', 'files', 'location']:
                    self.show_file_info()
                
                elif user_input.lower() in ['saveinfo', 'saves', 'autosave']:
                    self.show_save_info()
                
                elif user_input.startswith('save '):
                    # Manual save command
                    filename = user_input[5:].strip()
                    if filename:
                        self.command_executor.manual_save(filename)
                    else:
                        self.command_executor.manual_save()
                
                elif user_input.lower() in ['gui', 'open', 'view']:
                    # Open current document in GUI
                    result = self.command_executor.open_current_in_gui()
                    if result.get("status") == "success":
                        print("✅ Document opened in FreeCAD GUI")
                    else:
                        print(f"❌ Failed to open in GUI: {result.get('message', 'Unknown error')}")
                
                elif user_input.lower() in ['gui-on', 'auto-gui-on']:
                    # Enable auto GUI opening
                    self.command_executor.set_auto_open_gui(True)
                
                elif user_input.lower() in ['gui-off', 'auto-gui-off']:
                    # Disable auto GUI opening
                    self.command_executor.set_auto_open_gui(False)
                
                elif user_input.lower() in ['complex', 'examples']:
                    # Show complex shape examples
                    self.show_complex_examples()
                
                elif user_input.lower() in ['websocket', 'ws', 'realtime']:
                    # Show WebSocket status
                    self.show_websocket_status()
                
                elif user_input.lower() in ['persistent-gui', 'pgui', 'gui-status']:
                    # Show persistent GUI status
                    self.show_persistent_gui_status()
                
                elif user_input.lower() in ['start-websocket', 'ws-start']:
                    # Start WebSocket server manually
                    self.start_websocket_manually()
                
                elif user_input.lower() in ['stop-gui', 'gui-stop']:
                    # Stop persistent GUI
                    self.stop_persistent_gui()
                
                elif user_input.lower() in ['restart-gui', 'gui-restart']:
                    # Restart persistent GUI
                    self.restart_persistent_gui()
                
                elif user_input.startswith('deepseek '):
                    # DeepSeek R1 specific command
                    deepseek_command = user_input[9:].strip()
                    if self.deepseek_enabled:
                        self.execute_deepseek_command(deepseek_command)
                    else:
                        print("❌ DeepSeek R1 is not enabled. Use --deepseek-enabled flag when starting CLI.")
                
                elif self.deepseek_enabled and any(keyword in user_input.lower() for keyword in ['gear', 'complex', 'bracket', 'assembly', 'housing', 'detailed']):
                    # Auto-detect complex commands that should use DeepSeek R1
                    print(f"🧠 Complex command detected - using DeepSeek R1: {user_input}")
                    self.execute_deepseek_command(user_input)
                
                else:
                    self.execute_command(user_input)
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                print("\nGoodbye!")
                break
        
        # Cleanup
        self.cleanup()
    
    def cleanup(self):
        """Cleanup resources when shutting down"""
        print("🧹 Cleaning up resources...")
        
        # Stop persistent GUI
        if self.enable_persistent_gui and self.persistent_gui:
            if self.persistent_gui.is_gui_running():
                print("🛑 Stopping persistent GUI...")
                self.persistent_gui.stop_gui()
        
        # Stop WebSocket server
        if self.enable_websocket and self.websocket_manager:
            if self.websocket_manager.running:
                print("🛑 Stopping WebSocket server...")
                try:
                    # This needs to be run in the event loop
                    if self.websocket_thread and self.websocket_thread.is_alive():
                        # Send stop signal
                        asyncio.run_coroutine_threadsafe(
                            self.websocket_manager.stop_server(),
                            asyncio.get_event_loop()
                        )
                except:
                    pass
        
        print("✅ Cleanup completed")

    def execute_command(self, command):
        """Execute a single command using Phase 2 & 3 advanced workflows with real-time updates"""
        command_id = f"cmd_{int(time.time() * 1000)}"
        
        try:
            print(f"🧠 Processing with Phase 2 & 3 workflows: {command}")
            
            # Send initial progress update
            if self.progress_tracker:
                self.progress_tracker.start_tracking(command_id, 5, self.session_id)
            
            # Check if user wants REAL FreeCAD execution vs simulation
            if "--real" in command:
                print("🔧 REAL EXECUTION MODE: Creating actual FreeCAD objects...")
                clean_command = command.replace("--real", "").strip()
                
                # Update progress
                if self.progress_tracker:
                    self.progress_tracker.update_progress(command_id, 1, "Generating FreeCAD code...")
                
                # Use direct command executor for real execution
                if clean_command.startswith('!'):
                    # Direct FreeCAD Python command
                    freecad_command = clean_command[1:]
                    result = self.command_executor.execute(freecad_command)
                else:
                    # Natural language command with real execution
                    result = self.command_executor.execute_natural_language(clean_command)
                
                # Update progress
                if self.progress_tracker:
                    self.progress_tracker.update_progress(command_id, 3, "Executing in FreeCAD...")
                
                # Send to persistent GUI if available
                if self.enable_persistent_gui and self.persistent_gui and self.persistent_gui.is_gui_running():
                    if result and result.get("status") == "success":
                        # Get the generated command and send to GUI
                        freecad_script = result.get('command', '')
                        if freecad_script:
                            print("📡 Sending real-time update to persistent GUI...")
                            gui_success = self.persistent_gui.execute_script_in_gui(freecad_script)
                            if gui_success:
                                print("✅ Command executed in persistent GUI")
                                # Update view
                                self.persistent_gui.update_gui_view()
                            else:
                                print("⚠️  GUI update failed, but command executed")
                
                # Update progress
                if self.progress_tracker:
                    self.progress_tracker.update_progress(command_id, 4, "Updating views...")
                
                # Convert result format for consistency
                if result and result.get("status") == "success":
                    print(f"✅ REAL EXECUTION SUCCESS: {result.get('message', 'Command executed successfully')}")
                    print(f"📁 File saved: {result.get('saved_path', 'Check outputs/ directory')}")
                    result['execution_type'] = 'REAL_FREECAD'
                    
                    # Complete progress tracking
                    if self.progress_tracker:
                        self.progress_tracker.complete_tracking(command_id, True, "Command completed successfully")
                else:
                    print(f"❌ REAL EXECUTION FAILED: {result.get('message', 'Execution failed')}")
                    result['execution_type'] = 'REAL_FREECAD'
                    
                    # Fail progress tracking
                    if self.progress_tracker:
                        self.progress_tracker.fail_tracking(command_id, result.get('message', 'Execution failed'))
                
            # Use StateAwareCommandProcessor for all commands
            elif hasattr(self.command_executor, 'state_aware_processor') and self.command_executor.state_aware_processor:
                print("🎯 Using advanced State-Aware Processing (Phase 2 & 3)")
                
                # Update progress
                if self.progress_tracker:
                    self.progress_tracker.update_progress(command_id, 1, "Analyzing workflow strategy...")
                
                # Let the state-aware processor handle workflow detection and execution
                result = self.command_executor.state_aware_processor.process_complex_command(command)
                
                # Update progress
                if self.progress_tracker:
                    self.progress_tracker.update_progress(command_id, 3, "Processing workflow steps...")
                
                # Display detailed workflow results
                self._display_workflow_results(result, command)
                
                # Complete progress tracking
                if self.progress_tracker:
                    status = result.get('status', 'unknown')
                    if status == 'success':
                        self.progress_tracker.complete_tracking(command_id, True, "Workflow analysis completed")
                    else:
                        self.progress_tracker.fail_tracking(command_id, result.get('error', 'Workflow failed'))
                
            else:
                print("⚠️ Falling back to basic processing")
                
                # Update progress
                if self.progress_tracker:
                    self.progress_tracker.update_progress(command_id, 1, "Basic command processing...")
                
                # Fallback to basic processing
                if command.startswith('!'):
                    # Direct FreeCAD Python command
                    freecad_command = command[1:]
                    result = self.command_executor.execute(freecad_command)
                else:
                    # Natural language command
                    result = self.command_executor.execute_natural_language(command)
                
                if result["status"] == "success":
                    print(f"✓ {result['message']}")
                    if self.progress_tracker:
                        self.progress_tracker.complete_tracking(command_id, True, "Basic command completed")
                else:
                    print(f"✗ Error: {result['message']}")
                    if self.progress_tracker:
                        self.progress_tracker.fail_tracking(command_id, result['message'])
                
        except Exception as e:
            print(f"✗ Exception: {e}")
            if self.progress_tracker:
                self.progress_tracker.fail_tracking(command_id, str(e))
            import traceback
            traceback.print_exc()
    
    def _display_workflow_results(self, result, original_command):
        """Display detailed results from Phase 2 & 3 workflow processing"""
        print(f"\n📊 Workflow Execution Results:")
        print("=" * 50)
        
        status = result.get('status', 'unknown')
        workflow_type = result.get('workflow', 'unknown')
        
        # Status with emoji
        status_emoji = "✅" if status == 'success' else "❌" if status == 'error' else "⚠️"
        print(f"Status: {status_emoji} {status.upper()}")
        print(f"Workflow: {workflow_type}")
        print(f"Command: {original_command}")
        
        # Phase 2: Face Selection Results
        if workflow_type == 'face_selection':
            print(f"\n🎯 Phase 2 - Face Selection Workflow:")
            selected_face = result.get('selected_face')
            if selected_face:
                print(f"  • Selected Face: {selected_face.get('object_name', 'Unknown')}")
                print(f"  • Face Type: {selected_face.get('face_type', 'Unknown')}")
                print(f"  • Suitability Score: {selected_face.get('suitability_score', 0):.2f}")
            
            operation_type = result.get('operation_type', 'Unknown')
            print(f"  • Operation: {operation_type}")
        
        # Phase 3: Complex Workflow Results
        elif workflow_type == 'complex_workflow':
            print(f"\n🏗️ Phase 3 - Complex Multi-Step Workflow:")
            total_steps = result.get('total_steps', 0)
            completed_steps = result.get('completed_steps', 0)
            failed_steps = result.get('failed_steps', 0)
            execution_time = result.get('execution_time', 0)
            complexity_score = result.get('complexity_score', 0)
            
            print(f"  • Total Steps: {total_steps}")
            print(f"  • Completed: {completed_steps}")
            print(f"  • Failed: {failed_steps}")
            print(f"  • Execution Time: {execution_time:.2f}s")
            print(f"  • Complexity Score: {complexity_score:.2f}")
            
            # Show step details
            step_results = result.get('step_results', [])
            if step_results:
                print(f"\n  🔧 Step Details:")
                for i, step in enumerate(step_results, 1):
                    if hasattr(step, 'status'):
                        step_status = "✅" if step.status == 'success' else "❌"
                        step_name = getattr(step, 'step_name', f'Step {i}')
                    else:
                        step_status = "✅" if step.get('status') == 'success' else "❌"
                        step_name = step.get('step_name', f'Step {i}')
                    print(f"    {step_status} {step_name}")
        
        # Phase 1: Sketch-Then-Operate Results
        elif workflow_type == 'sketch_then_operate':
            print(f"\n✏️ Phase 1 - Sketch-Then-Operate Workflow:")
            objects_created = result.get('objects_created', 0)
            print(f"  • Objects Created: {objects_created}")
            
            validation = result.get('validation', {})
            if validation:
                quality_score = validation.get('quality_score', 0)
                print(f"  • Quality Score: {quality_score:.2f}")
                
                issues = validation.get('issues', [])
                if issues:
                    print(f"  • Issues: {', '.join(issues)}")
        
        # Multi-step workflow results
        elif workflow_type == 'multi_step':
            print(f"\n🔄 Multi-Step Workflow:")
            steps_executed = result.get('steps_executed', 0)
            print(f"  • Steps Executed: {steps_executed}")
        
        # Show execution results
        execution_results = result.get('execution_results', [])
        if execution_results:
            print(f"\n📋 Execution Steps:")
            for i, exec_result in enumerate(execution_results, 1):
                step_status = "✅" if exec_result.get('status') == 'success' else "❌"
                operation = exec_result.get('operation', f'Step {i}')
                print(f"  {step_status} {operation}")
        
        # Final state summary
        final_state = result.get('final_state', {})
        if final_state:
            object_count = final_state.get('object_count', 0)
            print(f"\n📈 Final State: {object_count} objects in document")
        
        # Success message
        if status == 'success':
            print(f"\n🎉 SUCCESS: Advanced workflow completed!")
            if workflow_type == 'complex_workflow':
                print(f"✅ Phase 3 complex multi-step workflow executed")
            elif workflow_type == 'face_selection':
                print(f"✅ Phase 2 intelligent face selection performed")
            elif workflow_type == 'sketch_then_operate':
                print(f"✅ Phase 1 sketch-then-operate workflow completed")
        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
            suggestion = result.get('suggestion', '')
            if suggestion:
                print(f"💡 Suggestion: {suggestion}")

    def execute_script(self, script_path):
        """Execute a FreeCAD script file"""
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

    def show_state(self):
        """Show current FreeCAD document state"""
        state = self.command_executor.get_state()
        print("\nCurrent FreeCAD State:")
        print(f"Document: {state.get('active_document', 'None')}")
        print(f"Objects: {state.get('object_count', 0)}")
        
        for obj in state.get('objects', []):
            print(f"  - {obj['name']} ({obj['type']})")

    def analyze_state(self, doc_path=None):
        """Perform comprehensive state analysis"""
        if not self.state_analyzer:
            print("✗ State analyzer not available")
            return
        
        print("🔄 Analyzing FreeCAD document state...")
        
        try:
            analysis = self.state_analyzer.analyze_document_state(doc_path)
            self.state_analyzer.print_analysis_results(analysis)
            
            # Cache the analysis results if Redis is available
            if self.state_cache and "analysis" in analysis:
                self.state_cache.cache_state(analysis, "last_analysis")
                print("\n💾 Analysis results cached")
                
        except Exception as e:
            print(f"✗ Analysis failed: {e}")

    def show_history(self):
        """Show command history"""
        history = self.command_executor.get_command_history()
        print(f"\nCommand History ({len(history)} commands):")
        for i, cmd in enumerate(history[-10:], 1):  # Show last 10 commands
            print(f"{i:2d}. {cmd[:50]}{'...' if len(cmd) > 50 else ''}")

    def execute_deepseek_command(self, command):
        """Execute command using DeepSeek R1 for complex part generation"""
        if not self.deepseek_enabled or not self.deepseek_client:
            print("❌ DeepSeek R1 is not enabled or not initialized")
            print("🔄 Falling back to standard processing...")
            return self.execute_command(command)
        
        command_id = f"deepseek_cmd_{int(time.time() * 1000)}"
    
    def _use_direct_deepseek_api(self, command, mode, command_id):
        """Use direct DeepSeek R1 API call"""
        try:
            # Progress update
            if self.progress_tracker:
                self.progress_tracker.update_progress(command_id, 2, "Sending request to DeepSeek R1...")
            
            print("🔄 Attempting DeepSeek R1 API call (may take up to 2 minutes for 14b model)...")
            
            # Create a shorter timeout for CLI usage
            original_timeout = self.deepseek_client.config.timeout
            self.deepseek_client.config.timeout = 120  # 2 minutes max for CLI
            
            response = asyncio.run(self.deepseek_client.generate_complex_part(
                prompt=command,
                mode=mode,
                enable_reasoning=True
            ))
            
            # Restore original timeout
            self.deepseek_client.config.timeout = original_timeout
            
            if response and response.success:
                if response.reasoning:
                    print(f"\n🧠 DeepSeek R1 Reasoning:")
                    print("=" * 50)
                    print(response.reasoning[:500] + "..." if len(response.reasoning) > 500 else response.reasoning)
                    print("=" * 50)
                
                # Execute the code
                if response.freecad_code:
                    self._execute_generated_code(response.freecad_code, command_id, "Direct API")
                else:
                    print("⚠️  No FreeCAD code generated from direct API")
                    if self.progress_tracker:
                        self.progress_tracker.fail_tracking(command_id, "No FreeCAD code generated")
            else:
                error_msg = response.error if response else "No response from DeepSeek R1"
                print(f"❌ DeepSeek R1 API failed: {error_msg}")
                if self.progress_tracker:
                    self.progress_tracker.fail_tracking(command_id, error_msg)
                    
        except Exception as e:
            print(f"❌ Direct API exception: {e}")
            if self.progress_tracker:
                self.progress_tracker.fail_tracking(command_id, str(e))
    
    def _execute_generated_code(self, freecad_code, command_id, source):
        """Execute generated FreeCAD code and update GUI"""
        try:
            print(f"\n🔧 Generated FreeCAD Code from {source}:")
            print(freecad_code[:300] + "..." if len(freecad_code) > 300 else freecad_code)
            
            # Execute in FreeCAD
            if self.progress_tracker:
                self.progress_tracker.update_progress(command_id, 5, "Executing in FreeCAD...")
            
            exec_result = self.command_executor.execute(freecad_code)
            
            if exec_result.get("status") == "success":
                print(f"✅ DeepSeek R1 SUCCESS: {exec_result.get('message', 'Code executed successfully')}")
                
                # Send to persistent GUI if available
                if self.enable_persistent_gui and self.persistent_gui and self.persistent_gui.is_gui_running():
                    print("📡 Sending to persistent GUI...")
                    gui_success = self.persistent_gui.execute_script_in_gui(freecad_code)
                    if gui_success:
                        print("✅ Real-time GUI update completed")
                        self.persistent_gui.update_gui_view()
                
                # Complete progress tracking
                if self.progress_tracker:
                    self.progress_tracker.complete_tracking(command_id, True, f"DeepSeek R1 {source} completed successfully")
            else:
                print(f"❌ FreeCAD execution failed: {exec_result.get('message', 'Execution failed')}")
                if self.progress_tracker:
                    self.progress_tracker.fail_tracking(command_id, f"FreeCAD execution failed: {exec_result.get('message')}")
                    
        except Exception as e:
            print(f"❌ Code execution exception: {e}")
            if self.progress_tracker:
                self.progress_tracker.fail_tracking(command_id, str(e))

    def show_help(self):
        """Show help information"""
        help_text = """
🚀 Phase 2 & 3 Enhanced FreeCAD CLI - Advanced Workflow System with DeepSeek R1

Available Commands:
  🧠 DeepSeek R1 Complex Part Generation:
    - deepseek create detailed gear with 20 teeth    Use DeepSeek R1 reasoning for complex parts
    - deepseek design bracket with mounting holes    Advanced AI-driven part generation
    - deepseek build mechanical assembly             Multi-component system design
    
    Auto-Detection (when --deepseek-enabled):
    - create gear with 20 teeth and hub              Auto-detected as complex → uses DeepSeek R1
    - design detailed bracket assembly               Auto-detected as complex → uses DeepSeek R1
    - build complex housing with features            Auto-detected as complex → uses DeepSeek R1

  🎯 Smart Natural Language Processing:
    - create box 10x20x30                    Create a box with dimensions
    - create cylinder radius 5               Create a cylinder  
    - create sphere radius 10                Create a sphere
    - add hole on top face                   Phase 2: Intelligent face selection
    - create bracket with mounting holes     Phase 3: Complex multi-step workflow
    - design gear with hub and fillets       Phase 3: Advanced feature generation
    - build assembly with multiple parts     Phase 3: Complex assembly workflow

  🔧 REAL EXECUTION vs SIMULATION:
    - create gear --real                     REAL: Actually creates FreeCAD objects
    - create gear                            SIMULATION: Shows workflow analysis only
    - create box 10x20x30 --real             REAL: Creates actual box in FreeCAD
    - create complex assembly --real         REAL: Executes all steps in FreeCAD
    
  🌐 REAL-TIME FEATURES:
    - websocket / ws                         Show WebSocket server status
    - persistent-gui / pgui                  Show persistent GUI status  
    - restart-gui                            Restart persistent FreeCAD GUI
    - stop-gui                               Stop persistent GUI
    💡 Connect to ws://localhost:8765 for real-time updates
  
  🏗️ Phase 3 - Complex Multi-Step Workflows:
    - create a bracket with 4 mounting holes and fillets
    - design a gear housing with cover and mounting features  
    - build a complex mechanical assembly with patterns
    - create architectural structure with multiple levels
    - make a planetary gear system with sun, planet, and ring gears
    - design a tower with base, pillars, and roof
    - create a rocket with body, nose cone, and fins
  
  🎯 Phase 2 - Intelligent Face Selection & Operations:
    - add 10mm hole on the top face          Smart face detection
    - create pocket in the center            Optimal face selection
    - drill 4 holes in square pattern        Pattern on selected face
    - add mounting holes on flat surface     Surface analysis
    - create slots on the side face          Face type recognition
  
  ✏️ Phase 1 - Sketch-Then-Operate (Enhanced):
    - create 50mm diameter cylinder 100mm tall    Parametric sketch creation
    - make rectangular base 100x50x10mm           Constraint-based modeling
    - design L-shaped bracket with dimensions     Complex sketch geometry
  
  Direct FreeCAD Commands (prefix with !):
    - !box = doc.addObject("Part::Box", "MyBox")
    - !box.Length = 10
    
  CLI Commands:
    - state                      Show basic document state
    - analyze                    Perform comprehensive state analysis
    - analyze <file.FCStd>       Analyze specific FreeCAD file
    - history                    Show command history
    - script <path>             Execute script file
    - fileinfo                  Show file locations and paths
    - saveinfo                  Show auto-save information and file locations
    - save [filename]           Manually save document (auto-save also enabled)
    - gui / open / view         Open current document in FreeCAD GUI
    - gui-on / auto-gui-on      Enable automatic GUI opening after commands
    - gui-off / auto-gui-off    Disable automatic GUI opening
    - websocket / ws            Show WebSocket server status and connection info
    - persistent-gui / pgui     Show persistent GUI status
    - restart-gui               Restart persistent FreeCAD GUI
    - stop-gui                  Stop persistent GUI
    - complex / examples        Show complex shape examples
    - help                      Show this help
    - quit                      Exit

🌐 Real-Time Features:

  🔗 WebSocket Server:
    ✅ Live Progress Updates     Real-time command execution progress
    ✅ Step-by-Step Tracking     See each workflow step as it executes
    ✅ Error Notifications       Instant error reporting and suggestions
    ✅ State Change Updates      Live document state synchronization
    ✅ Multi-Client Support      Multiple clients can connect simultaneously
    
  🖥️ Persistent FreeCAD GUI:
    ✅ Continuous Display       GUI stays open throughout session
    ✅ Real-Time Updates         Changes appear instantly as commands execute
    ✅ Step-by-Step Visualization  Watch complex workflows build progressively
    ✅ Socket Communication      Direct communication with CLI via sockets
    ✅ Auto View Updates         Automatically fits view to show new objects
    ✅ Background Processing     No need to manually open/close FreeCAD
    
  📡 Connection Details:
    🌐 WebSocket URL: ws://localhost:8765
    🔌 GUI Communication: Socket-based real-time updates
    📱 Session Tracking: Each session gets unique ID for isolation
    🔄 Auto-Reconnection: Robust connection handling with retries

🚀 Advanced Workflow Features (Phase 2 & 3):

  🎯 Phase 2 - Face Selection Engine:
    ✅ Intelligent Face Detection    Automatically finds suitable faces
    ✅ Face Type Recognition         Distinguishes flat, curved, complex faces
    ✅ Suitability Scoring          Ranks faces by operation compatibility
    ✅ Surface Area Analysis         Considers face size for operations
    ✅ Normal Vector Calculation     Determines face orientation
    ✅ Smart Hole Placement          Optimal positioning for holes/pockets

  🏗️ Phase 3 - Complex Workflow Orchestrator:
    ✅ Multi-Step Decomposition     Breaks complex commands into steps
    ✅ Dependency Management        Ensures proper step execution order
    ✅ Pattern Generation           Creates linear, circular, matrix patterns
    ✅ Feature Operations           Adds fillets, chamfers, shells automatically
    ✅ Assembly Operations          Coordinates multiple part creation
    ✅ Complexity Analysis          Scores and routes commands intelligently
    ✅ Workflow Validation          Ensures each step completes successfully

  📊 Intelligent Strategy Selection:
    🔍 Simple Command              → Direct execution
    ✏️ Sketch Required            → Phase 1: Sketch-then-operate workflow
    🎯 Face Operation             → Phase 2: Face selection workflow  
    🔄 Multi-step Process         → Traditional multi-step workflow
    🏗️ Complex Assembly          → Phase 3: Complex workflow orchestrator

  🎛️ Real-time Workflow Analysis:
    📈 Complexity Scoring         Analyzes command complexity (0-1 scale)
    📊 Step Estimation            Predicts number of execution steps
    🔍 Strategy Detection         Automatically selects optimal workflow
    ⚡ Performance Optimization   Routes commands to best processor
    📋 Progress Tracking          Shows step-by-step execution status

  Examples by Workflow Type:

  Phase 1 (Sketch-Then-Operate):
    "create 50mm diameter cylinder 100mm tall"
    "make rectangular pocket 20x10x5mm deep"
    "design circular pad with 25mm radius"

  Phase 2 (Face Selection):  
    "add 8mm hole on the top face"
    "create rectangular pocket on flat surface"
    "drill 4 mounting holes in corners"

  Phase 3 (Complex Workflows):
    "create bracket with 4 mounting holes and fillets"
    "design gear housing with cover and ventilation"
    "build mechanical assembly with multiple components"
"""
        print(help_text)

    def show_file_info(self):
        """Show current file and directory information"""
        print("\nFile Location Information:")
        print("=" * 30)
        try:
            result = self.api_client.get_file_info()
            if result["status"] == "success":
                for line in result["message"].split('\n'):
                    if line.startswith("CURRENT_DIR: "):
                        print(f"Working Directory: {line.replace('CURRENT_DIR: ', '')}")
                    elif line.startswith("HOME_DIR: "):
                        print(f"Home Directory: {line.replace('HOME_DIR: ', '')}")
                    elif line.startswith("DOCUMENT_NAME: "):
                        print(f"Document Name: {line.replace('DOCUMENT_NAME: ', '')}")
                    elif line.startswith("DOCUMENT_PATH: "):
                        path = line.replace('DOCUMENT_PATH: ', '')
                        if path == "Not saved yet":
                            print(f"Document Status: {path}")
                            print("Default save location: Current working directory")
                        else:
                            print(f"Document Path: {path}")
            else:
                print(f"Error getting file info: {result['message']}")
        except Exception as e:
            print(f"Error: {e}")

    def show_save_info(self):
        """Show information about saved files"""
        if not self.command_executor:
            print("❌ Command executor not initialized")
            return
            
        save_info = self.command_executor.get_save_info()
        print("\n💾 File Save Information:")
        print("=" * 40)
        print(f"Auto-save enabled: {'✅ Yes' if save_info['auto_save_enabled'] else '❌ No'}")
        print(f"Save counter: {save_info['save_counter']}")
        
        if save_info['last_saved_path']:
            print(f"Last saved to: {save_info['last_saved_path']}")
            # Check if file exists
            if os.path.exists(save_info['last_saved_path']):
                file_size = os.path.getsize(save_info['last_saved_path'])
                print(f"File size: {file_size} bytes")
                mod_time = os.path.getmtime(save_info['last_saved_path'])
                import datetime
                mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                print(f"Last modified: {mod_time_str}")
            else:
                print("⚠️  File no longer exists at saved location")
        else:
            print("No files saved yet")

    def execute_complex_shape(self, description):
        """Execute complex shape creation with multiple operations"""
        print(f"🔄 Creating complex shape: {description}")
        
        # Enhanced prompts for complex shape creation
        complex_prompts = {
            "cone and cylinder": [
                "create a cylinder with radius 5 and height 10",
                "create a cone with radius 3 and height 8 positioned on top of the cylinder",
                "fuse the cylinder and cone together"
            ],
            "tower": [
                "create a cylinder base with radius 8 and height 5",
                "create a smaller cylinder with radius 6 and height 10 on top",
                "create a cone roof with radius 6 and height 6 on top",
                "fuse all parts together"
            ],
            "rocket": [
                "create a cylinder body with radius 4 and height 20",
                "create a cone nose with radius 4 and height 8 on top",
                "create 4 small cylinders as fins with radius 1 and height 6",
                "position fins around the base",
                "fuse body and nose together"
            ],
            "complex structure": [
                "create a box base 20x20x5",
                "create a cylinder pillar radius 3 height 15 at each corner",
                "create a cone roof radius 8 height 5 in the center",
                "fuse all components together"
            ]
        }
        
        # Try to match the description to known complex shapes
        description_lower = description.lower()
        
        if "cone" in description_lower and "cylinder" in description_lower:
            commands = complex_prompts["cone and cylinder"]
        elif "tower" in description_lower:
            commands = complex_prompts["tower"]
        elif "rocket" in description_lower:
            commands = complex_prompts["rocket"]
        elif "complex" in description_lower or "structure" in description_lower:
            commands = complex_prompts["complex structure"]
        else:
            # Fallback to LLM for complex interpretation
            commands = [f"create a complex shape: {description}"]
        
        results = []
        for i, command in enumerate(commands, 1):
            print(f"  Step {i}/{len(commands)}: {command}")
            try:
                if command.startswith('!'):
                    # Direct FreeCAD Python command
                    freecad_command = command[1:]
                    result = self.command_executor.execute(freecad_command)
                else:
                    # Natural language command
                    result = self.command_executor.execute_natural_language(command)
                
                if result["status"] == "success":
                    print(f"    ✓ {result['message']}")
                    results.append(result)
                else:
                    print(f"    ✗ Error: {result['message']}")
                    # Continue with next step even if one fails
                    
            except Exception as e:
                print(f"    ✗ Exception: {e}")
        
        print(f"✅ Complex shape creation completed with {len(results)} successful operations")
        return results

    def show_websocket_status(self):
        """Show WebSocket server status"""
        print("\n🌐 WebSocket Server Status:")
        print("=" * 40)
        
        if not self.enable_websocket or not self.websocket_manager:
            print("❌ WebSocket server is disabled")
            return
        
        stats = self.websocket_manager.get_stats()
        
        print(f"Status: {'🟢 Running' if stats['running'] else '🔴 Stopped'}")
        print(f"Active connections: {stats['active_connections']}")
        print(f"Total connections: {stats['total_connections']}")
        print(f"Messages sent: {stats['messages_sent']}")
        print(f"Messages received: {stats['messages_received']}")
        print(f"Session count: {stats['session_count']}")
        
        if stats['uptime_seconds']:
            uptime_str = f"{stats['uptime_seconds']:.1f}s"
            if stats['uptime_seconds'] > 60:
                uptime_str = f"{stats['uptime_seconds']/60:.1f}m"
            print(f"Uptime: {uptime_str}")
        
        print(f"🔗 Connection URL: ws://localhost:8765")
        print(f"📱 Session ID: {self.session_id}")
    
    def show_persistent_gui_status(self):
        """Show persistent GUI status"""
        print("\n🖥️  Persistent GUI Status:")
        print("=" * 40)
        
        if not self.enable_persistent_gui or not self.persistent_gui:
            print("❌ Persistent GUI is disabled")
            return
        
        status = self.persistent_gui.get_status()
        
        print(f"Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
        if status['pid']:
            print(f"Process ID: {status['pid']}")
        print(f"Communication port: {status['communication_port']}")
        print(f"Session ID: {status['session_id']}")
        
        if status['running']:
            print("✅ GUI is ready for real-time updates")
            print("💡 Use '--real' flag with commands to see live updates")
        else:
            print("⚠️  GUI is not running - try restarting with 'restart-gui'")
    
    def start_websocket_manually(self):
        """Start WebSocket server manually"""
        if self.enable_websocket and self.websocket_manager:
            if self.websocket_manager.running:
                print("⚠️  WebSocket server is already running")
            else:
                print("🔄 Starting WebSocket server...")
                self._start_websocket_server()
        else:
            print("❌ WebSocket server is not available")
    
    def stop_persistent_gui(self):
        """Stop the persistent GUI"""
        if self.enable_persistent_gui and self.persistent_gui:
            if self.persistent_gui.is_gui_running():
                print("🛑 Stopping persistent GUI...")
                self.persistent_gui.stop_gui()
            else:
                print("⚠️  Persistent GUI is not running")
        else:
            print("❌ Persistent GUI is not available")
    
    def restart_persistent_gui(self):
        """Restart the persistent GUI"""
        if self.enable_persistent_gui and self.persistent_gui:
            print("🔄 Restarting persistent GUI...")
            
            # Stop if running
            if self.persistent_gui.is_gui_running():
                self.persistent_gui.stop_gui()
                time.sleep(2)
            
            # Start again
            if self.persistent_gui.start_persistent_gui():
                print("✅ Persistent GUI restarted successfully")
            else:
                print("❌ Failed to restart persistent GUI")
        else:
            print("❌ Persistent GUI is not available")
        """Show examples of Phase 2 & 3 enhanced commands"""
        examples = """
🚀 Phase 2 & 3 Enhanced Command Examples:

🎯 Phase 2 - Intelligent Face Selection & Operations:

  Basic Face Operations:
    add 10mm hole on the top face
    create 5mm deep pocket on flat surface  
    drill 6mm hole in the center
    make rectangular slot on side face
    add chamfer to sharp edges
  
  Advanced Face Operations:
    create 4 mounting holes in square pattern
    add threaded holes with M6 specification
    make keyway slot on cylindrical surface
    create counterbore holes for cap screws
    drill angled holes at 45 degrees
  
  Multi-Face Operations:
    add holes on all flat faces
    create pockets on top and bottom
    drill holes on cylindrical surfaces
    make slots on parallel faces

🏗️ Phase 3 - Complex Multi-Step Workflows:

  Mechanical Components:
    create a bracket with 4 mounting holes and fillets
    design a gear with 20 teeth and central hub
    build a bearing housing with mounting features
    make a shaft collar with set screws
    create a pulley with keyway and hub
  
  Assembly Workflows:
    design a gear box housing with cover and mounting
    build a motor mount with vibration damping
    create a valve body with inlet and outlet ports
    make a pump housing with impeller chamber
    design a bearing block with lubrication fittings
  
  Architectural Elements:
    create a column with base and capital
    build a staircase with railings and supports
    design a truss structure with multiple joints
    make a roof frame with rafters and beams
    create a foundation with anchor bolts
  
  Pattern & Feature Operations:
    create linear pattern of holes along edge
    make circular pattern of mounting features
    add matrix pattern of ventilation holes
    create helical pattern around cylinder
    make variable spacing pattern with fillets

✏️ Phase 1 Enhanced - Sketch-Then-Operate:

  Parametric Sketching:
    create 50mm diameter cylinder 100mm tall
    make rectangular base 100x50x10mm with fillets
    design L-shaped bracket with specific dimensions
    create hexagonal prism with 25mm sides
    make tapered cylinder with 20mm to 10mm diameter

🔄 Workflow Strategy Examples:

  Command: "create box"
  → Strategy: Simple (direct execution)
  
  Command: "create 50mm cylinder with 10mm hole"  
  → Strategy: Sketch-then-operate (Phase 1)
  
  Command: "add hole on top face"
  → Strategy: Face selection (Phase 2)
  
  Command: "create bracket with mounting holes and fillets"
  → Strategy: Complex workflow (Phase 3)

💡 Pro Tips for Advanced Workflows:

  🎯 For Face Operations:
    - Mention face location: "top", "side", "flat", "cylindrical"
    - Specify operation: "hole", "pocket", "slot", "chamfer"
    - Include dimensions: "10mm diameter", "5mm deep"
  
  🏗️ For Complex Workflows:
    - Use descriptive terms: "bracket", "housing", "assembly"
    - Mention multiple features: "holes and fillets"
    - Specify patterns: "4 holes in square pattern"
    - Include mounting: "mounting features", "bolt holes"
  
  ⚡ System Intelligence:
    - Commands are automatically analyzed for complexity
    - Optimal workflow strategy is selected automatically
    - Multi-step operations are decomposed intelligently
    - Face selection happens automatically when needed
    - Pattern operations are recognized and executed
    - Feature operations (fillets, chamfers) are applied automatically

🔧 Example Workflow Progressions:

  Simple → Complex:
    1. "create cylinder" (Phase 1)
    2. "add hole on top" (Phase 2) 
    3. "add 4 mounting holes in pattern" (Phase 2 + Pattern)
    4. "create bracket with multiple holes and fillets" (Phase 3)

  The system learns your intent and applies the most sophisticated
  workflow automatically for optimal results!
"""
        print(examples)

def main():
    parser = argparse.ArgumentParser(description="FreeCAD Command Line Interface with Real-time Features")
    parser.add_argument('--gui', action='store_true', help='Use FreeCAD GUI instead of headless mode')
    parser.add_argument('--script', help='Execute a specific script file')
    parser.add_argument('--command', help='Execute a single command and exit')
    parser.add_argument('--analyze', help='Analyze a specific FreeCAD file and exit')
    parser.add_argument('--auto-analyze', action='store_true', help='Automatically analyze state after each command')
    parser.add_argument('--llm-provider', choices=['openai', 'google'], default='openai', help='LLM provider to use (openai or google)')
    parser.add_argument('--llm-api-key', help='API key for the selected LLM provider')
    parser.add_argument('--no-websocket', action='store_true', help='Disable WebSocket server for real-time updates')
    parser.add_argument('--no-persistent-gui', action='store_true', help='Disable persistent FreeCAD GUI')
    parser.add_argument('--websocket-port', type=int, default=8765, help='WebSocket server port (default: 8765)')
    parser.add_argument('--deepseek-enabled', action='store_true', help='Enable DeepSeek R1 for complex part generation')
    parser.add_argument('--deepseek-mode', choices=['reasoning', 'fast', 'creative', 'technical'], default='reasoning', help='DeepSeek R1 generation mode')
    parser.add_argument('--deepseek-port', type=int, default=11434, help='DeepSeek R1 server port (default: 11434)')
    args = parser.parse_args()
    
    # Initialize CLI with new features
    cli = FreeCADCLI(
        use_headless=not args.gui, 
        llm_provider=args.llm_provider, 
        llm_api_key=args.llm_api_key,
        enable_websocket=not args.no_websocket,
        enable_persistent_gui=not args.no_persistent_gui,
        deepseek_enabled=args.deepseek_enabled,
        deepseek_mode=args.deepseek_mode,
        deepseek_port=args.deepseek_port
    )
    
    if args.analyze:
        # Analysis mode
        if cli.initialize():
            cli.analyze_state(args.analyze)
    elif args.script:
        # Execute script mode
        if cli.initialize():
            cli.execute_script(args.script)
    elif args.command:
        # Single command mode
        if cli.initialize():
            # Check if DeepSeek should be used for this command
            if cli.deepseek_enabled and any(keyword in args.command.lower() for keyword in ['gear', 'complex', 'bracket', 'assembly', 'housing', 'detailed']):
                print(f"🧠 Complex command detected - using DeepSeek R1: {args.command}")
                cli.execute_deepseek_command(args.command)
            else:
                cli.execute_command(args.command)
    else:
        # Interactive mode
        cli.interactive_mode()

if __name__ == "__main__":
    main()
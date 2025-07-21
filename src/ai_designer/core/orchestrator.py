"""
Main System Orchestrator
Integrates all components according to the architecture diagram
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta

from .intent_processor import IntentProcessor
from .queue_manager import QueueManager, CommandPriority
from .command_generator import StateAwareCommandGenerator
from .state_llm_integration import StateLLMIntegration
from ..services.state_service import FreeCADStateService
from ..freecad.command_executor import CommandExecutor
from ..llm.client import LLMClient
from ..realtime.websocket_manager import WebSocketManager, ProgressTracker

class SystemOrchestrator:
    """
    Main orchestrator that implements the complete architecture flow:
    User Input → Intent Processing → Command Generator → Queue Manager → Executor → State Management
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize core components
        self.state_service = None
        self.intent_processor = None
        self.command_generator = None
        self.queue_manager = None
        self.command_executor = None
        self.llm_client = None
        
        # Enhanced components for complete architecture
        # Initialize enhanced components
        self.state_llm_integration = None
        self.websocket_manager = None
        self.progress_tracker = None
        
        # Session management
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.system_running = False
        
        # Performance tracking
        self.performance_metrics = {
            'commands_processed': 0,
            'average_processing_time': 0,
            'success_rate': 0,
            'cache_hit_rate': 0
        }
        
        # Real-time features
        self.enable_realtime = self.config.get('enable_realtime', True)
        self.websocket_port = self.config.get('websocket_port', 8765)
        
        # Enhanced state management
        self.state_checkpoint_interval = self.config.get('state_checkpoint_interval', 30)  # seconds
        self.last_state_checkpoint = time.time()
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components according to architecture"""
        try:
            # 1. Initialize State Service (Storage Layer)
            print("🔧 Initializing State Service...")
            self.state_service = FreeCADStateService(
                redis_host=self.config.get('redis_host', 'localhost'),
                redis_port=self.config.get('redis_port', 6379)
            )
            
            if self.state_service.connect():
                print("✅ State Service connected")
            else:
                print("⚠️ State Service connection failed - continuing without Redis")
            
            # 2. Initialize LLM Client (AI Layer)
            print("🔧 Initializing LLM Client...")
            self.llm_client = LLMClient(
                provider=self.config.get('llm_provider', 'google'),
                api_key=self.config.get('llm_api_key')
            )
            print("✅ LLM Client initialized")
            
            # 3. Initialize Command Executor (Execution Layer)
            print("🔧 Initializing Command Executor...")
            from ..freecad.api_client import FreeCADAPIClient
            api_client = FreeCADAPIClient(
                use_headless=self.config.get('headless', True)
            )
            
            if api_client.connect():
                self.command_executor = CommandExecutor(
                    api_client=api_client,
                    state_manager=self.state_service.state_cache if self.state_service else None,
                    llm_provider=self.config.get('llm_provider', 'google'),
                    llm_api_key=self.config.get('llm_api_key')
                )
                print("✅ Command Executor initialized")
            else:
                print("❌ Failed to connect to FreeCAD")
                raise Exception("FreeCAD connection failed")
            
            # 4. Initialize Command Generator (AI Layer)
            print("🔧 Initializing Command Generator...")
            self.command_generator = StateAwareCommandGenerator(
                llm_client=self.llm_client,
                state_service=self.state_service
            )
            print("✅ Command Generator initialized")
            
            # 5. Initialize Intent Processor (AI Layer)
            print("🔧 Initializing Intent Processor...")
            self.intent_processor = IntentProcessor(
                state_service=self.state_service,
                llm_client=self.llm_client
            )
            print("✅ Intent Processor initialized")
            
            # 6. Initialize Queue Manager (Processing Layer)
            print("🔧 Initializing Queue Manager...")
            self.queue_manager = QueueManager(
                command_executor=self.command_executor,
                state_service=self.state_service,
                max_concurrent=self.config.get('max_concurrent', 3)
            )
            print("✅ Queue Manager initialized")
            
            # 7. Initialize State-LLM Integration (Enhanced AI Layer)
            print("🔧 Initializing State-LLM Integration...")
            self.state_llm_integration = StateLLMIntegration(
                state_service=self.state_service,
                llm_client=self.llm_client,
                command_executor=self.command_executor,
                queue_manager=self.queue_manager,
                intent_processor=self.intent_processor
            )
            print("✅ State-LLM Integration initialized")
            
            # 8. Initialize Real-time features (if enabled)
            if self.enable_realtime:
                print("🔧 Initializing WebSocket Manager...")
                self.websocket_manager = WebSocketManager(
                    host=self.config.get('websocket_host', 'localhost'),
                    port=self.websocket_port
                )
                
                self.progress_tracker = ProgressTracker(self.websocket_manager)
                print("✅ WebSocket Manager initialized")
            
            print("🚀 System Orchestrator fully initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize system: {e}")
            raise
    
    def start_system(self):
        """Start the complete system"""
        if self.system_running:
            print("⚠️ System already running")
            return
        
        print("🚀 Starting FreeCAD LLM Automation System...")
        
        # Start queue manager
        self.queue_manager.start()
        
        # Start WebSocket server if enabled
        if self.enable_realtime and self.websocket_manager:
            print("🌐 Starting WebSocket server...")
            # Create a task instead of using asyncio.run()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an event loop, create a task
                    loop.create_task(self.websocket_manager.start_server())
                else:
                    # If no event loop is running, use asyncio.run()
                    asyncio.run(self.websocket_manager.start_server())
            except RuntimeError:
                # Fallback: create new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.websocket_manager.start_server())
            print("✅ WebSocket server started")
        
        self.system_running = True
        print("✅ System started successfully")
        
        # Start performance monitoring
        self._start_performance_monitoring()
        
        # Start state checkpoint monitoring
        self._start_state_monitoring()
    
    def stop_system(self):
        """Stop the complete system"""
        if not self.system_running:
            return
        
        print("🛑 Stopping system...")
        
        # Stop queue manager
        if self.queue_manager:
            self.queue_manager.stop()
        
        self.system_running = False
        print("✅ System stopped")
    
    def process_user_input(self, user_input: str, session_id: str = None) -> str:
        """
        Main entry point - processes user input through the complete pipeline
        
        Architecture Flow:
        User Input → Intent Processing → Command Generation → Queue → Execution → State Update
        """
        if not self.system_running:
            return "❌ System not running. Please start the system first."
        
        session_id = session_id or "default"
        start_time = time.time()
        
        try:
            print(f"📝 Processing input: '{user_input}' (Session: {session_id[:8]})")
            
            # Step 1: Intent Processing (matches architecture diagram)
            print("🧠 Step 1: Processing intent...")
            intent_data = self.intent_processor.process_intent(user_input, session_id)
            
            if 'error' in intent_data:
                return f"❌ Intent processing failed: {intent_data['error']}"
            
            print(f"✅ Intent classified: {intent_data['intent_type']} (confidence: {intent_data['confidence']:.2f})")
            
            # Step 2: Command Generation (AI Enhancement layer)
            print("⚡ Step 2: Generating command...")
            command_data = self.command_generator.generate_command_with_state(
                user_input, intent_data, session_id
            )
            
            if 'error' in command_data:
                return f"❌ Command generation failed: {command_data['error']}"
            
            print(f"✅ Command generated: {command_data['command'][:50]}...")
            
            # Step 3: Validation (matches Validation in diagram)
            print("🔍 Step 3: Validating command...")
            validation_result = self._validate_command(command_data['command'], intent_data)
            
            if not validation_result['valid']:
                return f"❌ Command validation failed: {validation_result['reason']}"
            
            # Step 4: Queue Management (Processing Layer)
            print("📤 Step 4: Queuing command...")
            
            # Determine priority based on intent
            priority = self._determine_priority(intent_data)
            
            # Submit to queue
            command_id = self.queue_manager.submit_command(
                user_input=user_input,
                command=command_data['command'],
                session_id=session_id,
                priority=priority,
                state_context=intent_data.get('state_snapshot', {}),
                callback=self._create_completion_callback(session_id, start_time)
            )
            
            print(f"✅ Command queued: {command_id[:8]}")
            
            # Step 5: Wait for execution and get result
            print("⏳ Step 5: Waiting for execution...")
            result = self.queue_manager.get_command_result(command_id, timeout=30)
            
            if not result:
                return f"⏰ Command {command_id[:8]} timed out"
            
            # Step 6: Process result and provide response
            return self._format_response(result, command_data, intent_data, session_id)
            
        except Exception as e:
            print(f"❌ Error processing user input: {e}")
            return f"❌ Processing failed: {e}"
    
    def process_user_input_enhanced(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """
        Enhanced entry point using State-LLM Integration for intelligent decision making
        
        This method follows the complete architecture:
        User Input → Intent → State Context → LLM Decision → Validation → Execution → State Update
        """
        if not self.system_running:
            return {
                'status': 'error',
                'error': 'System not running. Please start the system first.',
                'timestamp': datetime.now().isoformat()
            }
        
        session_id = session_id or "default"
        
        try:
            # Use enhanced state-LLM integration
            if self.state_llm_integration:
                print(f"🧠 Using enhanced State-LLM Integration for: {user_input[:50]}...")
                
                # Send progress update if real-time enabled
                if self.progress_tracker:
                    command_id = f"cmd_{int(time.time() * 1000)}"
                    self.progress_tracker.start_tracking(command_id, 5, session_id)
                    
                    # Progress updates during processing
                    self.progress_tracker.update_progress(command_id, 1, "Processing intent...")
                
                # Use the integrated state-LLM flow
                result = self.state_llm_integration.process_user_request(user_input, session_id)
                
                if self.progress_tracker:
                    if result.get('status') == 'success':
                        self.progress_tracker.complete_tracking(command_id, True, "Request completed successfully")
                    else:
                        self.progress_tracker.fail_tracking(command_id, result.get('error', 'Unknown error'))
                
                # Send state change notification if real-time enabled
                if self.websocket_manager and result.get('status') == 'success':
                    execution_result = result.get('execution', {})
                    if execution_result.get('status') == 'success':
                        self.websocket_manager.send_state_change(
                            {'status': 'updated', 'session_id': session_id},
                            session_id
                        )
                
                return result
            
            else:
                # Fallback to original processing
                print("⚠️ State-LLM Integration not available, using fallback...")
                return self._process_user_input_fallback(user_input, session_id)
        
        except Exception as e:
            print(f"❌ Error in enhanced processing: {e}")
            
            # Send error notification if real-time enabled
            if self.websocket_manager:
                self.websocket_manager.send_error(
                    f"Processing failed: {str(e)}",
                    {'user_input': user_input, 'session_id': session_id},
                    session_id
                )
            
            return {
                'status': 'error',
                'error': str(e),
                'user_input': user_input,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def _process_user_input_fallback(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Fallback processing method using original flow"""
        try:
            # This maintains the original process_user_input logic but returns structured data
            original_result = self.process_user_input(user_input, session_id)
            
            # Convert string result to structured format
            if "✅" in original_result:
                status = "success"
            elif "❌" in original_result:
                status = "error"
            elif "⏰" in original_result:
                status = "timeout"
            else:
                status = "unknown"
            
            return {
                'status': status,
                'message': original_result,
                'user_input': user_input,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'processing_method': 'fallback'
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'user_input': user_input,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'processing_method': 'fallback'
            }
    
    def _validate_command(self, command: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated command (Validation step in architecture)"""
        
        # Basic validation checks
        if not command or not command.strip():
            return {'valid': False, 'reason': 'Empty command'}
        
        # Check for dangerous operations
        dangerous_patterns = ['rm ', 'del ', 'format', 'shutdown']
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                return {'valid': False, 'reason': f'Dangerous operation detected: {pattern}'}
        
        # Check for basic FreeCAD syntax
        if 'doc.' not in command and 'App.' not in command:
            # Allow simple analysis commands
            if intent_data.get('intent_type') != 'analyze_state':
                return {'valid': False, 'reason': 'Not a valid FreeCAD command'}
        
        return {'valid': True, 'reason': 'Command validation passed'}
    
    def _determine_priority(self, intent_data: Dict[str, Any]) -> CommandPriority:
        """Determine command priority based on intent"""
        intent_type = intent_data.get('intent_type')
        confidence = intent_data.get('confidence', 0.5)
        
        # High priority for state analysis and system commands
        if intent_type in ['analyze_state', 'save_export']:
            return CommandPriority.HIGH
        
        # Normal priority for create operations
        if intent_type == 'create_object' and confidence > 0.8:
            return CommandPriority.NORMAL
        
        # Low priority for uncertain commands
        if confidence < 0.6:
            return CommandPriority.LOW
        
        return CommandPriority.NORMAL
    
    def _create_completion_callback(self, session_id: str, start_time: float) -> Callable:
        """Create callback for command completion"""
        def callback(command_result):
            processing_time = time.time() - start_time
            
            # Update performance metrics
            self.performance_metrics['commands_processed'] += 1
            
            # Update average processing time
            total_commands = self.performance_metrics['commands_processed']
            current_avg = self.performance_metrics['average_processing_time']
            self.performance_metrics['average_processing_time'] = (
                (current_avg * (total_commands - 1) + processing_time) / total_commands
            )
            
            # Update success rate
            if command_result.status.value == 'completed':
                success_count = self.performance_metrics.get('success_count', 0) + 1
                self.performance_metrics['success_count'] = success_count
                self.performance_metrics['success_rate'] = success_count / total_commands
            
            # Update session context
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = {
                    'created_at': datetime.now(),
                    'command_count': 0,
                    'last_activity': datetime.now()
                }
            
            session = self.active_sessions[session_id]
            session['command_count'] += 1
            session['last_activity'] = datetime.now()
            session['last_processing_time'] = processing_time
            
            print(f"📊 Command completed in {processing_time:.2f}s (Session: {session_id[:8]})")
        
        return callback
    
    def _format_response(self, result, command_data: Dict[str, Any], 
                        intent_data: Dict[str, Any], session_id: str) -> str:
        """Format the final response to user"""
        
        status_icons = {
            'completed': '✅',
            'failed': '❌',
            'timeout': '⏰',
            'cancelled': '🚫'
        }
        
        status = result.status.value
        icon = status_icons.get(status, '❓')
        
        if status == 'completed':
            # Success response
            response_parts = [
                f"{icon} Command executed successfully!",
                f"📊 Processing time: {result.completed_at - result.started_at if result.completed_at and result.started_at else 'N/A'}"
            ]
            
            # Add next steps if available
            next_steps = command_data.get('next_steps', [])
            if next_steps:
                response_parts.append("🔮 Suggested next steps:")
                for step in next_steps[:3]:  # Limit to 3 suggestions
                    response_parts.append(f"  • {step.replace('_', ' ').title()}")
            
            # Add state changes
            state_changes = command_data.get('state_changes', {})
            if state_changes:
                response_parts.append("📈 State changes:")
                for change, value in state_changes.items():
                    response_parts.append(f"  • {change.replace('_', ' ').title()}: {value}")
            
            return "\\n".join(response_parts)
        
        else:
            # Error response
            error_msg = result.error or "Unknown error occurred"
            return f"{icon} Command failed: {error_msg}"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'system_running': self.system_running,
            'active_sessions': len(self.active_sessions),
            'queue_status': self.queue_manager.get_queue_status() if self.queue_manager else {},
            'performance_metrics': self.performance_metrics,
            'components_status': {
                'state_service': self.state_service.connected if self.state_service else False,
                'intent_processor': self.intent_processor is not None,
                'command_generator': self.command_generator is not None,
                'queue_manager': self.queue_manager is not None,
                'command_executor': self.command_executor is not None,
                'llm_client': self.llm_client is not None
            }
        }
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a specific session"""
        if session_id not in self.active_sessions:
            return {'error': f'Session {session_id} not found'}
        
        session = self.active_sessions[session_id]
        
        # Get state information
        state_info = {}
        if self.state_service:
            try:
                state_info = self.state_service.get_latest_state(session_id) or {}
            except Exception as e:
                state_info = {'error': f'Failed to get state: {e}'}
        
        return {
            'session_id': session_id,
            'created_at': session['created_at'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
            'command_count': session['command_count'],
            'last_processing_time': session.get('last_processing_time', 0),
            'current_state': state_info
        }
    
    def _start_performance_monitoring(self):
        """Start background performance monitoring"""
        def monitor():
            while self.system_running:
                try:
                    # Clean up old sessions (older than 1 hour)
                    cutoff_time = datetime.now() - timedelta(hours=1)
                    old_sessions = [
                        sid for sid, session in self.active_sessions.items()
                        if session['last_activity'] < cutoff_time
                    ]
                    
                    for sid in old_sessions:
                        del self.active_sessions[sid]
                    
                    if old_sessions:
                        print(f"🧹 Cleaned up {len(old_sessions)} old sessions")
                    
                except Exception as e:
                    print(f"⚠️ Monitoring error: {e}")
                
                time.sleep(300)  # Check every 5 minutes
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _start_state_monitoring(self):
        """Start background state monitoring for intelligent checkpointing"""
        def state_monitor():
            while self.system_running:
                try:
                    current_time = time.time()
                    
                    # Check if it's time for a state checkpoint
                    if current_time - self.last_state_checkpoint > self.state_checkpoint_interval:
                        print("📊 Creating state checkpoint...")
                        
                        # Trigger state analysis for all active sessions
                        for session_id in self.active_sessions.keys():
                            try:
                                if self.state_service:
                                    self.state_service.analyze_and_cache(session_id)
                                    
                                # Send state update to WebSocket clients
                                if self.websocket_manager:
                                    latest_state = self.state_service.get_latest_state(f"session_{session_id}")
                                    if latest_state:
                                        self.websocket_manager.send_state_change(
                                            {
                                                'checkpoint': True,
                                                'object_count': latest_state.get('object_count', 0),
                                                'timestamp': datetime.now().isoformat()
                                            },
                                            session_id
                                        )
                            except Exception as e:
                                print(f"⚠️ Failed to checkpoint session {session_id}: {e}")
                        
                        self.last_state_checkpoint = current_time
                        print(f"✅ State checkpoint completed for {len(self.active_sessions)} sessions")
                    
                    time.sleep(5)  # Check every 5 seconds
                
                except Exception as e:
                    print(f"❌ State monitoring error: {e}")
                    time.sleep(10)  # Longer delay on error
        
        monitor_thread = threading.Thread(target=state_monitor, daemon=True)
        monitor_thread.start()
        print("📊 State monitoring started")
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive session state for decision making"""
        if not self.state_service:
            return {'error': 'State service not available'}
        
        try:
            # Get cached state
            state_key = f"session_{session_id}"
            cached_state = self.state_service.get_latest_state(state_key)
            
            # Get session metadata
            session_info = self.active_sessions.get(session_id, {})
            
            # Combine state information
            return {
                'session_id': session_id,
                'cached_state': cached_state,
                'session_info': session_info,
                'last_checkpoint': self.last_state_checkpoint,
                'system_metrics': self.get_performance_metrics(),
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                'error': f'Failed to get session state: {e}',
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def force_state_checkpoint(self, session_id: str = None) -> Dict[str, Any]:
        """Force immediate state checkpoint for a session or all sessions"""
        results = {}
        
        sessions_to_checkpoint = [session_id] if session_id else list(self.active_sessions.keys())
        
        for sid in sessions_to_checkpoint:
            try:
                if self.state_service:
                    result = self.state_service.analyze_and_cache(sid)
                    results[sid] = {
                        'status': 'success',
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Notify WebSocket clients
                    if self.websocket_manager:
                        self.websocket_manager.send_state_change(
                            {
                                'forced_checkpoint': True,
                                'result': result,
                                'timestamp': datetime.now().isoformat()
                            },
                            sid
                        )
                else:
                    results[sid] = {
                        'status': 'error',
                        'error': 'State service not available'
                    }
            
            except Exception as e:
                results[sid] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        self.last_state_checkpoint = time.time()
        return results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        base_metrics = self.performance_metrics.copy()
        
        # Add real-time metrics
        if self.websocket_manager:
            ws_stats = self.websocket_manager.get_stats()
            base_metrics['websocket'] = ws_stats
        
        # Add state-LLM integration metrics
        if self.state_llm_integration:
            llm_metrics = self.state_llm_integration.get_performance_metrics()
            base_metrics['state_llm'] = llm_metrics
        
        # Add queue metrics
        if self.queue_manager:
            queue_status = self.queue_manager.get_queue_status()
            base_metrics['queue'] = queue_status
        
        # Add session metrics
        base_metrics['sessions'] = {
            'active_count': len(self.active_sessions),
            'session_ids': list(self.active_sessions.keys())
        }
        
        return base_metrics
    
    def interactive_mode(self):
        """Start interactive mode for testing"""
        if not self.system_running:
            self.start_system()
        
        print("\\n" + "="*60)
        print("🚀 FreeCAD LLM Automation - Interactive Mode")
        print("="*60)
        print("Commands:")
        print("  • Type your request in natural language")
        print("  • 'status' - Show system status") 
        print("  • 'sessions' - Show active sessions")
        print("  • 'help' - Show this help")
        print("  • 'quit' - Exit interactive mode")
        print("="*60)
        
        session_id = f"interactive_{int(time.time())}"
        
        while True:
            try:
                user_input = input(f"\\nFreeCAD[{session_id[:8]}]> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                elif user_input.lower() == 'status':
                    status = self.get_system_status()
                    print("\\n📊 System Status:")
                    print(f"  Running: {status['system_running']}")
                    print(f"  Active Sessions: {status['active_sessions']}")
                    print(f"  Commands Processed: {status['performance_metrics']['commands_processed']}")
                    print(f"  Success Rate: {status['performance_metrics']['success_rate']:.2%}")
                    print(f"  Avg Processing Time: {status['performance_metrics']['average_processing_time']:.2f}s")
                
                elif user_input.lower() == 'sessions':
                    print("\\n👥 Active Sessions:")
                    for sid in self.active_sessions:
                        session_info = self.get_session_info(sid)
                        print(f"  • {sid[:8]}: {session_info['command_count']} commands")
                
                elif user_input.lower() == 'help':
                    print("\\n📖 Available Commands:")
                    print("  • Natural language: 'create a box', 'analyze current state', etc.")
                    print("  • System commands: 'status', 'sessions', 'quit'")
                
                else:
                    # Process as normal user input
                    print(f"\\n🔄 Processing: {user_input}")
                    result = self.process_user_input(user_input, session_id)
                    print(f"\\n{result}")
            
            except KeyboardInterrupt:
                print("\\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\\n❌ Error: {e}")

# Global instance for easy access
orchestrator = None

def get_orchestrator(config: Dict[str, Any] = None) -> SystemOrchestrator:
    """Get or create the global orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        orchestrator = SystemOrchestrator(config)
    return orchestrator

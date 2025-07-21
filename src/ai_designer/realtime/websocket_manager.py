"""
WebSocket Manager for Real-time Updates
Provides live progress tracking and updates to connected clients
"""

import asyncio
import json
import time
import websockets
from typing import Dict, Any, Set, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from queue import Queue

class MessageType(Enum):
    """Types of WebSocket messages"""
    PROGRESS_UPDATE = "progress_update"
    COMMAND_STATUS = "command_status"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    SYSTEM_STATUS = "system_status"
    USER_NOTIFICATION = "user_notification"
    LIVE_PREVIEW = "live_preview"

@dataclass
class ProgressUpdate:
    """Progress update message"""
    command_id: str
    progress: float  # 0.0 to 1.0
    status: str
    message: str
    timestamp: datetime
    session_id: str
    estimated_remaining: Optional[int] = None  # seconds

@dataclass
class WebSocketMessage:
    """Standard WebSocket message format"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime
    session_id: Optional[str] = None
    target_clients: Optional[List[str]] = None  # Specific client IDs

class WebSocketManager:
    """
    Manages WebSocket connections and real-time updates
    """
    
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.session_clients: Dict[str, Set[str]] = {}  # session_id -> client_ids
        
        # Message queues for async processing
        self.message_queue = Queue()
        self.broadcast_queue = Queue()
        
        # Server state
        self.server = None
        self.running = False
        
        # Progress tracking
        self.active_commands: Dict[str, ProgressUpdate] = {}
        
        # Performance monitoring
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'start_time': None
        }
        
        # Background worker thread
        self.worker_thread = None
        self.stop_event = threading.Event()
    
    async def start_server(self):
        """Start the WebSocket server"""
        print(f"🌐 Starting WebSocket server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Start background worker
        self.worker_thread = threading.Thread(target=self._background_worker, daemon=True)
        self.worker_thread.start()
        
        print(f"✅ WebSocket server started successfully")
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if not self.running:
            return
        
        print("🛑 Stopping WebSocket server...")
        
        self.running = False
        self.stop_event.set()
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients.values()],
                return_exceptions=True
            )
        
        # Stop the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        print("✅ WebSocket server stopped")
    
    async def handle_client(self, websocket, path):
        """Handle new client connection"""
        client_id = f"client_{int(time.time() * 1000)}_{len(self.clients)}"
        
        try:
            # Register client
            self.clients[client_id] = websocket
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            
            print(f"👤 Client connected: {client_id}")
            
            # Send welcome message
            welcome_msg = WebSocketMessage(
                type=MessageType.SYSTEM_STATUS,
                data={
                    'client_id': client_id,
                    'server_status': 'connected',
                    'server_time': datetime.now().isoformat()
                },
                timestamp=datetime.now()
            )
            
            await self.send_to_client(client_id, welcome_msg)
            
            # Handle messages from client
            async for message in websocket:
                await self.handle_client_message(client_id, message)
        
        except websockets.exceptions.ConnectionClosed:
            print(f"👋 Client disconnected: {client_id}")
        
        except Exception as e:
            print(f"❌ Error handling client {client_id}: {e}")
        
        finally:
            # Cleanup
            if client_id in self.clients:
                del self.clients[client_id]
                self.stats['active_connections'] -= 1
            
            # Remove from session mapping
            for session_id, client_ids in self.session_clients.items():
                client_ids.discard(client_id)
    
    async def handle_client_message(self, client_id: str, message: str):
        """Handle message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            self.stats['messages_received'] += 1
            
            if msg_type == 'register_session':
                session_id = data.get('session_id', 'default')
                self.register_client_session(client_id, session_id)
                
                response = WebSocketMessage(
                    type=MessageType.SYSTEM_STATUS,
                    data={
                        'status': 'session_registered',
                        'session_id': session_id,
                        'client_id': client_id
                    },
                    timestamp=datetime.now(),
                    session_id=session_id
                )
                
                await self.send_to_client(client_id, response)
            
            elif msg_type == 'ping':
                response = WebSocketMessage(
                    type=MessageType.SYSTEM_STATUS,
                    data={'status': 'pong', 'timestamp': datetime.now().isoformat()},
                    timestamp=datetime.now()
                )
                await self.send_to_client(client_id, response)
            
            elif msg_type == 'get_status':
                await self.send_system_status(client_id)
            
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON from client {client_id}: {message}")
        
        except Exception as e:
            print(f"❌ Error processing message from {client_id}: {e}")
    
    def register_client_session(self, client_id: str, session_id: str):
        """Register a client with a specific session"""
        if session_id not in self.session_clients:
            self.session_clients[session_id] = set()
        
        self.session_clients[session_id].add(client_id)
        print(f"📝 Client {client_id} registered for session {session_id}")
    
    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """Send message to specific client"""
        if client_id not in self.clients:
            return False
        
        try:
            websocket = self.clients[client_id]
            message_data = {
                'type': message.type.value,
                'data': message.data,
                'timestamp': message.timestamp.isoformat(),
                'session_id': message.session_id
            }
            
            await websocket.send(json.dumps(message_data))
            self.stats['messages_sent'] += 1
            return True
        
        except Exception as e:
            print(f"❌ Failed to send message to {client_id}: {e}")
            return False
    
    async def send_to_session(self, session_id: str, message: WebSocketMessage):
        """Send message to all clients in a session"""
        if session_id not in self.session_clients:
            return 0
        
        sent_count = 0
        client_ids = list(self.session_clients[session_id])  # Copy to avoid modification during iteration
        
        for client_id in client_ids:
            if await self.send_to_client(client_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return 0
        
        sent_count = 0
        client_ids = list(self.clients.keys())  # Copy to avoid modification during iteration
        
        for client_id in client_ids:
            if await self.send_to_client(client_id, message):
                sent_count += 1
        
        return sent_count
    
    async def send_system_status(self, client_id: str):
        """Send current system status to client"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        status_msg = WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,
            data={
                'server_status': 'running' if self.running else 'stopped',
                'active_connections': self.stats['active_connections'],
                'total_connections': self.stats['total_connections'],
                'messages_sent': self.stats['messages_sent'],
                'messages_received': self.stats['messages_received'],
                'uptime_seconds': uptime,
                'active_commands': len(self.active_commands),
                'server_time': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        
        await self.send_to_client(client_id, status_msg)
    
    # Public API methods for integration with other components
    
    def send_progress_update(self, command_id: str, progress: float, status: str, 
                           message: str, session_id: str = None, estimated_remaining: int = None):
        """Send progress update (thread-safe)"""
        update = ProgressUpdate(
            command_id=command_id,
            progress=progress,
            status=status,
            message=message,
            timestamp=datetime.now(),
            session_id=session_id or "default",
            estimated_remaining=estimated_remaining
        )
        
        self.active_commands[command_id] = update
        
        # Queue for async sending
        ws_message = WebSocketMessage(
            type=MessageType.PROGRESS_UPDATE,
            data=asdict(update),
            timestamp=datetime.now(),
            session_id=session_id
        )
        
        self.message_queue.put(('session', session_id, ws_message))
    
    def send_command_status(self, command_id: str, status: str, result: Dict[str, Any], 
                          session_id: str = None):
        """Send command status update (thread-safe)"""
        message = WebSocketMessage(
            type=MessageType.COMMAND_STATUS,
            data={
                'command_id': command_id,
                'status': status,
                'result': result,
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            session_id=session_id
        )
        
        self.message_queue.put(('session', session_id, message))
        
        # Remove from active commands if completed
        if status in ['completed', 'failed', 'cancelled']:
            self.active_commands.pop(command_id, None)
    
    def send_state_change(self, state_data: Dict[str, Any], session_id: str = None):
        """Send state change notification (thread-safe)"""
        message = WebSocketMessage(
            type=MessageType.STATE_CHANGE,
            data={
                'state': state_data,
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            session_id=session_id
        )
        
        self.message_queue.put(('session', session_id, message))
    
    def send_error(self, error_message: str, error_details: Dict[str, Any] = None, 
                  session_id: str = None):
        """Send error notification (thread-safe)"""
        message = WebSocketMessage(
            type=MessageType.ERROR,
            data={
                'error': error_message,
                'details': error_details or {},
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            session_id=session_id
        )
        
        self.message_queue.put(('session', session_id, message))
    
    def send_user_notification(self, notification: str, notification_type: str = "info", 
                             session_id: str = None):
        """Send user notification (thread-safe)"""
        message = WebSocketMessage(
            type=MessageType.USER_NOTIFICATION,
            data={
                'message': notification,
                'type': notification_type,  # info, warning, error, success
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            session_id=session_id
        )
        
        self.message_queue.put(('session', session_id, message))
    
    def _background_worker(self):
        """Background worker to process message queue"""
        while not self.stop_event.is_set():
            try:
                if not self.message_queue.empty():
                    send_type, target, message = self.message_queue.get(timeout=0.1)
                    
                    # Schedule async sending
                    if self.running:
                        asyncio.run_coroutine_threadsafe(
                            self._send_queued_message(send_type, target, message),
                            asyncio.get_event_loop()
                        )
                
                time.sleep(0.01)  # Small delay to prevent busy waiting
            
            except Exception as e:
                print(f"❌ Background worker error: {e}")
                time.sleep(1)
    
    async def _send_queued_message(self, send_type: str, target: str, message: WebSocketMessage):
        """Send queued message asynchronously"""
        try:
            if send_type == 'session':
                await self.send_to_session(target, message)
            elif send_type == 'client':
                await self.send_to_client(target, message)
            elif send_type == 'broadcast':
                await self.broadcast_to_all(message)
        
        except Exception as e:
            print(f"❌ Failed to send queued message: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket server statistics"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'active_commands': len(self.active_commands),
            'session_count': len(self.session_clients),
            'running': self.running
        }

# Progress tracker that integrates with the WebSocket manager
class ProgressTracker:
    """
    Utility class for tracking command progress and sending updates
    """
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.active_trackers: Dict[str, Dict[str, Any]] = {}
    
    def start_tracking(self, command_id: str, total_steps: int, session_id: str = None):
        """Start tracking progress for a command"""
        self.active_trackers[command_id] = {
            'total_steps': total_steps,
            'current_step': 0,
            'session_id': session_id,
            'start_time': time.time(),
            'last_update': time.time()
        }
        
        self.ws_manager.send_progress_update(
            command_id=command_id,
            progress=0.0,
            status="started",
            message="Command execution started",
            session_id=session_id
        )
    
    def update_progress(self, command_id: str, step: int = None, message: str = None):
        """Update progress for a command"""
        if command_id not in self.active_trackers:
            return
        
        tracker = self.active_trackers[command_id]
        
        if step is not None:
            tracker['current_step'] = step
        else:
            tracker['current_step'] += 1
        
        progress = tracker['current_step'] / tracker['total_steps']
        progress = min(progress, 1.0)
        
        # Estimate remaining time
        elapsed = time.time() - tracker['start_time']
        if progress > 0:
            total_estimated = elapsed / progress
            remaining = max(0, total_estimated - elapsed)
        else:
            remaining = None
        
        tracker['last_update'] = time.time()
        
        self.ws_manager.send_progress_update(
            command_id=command_id,
            progress=progress,
            status="running",
            message=message or f"Step {tracker['current_step']}/{tracker['total_steps']}",
            session_id=tracker['session_id'],
            estimated_remaining=int(remaining) if remaining else None
        )
    
    def complete_tracking(self, command_id: str, success: bool = True, message: str = None):
        """Complete progress tracking for a command"""
        if command_id not in self.active_trackers:
            return
        
        tracker = self.active_trackers[command_id]
        
        self.ws_manager.send_progress_update(
            command_id=command_id,
            progress=1.0,
            status="completed" if success else "failed",
            message=message or ("Command completed successfully" if success else "Command failed"),
            session_id=tracker['session_id']
        )
        
        del self.active_trackers[command_id]
    
    def fail_tracking(self, command_id: str, error_message: str):
        """Mark tracking as failed"""
        self.complete_tracking(command_id, success=False, message=f"Error: {error_message}")
    
    def get_active_commands(self) -> List[str]:
        """Get list of actively tracked commands"""
        return list(self.active_trackers.keys())

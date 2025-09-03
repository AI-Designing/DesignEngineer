"""
Queue Manager and Command Queue System
Manages command execution queue with priority and dependency handling
"""

import asyncio
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CommandPriority(Enum):
    """Command priority levels"""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class CommandStatus(Enum):
    """Command execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class QueuedCommand:
    """Represents a command in the execution queue"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command: str = ""
    priority: CommandPriority = CommandPriority.NORMAL
    session_id: str = ""
    user_input: str = ""
    state_context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300  # 5 minutes default
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: CommandStatus = CommandStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    callback: Optional[Callable] = None


class CommandQueue:
    """
    Priority-based command queue with dependency management
    """

    def __init__(self, max_concurrent=3):
        self.queue = queue.PriorityQueue()
        self.active_commands: Dict[str, QueuedCommand] = {}
        self.completed_commands: Dict[str, QueuedCommand] = {}
        self.max_concurrent = max_concurrent
        self.running = False
        self.worker_thread = None
        self._lock = threading.Lock()

    def add_command(self, command: QueuedCommand) -> str:
        """Add command to queue"""
        with self._lock:
            # Priority queue uses tuple (priority_value, timestamp, command)
            # Lower priority_value = higher priority
            priority_value = command.priority.value
            timestamp = time.time()

            self.queue.put((priority_value, timestamp, command))
            print(
                f"🔄 Command queued: {command.id[:8]} (Priority: {command.priority.name})"
            )

            return command.id

    def get_next_command(self) -> Optional[QueuedCommand]:
        """Get next command from queue (blocking)"""
        try:
            _, _, command = self.queue.get(timeout=1.0)
            return command
        except queue.Empty:
            return None

    def get_command_status(self, command_id: str) -> Optional[CommandStatus]:
        """Get status of a specific command"""
        with self._lock:
            if command_id in self.active_commands:
                return self.active_commands[command_id].status
            elif command_id in self.completed_commands:
                return self.completed_commands[command_id].status
            return None

    def get_queue_info(self) -> Dict[str, Any]:
        """Get current queue information"""
        with self._lock:
            return {
                "pending_count": self.queue.qsize(),
                "active_count": len(self.active_commands),
                "completed_count": len(self.completed_commands),
                "active_commands": [
                    {
                        "id": cmd.id[:8],
                        "status": cmd.status.value,
                        "started_at": (
                            cmd.started_at.isoformat() if cmd.started_at else None
                        ),
                    }
                    for cmd in self.active_commands.values()
                ],
            }

    def cancel_command(self, command_id: str) -> bool:
        """Cancel a pending or running command"""
        with self._lock:
            if command_id in self.active_commands:
                command = self.active_commands[command_id]
                command.status = CommandStatus.CANCELLED
                command.completed_at = datetime.now()
                self.completed_commands[command_id] = command
                del self.active_commands[command_id]
                return True
            return False


class QueueManager:
    """
    High-level queue manager with load balancing and dependency resolution
    """

    def __init__(self, command_executor=None, state_service=None, max_concurrent=3):
        self.command_queue = CommandQueue(max_concurrent)
        self.command_executor = command_executor
        self.state_service = state_service
        self.running = False
        self.worker_threads = []
        self.dependency_graph: Dict[str, List[str]] = {}
        self._shutdown_event = threading.Event()

    def start(self):
        """Start the queue processing"""
        if self.running:
            return

        self.running = True
        self._shutdown_event.clear()

        # Start worker threads
        for i in range(self.command_queue.max_concurrent):
            worker = threading.Thread(
                target=self._worker_loop, name=f"QueueWorker-{i+1}", daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)

        print(f"🚀 Queue manager started with {len(self.worker_threads)} workers")

    def stop(self, timeout=30):
        """Stop the queue processing"""
        if not self.running:
            return

        print("🛑 Stopping queue manager...")
        self.running = False
        self._shutdown_event.set()

        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=timeout)

        self.worker_threads.clear()
        print("✅ Queue manager stopped")

    def submit_command(
        self,
        user_input: str,
        command: str,
        session_id: str = None,
        priority: CommandPriority = CommandPriority.NORMAL,
        state_context: Dict[str, Any] = None,
        dependencies: List[str] = None,
        callback: Callable = None,
    ) -> str:
        """Submit a command for execution"""

        queued_command = QueuedCommand(
            command=command,
            user_input=user_input,
            session_id=session_id or "default",
            priority=priority,
            state_context=state_context or {},
            dependencies=dependencies or [],
            callback=callback,
        )

        command_id = self.command_queue.add_command(queued_command)

        # Update dependency graph
        if dependencies:
            self.dependency_graph[command_id] = dependencies

        return command_id

    def _worker_loop(self):
        """Main worker loop for processing commands"""
        while self.running and not self._shutdown_event.is_set():
            try:
                # Get next command
                command = self.command_queue.get_next_command()
                if not command:
                    continue

                # Check if dependencies are satisfied
                if not self._dependencies_satisfied(command):
                    # Re-queue the command
                    self.command_queue.add_command(command)
                    time.sleep(0.1)  # Small delay to prevent busy waiting
                    continue

                # Move to active commands
                with self.command_queue._lock:
                    self.command_queue.active_commands[command.id] = command

                # Execute the command
                self._execute_command(command)

                # Move to completed commands
                with self.command_queue._lock:
                    if command.id in self.command_queue.active_commands:
                        del self.command_queue.active_commands[command.id]
                    self.command_queue.completed_commands[command.id] = command

                # Call callback if provided
                if command.callback:
                    try:
                        command.callback(command)
                    except Exception as e:
                        print(f"❌ Callback error for command {command.id[:8]}: {e}")

            except Exception as e:
                print(f"❌ Worker error: {e}")
                time.sleep(1)  # Prevent rapid error loops

    def _dependencies_satisfied(self, command: QueuedCommand) -> bool:
        """Check if command dependencies are satisfied"""
        if not command.dependencies:
            return True

        with self.command_queue._lock:
            for dep_id in command.dependencies:
                # Check if dependency is completed successfully
                if dep_id not in self.command_queue.completed_commands:
                    return False

                dep_command = self.command_queue.completed_commands[dep_id]
                if dep_command.status != CommandStatus.COMPLETED:
                    return False

        return True

    def _execute_command(self, command: QueuedCommand):
        """Execute a single command"""
        try:
            command.status = CommandStatus.RUNNING
            command.started_at = datetime.now()

            print(f"⚡ Executing command {command.id[:8]}: {command.user_input}")

            # Check for timeout
            def timeout_handler():
                time.sleep(command.timeout_seconds)
                if command.status == CommandStatus.RUNNING:
                    command.status = CommandStatus.TIMEOUT
                    command.error = (
                        f"Command timed out after {command.timeout_seconds} seconds"
                    )
                    command.completed_at = datetime.now()

            timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
            timeout_thread.start()

            # Execute the actual command
            if self.command_executor:
                # Update state context before execution
                if self.state_service:
                    current_state = self.state_service.get_latest_state()
                    if current_state:
                        command.state_context.update(current_state)

                # Execute command
                result = self.command_executor.execute(command.command)

                if command.status == CommandStatus.RUNNING:  # Not timed out
                    command.result = result
                    command.status = CommandStatus.COMPLETED
                    command.completed_at = datetime.now()

                    print(f"✅ Command {command.id[:8]} completed successfully")

                    # Update state cache after successful execution
                    if self.state_service and result.get("status") == "success":
                        try:
                            self.state_service.analyze_and_cache(command.session_id)
                        except Exception as e:
                            print(f"⚠️ Failed to update state cache: {e}")
            else:
                command.error = "No command executor available"
                command.status = CommandStatus.FAILED
                command.completed_at = datetime.now()

        except Exception as e:
            command.error = str(e)
            command.status = CommandStatus.FAILED
            command.completed_at = datetime.now()

            print(f"❌ Command {command.id[:8]} failed: {e}")

            # Retry logic
            if command.retry_count < command.max_retries:
                command.retry_count += 1
                command.status = CommandStatus.PENDING
                command.started_at = None
                command.error = None

                print(
                    f"🔄 Retrying command {command.id[:8]} (attempt {command.retry_count + 1}/{command.max_retries + 1})"
                )

                # Re-queue for retry
                self.command_queue.add_command(command)
                return

    def get_command_result(
        self, command_id: str, timeout: int = 30
    ) -> Optional[QueuedCommand]:
        """Wait for command completion and return result"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            with self.command_queue._lock:
                if command_id in self.command_queue.completed_commands:
                    return self.command_queue.completed_commands[command_id]

            time.sleep(0.1)

        return None  # Timeout

    def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status"""
        queue_info = self.command_queue.get_queue_info()

        return {
            **queue_info,
            "manager_running": self.running,
            "worker_count": len(self.worker_threads),
            "dependency_count": len(self.dependency_graph),
        }

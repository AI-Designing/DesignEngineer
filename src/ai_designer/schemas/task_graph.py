"""
Task graph schemas for hierarchical task decomposition.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task node."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskNode(BaseModel):
    """A single task in the decomposition graph."""

    task_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique task identifier"
    )
    description: str = Field(..., min_length=1, description="Task description")
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current task status"
    )

    # CAD operation details
    operation_type: str = Field(
        ..., description="Type of CAD operation (sketch, extrude, fillet, etc.)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Operation parameters"
    )

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list, description="Task IDs this task depends on"
    )

    # Execution tracking
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated duration in seconds"
    )
    actual_duration: Optional[float] = Field(
        default=None, description="Actual execution duration"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="Task start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Task completion timestamp"
    )

    # Output
    output: Optional[Dict[str, Any]] = Field(
        default=None, description="Task execution output"
    )
    errors: List[str] = Field(
        default_factory=list, description="Errors encountered during execution"
    )

    def mark_started(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def mark_completed(self, output: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if output:
            self.output = output
        if self.started_at:
            self.actual_duration = (datetime.utcnow() - self.started_at).total_seconds()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.errors.append(error)
        if self.started_at:
            self.actual_duration = (datetime.utcnow() - self.started_at).total_seconds()


class TaskDependency(BaseModel):
    """Edge in the task dependency graph."""

    from_task: str = Field(..., description="Source task ID")
    to_task: str = Field(..., description="Target task ID (depends on from_task)")
    dependency_type: str = Field(
        default="requires", description="Type of dependency (requires, optional, etc.)"
    )


class TaskGraph(BaseModel):
    """Hierarchical graph of tasks for CAD design generation."""

    graph_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique graph identifier"
    )
    request_id: UUID = Field(..., description="Links to DesignRequest/DesignState")

    # Graph structure
    nodes: Dict[str, TaskNode] = Field(
        default_factory=dict, description="Task nodes indexed by task_id"
    )
    edges: List[TaskDependency] = Field(
        default_factory=list, description="Dependency edges"
    )

    # Metadata
    total_tasks: int = Field(default=0, description="Total number of tasks")
    completed_tasks: int = Field(default=0, description="Number of completed tasks")
    failed_tasks: int = Field(default=0, description="Number of failed tasks")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Graph creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )

    @property
    def complexity_score(self) -> float:
        """Compute a complexity score based on task count and dependency depth.

        Returns:
            Float between 0.0 and 1.0 representing relative complexity.
        """
        if not self.nodes:
            return 0.0
        task_count = len(self.nodes)
        dep_count = len(self.edges)
        levels = self.get_execution_order()
        depth = len(levels) if levels else 1
        # Weighted formula: tasks, deps, and depth all contribute
        raw = (task_count * 0.4) + (dep_count * 0.3) + (depth * 0.3)
        # Normalize to 0-1 range (10 is "very complex")
        return min(raw / 10.0, 1.0)

    def add_task(self, task: TaskNode) -> None:
        """Add a task node to the graph."""
        self.nodes[task.task_id] = task
        self.total_tasks = len(self.nodes)
        self.updated_at = datetime.utcnow()

    def add_dependency(
        self, from_task: str, to_task: str, dependency_type: str = "requires"
    ) -> None:
        """Add a dependency edge."""
        if from_task not in self.nodes or to_task not in self.nodes:
            raise ValueError(f"Both tasks must exist in graph: {from_task}, {to_task}")

        dependency = TaskDependency(
            from_task=from_task, to_task=to_task, dependency_type=dependency_type
        )
        self.edges.append(dependency)
        self.nodes[to_task].depends_on.append(from_task)
        self.updated_at = datetime.utcnow()

    def get_ready_tasks(self) -> List[TaskNode]:
        """Get tasks that are ready to execute (dependencies met)."""
        ready: List[TaskNode] = []
        for task in self.nodes.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are completed
            deps_completed = all(
                self.nodes[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.depends_on
            )
            if deps_completed:
                ready.append(task)

        return ready

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """Get a task by ID."""
        return self.nodes.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update a task's status and graph metrics."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        old_status = task.status
        task.status = status

        # Update counters
        if status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
            self.completed_tasks += 1
        elif status == TaskStatus.FAILED and old_status != TaskStatus.FAILED:
            self.failed_tasks += 1

        self.updated_at = datetime.utcnow()

    def is_complete(self) -> bool:
        """Check if all tasks are completed or failed."""
        return all(
            task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED}
            for task in self.nodes.values()
        )

    def get_execution_order(self) -> List[List[str]]:
        """
        Get tasks in topological order (grouped by execution level).

        Returns:
            List of task ID lists, where each inner list can execute in parallel.
        """
        # Build adjacency list
        in_degree: Dict[str, int] = {task_id: 0 for task_id in self.nodes}
        adj: Dict[str, List[str]] = {task_id: [] for task_id in self.nodes}

        for edge in self.edges:
            adj[edge.from_task].append(edge.to_task)
            in_degree[edge.to_task] += 1

        # Kahn's algorithm for topological sort with levels
        levels: List[List[str]] = []
        current_level: List[str] = [
            task_id for task_id, degree in in_degree.items() if degree == 0
        ]

        while current_level:
            levels.append(current_level)
            next_level: List[str] = []

            for task_id in current_level:
                for neighbor in adj[task_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_level.append(neighbor)

            current_level = next_level

        return levels

    def has_cycles(self) -> bool:
        """Check if the graph has cycles (should be DAG)."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = self.nodes[task_id]
            for dep_id in task.depends_on:
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in self.nodes:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False

#!/usr/bin/env python3
"""
Task management for real estate transactions.

Defines Task class for tracking work items with dependencies,
status lifecycle, and assignment.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4


class TaskStatus(Enum):
    """Task status lifecycle."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """
    Represents a work item in a real estate transaction.

    Tasks track individual action items with dependencies, assignees,
    and lifecycle timestamps.

    Example:
        task = Task(
            title="Order home inspection",
            description="Schedule inspection within 7 days",
            assignee="inspector@example.com",
        )
        task.mark_in_progress()
        task.mark_completed()
    """
    # Core identity
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""

    # Status and lifecycle
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Assignment and scheduling
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None

    # Dependencies (task IDs that must complete first)
    dependencies: List[UUID] = field(default_factory=list)

    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_in_progress(self) -> None:
        """Mark task as in progress."""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.IN_PROGRESS

    def mark_completed(self) -> None:
        """Mark task as completed with timestamp."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_blocked(self) -> None:
        """Mark task as blocked (waiting on dependencies)."""
        self.status = TaskStatus.BLOCKED

    def is_blocked_by_dependencies(self, all_tasks: Dict[UUID, 'Task']) -> bool:
        """
        Check if task is blocked by incomplete dependencies.

        Args:
            all_tasks: Dictionary of all tasks by UUID

        Returns:
            True if any dependency is not completed
        """
        for dep_id in self.dependencies:
            dep_task = all_tasks.get(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                return True
        return False

    def can_start(self, all_tasks: Dict[UUID, 'Task']) -> bool:
        """
        Check if task can be started (dependencies satisfied).

        Args:
            all_tasks: Dictionary of all tasks by UUID

        Returns:
            True if all dependencies are completed
        """
        return not self.is_blocked_by_dependencies(all_tasks)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation of task
        """
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'assignee': self.assignee,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'dependencies': [str(dep_id) for dep_id in self.dependencies],
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation from to_dict()

        Returns:
            Task instance
        """
        return cls(
            id=UUID(data['id']),
            title=data['title'],
            description=data['description'],
            status=TaskStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            assignee=data.get('assignee'),
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            dependencies=[UUID(dep_id) for dep_id in data.get('dependencies', [])],
            metadata=data.get('metadata', {}),
        )

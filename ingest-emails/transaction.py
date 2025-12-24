#!/usr/bin/env python3
"""
Transaction management for real estate deals.

Defines Transaction class for managing state transitions, task tracking,
and property metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from state import State, StateRegistry, TaskTemplate
from task import Task, TaskStatus


@dataclass
class StateTransition:
    """
    Record of a state change in transaction history.

    Example:
        transition = StateTransition(
            timestamp=datetime.now(),
            from_state="new_listing",
            to_state="under_contract",
            notes="Offer accepted at $950,000"
        )
    """
    timestamp: datetime
    from_state: Optional[str]  # None for initial state
    to_state: str
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'from_state': self.from_state,
            'to_state': self.to_state,
            'notes': self.notes,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateTransition':
        """Deserialize from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            from_state=data.get('from_state'),
            to_state=data['to_state'],
            notes=data.get('notes', ''),
            metadata=data.get('metadata', {}),
        )


@dataclass
class Transaction:
    """
    Represents a real estate transaction.

    Manages state transitions, task tracking, and property metadata
    for a single real estate deal.

    Example:
        transaction = Transaction(property_address="7250 Franklin Ave")
        transaction.set_state_registry(registry)
        transaction.transition_to("new_listing", notes="Initial listing")
    """
    # Core identity
    id: UUID = field(default_factory=uuid4)
    property_address: str = ""

    # State management
    current_state: Optional[State] = None
    state_history: List[StateTransition] = field(default_factory=list)

    # Task management
    tasks: Dict[UUID, Task] = field(default_factory=dict)

    # Property metadata
    property_metadata: Dict[str, Any] = field(default_factory=dict)

    # Transaction metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Reference to state registry for validation
    _state_registry: Optional[StateRegistry] = field(default=None, repr=False)

    def set_state_registry(self, registry: StateRegistry) -> None:
        """
        Set the state registry for validation.

        Args:
            registry: StateRegistry instance
        """
        self._state_registry = registry

    def transition_to(
        self,
        target_state_name: str,
        notes: str = "",
        auto_create_tasks: bool = True
    ) -> bool:
        """
        Transition to a new state with validation.

        Args:
            target_state_name: Name of target state
            notes: Optional notes about the transition
            auto_create_tasks: Whether to create tasks from templates

        Returns:
            True if transition successful, False if invalid

        Raises:
            ValueError: If state registry not set or target state unknown
        """
        if not self._state_registry:
            raise ValueError("State registry not set. Call set_state_registry() first.")

        target_state = self._state_registry.get(target_state_name)
        if not target_state:
            raise ValueError(f"Unknown state: {target_state_name}")

        # Validate transition
        if self.current_state:
            if not self.current_state.can_transition_to(target_state_name):
                return False

        # Record transition
        transition = StateTransition(
            timestamp=datetime.now(),
            from_state=self.current_state.name if self.current_state else None,
            to_state=target_state_name,
            notes=notes,
        )
        self.state_history.append(transition)

        # Update current state
        self.current_state = target_state

        # Auto-create tasks from templates
        if auto_create_tasks:
            self._create_tasks_from_templates(target_state)

        return True

    def _create_tasks_from_templates(self, state: State) -> None:
        """
        Create tasks from state's task templates.

        Args:
            state: State with task templates
        """
        # Build template name to task ID mapping for dependencies
        template_to_task: Dict[str, UUID] = {}

        for template in state.task_templates:
            task = Task(
                title=template.title,
                description=template.description,
                assignee=template.assignee,
                metadata=template.metadata.copy(),
            )

            # Set due date if specified
            if template.days_until_due is not None:
                task.due_date = datetime.now() + timedelta(days=template.days_until_due)

            # Store for dependency resolution
            template_to_task[template.title] = task.id

            # Add to transaction
            self.tasks[task.id] = task

        # Resolve dependencies (second pass)
        for template in state.task_templates:
            if template.dependencies:
                task_id = template_to_task[template.title]
                task = self.tasks[task_id]

                for dep_template_name in template.dependencies:
                    if dep_template_name in template_to_task:
                        dep_id = template_to_task[dep_template_name]
                        task.dependencies.append(dep_id)

    def add_task(self, task: Task) -> UUID:
        """
        Add a task to the transaction.

        Args:
            task: Task to add

        Returns:
            UUID of the added task
        """
        self.tasks[task.id] = task
        return task.id

    def get_task(self, task_id: UUID) -> Optional[Task]:
        """
        Get task by ID.

        Args:
            task_id: UUID of task

        Returns:
            Task instance or None if not found
        """
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        Get all tasks with given status.

        Args:
            status: TaskStatus to filter by

        Returns:
            List of tasks with matching status
        """
        return [t for t in self.tasks.values() if t.status == status]

    def get_pending_tasks(self) -> List[Task]:
        """
        Get all pending tasks that can be started (dependencies met).

        Returns:
            List of pending tasks ready to start
        """
        return [
            t for t in self.tasks.values()
            if t.status == TaskStatus.PENDING and t.can_start(self.tasks)
        ]

    def get_state_path(self) -> List[str]:
        """
        Get full path of current state.

        Returns:
            List of state names from root to current
        """
        if self.current_state:
            return self.current_state.get_full_path()
        return []

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation of transaction
        """
        return {
            'id': str(self.id),
            'property_address': self.property_address,
            'current_state': self.current_state.name if self.current_state else None,
            'state_history': [t.to_dict() for t in self.state_history],
            'tasks': {str(task_id): task.to_dict() for task_id, task in self.tasks.items()},
            'property_metadata': self.property_metadata,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        state_registry: StateRegistry
    ) -> 'Transaction':
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation from to_dict()
            state_registry: StateRegistry to resolve state references

        Returns:
            Transaction instance
        """
        transaction = cls(
            id=UUID(data['id']),
            property_address=data['property_address'],
            state_history=[StateTransition.from_dict(t) for t in data.get('state_history', [])],
            tasks={
                UUID(task_id): Task.from_dict(task_data)
                for task_id, task_data in data.get('tasks', {}).items()
            },
            property_metadata=data.get('property_metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            metadata=data.get('metadata', {}),
        )

        # Set state registry
        transaction.set_state_registry(state_registry)

        # Resolve current state
        current_state_name = data.get('current_state')
        if current_state_name:
            transaction.current_state = state_registry.get(current_state_name)

        return transaction

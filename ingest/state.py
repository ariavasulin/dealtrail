#!/usr/bin/env python3
"""
State machine for real estate transactions.

Defines State class with hierarchical structure, transition rules,
and task templates for automatic task creation.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Set, Dict, Any


@dataclass
class TaskTemplate:
    """
    Template for creating tasks when entering a state.

    Used to define standard tasks that should be created
    when a transaction enters a particular state.

    Example:
        template = TaskTemplate(
            title="Order home inspection",
            description="Schedule inspection within 7 days",
            days_until_due=7,
            assignee="inspector@example.com"
        )
    """
    title: str
    description: str = ""
    assignee: Optional[str] = None
    days_until_due: Optional[int] = None  # Days from state entry
    dependencies: List[str] = field(default_factory=list)  # Task template names
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class State:
    """
    Represents a state in the transaction state machine.

    States form a hierarchical tree structure with parent-child
    relationships and define valid transitions.

    Example:
        under_contract = State(
            name="under_contract",
            display_name="Under Contract",
            description="Offer accepted, working toward close",
            allowed_transitions={"pending_inspection", "cancelled"},
        )
    """
    # Core identity
    name: str  # Unique identifier (e.g., "under_contract")
    display_name: str  # Human-readable (e.g., "Under Contract")
    description: str = ""

    # Hierarchy
    parent: Optional['State'] = None
    children: List['State'] = field(default_factory=list)

    # State machine rules
    allowed_transitions: Set[str] = field(default_factory=set)  # State names

    # Task templates (auto-create when entering this state)
    task_templates: List[TaskTemplate] = field(default_factory=list)

    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_transition_to(self, target_state_name: str) -> bool:
        """
        Check if transition to target state is allowed.

        Args:
            target_state_name: Name of target state

        Returns:
            True if transition is allowed
        """
        return target_state_name in self.allowed_transitions

    def add_allowed_transition(self, state_name: str) -> None:
        """
        Add an allowed transition from this state.

        Args:
            state_name: Name of state to allow transition to
        """
        self.allowed_transitions.add(state_name)

    def add_child(self, child_state: 'State') -> None:
        """
        Add a child state (sets parent reference).

        Args:
            child_state: Child state to add
        """
        child_state.parent = self
        if child_state not in self.children:
            self.children.append(child_state)

    def get_full_path(self) -> List[str]:
        """
        Get full path from root to this state.

        Returns:
            List of state names from root to current
        """
        path = []
        current = self
        while current:
            path.insert(0, current.name)
            current = current.parent
        return path

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation of state
        """
        return {
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'parent': self.parent.name if self.parent else None,
            'allowed_transitions': list(self.allowed_transitions),
            'task_templates': [
                {
                    'title': tt.title,
                    'description': tt.description,
                    'assignee': tt.assignee,
                    'days_until_due': tt.days_until_due,
                    'dependencies': tt.dependencies,
                    'metadata': tt.metadata,
                }
                for tt in self.task_templates
            ],
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], state_registry: 'StateRegistry') -> 'State':
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation from to_dict()
            state_registry: Registry to resolve parent references

        Returns:
            State instance
        """
        state = cls(
            name=data['name'],
            display_name=data['display_name'],
            description=data.get('description', ''),
            allowed_transitions=set(data.get('allowed_transitions', [])),
            task_templates=[
                TaskTemplate(**tt) for tt in data.get('task_templates', [])
            ],
            metadata=data.get('metadata', {}),
        )

        # Resolve parent reference
        parent_name = data.get('parent')
        if parent_name and parent_name in state_registry._states:
            state.parent = state_registry._states[parent_name]

        return state


class StateRegistry:
    """
    Global registry for state definitions.

    Provides lookup and validation for state machine.

    Example:
        registry = StateRegistry()
        registry.register(new_listing)
        registry.register(under_contract)
        errors = registry.validate_transitions()
    """
    def __init__(self):
        self._states: Dict[str, State] = {}

    def register(self, state: State) -> None:
        """
        Register a state in the registry.

        Args:
            state: State to register
        """
        self._states[state.name] = state

    def get(self, name: str) -> Optional[State]:
        """
        Get state by name.

        Args:
            name: State name

        Returns:
            State instance or None if not found
        """
        return self._states.get(name)

    def all_states(self) -> Dict[str, State]:
        """
        Get all registered states.

        Returns:
            Dictionary of all states by name
        """
        return self._states.copy()

    def validate_transitions(self) -> List[str]:
        """
        Validate that all allowed_transitions reference valid states.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        for state in self._states.values():
            for target_name in state.allowed_transitions:
                if target_name not in self._states:
                    errors.append(
                        f"State '{state.name}' allows transition to "
                        f"undefined state '{target_name}'"
                    )
        return errors

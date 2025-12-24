# Email Ingesting Pipeline

## Problem
We only see emails in fairly unstructured .mbox format. From this we want to:
*   A) parse the emails into a tidy email format
*   B) group them into the correct transaction
*   C) conclude if there are any tasks for Amy

## Architecture

### Data Flow

```
MBOX Export (Gmail)
    ↓
ingest.sh (bash wrapper)
    ↓
mbox_to_json.py (Python preprocessor)
    ↓
Property-grouped JSON
    ↓
Transaction Model (OOP layer) ← NEW
    ↓
TraceWriter UI (annotation)
```

### Components

#### 1. MBOX Preprocessing (`ingest.sh` + `mbox_to_json.py`)
- **Input**: MBOX file from email export
- **Processing**:
  - Extracts property addresses from email subject/body
  - Groups emails by property (one transaction per property)
  - Cleans email bodies (removes quotes, signatures, HTML)
  - Normalizes addresses (7250 Franklin Ave → 7250 franklin)
- **Output**: JSON with property-grouped email threads

#### 2. Transaction Model (OOP Layer) ← NEW

The transaction model provides a structured, object-oriented way to represent real estate deals with states, tasks, and audit trails.

##### Files

**task.py** - Task management
- `TaskStatus` enum: `pending`, `in_progress`, `completed`, `blocked`
- `Task` class: Individual work items with dependencies, assignees, due dates
- UUID-based identity for reliable references
- Dependency tracking: tasks can block other tasks
- JSON serialization for persistence

**state.py** - State machine
- `State` class: Represents transaction states (e.g., "Under Contract", "Pending Inspection")
- Hierarchical structure: states can have parent states and children
- `TaskTemplate`: Auto-create standard tasks when entering a state
- `StateRegistry`: Global lookup and validation for all states
- Transition rules: each state defines which states it can transition to

**transaction.py** - Transaction coordination
- `Transaction` class: Represents a real estate deal
- Property address as primary identifier
- Current state + full state history (audit trail)
- Task collection (dict by UUID)
- State transition validation
- Auto-creates tasks from state templates
- JSON serialization

##### Key Features

**State Hierarchy**: Tree structure where each state has optional parent
```python
under_contract = State(name="under_contract", parent=None)
pending_inspection = State(name="pending_inspection", parent=under_contract)
```

**Task Dependencies**: Tasks can require other tasks to complete first
```python
task_a = Task(title="Order inspection")
task_b = Task(title="Review inspection", dependencies=[task_a.id])
```

**Transition Validation**: Prevents invalid state changes
```python
new_listing.allowed_transitions = {"under_contract", "withdrawn"}
# Can only transition to these states, others will be rejected
```

**Auto-Task Creation**: States define standard tasks
```python
under_contract = State(
    name="under_contract",
    task_templates=[
        TaskTemplate(title="Order inspection", days_until_due=7),
        TaskTemplate(title="Submit loan app", days_until_due=3)
    ]
)
```

**Audit Trail**: Complete history of state changes
```python
transaction.state_history  # List of all transitions with timestamps
```

##### Example Usage

```python
from state import State, StateRegistry, TaskTemplate
from transaction import Transaction

# 1. Define your custom states
registry = StateRegistry()

new_listing = State(
    name="new_listing",
    display_name="New Listing",
    allowed_transitions={"under_contract", "withdrawn"},
    task_templates=[
        TaskTemplate(title="Set up MLS listing", days_until_due=1)
    ]
)

under_contract = State(
    name="under_contract",
    display_name="Under Contract",
    allowed_transitions={"pending_inspection", "cancelled"},
    task_templates=[
        TaskTemplate(title="Order inspection", days_until_due=7)
    ]
)

registry.register(new_listing)
registry.register(under_contract)

# 2. Create transaction
transaction = Transaction(property_address="7250 Franklin Ave")
transaction.set_state_registry(registry)

# 3. Transition states (auto-creates tasks)
transaction.transition_to("new_listing", notes="Initial listing")
print(f"Created {len(transaction.tasks)} tasks")

# 4. Work with tasks
for task in transaction.get_pending_tasks():
    print(f"TODO: {task.title}")
    task.mark_in_progress()

# 5. Save to JSON
import json
with open("transaction.json", "w") as f:
    json.dump(transaction.to_dict(), f, indent=2)

# 6. Load from JSON
with open("transaction.json", "r") as f:
    data = json.load(f)
restored = Transaction.from_dict(data, registry)
```

##### Design Principles

- **Standalone**: No dependencies on TraceWriter or other systems
- **Flexible**: Easy to define custom states and hierarchies
- **Type-safe**: Python dataclasses with type hints
- **Persistent**: Full JSON serialization support
- **Validated**: State transitions are checked before execution
- **Auditable**: Complete history of all state changes

#### 3. TraceWriter UI (React frontend)
- Annotation tool for capturing "off-screen" work between emails
- Keyboard-first navigation
- Import/export for annotated data (export not yet implemented)





# HumanLayer's Linear Development Workflow

This document reverse-engineers the `.claude/commands` directory to understand the sophisticated ticket-driven development workflow implemented in this repository.

## Overview

This workflow integrates with:
- **Linear** (project management) for ticket tracking and status progression
- **`thoughts/` directory** - a shared knowledge base synced across sessions
- **Specialized sub-agents** for parallel research and analysis
- **Git worktrees** for isolated development

## The Core Workflow Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LINEAR TICKET STATUS PROGRESSION                                           │
│                                                                             │
│  Triage → Spec Needed → Research Needed → Research in Progress              │
│           → Ready for Plan → Plan in Progress → Plan in Review              │
│           → Ready for Dev → In Dev → Code Review → Done                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key principle**: Review and alignment happen at the **plan stage** (not the PR stage) to move faster and avoid rework.

---

## Phase 1: Research

**Commands**: `/ralph_research` or `/research_codebase`

**Purpose**: Investigate a ticket and document findings before planning.

**What happens**:
1. Fetches the top priority "research needed" ticket from Linear
2. Moves ticket to "research in progress"
3. Spawns parallel sub-agents to analyze codebase
4. Documents findings in `thoughts/shared/research/YYYY-MM-DD-ENG-XXXX-description.md`
5. Syncs to shared `thoughts/` repository via `humanlayer thoughts sync`
6. Attaches document to Linear ticket
7. Moves ticket to "research in review"

**Key principle**: Document what IS, not what SHOULD BE. Be unbiased - no recommendations at this stage.

**Output**: Research document with:
- Key findings with file:line references
- Technical constraints and opportunities
- Potential implementation approaches
- Risks or concerns discovered

---

## Phase 2: Planning

**Commands**: `/ralph_plan` or `/create_plan`

**Purpose**: Create a detailed implementation plan after research is complete.

**What happens**:
1. Fetches the top priority "ready for spec" ticket
2. Reads linked research document
3. Spawns sub-agents to verify codebase patterns
4. Interactive process: presents understanding, asks clarifying questions
5. Creates phased implementation plan with:
   - Current state analysis
   - Desired end state
   - What we're NOT doing (explicit scope control)
   - Per-phase success criteria (automated vs manual)
6. Saves to `thoughts/shared/plans/YYYY-MM-DD-ENG-XXXX-description.md`
7. Attaches to Linear ticket
8. Moves ticket to "plan in review"

**Key principle**: No open questions in final plan. All decisions must be made before coding begins.

### Plan Template Structure

```markdown
# [Feature/Task Name] Implementation Plan

## Overview
[Brief description of what we're implementing and why]

## Current State Analysis
[What exists now, what's missing, key constraints discovered]

## Desired End State
[Specification of the desired end state and how to verify it]

## What We're NOT Doing
[Explicitly list out-of-scope items to prevent scope creep]

## Implementation Approach
[High-level strategy and reasoning]

## Phase 1: [Descriptive Name]

### Overview
[What this phase accomplishes]

### Changes Required:
#### 1. [Component/File Group]
**File**: `path/to/file.ext`
**Changes**: [Summary of changes]

### Success Criteria:

#### Automated Verification:
- [ ] Migration applies cleanly: `make migrate`
- [ ] Unit tests pass: `make test`
- [ ] Type checking passes: `npm run typecheck`

#### Manual Verification:
- [ ] Feature works as expected when tested via UI
- [ ] Performance is acceptable

**Implementation Note**: Pause here for manual confirmation before proceeding.

---

## Phase 2: [Descriptive Name]
[Similar structure...]

## Testing Strategy
[Unit tests, integration tests, manual testing steps]

## References
- Original ticket: `thoughts/shared/tickets/eng_XXXX.md`
- Related research: `thoughts/shared/research/[relevant].md`
```

---

## Phase 3: Implementation

**Commands**: `/ralph_impl` or `/implement_plan`

**Purpose**: Execute the approved plan.

**What happens**:
1. Creates a git worktree for isolated development (`hack/create_worktree.sh`)
2. Launches a separate Claude session for implementation
3. Follows the plan phase-by-phase
4. Runs automated verification after each phase
5. **Pauses for manual verification** from human between phases
6. Checks off items in plan document as completed
7. Moves ticket to "in dev"

**Key principle**: Human verification gates between phases. Automated checks run first, then pause for manual testing confirmation.

### Implementation Philosophy

From the `/implement_plan` command:

> Plans are carefully designed, but reality can be messy. Your job is to:
> - Follow the plan's intent while adapting to what you find
> - Implement each phase fully before moving to the next
> - Verify your work makes sense in the broader codebase context
> - Update checkboxes in the plan as you complete sections

---

## Phase 4: Commit & PR

**Commands**: `/commit`, `/describe_pr`

**Purpose**: Clean git history and comprehensive documentation.

### `/commit`
1. Reviews conversation history and `git diff`
2. Plans logical commit groupings
3. Presents plan to user for approval
4. Creates focused, atomic commits
5. **No Claude attribution** - commits appear as if user wrote them

### `/describe_pr`
1. Reads PR description template from `thoughts/shared/pr_description.md`
2. Analyzes full PR diff and commit history
3. Runs verification commands and checks boxes
4. Generates comprehensive description with:
   - Summary of changes
   - How to verify
   - Breaking changes / migration notes
5. Updates PR via `gh pr edit`
6. Syncs to `thoughts/shared/prs/{number}_description.md`

---

## Phase 5: Validation

**Command**: `/validate_plan`

**Purpose**: Verify implementation matches the plan.

**What happens**:
1. Reads the implementation plan completely
2. Compares git diff to plan specifications
3. Runs all automated verification commands
4. Documents:
   - What matches the plan
   - Deviations from plan (improvements vs issues)
   - Potential issues discovered
5. Lists manual testing requirements
6. Generates validation report

**Recommended workflow**:
```
/implement_plan → /commit → /validate_plan → /describe_pr
```

---

## Supporting Commands

### Ticket Management

| Command | Purpose |
|---------|---------|
| `/linear` | Create/update Linear tickets, manage workflow status |
| `/iterate_plan` | Update existing plans based on feedback |

### Session Continuity

| Command | Purpose |
|---------|---------|
| `/create_handoff` | Save session context for continuation |
| `/resume_handoff` | Resume from a handoff document |

Handoffs are stored in `thoughts/shared/handoffs/ENG-XXXX/` and include:
- Tasks and their statuses
- Recent changes made
- Learnings and discoveries
- Artifacts produced
- Action items for next session

### Debugging & Special Cases

| Command | Purpose |
|---------|---------|
| `/debug` | Investigate issues via logs, database, git (read-only) |
| `/founder_mode` | Retroactively create ticket + PR for experimental work |

### Shortcuts

| Command | Purpose |
|---------|---------|
| `/oneshot ENG-XXXX` | Research → Plan in one flow |
| `/oneshot_plan ENG-XXXX` | Plan → Implement in one flow |

---

## Key Architectural Patterns

### 1. Specialized Sub-Agents

The workflow uses parallel sub-agents for efficient research:

| Agent | Purpose |
|-------|---------|
| `codebase-locator` | Find files related to a feature/task |
| `codebase-analyzer` | Understand implementation details |
| `codebase-pattern-finder` | Find similar patterns to model after |
| `thoughts-locator` | Find relevant documents in thoughts/ |
| `thoughts-analyzer` | Extract insights from thoughts documents |
| `web-search-researcher` | Research external solutions/APIs |

### 2. Knowledge Base (`thoughts/`)

A shared directory synced via `humanlayer thoughts sync`:

```
thoughts/
├── shared/
│   ├── research/          # Research documents
│   ├── plans/             # Implementation plans
│   ├── handoffs/          # Session continuity
│   │   └── ENG-XXXX/      # Per-ticket handoffs
│   ├── prs/               # PR descriptions
│   └── tickets/           # Cached Linear tickets
├── allison/               # Per-user thoughts
└── global/                # Global thoughts
```

### 3. Git Worktrees

Isolated development environments created via `hack/create_worktree.sh`:
- Keeps main branch clean
- Enables parallel development
- Each ticket gets its own worktree at `~/wt/humanlayer/ENG-XXXX/`

### 4. Linear Integration

Workflow states are managed via Linear MCP tools:
- Automatic status progression
- Document attachment via `links` parameter
- Comment threading for context
- Automatic label assignment (hld, wui, meta)

---

## Suggested Linear Workflow for Developers

### Standard Flow

```bash
# 1. Understand the codebase first (optional)
/research_codebase "your question"

# 2. Create a ticket
/linear

# 3. Research the ticket
/ralph_research ENG-XXXX

# 4. Create implementation plan
/ralph_plan ENG-XXXX

# 5. Execute the plan
/implement_plan path/to/plan.md

# 6. Create commits
/commit

# 7. Generate PR description
/describe_pr

# 8. Verify implementation
/validate_plan
```

### Quick Flow (All-in-One)

```bash
# Research + Plan + Implement in sequence
/oneshot ENG-XXXX
```

### Experimental/Founder Mode

For when you've already built something without a ticket:

```bash
# Create commit, then retroactively create ticket and PR
/founder_mode
```

### Session Continuity

```bash
# When stopping work
/create_handoff

# When resuming
/resume_handoff ENG-XXXX
```

---

## Design Principles

1. **Alignment Before Code**: The review happens at the plan stage, not the PR stage, to prevent rework.

2. **No Open Questions**: Plans must be complete and actionable. All decisions made before coding.

3. **Human Gates**: Manual verification required between implementation phases.

4. **Explicit Scope**: Every plan includes "What We're NOT Doing" to prevent scope creep.

5. **Incremental Verification**: Both automated and manual success criteria, checked as you go.

6. **Session Continuity**: Handoffs preserve context across Claude sessions.

7. **Shared Knowledge**: The `thoughts/` directory creates institutional memory.

---

## File Naming Conventions

All documents follow the pattern: `YYYY-MM-DD-ENG-XXXX-description.md`

- `YYYY-MM-DD`: Today's date
- `ENG-XXXX`: Linear ticket number (omit if no ticket)
- `description`: Brief kebab-case description

Examples:
- With ticket: `2025-01-08-ENG-1478-parent-child-tracking.md`
- Without ticket: `2025-01-08-error-handling-patterns.md`

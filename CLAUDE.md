# DealTrail

## What

**DealTrail** is building an autonomous AI transaction coordinator for real estate. We're training an agent to handle the relationship-heavy work of managing deals from offer to close.

**Current focus**: TraceWriter - an annotation tool for capturing "off-screen actions" in TC email threads (the phone calls, document reviews, and coordination that happens between emails).

**Status**: Phase 1 (data collection) - annotation UI and import complete, export not yet implemented.

## Why

Transaction coordinators do critical work that never appears in email: deadline tracking, stakeholder coordination, document reviews, follow-ups. By annotating these gaps in real email threads, we're building training data that captures what *actually* happens in transactions.

## How

### Quick Start

```bash
# TraceWriter development
cd tracewriter && npm install && npm run dev

# Preprocess email data (Python 3)
python tracewriter/scripts/mbox_to_json.py <input.mbox> <output.json>
```

### Project Structure

```
tracewriter/           # React/Vite app - the annotation tool
  src/App.jsx          # Main component (keyboard navigation, state)
  src/utils/           # Email parsing utilities
  scripts/             # Python MBOX processing scripts
hack/                  # Developer utilities (Linear CLI, scripts)
thoughts/              # Research docs, plans, handoffs (git-ignored)
```

### Key Files

- `tracewriter/src/App.jsx` - Main UI with keyboard-first navigation
- `tracewriter/scripts/mbox_to_json.py` - Converts MBOX to property-grouped JSON
- `thoughts/shared/plans/2024-12-16-tracewriter-email-annotation-tool.md` - Full implementation spec

### Tech Stack

- **Frontend**: React 19, Vite 7, pure CSS
- **Data Processing**: Python (MBOX parsing)
- **No backend** - client-only, all data stays local

### Data Flow

MBOX export -> Python preprocessing (groups by property) -> JSON -> TraceWriter UI -> Annotations (in-memory only, export TODO)

### Keyboard Navigation

The UI is keyboard-first for rapid annotation:
- `Tab` / `Shift+Tab` - Navigate between emails
- `Shift+Arrow` - Switch threads
- `Enter` - Edit annotation for current gap
- `Esc` - Exit edit mode

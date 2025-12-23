# Dealtrail / TraceWriter

## What

**TraceWriter** is an email annotation tool for capturing "off-screen actions" in real estate transactions - the work that happens between emails. This creates training data for an AI agent to understand transaction coordinator workflows.

**Status**: WIP - Core annotation UI complete, export functionality in progress.

## Why

Real estate transaction coordinators handle complex email threads where critical actions (phone calls, document reviews, escrow updates) aren't visible in the email chain. By annotating these gaps, we're building training data to teach AI agents what actually happens between emails.

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
plans/                 # Implementation specifications
hack/                  # Developer utilities (Linear CLI, scripts)
```

### Key Files

- `tracewriter/src/App.jsx` - Main UI with keyboard-first navigation
- `tracewriter/scripts/mbox_to_json.py` - Converts MBOX to property-grouped JSON
- `plans/2024-12-16-tracewriter-email-annotation-tool.md` - Full implementation spec

### Tech Stack

- **Frontend**: React 19, Vite 7, pure CSS
- **Data Processing**: Python (MBOX parsing)
- **No backend** - client-only, all data stays local

### Data Flow

MBOX export -> Python preprocessing (groups by property) -> JSON -> TraceWriter UI -> Annotated JSON

### Keyboard Navigation

The UI is keyboard-first for rapid annotation:
- `Tab` / `Shift+Tab` - Navigate between emails
- `Shift+Arrow` - Switch threads
- `Enter` - Edit annotation for current gap
- `Esc` - Exit edit mode

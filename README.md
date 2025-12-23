# DealTrail

**Building an autonomous AI transaction coordinator.**

DealTrail is training an AI agent to handle real estate transaction coordination—the relationship-heavy work of managing 8-15 stakeholders (buyers, sellers, agents, lenders, escrow, title) through complex deals from offer to close.

## The Approach

Transaction coordinators manage deals through email, but the critical work happens *off-screen*: phone calls, document reviews, deadline tracking, follow-ups. This hidden work is what makes deals close.

We're building training data by annotating real TC email threads—capturing what happened between each message. Then training an AI agent that understands not just the emails, but the invisible coordination that drives transactions forward.

**Current phase**: Data collection with TraceWriter
**Next**: Action taxonomy → Training pipeline → Agent deployment

---

## TraceWriter

Keyboard-first annotation tool for capturing off-screen actions in email threads.

### Quick Start

```bash
# Clone and install
git clone https://github.com/ariavasulin/dealtrail.git
cd dealtrail/tracewriter
npm install

# Start the annotation tool
npm run dev
```

Then import your preprocessed email JSON and start annotating.

### Workflow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌──────────────┐
│ Gmail MBOX  │ ──▶ │ Python Preprocess │ ──▶ │ TraceWriter │ ──▶ │ Annotated    │
│ Export      │     │ (group by property)│     │ UI          │     │ JSON (TODO)  │
└─────────────┘     └──────────────────┘     └─────────────┘     └──────────────┘
```

**1. Export emails from Gmail as MBOX**

**2. Preprocess with Python**
```bash
python tracewriter/scripts/mbox_to_json.py input.mbox output.json
```
This groups emails by property address (not traditional threading) and cleans up signatures, quoted replies, and HTML.

**3. Annotate in TraceWriter**

Import the JSON and document what happened between each email pair.

**4. Export annotated data** *(coming soon)*

Export functionality is not yet implemented. Annotations are currently stored in-memory only.

### Keyboard Navigation

TraceWriter is built for speed:

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Navigate between emails |
| `Shift+↑` / `Shift+↓` | Switch threads |
| `Enter` | Edit annotation for current gap |
| `Esc` | Exit edit mode |

### Project Structure

```
dealtrail/
├── tracewriter/             # Annotation tool (current focus)
│   ├── src/
│   │   ├── App.jsx          # Main UI component
│   │   └── utils/           # Email parsing utilities
│   └── scripts/
│       └── mbox_to_json.py  # MBOX → JSON converter
└── hack/                    # Developer utilities
```

### Tech Stack

- **Frontend**: React 19, Vite 7, pure CSS
- **Data Processing**: Python 3 (MBOX parsing)
- **Architecture**: Client-only, no backend—all data stays local

## Status

**Phase 1: TraceWriter** (in progress)

- [x] Core annotation UI with keyboard navigation
- [x] MBOX preprocessing pipeline
- [x] JSON import
- [ ] JSON export
- [x] Thread sidebar navigation
- [ ] localStorage persistence
- [ ] Export to training format

**Future phases**

- [ ] Action taxonomy discovery
- [ ] Training pipeline
- [ ] Agent deployment

---

*Training an AI to do the invisible work that makes real estate deals close.*

# TraceWriter

**Capture the work that happens between emails.**

TraceWriter is a keyboard-first annotation tool for documenting "off-screen actions" in email threads—the phone calls, document reviews, and decisions that happen between messages but never appear in the email chain.

## The Problem

Real estate transaction coordinators manage complex deals through email, but the most critical work happens *off-screen*:

- "Called the lender to expedite appraisal"
- "Reviewed contract and flagged contingency deadline"
- "Coordinated with escrow to release earnest money"

These actions drive transactions forward but leave no trace in the email history. TraceWriter captures this invisible work to create training data for AI agents that understand real transaction workflows.

## Quick Start

```bash
# Clone and install
git clone https://github.com/ariavasulin/dealtrail.git
cd dealtrail/tracewriter
npm install

# Start the annotation tool
npm run dev
```

Then import your preprocessed email JSON and start annotating.

## Workflow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌──────────────┐
│ Gmail MBOX  │ ──▶ │ Python Preprocess │ ──▶ │ TraceWriter │ ──▶ │ Annotated    │
│ Export      │     │ (group by property)│     │ UI          │     │ JSON         │
└─────────────┘     └──────────────────┘     └─────────────┘     └──────────────┘
```

### 1. Export emails from Gmail as MBOX

### 2. Preprocess with Python
```bash
python tracewriter/scripts/mbox_to_json.py input.mbox output.json
```
This groups emails by property address (not traditional threading) and cleans up signatures, quoted replies, and HTML.

### 3. Annotate in TraceWriter
Import the JSON and document what happened between each email pair.

### 4. Export annotated data
JSON output includes `_annotation_after` fields for each email gap.

## Keyboard Navigation

TraceWriter is built for speed. Keep your hands on the keyboard:

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Navigate between emails |
| `Shift+↑` / `Shift+↓` | Switch threads |
| `Enter` | Edit annotation for current gap |
| `Esc` | Exit edit mode |

## Project Structure

```
tracewriter/
├── src/
│   ├── App.jsx              # Main UI component
│   └── utils/emailParser.js # Import/export handling
├── scripts/
│   ├── mbox_to_json.py      # MBOX → JSON converter
│   └── analyze_unmatched_emails.py
└── package.json

plans/                       # Implementation specs
hack/                        # Developer utilities
```

## Tech Stack

- **Frontend**: React 19, Vite 7, pure CSS
- **Data Processing**: Python 3 (MBOX parsing)
- **Architecture**: Client-only, no backend—all data stays local

## Status

**Work in Progress**

- [x] Core annotation UI with keyboard navigation
- [x] MBOX preprocessing pipeline
- [x] JSON import/export
- [x] Thread sidebar navigation
- [ ] localStorage persistence
- [ ] Export to training format
- [ ] Jump to next unannotated gap

## Why "TraceWriter"?

Transaction coordinators leave traces of their work scattered across emails, but the most important actions—the calls, the reviews, the coordination—leave no trace at all. TraceWriter captures these invisible traces to teach AI what really happens in a transaction.

---

*Building training data for AI agents that understand real estate workflows.*

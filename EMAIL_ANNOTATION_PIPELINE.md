# Email Annotation Pipeline

Complete guide for processing real estate transaction coordinator emails from MBOX export to annotated data with AI-identified off-screen actions.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pipeline Steps](#pipeline-steps)
4. [Data Flow](#data-flow)
5. [Usage Examples](#usage-examples)
6. [Troubleshooting](#troubleshooting)

---

## Overview

This pipeline processes email archives to identify implicit "off-screen actions" - the work that happens between emails (phone calls, document reviews, coordination, etc.) that's critical to understanding how transaction coordinators work.

**Pipeline Stages:**
```
MBOX Export → JSON Parse → Thread Grouping → Batch Annotation → Merge Results
     ↓            ↓              ↓                  ↓                ↓
  emails.mbox → parsed.json → grouped.json → OpenAI API → annotated.json
```

---

## Prerequisites

### Required Software
- **Python 3.12+** (with venv)
- **OpenAI API Key** (for annotation)

### Python Dependencies
```bash
# Install in virtual environment
venv/bin/pip install tiktoken openai python-dotenv
```

### Environment Setup
Create `.env` file in project root:
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

---

## Pipeline Steps

### Step 1: MBOX to JSON (`mbox_to_json.py`)

**Purpose:** Convert email MBOX export into structured JSON, grouped by property.

**Location:** `tracewriter/scripts/mbox_to_json.py`

**Input:** MBOX file (email export from Gmail, Outlook, etc.)

**Output:** `Data/parsed.json`

**Data Structure (parsed.json):**
```json
[
  {
    "id": "prop_7250_franklin",
    "subject": "7250 Franklin",
    "property": "7250 franklin",
    "emails": [
      {
        "id": "email_id",
        "from": "sender@example.com",
        "to": "recipient@example.com",
        "date": "2022-02-11T15:37:17-06:00",
        "dateDisplay": "Feb 11, 03:37 PM",
        "subject": "Email subject",
        "body": "Email body content..."
      }
    ]
  }
]
```

**Usage:**
```bash
python tracewriter/scripts/mbox_to_json.py <input.mbox> Data/parsed.json
```

**What it does:**
- Parses MBOX format emails
- Extracts metadata (from, to, date, subject, body)
- Groups emails by property address (extracted from subject)
- Normalizes property names
- Sorts emails chronologically

---

### Step 2: Thread Grouping (`group_data.py`)

**Purpose:** Reorganize emails into conversation threads within each transaction.

**Location:** `tracewriter/scripts/group_data.py`

**Input:** `Data/parsed.json` (from Step 1)

**Output:** `Data/parsed_grouped.json`

**Data Structure (parsed_grouped.json):**
```json
[
  {
    "id": "prop_7250_franklin",
    "subject": "7250 Franklin",
    "property": "7250 franklin",
    "thread_count": 49,
    "email_count": 183,
    "threads": [
      {
        "id": "prop_7250_franklin_thread_0",
        "subject": "TC Introduction Email",
        "normalized_subject": "tc introduction email",
        "email_count": 7,
        "emails": [...]
      }
    ]
  }
]
```

**Usage:**
```bash
python tracewriter/scripts/group_data.py
```

**What it does:**
- Groups emails by normalized subject line (removes Re:, Fwd:, etc.)
- Creates thread hierarchy: Transaction → Thread → Email
- Sorts emails chronologically within each thread
- Preserves all email metadata
- Calculates thread and email counts

**Example Output:**
```
Transaction 1/22: 7250 franklin - 183 emails -> 49 threads
Transaction 2/22: 5693 holly oak - 185 emails -> 58 threads
...
Summary:
  Total transactions: 22
  Total threads: 819
  Total emails: 3045
  Average threads per transaction: 37.2
```

---

### Step 3: Batch Request Generation & Submission (`create_batch_requests.py`)

**Purpose:** Generate OpenAI Batch API requests to annotate each email with off-screen actions, with automatic cost estimation and submission.

**Location:** `create_batch_requests.py`

**Input:** `Data/parsed_grouped.json` (from Step 2)

**Output:**
- `Data/batch_requests.jsonl` (or `batch_requests_1.jsonl`, `batch_requests_2.jsonl`, etc. if split)
- Optionally submits directly to OpenAI

**Usage:**
```bash
venv/bin/python create_batch_requests.py
```

**Interactive Flow:**

1. **Cost Estimation**
   ```
   BATCH ANNOTATION - MODEL SELECTION
   ===================================
   Total requests: 3,045

   1. gpt-5-nano
      GPT-5 smallest - ultra cheap, good quality (BEST VALUE)
      TOTAL: $2.50

   2. gpt-5-mini
      GPT-5 balanced - great quality, affordable (RECOMMENDED)
      TOTAL: $8.75

   ...

   Select model (1-6):
   ```

2. **Batch Generation**
   ```
   GENERATING BATCH FILES
   ======================
   Batch 1: 1523 requests, ~3,950,000 tokens
   Batch 2: 1522 requests, ~3,920,000 tokens

   Writing 3045 requests across 2 batch files...
   ```

3. **Submission (Optional)**
   ```
   Submit batches to OpenAI now? (y/n): y

   SUBMITTING BATCHES TO OPENAI
   ============================
   Batch 1/2: batch_requests_1.jsonl
     ✓ File uploaded: file-abc123
     ✓ Batch created: batch_xyz789
     Status: validating

   ⚠️  Waiting for batch to complete...
   ⠹ Waiting... Status: in_progress | Elapsed: 15:42
   ✓ Batch completed after 23:45

   Batch 2/2: batch_requests_2.jsonl
   ...
   ```

**Key Features:**

**Context Strategy (Hybrid):**
- All previous emails from current thread (maintains conversation flow)
- Last 15 emails from other threads (captures cross-thread coordination)
- Maximum 50 total context emails (prevents explosion)
- Chronologically sorted

**Automatic Batch Splitting:**
- Splits into multiple files if exceeds 4M tokens
- Stays under OpenAI's 5M token enqueued limit
- Each batch ~4M tokens with safety buffer

**Smart Submission:**
- Waits for each batch to complete before submitting next
- Animated spinner with elapsed time
- Handles API errors gracefully
- Shows batch IDs for tracking

**Batch Request Format (JSONL):**
```json
{
  "custom_id": "prop_7250_franklin|prop_7250_franklin_thread_2|5",
  "method": "POST",
  "url": "/v1/chat/completions",
  "body": {
    "model": "gpt-5-mini",
    "messages": [{"role": "user", "content": "...prompt..."}],
    "response_format": {"type": "json_object"}
  }
}
```

**Annotation Prompt:**
The prompt asks the model to identify:
- **Implicit Actions**: What likely happened off-screen
- **Trigger**: What suggests these actions occurred
- **Confidence**: High/Medium/Low
- **Category**: phone_call, document_prep, research, coordination, follow_up, other

**Configuration:**
Edit these constants in the script:
- `CROSS_THREAD_WINDOW = 15` - Max emails from other threads
- `MAX_CONTEXT_EMAILS = 50` - Absolute max context
- `max_tokens_per_batch = 4_000_000` - Batch size limit

---

### Step 4: Result Merging (`merge_batch_results.py`)

**Purpose:** Download completed batch results from OpenAI and merge annotations back into the data.

**Location:** `merge_batch_results.py`

**Input:**
- `Data/parsed_grouped.json` (from Step 2)
- Completed OpenAI batches

**Output:** `Data/parsed_grouped_annotated.json`

**Usage:**
```bash
venv/bin/python merge_batch_results.py
```

**Interactive Flow:**

1. **List Batches**
   ```
   Fetching recent batches...

   Found 3 batches:
     Completed: 2
     In Progress: 1

   Completed batches:
   1. batch_abc123 - split 1
   2. batch_def456 - split 2
   ```

2. **Select & Download**
   ```
   Select batches to download: all

   Downloading 2 batch result(s)...
     Downloading batch_abc123...
       ✓ Saved to batch_results_batch_abc123.jsonl
       ✓ Found 1523 annotations

     Downloading batch_def456...
       ✓ Saved to batch_results_batch_def456.jsonl
       ✓ Found 1522 annotations

   Total annotations collected: 3045
   ```

3. **Merge**
   ```
   Merging annotations into data...
     ✓ Matched 3045/3045 annotations to emails
     Total emails: 3045
     Annotated: 3045
     Coverage: 100.0%

   Saving to Data/parsed_grouped_annotated.json...
   ✓ Done!
   ```

**Output Structure (parsed_grouped_annotated.json):**
```json
{
  "id": "email_id",
  "from": "sender@example.com",
  "to": "recipient@example.com",
  "date": "2022-02-11T15:37:17-06:00",
  "subject": "Email subject",
  "body": "Email body...",
  "annotation": {
    "actions": [
      {
        "description": "Called escrow to confirm wire instructions",
        "trigger": "Email mentions wire transfer due today",
        "confidence": "high",
        "category": "phone_call"
      },
      {
        "description": "Reviewed preliminary title report",
        "trigger": "Reference to 'prelim received yesterday'",
        "confidence": "medium",
        "category": "document_prep"
      }
    ],
    "summary": "TC likely called escrow officer and reviewed title docs before sending this update"
  }
}
```

**Files Created:**
- `Data/batch_results/batch_results_*.jsonl` - Raw JSONL results from OpenAI
- `Data/parsed_grouped_annotated.json` - Final annotated data

---

## Data Flow

### Complete Pipeline

```
┌─────────────────┐
│  emails.mbox    │  (Email export from Gmail/Outlook)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ mbox_to_json.py │  Groups by property
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  parsed.json    │  Transaction → [Emails]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ group_data.py   │  Groups by thread
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ parsed_grouped  │  Transaction → Thread → Email
│     .json       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│create_batch_    │  Generate & submit batches
│  requests.py    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OpenAI Batch   │  Process annotations
│      API        │  (up to 24 hours)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│merge_batch_     │  Download & merge results
│  results.py     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│parsed_grouped_  │  Transaction → Thread → Email (with annotations)
│ annotated.json  │
└─────────────────┘
```

### Directory Structure

```
DealTrail/
├── .env                          # API keys
├── Data/
│   ├── parsed.json              # Step 1 output
│   ├── parsed_grouped.json      # Step 2 output
│   ├── batch_requests.jsonl     # Step 3 output (single)
│   ├── batch_requests_1.jsonl   # Step 3 output (split)
│   ├── batch_requests_2.jsonl
│   ├── batch_results/           # Step 4 downloads
│   │   ├── batch_results_abc.jsonl
│   │   └── batch_results_def.jsonl
│   └── parsed_grouped_annotated.json  # Step 4 output
├── tracewriter/
│   └── scripts/
│       ├── mbox_to_json.py      # Step 1
│       └── group_data.py        # Step 2
├── create_batch_requests.py     # Step 3
└── merge_batch_results.py       # Step 4
```

---

## Usage Examples

### Complete Pipeline Run

```bash
# Step 1: Convert MBOX to JSON
python tracewriter/scripts/mbox_to_json.py emails_export.mbox Data/parsed.json

# Step 2: Group by threads
python tracewriter/scripts/group_data.py

# Step 3: Generate and submit batches
venv/bin/python create_batch_requests.py
# Select model → Confirm → Choose 'y' to submit

# Wait for batches to complete (check OpenAI dashboard)
# Or wait automatically if you selected sequential submission

# Step 4: Download and merge results
venv/bin/python merge_batch_results.py
# Select 'all' → Results merged into parsed_grouped_annotated.json
```

### Quick Start (From Scratch)

```bash
# 1. Set up environment
echo "OPENAI_API_KEY=sk-your-key" > .env
venv/bin/pip install tiktoken openai python-dotenv

# 2. Export emails from Gmail/Outlook as MBOX
# (Use Gmail Takeout or Outlook export feature)

# 3. Run pipeline
python tracewriter/scripts/mbox_to_json.py export.mbox Data/parsed.json
python tracewriter/scripts/group_data.py
venv/bin/python create_batch_requests.py

# 4. Wait for completion, then merge
venv/bin/python merge_batch_results.py
```

---

## Troubleshooting

### Common Issues

**1. "Enqueued token limit reached"**
```
Error: Enqueued token limit reached for gpt-5-mini
```

**Solution:** The script automatically splits batches, but if you still hit the limit:
- Wait for current batches to complete
- Script will show how many batches succeeded
- Rerun script to submit remaining batches

**2. "tiktoken not installed"**
```
Error: tiktoken not installed
```

**Solution:**
```bash
venv/bin/pip install tiktoken
```

**3. "OpenAI API key not found"**
```
Error initializing OpenAI client
```

**Solution:** Check `.env` file:
```bash
# .env should contain:
OPENAI_API_KEY=sk-your-actual-key-here
```

**4. "No completed batches found"**

**Solution:** Batches take time to process:
- Check status at https://platform.openai.com/batches
- Wait 30 minutes - 24 hours depending on queue
- Rerun `merge_batch_results.py` when completed

**5. Thread grouping seems wrong**

The script groups by normalized subject. If subjects vary too much:
- Emails with slightly different subjects become separate threads
- This is expected behavior
- Cross-thread context (15 emails) helps maintain continuity

### Checking Batch Status Manually

```python
from openai import OpenAI
client = OpenAI()

# List batches
batches = client.batches.list(limit=10)
for batch in batches.data:
    print(f"{batch.id}: {batch.status}")

# Check specific batch
batch = client.batches.retrieve("batch_abc123")
print(f"Status: {batch.status}")
print(f"Progress: {batch.request_counts}")
```

### Cost Estimation

Approximate costs (with 50% Batch API discount):

| Model | Cost per 1M tokens (in) | Cost per 1M tokens (out) | Est. for 3,045 emails |
|-------|------------------------|-------------------------|---------------------|
| gpt-5-nano | $0.025 | $0.20 | ~$2-3 |
| gpt-5-mini | $0.125 | $1.00 | ~$8-10 |
| gpt-5 | $0.625 | $5.00 | ~$35-40 |
| gpt-4o-mini | $0.075 | $0.30 | ~$5-7 |

**Note:** Actual costs depend on:
- Email length (longer emails = more context tokens)
- Thread size (more emails in thread = more context)
- Model selected

---

## Advanced Configuration

### Adjusting Context Window

Edit `create_batch_requests.py`:

```python
# Reduce for lower costs
CROSS_THREAD_WINDOW = 10  # Default: 15
MAX_CONTEXT_EMAILS = 30   # Default: 50

# Increase for more context (higher cost)
CROSS_THREAD_WINDOW = 25
MAX_CONTEXT_EMAILS = 75
```

### Customizing Annotation Prompt

Edit the `create_annotation_prompt()` function in `create_batch_requests.py` to:
- Add specific action categories
- Change confidence levels
- Request different output format
- Add domain-specific instructions

### Processing Subset of Data

To test on a small subset:

```python
# In create_batch_requests.py, modify main():
# After loading transactions:
transactions = transactions[:5]  # Process only first 5 transactions
```

---

## Next Steps

After completing the pipeline, you can:

1. **Analyze annotations** - Load `parsed_grouped_annotated.json` and analyze patterns
2. **Train models** - Use annotations as training data for custom models
3. **Build UI** - Import into TraceWriter annotation tool for review/editing
4. **Export to other formats** - Convert to CSV, database, etc.

---

## Support

For issues or questions:
1. Check this documentation
2. Review error messages in terminal
3. Check OpenAI dashboard for batch status
4. Verify `.env` configuration

---

**Last Updated:** 2025-12-25
**Pipeline Version:** 1.0

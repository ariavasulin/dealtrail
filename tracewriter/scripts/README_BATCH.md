# Batch Email Annotation Guide

## Overview

The `create_batch_requests.py` script generates OpenAI Batch API requests to annotate emails with "off-screen actions" - the implicit work that happens between emails (phone calls, document reviews, coordination, etc.).

## Context Strategy (Hybrid Approach)

For each email being annotated:
- **Include**: All previous emails from the same thread
- **Include**: Last 15 emails from other threads (chronologically before current email)
- **Limit**: Maximum 50 total context emails

This gives rich transaction context while controlling costs.

## Usage

```bash
# Run the script
venv/bin/python tracewriter/scripts/create_batch_requests.py
```

The script will:
1. Analyze your `Data/parsed_grouped.json`
2. Calculate token counts and cost estimates
3. Show interactive menu with pricing for each model
4. Generate `Data/batch_requests.jsonl` after you select a model

## Model Options

The menu will show estimates for:
- **gpt-4o-mini** (RECOMMENDED) - Fast, cheap, good quality
- **gpt-4o** - Best quality, more expensive
- **gpt-4-turbo** - Older flagship, very expensive
- **gpt-3.5-turbo** - Cheapest but lower quality

All prices include the 50% Batch API discount.

## Output Format

Each email annotation will return JSON:
```json
{
  "actions": [
    {
      "description": "Called escrow to confirm wire instructions",
      "trigger": "Email mentions wire transfer due today",
      "confidence": "high",
      "category": "phone_call"
    }
  ],
  "summary": "TC likely called escrow between previous email and this one"
}
```

## Next Steps After Generation

1. **Upload to OpenAI** (via UI or API):
   ```python
   from openai import OpenAI
   client = OpenAI()

   # Upload file
   batch_file = client.files.create(
       file=open('Data/batch_requests.jsonl', 'rb'),
       purpose='batch'
   )

   # Create batch job
   batch = client.batches.create(
       input_file_id=batch_file.id,
       endpoint='/v1/chat/completions',
       completion_window='24h'
   )

   print(f"Batch ID: {batch.id}")
   ```

2. **Monitor Progress**:
   ```python
   # Check status
   batch = client.batches.retrieve(batch.id)
   print(f"Status: {batch.status}")
   ```

3. **Download Results** (when complete):
   ```python
   # Download output file
   result_file = client.files.content(batch.output_file_id)
   with open('Data/batch_results.jsonl', 'wb') as f:
       f.write(result_file.content)
   ```

4. **Merge Results** (TODO - create merge script):
   ```bash
   python tracewriter/scripts/merge_batch_results.py
   ```

## Configuration

Edit these constants in `create_batch_requests.py`:
- `CROSS_THREAD_WINDOW = 15` - Max emails from other threads
- `MAX_CONTEXT_EMAILS = 50` - Absolute max context emails

## Troubleshooting

**Error: "tiktoken not installed"**
```bash
venv/bin/pip install tiktoken
```

**Cost too high?**
- Reduce `CROSS_THREAD_WINDOW` (e.g., 10 instead of 15)
- Reduce `MAX_CONTEXT_EMAILS` (e.g., 30 instead of 50)
- Choose cheaper model (gpt-3.5-turbo or gpt-4o-mini)

## File Structure

```
Data/
  parsed.json              # Original flat structure
  parsed_grouped.json      # Transaction → Thread → Email
  batch_requests.jsonl     # Generated batch requests (input to OpenAI)
  batch_results.jsonl      # Downloaded results from OpenAI
  annotated.json          # Final output with annotations merged in
```

#!/usr/bin/env python3
# Note: Run with venv: venv/bin/python tracewriter/scripts/create_batch_requests.py
"""
Generate OpenAI Batch API requests for email annotation.

Reads parsed_grouped.json and creates a JSONL file where each email is annotated
with context from previous emails (both within thread and across threads).

Features:
- Hybrid context: All emails from current thread + last N from other threads
- Token counting and cost estimation
- Interactive model selection menu
- Configurable context window

Output: batch_requests.jsonl (ready for OpenAI Batch API)
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import tiktoken
except ImportError:
    print("Error: tiktoken not installed. Install with: pip install tiktoken")
    exit(1)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv not required, user can set env vars manually


# OpenAI model pricing (per 1M tokens) - Batch API gets 50% discount on input
MODEL_PRICING = {
    'gpt-5-nano': {
        'input': 0.05 / 2,    # Batch discount
        'output': 0.40 / 2,
        'description': 'GPT-5 smallest - ultra cheap, good quality (BEST VALUE)'
    },
    'gpt-5-mini': {
        'input': 0.25 / 2,
        'output': 2.00 / 2,
        'description': 'GPT-5 balanced - great quality, affordable (RECOMMENDED)'
    },
    'gpt-5': {
        'input': 1.25 / 2,
        'output': 10.00 / 2,
        'description': 'GPT-5 flagship - excellent quality'
    },
    'gpt-5.2': {
        'input': 1.50 / 2,    # Estimated slightly higher than gpt-5
        'output': 12.00 / 2,
        'description': 'GPT-5.2 newest - best quality available'
    },
    'gpt-4o-mini': {
        'input': 0.150 / 2,
        'output': 0.600 / 2,
        'description': 'GPT-4o small - older generation'
    },
    'gpt-4o': {
        'input': 2.50 / 2,
        'output': 10.00 / 2,
        'description': 'GPT-4o - older generation'
    }
}


def count_tokens(text, model="gpt-4o-mini"):
    """Count tokens in text using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Default to cl100k_base for newer models
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


def parse_email_date(date_str):
    """Parse ISO date string to datetime."""
    try:
        # Handle both formats with timezone
        if '+' in date_str or date_str.endswith('Z'):
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return datetime.fromisoformat(date_str)
    except:
        return datetime.min


def get_previous_emails_with_context(
    current_email,
    current_thread_emails,
    all_transaction_emails,
    current_email_idx,
    cross_thread_window=15,
    max_context_emails=50
):
    """
    Get previous emails for context using hybrid approach.

    Args:
        current_email: The email being annotated
        current_thread_emails: All emails in the current thread
        all_transaction_emails: All emails in the transaction (all threads)
        current_email_idx: Index of current email in its thread
        cross_thread_window: Max emails to include from other threads
        max_context_emails: Absolute max emails to include

    Returns:
        List of emails to include as context, sorted by date
    """
    current_date = parse_email_date(current_email['date'])

    # 1. All previous emails from current thread
    thread_context = current_thread_emails[:current_email_idx]

    # 2. Recent emails from other threads (before current email)
    other_thread_emails = [
        e for e in all_transaction_emails
        if e['id'] != current_email['id'] and
           e not in thread_context and
           parse_email_date(e['date']) < current_date
    ]

    # Sort by date and take most recent N
    other_thread_emails.sort(key=lambda e: parse_email_date(e['date']), reverse=True)
    other_context = other_thread_emails[:cross_thread_window]

    # 3. Combine and sort chronologically
    all_context = thread_context + other_context
    all_context.sort(key=lambda e: parse_email_date(e['date']))

    # 4. Apply max limit if needed
    if len(all_context) > max_context_emails:
        # Keep all thread emails, trim others
        thread_ids = {e['id'] for e in thread_context}
        thread_emails_kept = [e for e in all_context if e['id'] in thread_ids]
        other_emails_kept = [e for e in all_context if e['id'] not in thread_ids]

        remaining_slots = max_context_emails - len(thread_emails_kept)
        if remaining_slots > 0:
            all_context = thread_emails_kept + other_emails_kept[-remaining_slots:]
        else:
            # Even thread context is too large, take most recent
            all_context = thread_context[-max_context_emails:]

        all_context.sort(key=lambda e: parse_email_date(e['date']))

    return all_context


def create_annotation_prompt(email, previous_emails, transaction_context):
    """
    Create the prompt for annotating a single email.

    Args:
        email: The email to annotate
        previous_emails: List of emails that came before this one
        transaction_context: Info about the property/transaction

    Returns:
        String prompt for the LLM
    """
    # Build context from previous emails
    context_text = ""
    if previous_emails:
        context_text = "\n\n## Previous emails in this transaction:\n\n"
        for i, prev_email in enumerate(previous_emails, 1):
            context_text += f"### Email {i} ({prev_email['dateDisplay']})\n"
            context_text += f"**From:** {prev_email['from']}\n"
            context_text += f"**To:** {prev_email['to']}\n"
            context_text += f"**Subject:** {prev_email['subject']}\n\n"

            # Truncate very long emails
            body = prev_email['body']
            if len(body) > 2000:
                body = body[:2000] + "\n[... truncated ...]"
            context_text += f"{body}\n\n"
            context_text += "---\n\n"

    # Current email to annotate
    current_email_text = f"""## Current email to annotate:

**From:** {email['from']}
**To:** {email['to']}
**Date:** {email['dateDisplay']}
**Subject:** {email['subject']}

{email['body']}
"""

    # Full prompt
    prompt = f"""You are analyzing a real estate transaction coordinator's email thread for property: {transaction_context['property']}.

Your task is to identify "off-screen actions" - activities that likely happened between previous emails and this one, but aren't explicitly mentioned. These include:

- Phone calls or in-person conversations
- Document reviews or preparations
- Internal coordination or research
- Deadline tracking or calendar updates
- Follow-ups or reminders
- Actions taken based on information received

{context_text}

{current_email_text}

Based on the context and this email, what off-screen actions likely occurred BEFORE this email was sent? Provide:

1. **Implicit Actions**: List specific actions that likely happened
2. **Trigger**: What in the context or email suggests these actions?
3. **Confidence**: High/Medium/Low for each action

Format your response as JSON:
{{
  "actions": [
    {{
      "description": "Brief description of the action",
      "trigger": "What suggests this happened",
      "confidence": "high|medium|low",
      "category": "phone_call|document_prep|research|coordination|follow_up|other"
    }}
  ],
  "summary": "Brief summary of what likely happened between the previous context and this email"
}}

Only include actions you can reasonably infer. If no off-screen actions are apparent, return an empty actions array.
"""

    return prompt


def estimate_costs(transactions, cross_thread_window=15, max_context_emails=50):
    """
    Estimate token usage and costs for different models.

    Returns:
        dict with token counts and cost estimates per model
    """
    print("Analyzing emails and estimating costs...")
    print("(This may take a minute...)\n")

    total_requests = 0
    total_input_tokens = 0
    sample_prompts = []

    # Sample every Nth email for faster estimation
    sample_rate = max(1, sum(len(t['threads']) for t in transactions) // 100)

    for transaction in transactions:
        # Collect all emails in transaction for cross-thread context
        all_transaction_emails = []
        for thread in transaction['threads']:
            all_transaction_emails.extend(thread['emails'])

        # Sort by date for chronological context
        all_transaction_emails.sort(key=lambda e: parse_email_date(e['date']))

        transaction_context = {
            'id': transaction['id'],
            'property': transaction.get('property', ''),
            'subject': transaction.get('subject', '')
        }

        for thread in transaction['threads']:
            for email_idx, email in enumerate(thread['emails']):
                # Get previous emails (hybrid context)
                previous_emails = get_previous_emails_with_context(
                    email,
                    thread['emails'],
                    all_transaction_emails,
                    email_idx,
                    cross_thread_window,
                    max_context_emails
                )

                # Create prompt
                prompt = create_annotation_prompt(
                    email,
                    previous_emails,
                    transaction_context
                )

                total_requests += 1

                # Sample for token counting
                if total_requests % sample_rate == 0:
                    sample_prompts.append(prompt)

    # Count tokens on samples and extrapolate
    if sample_prompts:
        avg_input_tokens = sum(count_tokens(p) for p in sample_prompts) / len(sample_prompts)
    else:
        avg_input_tokens = 1000  # Fallback estimate

    total_input_tokens = int(avg_input_tokens * total_requests)

    # Estimate output tokens (JSON responses are typically short)
    avg_output_tokens = 300  # Estimated per response
    total_output_tokens = avg_output_tokens * total_requests

    # Calculate costs for each model
    estimates = {}
    for model_name, pricing in MODEL_PRICING.items():
        input_cost = (total_input_tokens / 1_000_000) * pricing['input']
        output_cost = (total_output_tokens / 1_000_000) * pricing['output']
        total_cost = input_cost + output_cost

        estimates[model_name] = {
            'description': pricing['description'],
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost,
            'requests': total_requests
        }

    return estimates


def display_model_selection_menu(estimates):
    """
    Display interactive menu for model selection.

    Returns:
        Selected model name
    """
    print("\n" + "="*70)
    print("BATCH ANNOTATION - MODEL SELECTION")
    print("="*70)
    print(f"\nTotal requests to process: {estimates['gpt-4o-mini']['requests']:,}")
    print(f"Average input tokens per request: {estimates['gpt-4o-mini']['input_tokens'] // estimates['gpt-4o-mini']['requests']:,}")
    print(f"Estimated output tokens per request: {estimates['gpt-4o-mini']['output_tokens'] // estimates['gpt-4o-mini']['requests']:,}")
    print("\n" + "-"*70)
    print("COST ESTIMATES (with 50% Batch API discount):")
    print("-"*70)

    models = list(MODEL_PRICING.keys())
    for i, model_name in enumerate(models, 1):
        est = estimates[model_name]
        print(f"\n{i}. {model_name}")
        print(f"   {est['description']}")
        print(f"   Input:  ${est['input_cost']:.2f} ({est['input_tokens']:,} tokens)")
        print(f"   Output: ${est['output_cost']:.2f} ({est['output_tokens']:,} tokens)")
        print(f"   TOTAL:  ${est['total_cost']:.2f}")

    print("\n" + "="*70)

    # Get user selection
    while True:
        try:
            choice = input(f"\nSelect model (1-{len(models)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                print("Cancelled.")
                exit(0)

            choice_num = int(choice)
            if 1 <= choice_num <= len(models):
                selected_model = models[choice_num - 1]
                print(f"\nSelected: {selected_model}")
                confirm = input("Proceed with batch generation? (y/n): ").strip().lower()
                if confirm == 'y':
                    return selected_model
                else:
                    print("Cancelled.")
                    exit(0)
            else:
                print(f"Please enter a number between 1 and {len(models)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            exit(0)


def generate_batch_requests(
    input_file,
    output_file,
    model,
    cross_thread_window=15,
    max_context_emails=50,
    max_tokens_per_batch=4_000_000  # Stay under 5M limit with buffer
):
    """
    Generate JSONL file(s) for OpenAI Batch API.
    Automatically splits into multiple batches if needed.

    Args:
        input_file: Path to parsed_grouped.json
        output_file: Path to output JSONL file (will append _1, _2, etc. if split)
        model: OpenAI model to use
        cross_thread_window: Max emails from other threads to include
        max_context_emails: Absolute max emails to include as context
        max_tokens_per_batch: Maximum tokens per batch file (default 4M)
    """
    # Read input
    print(f"\nReading from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        transactions = json.load(f)

    print(f"Found {len(transactions)} transactions")

    # Generate batch requests with token tracking
    all_batch_requests = []
    current_batch_requests = []
    current_batch_tokens = 0
    batch_number = 1
    total_requests = 0

    for transaction in transactions:
        # Collect all emails in transaction for cross-thread context
        all_transaction_emails = []
        for thread in transaction['threads']:
            all_transaction_emails.extend(thread['emails'])

        # Sort by date
        all_transaction_emails.sort(key=lambda e: parse_email_date(e['date']))

        transaction_context = {
            'id': transaction['id'],
            'property': transaction.get('property', ''),
            'subject': transaction.get('subject', '')
        }

        for thread in transaction['threads']:
            thread_id = thread['id']

            for email_idx, email in enumerate(thread['emails']):
                # Get previous emails (hybrid: thread + cross-thread)
                previous_emails = get_previous_emails_with_context(
                    email,
                    thread['emails'],
                    all_transaction_emails,
                    email_idx,
                    cross_thread_window,
                    max_context_emails
                )

                # Create prompt
                prompt = create_annotation_prompt(
                    email,
                    previous_emails,
                    transaction_context
                )

                # Count tokens for this request
                prompt_tokens = count_tokens(prompt, model)
                estimated_output_tokens = 300  # JSON response estimate
                request_tokens = prompt_tokens + estimated_output_tokens

                # Check if adding this request would exceed batch limit
                if current_batch_tokens + request_tokens > max_tokens_per_batch and current_batch_requests:
                    # Save current batch and start new one
                    all_batch_requests.append(current_batch_requests)
                    print(f"  Batch {batch_number}: {len(current_batch_requests)} requests, ~{current_batch_tokens:,} tokens")

                    current_batch_requests = []
                    current_batch_tokens = 0
                    batch_number += 1

                # Custom ID for tracking: transaction|thread|email_index
                custom_id = f"{transaction['id']}|{thread_id}|{email_idx}"

                # Create batch request in OpenAI format
                batch_request = {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        #"temperature": 0.3,  # Lower for consistent annotations
                        "response_format": {"type": "json_object"}
                    }
                }

                current_batch_requests.append(batch_request)
                current_batch_tokens += request_tokens
                total_requests += 1

    # Don't forget the last batch
    if current_batch_requests:
        all_batch_requests.append(current_batch_requests)
        print(f"  Batch {batch_number}: {len(current_batch_requests)} requests, ~{current_batch_tokens:,} tokens")

    # Write JSONL output files
    print(f"\nWriting {total_requests} requests across {len(all_batch_requests)} batch file(s)...")

    output_files = []
    for idx, batch_requests in enumerate(all_batch_requests, 1):
        if len(all_batch_requests) == 1:
            # Single batch - use original filename
            batch_file = output_file
        else:
            # Multiple batches - add batch number
            base = output_file.stem
            ext = output_file.suffix
            batch_file = output_file.parent / f"{base}_{idx}{ext}"

        with open(batch_file, 'w', encoding='utf-8') as f:
            for request in batch_requests:
                f.write(json.dumps(request) + '\n')

        output_files.append(batch_file)
        print(f"  Wrote: {batch_file.name}")

    print("Done!")
    print(f"\n{'='*70}")
    print("NEXT STEPS:")
    print(f"{'='*70}")

    if len(output_files) == 1:
        print(f"1. Upload {output_files[0].name} to OpenAI:")
        print(f"   https://platform.openai.com/batches")
    else:
        print(f"Split into {len(output_files)} batches to stay under 5M token limit:")
        for i, batch_file in enumerate(output_files, 1):
            print(f"  {i}. {batch_file.name}")
        print(f"\nSubmit batches SEQUENTIALLY (wait for each to complete before next):")

    print(f"\n2. Use OpenAI API to submit")
    # print(f"   from openai import OpenAI")
    # print(f"   client = OpenAI()")
    # print(f"")

    # if len(output_files) > 1:
    #     print(f"   # Submit batches one at a time:")
    #     for i, batch_file in enumerate(output_files, 1):
    #         print(f"\n   # Batch {i}:")
    #         print(f"   file_{i} = client.files.create(")
    #         print(f"       file=open('{batch_file}', 'rb'),")
    #         print(f"       purpose='batch'")
    #         print(f"   )")
    #         print(f"   batch_{i} = client.batches.create(")
    #         print(f"       input_file_id=file_{i}.id,")
    #         print(f"       endpoint='/v1/chat/completions',")
    #         print(f"       completion_window='24h'")
    #         print(f"   )")
    #         print(f"   print(f'Batch {i} ID: {{batch_{i}.id}}')")
    #         if i < len(output_files):
    #             print(f"   # Wait for batch_{i} to complete before submitting batch_{i+1}")
    # else:
    #     print(f"   batch_file = client.files.create(")
    #     print(f"       file=open('{output_files[0]}', 'rb'),")
    #     print(f"       purpose='batch'")
    #     print(f"   )")
    #     print(f"   batch = client.batches.create(")
    #     print(f"       input_file_id=batch_file.id,")
    #     print(f"       endpoint='/v1/chat/completions',")
    #     print(f"       completion_window='24h'")
    #     print(f"   )")

    print(f"\n3. Wait for completion (check status with batch.id)")
    print(f"\n4. Download results and use merge_batch_results.py")
    print(f"{'='*70}")

    return output_files


def submit_batches_via_api(batch_files, model):
    """
    Submit batch files to OpenAI API.

    Args:
        batch_files: List of batch file paths
        model: Model name (for display only)

    Returns:
        List of batch IDs
    """
    if not OPENAI_AVAILABLE:
        print("\nError: openai package not installed.")
        print("Install with: venv/bin/pip install openai")
        return []

    try:
        client = OpenAI()
    except Exception as e:
        print(f"\nError initializing OpenAI client: {e}")
        print("\nMake sure OPENAI_API_KEY is configured:")
        print("  Option 1: Add to .env file in project root:")
        print("    OPENAI_API_KEY=sk-your-key-here")
        print("  Option 2: Set environment variable:")
        print("    export OPENAI_API_KEY='sk-your-key-here'")
        return []

    batch_ids = []

    print(f"\n{'='*70}")
    print("SUBMITTING BATCHES TO OPENAI")
    print(f"{'='*70}")

    for i, batch_file in enumerate(batch_files, 1):
        try:
            print(f"\nBatch {i}/{len(batch_files)}: {batch_file.name}")

            # Upload file
            print(f"  Uploading file...")
            with open(batch_file, 'rb') as f:
                uploaded_file = client.files.create(
                    file=f,
                    purpose='batch'
                )
            print(f"  ✓ File uploaded: {uploaded_file.id}")

            # Create batch job
            batch_desc_str = f"split {i+1}"
            print(f"  Creating batch job...")
            batch = client.batches.create(
                input_file_id=uploaded_file.id,
                endpoint='/v1/chat/completions',
                completion_window='24h',
                metadata={
                    "description":batch_desc_str
                }
            )
            print(f"  ✓ Batch created: {batch.id}")
            print(f"  Status: {batch.status}")

            batch_ids.append({
                'batch_id': batch.id,
                'file_id': uploaded_file.id,
                'file_name': batch_file.name,
                'status': batch.status
            })

            if i < len(batch_files):
                print(f"\n⚠️  WARNING: You have {len(batch_files) - i} more batch(es) to submit.")
                print(f"   Waiting for this batch to complete before submitting next one...")
                print(f"   (to avoid hitting the 5M token enqueued limit)")

                # Wait until batch is completed to start again
                start_time = time.time()
                current_status = batch.status
                spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                spinner_idx = 0

                while current_status != 'completed':
                    # Calculate elapsed time
                    elapsed = int(time.time() - start_time)
                    minutes, seconds = divmod(elapsed, 60)
                    hours, minutes = divmod(minutes, 60)

                    # Format time string
                    if hours > 0:
                        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        time_str = f"{minutes:02d}:{seconds:02d}"

                    for i in range(100): # Loop the animation w/ out spamming API calls
                        # Update same line with spinner and time
                        sys.stdout.write(f"\r   {spinner[spinner_idx]} Waiting... Status: {current_status} | Elapsed: {time_str}")
                        sys.stdout.flush()

                        spinner_idx = (spinner_idx + 1) % len(spinner)

                        time.sleep(0.1)

                    # Refresh batch status
                    batch = client.batches.retrieve(batch.id)
                    current_status = batch.status

                # Clear the waiting line and show completion
                sys.stdout.write("\r" + " " * 80 + "\r")  # Clear line
                sys.stdout.flush()
                print(f"   ✓ Batch completed after {time_str}")

            
            

        except Exception as e:
            print(f"  ✗ Error: {e}")
            if "enqueued token limit" in str(e).lower():
                print(f"\n⚠️  Hit enqueued token limit!")
                print(f"   Successfully submitted {len(batch_ids)} batches.")
                print(f"   Wait for them to complete before submitting remaining {len(batch_files) - i} batches.")
                break
            else:
                print(f"   Skipping this batch...")

    # Summary
    print(f"\n{'='*70}")
    print("SUBMISSION SUMMARY")
    print(f"{'='*70}")
    print(f"Submitted: {len(batch_ids)}/{len(batch_files)} batches\n")

    for i, batch_info in enumerate(batch_ids, 1):
        print(f"{i}. {batch_info['file_name']}")
        print(f"   Batch ID: {batch_info['batch_id']}")
        print(f"   Status: {batch_info['status']}")
        print()

    if batch_ids:
        print("Check status:")
        print("  from openai import OpenAI")
        print("  client = OpenAI()")
        for i, batch_info in enumerate(batch_ids, 1):
            print(f"  batch_{i} = client.batches.retrieve('{batch_info['batch_id']}')")
            print(f"  print(f'Batch {i}: {{batch_{i}.status}}')")

    print(f"{'='*70}")

    return batch_ids


def main():
    """Main function with cost estimation and model selection."""
    # File paths
    input_file = Path(__file__).parent / 'Data' / 'parsed_grouped.json'
    output_file = Path(__file__).parent / 'Data' / 'batch_requests.jsonl'

    # Configuration
    CROSS_THREAD_WINDOW = 15  # Max emails from other threads
    MAX_CONTEXT_EMAILS = 50   # Absolute max context emails

    print("="*70)
    print("OPENAI BATCH REQUEST GENERATOR")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  - Context: All current thread + last {CROSS_THREAD_WINDOW} from other threads")
    print(f"  - Max context emails: {MAX_CONTEXT_EMAILS}")

    # Read and estimate costs
    with open(input_file, 'r', encoding='utf-8') as f:
        transactions = json.load(f)

    estimates = estimate_costs(
        transactions,
        CROSS_THREAD_WINDOW,
        MAX_CONTEXT_EMAILS
    )

    # Show menu and get model selection
    selected_model = display_model_selection_menu(estimates)

    # Generate batch requests
    print(f"\n{'='*70}")
    print("GENERATING BATCH FILES")
    print(f"{'='*70}")

    # Capture output files from generation
    output_files = generate_batch_requests(
        input_file,
        output_file,
        selected_model,
        CROSS_THREAD_WINDOW,
        MAX_CONTEXT_EMAILS
    )

    # Ask if user wants to submit via API
    print(f"\n{'='*70}")
    if OPENAI_AVAILABLE:
        submit = input("\nSubmit batches to OpenAI now? (y/n): ").strip().lower()
        if submit == 'y':
            submit_batches_via_api(output_files, selected_model)
        else:
            print("\nBatch files generated. Submit manually when ready.")
    else:
        print("\nOpenAI library not available. Install with: venv/bin/pip install openai")
        print("Batch files generated. Submit manually.")


if __name__ == '__main__':
    main()

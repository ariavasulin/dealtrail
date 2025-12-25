#!/usr/bin/env python3
"""
Download completed batch results from OpenAI and merge annotations into data.

Reads batch results, parses annotations, and saves to parsed_grouped_annotated.json
"""

import json
import os
from pathlib import Path
from collections import defaultdict

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed.")
    print("Install with: venv/bin/pip install openai")
    exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def list_batches(client, limit=20):
    """List recent batches."""
    batches = client.batches.list(limit=limit)
    return batches.data


def download_batch_results(client, batch_id, output_dir):
    """
    Download results from a completed batch.

    Args:
        client: OpenAI client
        batch_id: Batch ID to download
        output_dir: Directory to save results

    Returns:
        Path to downloaded file, or None if not ready
    """
    try:
        batch = client.batches.retrieve(batch_id)

        if batch.status != 'completed':
            return None, batch.status

        if not batch.output_file_id:
            return None, 'no_output'

        # Download output file
        result_content = client.files.content(batch.output_file_id)

        # Save to file
        output_file = output_dir / f"batch_results_{batch_id}.jsonl"
        with open(output_file, 'wb') as f:
            f.write(result_content.content)

        return output_file, 'completed'

    except Exception as e:
        print(f"Error downloading batch {batch_id}: {e}")
        return None, 'error'


def parse_batch_results(result_file):
    """
    Parse batch results JSONL file into annotations dict.

    Returns:
        Dict mapping custom_id to annotation
    """
    annotations = {}

    with open(result_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue

            result = json.loads(line)
            custom_id = result.get('custom_id')

            if not custom_id:
                continue

            # Extract annotation from response
            response = result.get('response', {})
            if response.get('status_code') == 200:
                body = response.get('body', {})
                choices = body.get('choices', [])

                if choices:
                    message = choices[0].get('message', {})
                    content = message.get('content', '')

                    # Parse JSON annotation
                    try:
                        annotation = json.loads(content)
                        annotations[custom_id] = annotation
                    except json.JSONDecodeError as e:
                        print(f"Warning: Could not parse annotation for {custom_id}: {e}")
                        annotations[custom_id] = {
                            'error': 'json_parse_error',
                            'raw_content': content
                        }
            else:
                # Error response
                annotations[custom_id] = {
                    'error': 'api_error',
                    'status_code': response.get('status_code'),
                    'body': response.get('body')
                }

    return annotations


def merge_annotations_into_data(transactions, annotations):
    """
    Merge annotations into transaction data.

    Args:
        transactions: List of transactions (from parsed_grouped.json)
        annotations: Dict mapping custom_id to annotation

    Returns:
        Updated transactions with annotations added
    """
    total_annotations = 0
    matched_annotations = 0

    for transaction in transactions:
        for thread in transaction.get('threads', []):
            thread_id = thread['id']

            for email_idx, email in enumerate(thread.get('emails', [])):
                # Reconstruct custom_id: transaction_id|thread_id|email_index
                custom_id = f"{transaction['id']}|{thread_id}|{email_idx}"

                if custom_id in annotations:
                    email['annotation'] = annotations[custom_id]
                    matched_annotations += 1
                else:
                    # No annotation found
                    email['annotation'] = None

    total_annotations = len(annotations)

    return transactions, matched_annotations, total_annotations


def main():
    """Main function."""
    print("="*70)
    print("BATCH RESULTS MERGER")
    print("="*70)

    # Initialize OpenAI client
    try:
        client = OpenAI()
    except Exception as e:
        print(f"\nError initializing OpenAI client: {e}")
        print("\nMake sure OPENAI_API_KEY is configured:")
        print("  Option 1: Add to .env file in project root:")
        print("    OPENAI_API_KEY=sk-your-key-here")
        print("  Option 2: Set environment variable:")
        print("    export OPENAI_API_KEY='sk-your-key-here'")
        return

    # File paths
    data_dir = Path(__file__).parent / 'Data'
    input_file = data_dir / 'parsed_grouped.json'
    output_file = data_dir / 'parsed_grouped_annotated.json'
    results_dir = data_dir / 'batch_results'
    results_dir.mkdir(exist_ok=True)

    # List recent batches
    print("\nFetching recent batches...")
    batches = list_batches(client, limit=50)
    for batch in batches:
        print(batch.status)

    # Filter for completed batches
    completed_batches = [b for b in batches if b.status == 'completed']
    in_progress_batches = [b for b in batches if b.status in ['validating', 'in_progress', 'finalizing']]

    print(f"\nFound {len(batches)} batches:")
    print(f"  Completed: {len(completed_batches)}")
    print(f"  In Progress: {len(in_progress_batches)}")

    if not completed_batches:
        print("\nNo completed batches found!")
        if in_progress_batches:
            print(f"\n{len(in_progress_batches)} batch(es) still in progress:")
            for batch in in_progress_batches:
                print(f"  - {batch.id}: {batch.status}")
        return

    # Show completed batches
    print(f"\nCompleted batches:")
    for i, batch in enumerate(completed_batches, 1):
        metadata = batch.metadata or {}
        desc = metadata.get('description', 'N/A')
        print(f"{i}. {batch.id} - {desc}")

    # Ask which batches to download
    print("\nOptions:")
    print("  'all' - Download all completed batches")
    print("  '1,2,3' - Download specific batches by number")
    print("  'q' - Quit")

    choice = input("\nSelect batches to download: ").strip().lower()

    if choice == 'q':
        print("Cancelled.")
        return

    # Determine which batches to download
    if choice == 'all':
        selected_batches = completed_batches
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected_batches = [completed_batches[i] for i in indices if 0 <= i < len(completed_batches)]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return

    if not selected_batches:
        print("No batches selected.")
        return

    # Download batch results
    print(f"\nDownloading {len(selected_batches)} batch result(s)...")
    all_annotations = {}

    for batch in selected_batches:
        print(f"\n  Downloading {batch.id}...")
        result_file, status = download_batch_results(client, batch.id, results_dir)

        if result_file:
            print(f"    ✓ Saved to {result_file.name}")

            # Parse results
            print(f"    Parsing annotations...")
            annotations = parse_batch_results(result_file)
            print(f"    ✓ Found {len(annotations)} annotations")

            # Merge into all_annotations
            all_annotations.update(annotations)
        else:
            print(f"    ✗ Status: {status}")

    print(f"\nTotal annotations collected: {len(all_annotations)}")

    if not all_annotations:
        print("\nNo annotations to merge.")
        return

    # Load original data
    print(f"\nLoading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        transactions = json.load(f)

    # Merge annotations
    print(f"Merging annotations into data...")
    updated_transactions, matched, total = merge_annotations_into_data(
        transactions,
        all_annotations
    )

    print(f"  ✓ Matched {matched}/{total} annotations to emails")

    # Calculate total emails
    total_emails = sum(
        len(email)
        for transaction in transactions
        for thread in transaction.get('threads', [])
        for email in [thread.get('emails', [])]
    )

    # Count annotated emails
    annotated_emails = sum(
        1
        for transaction in updated_transactions
        for thread in transaction.get('threads', [])
        for email in thread.get('emails', [])
        if email.get('annotation') is not None
    )

    print(f"  Total emails: {total_emails}")
    print(f"  Annotated: {annotated_emails}")
    print(f"  Coverage: {annotated_emails/total_emails*100:.1f}%")

    # Save annotated data
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(updated_transactions, f, indent=2, ensure_ascii=False)

    print("✓ Done!")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Batches downloaded: {len(selected_batches)}")
    print(f"Annotations merged: {matched}")
    print(f"Coverage: {annotated_emails}/{total_emails} emails ({annotated_emails/total_emails*100:.1f}%)")
    print(f"\nAnnotation structure added to each email:")
    print(f"  email['annotation'] = {{")
    print(f"    'actions': [...],")
    print(f"    'summary': '...'")
    print(f"  }}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

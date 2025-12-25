#!/usr/bin/env python3
"""
Group parsed email data by thread.

Reads Data/parsed.json where each element is a transaction containing multiple emails.
Groups emails within each transaction by thread (conversation), using normalized subject lines.
Outputs to Data/parsed_grouped.json where each element is a thread.
"""

import json
import re
from pathlib import Path
from collections import defaultdict


def normalize_subject(subject):
    """
    Normalize email subject by removing prefixes like Re:, Fwd:, etc.
    Also strips whitespace and newlines for comparison.
    """
    if not subject:
        return ""

    # Remove common email prefixes (case-insensitive)
    # Handle multiple prefixes like "Re: Fwd: Re:"
    normalized = subject
    while True:
        before = normalized
        # Remove Re:, Fwd:, Fw:, etc. at the beginning
        normalized = re.sub(r'^\s*(Re|Fwd?|Fw):\s*', '', normalized, flags=re.IGNORECASE)
        # Remove whitespace and newlines
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        if normalized == before:
            break

    return normalized.lower()


def group_by_thread(transaction):
    """
    Group emails within a transaction by thread based on normalized subject.

    Args:
        transaction: Dict with 'emails' list

    Returns:
        List of thread dicts, each containing grouped emails
    """
    # Group emails by normalized subject
    threads_dict = defaultdict(list)

    for email in transaction.get('emails', []):
        subject = email.get('subject', '')
        normalized = normalize_subject(subject)

        # Use normalized subject as thread key
        # If no subject, use email ID as unique thread
        thread_key = normalized if normalized else f"_no_subject_{email['id']}"
        threads_dict[thread_key].append(email)

    # Convert to list of thread objects
    threads = []
    for thread_key, emails in threads_dict.items():
        # Sort emails by date within thread
        sorted_emails = sorted(emails, key=lambda e: e.get('date', ''))

        # Use the first email's subject as the thread subject
        thread_subject = sorted_emails[0].get('subject', '') if sorted_emails else ''

        thread = {
            'id': f"{transaction['id']}_thread_{len(threads)}",
            'subject': thread_subject,
            'normalized_subject': thread_key,
            'email_count': len(sorted_emails),
            'emails': sorted_emails
        }
        threads.append(thread)

    # Sort threads by the date of their first email
    threads.sort(key=lambda t: t['emails'][0].get('date', '') if t['emails'] else '')

    return threads


def main():
    # File paths
    input_file = Path(__file__).parent.parent.parent / 'Data' / 'parsed.json'
    output_file = Path(__file__).parent.parent.parent / 'Data' / 'parsed_grouped.json'

    # Read input
    print(f"Reading from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        transactions = json.load(f)

    print(f"Found {len(transactions)} transactions")

    # Process each transaction and group its emails into threads
    grouped_transactions = []
    total_threads = 0
    total_emails = 0

    for i, transaction in enumerate(transactions):
        email_count = len(transaction.get('emails', []))
        total_emails += email_count

        threads = group_by_thread(transaction)
        total_threads += len(threads)

        # Create new transaction structure with threads instead of flat emails
        grouped_transaction = {
            'id': transaction['id'],
            'subject': transaction.get('subject', ''),
            'property': transaction.get('property', ''),
            'thread_count': len(threads),
            'email_count': email_count,
            'threads': threads
        }
        grouped_transactions.append(grouped_transaction)

        print(f"Transaction {i+1}/{len(transactions)}: {transaction.get('property', 'unknown')} - "
              f"{email_count} emails -> {len(threads)} threads")

    # Write output
    print(f"\nWriting {len(grouped_transactions)} transactions "
          f"({total_threads} threads, {total_emails} emails) to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(grouped_transactions, f, indent=2, ensure_ascii=False)

    print("Done!")

    # Print summary statistics
    print(f"\nSummary:")
    print(f"  Total transactions: {len(grouped_transactions)}")
    print(f"  Total threads: {total_threads}")
    print(f"  Total emails: {total_emails}")
    print(f"  Average emails per transaction: {total_emails/len(grouped_transactions):.1f}")
    print(f"  Average threads per transaction: {total_threads/len(grouped_transactions):.1f}")
    print(f"  Average emails per thread: {total_emails/total_threads:.1f}")


if __name__ == '__main__':
    main()

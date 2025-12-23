#!/usr/bin/env python3
"""
Analyze email threads to find patterns for associating unmatched emails with transactions.
Looks for property references, escrow numbers, client names, and nicknames.
"""

import json
import re
from collections import defaultdict, Counter
from pathlib import Path

def normalize_address(text):
    """Normalize an address for comparison."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    replacements = {
        'avenue': 'ave', 'drive': 'dr', 'boulevard': 'blvd',
        'street': 'st', 'road': 'rd', 'place': 'pl',
        'court': 'ct', 'lane': 'ln'
    }
    for long, short in replacements.items():
        text = text.replace(long, short)
    return text.strip()

def extract_addresses(text):
    """Extract potential property addresses from text."""
    # Pattern: street number + street name + street type + optional unit
    pattern = r'\b(\d{3,5}\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s+(?:Ave(?:nue)?|St(?:reet)?|Dr(?:ive)?|Blvd|Rd|Way|Ct|Pl|Ln|Circle|Cir)(?:[\s,#]*(?:Unit|#|Apt)?\s*[\w-]+)?)'
    return re.findall(pattern, text, re.IGNORECASE)

def extract_escrow_numbers(text):
    """Extract escrow numbers from text."""
    patterns = [
        r'\b(\d{2,3}-\d{5,6}-[A-Z]{2})\b',
        r'Escrow\s*#?:?\s*(\d{2,3}-\d{5,6}-[A-Z]{2})',
    ]
    escrows = []
    for pattern in patterns:
        escrows.extend(re.findall(pattern, text, re.IGNORECASE))
    return list(set(escrows))

def has_clear_address_in_subject(subject):
    """Check if subject has a clear property address."""
    normalized = normalize_address(subject)
    return bool(re.search(r'\b\d{3,5}\s+\w+.*?(?:ave|st|dr|blvd|rd|way|ct|pl|ln)', normalized))

def main():
    threads_path = Path(__file__).parent.parent / 'threads.json'
    with open(threads_path) as f:
        threads = json.load(f)

    print(f"Analyzing {len(threads)} total threads...\n")

    # Separate matched vs unmatched
    matched = []
    unmatched = []

    for thread in threads:
        subject = thread.get('subject', '')
        if has_clear_address_in_subject(subject):
            matched.append(thread)
        else:
            unmatched.append(thread)

    print(f"Threads WITH clear address in subject: {len(matched)}")
    print(f"Threads WITHOUT clear address in subject: {len(unmatched)}")

    # Build property reference map from matched threads
    property_map = {}  # base_address -> {escrows, clients, full_addresses}
    escrow_to_property = {}

    for thread in matched:
        subject = thread.get('subject', '')
        addresses = extract_addresses(subject)
        if not addresses:
            continue

        # Get base address (street number + first 2-3 words before street type)
        main_addr = normalize_address(addresses[0])
        base_match = re.match(r'(\d+\s+\w+(?:\s+\w+)?(?:\s+(?:ave|st|dr|blvd|rd|way|ct|pl|ln))?)', main_addr)
        base_addr = base_match.group(1) if base_match else main_addr

        if base_addr not in property_map:
            property_map[base_addr] = {'escrows': set(), 'full_addresses': set()}

        property_map[base_addr]['full_addresses'].add(addresses[0])

        # Extract escrow numbers from all emails
        for email in thread.get('emails', []):
            body = email.get('body', '')
            for escrow in extract_escrow_numbers(body):
                property_map[base_addr]['escrows'].add(escrow)
                escrow_to_property[escrow] = base_addr

    print(f"\nBuilt reference map: {len(property_map)} properties, {len(escrow_to_property)} escrow numbers")

    # Analyze unmatched threads
    matched_by_escrow = []
    matched_by_body_address = []
    potential_nicknames = defaultdict(list)
    truly_unmatched = []

    for thread in unmatched:
        subject = thread.get('subject', '')
        all_text = subject + " "
        for email in thread.get('emails', []):
            all_text += email.get('body', '')[:2000] + " "

        matched_property = None
        match_method = None

        # Try escrow number match
        escrows = extract_escrow_numbers(all_text)
        for escrow in escrows:
            if escrow in escrow_to_property:
                matched_property = escrow_to_property[escrow]
                match_method = f"escrow #{escrow}"
                break

        if matched_property:
            matched_by_escrow.append({
                'subject': subject,
                'method': match_method,
                'property': matched_property
            })
            continue

        # Try address in body match
        body_addresses = extract_addresses(all_text)
        for addr in body_addresses:
            norm_addr = normalize_address(addr)
            for prop_addr in property_map:
                if prop_addr in norm_addr or norm_addr.startswith(prop_addr.split()[0]):
                    matched_property = prop_addr
                    match_method = f"address in body: {addr}"
                    break
            if matched_property:
                break

        if matched_property:
            matched_by_body_address.append({
                'subject': subject,
                'method': match_method,
                'property': matched_property
            })
            continue

        # Look for potential nicknames (capitalized words)
        excluded = {'Completed', 'Please', 'DocuSign', 'Invitation', 'Updated',
                   'Welcome', 'Introduction', 'Email', 'Agent', 'Selling',
                   'Buyer', 'Seller', 'Request', 'Report', 'Package', 'Office',
                   'Subject', 'Escrow', 'Property', 'Transaction', 'Inspection',
                   'Schedule', 'Documents', 'Opening', 'Signed', 'Additional'}
        words = re.findall(r'\b([A-Z][a-z]{3,})\b', subject)
        for word in words:
            if word not in excluded:
                potential_nicknames[word].append(subject[:60])

        truly_unmatched.append({'subject': subject, 'id': thread['id']})

    # Print results
    print(f"\n{'='*80}")
    print("ANALYSIS RESULTS")
    print(f"{'='*80}\n")

    print(f"1. MATCHABLE BY ESCROW NUMBER: {len(matched_by_escrow)} threads")
    print("-" * 60)
    for item in matched_by_escrow[:10]:
        print(f"  Subject: {item['subject'][:55]}")
        print(f"  → {item['property']} via {item['method']}")
        print()
    if len(matched_by_escrow) > 10:
        print(f"  ... and {len(matched_by_escrow) - 10} more\n")

    print(f"\n2. MATCHABLE BY ADDRESS IN BODY: {len(matched_by_body_address)} threads")
    print("-" * 60)
    for item in matched_by_body_address[:10]:
        print(f"  Subject: {item['subject'][:55]}")
        print(f"  → {item['property']} via {item['method'][:50]}")
        print()
    if len(matched_by_body_address) > 10:
        print(f"  ... and {len(matched_by_body_address) - 10} more\n")

    print(f"\n3. POTENTIAL PROPERTY NICKNAMES (words appearing 2+ times)")
    print("-" * 60)
    frequent = {k: v for k, v in potential_nicknames.items() if len(v) >= 2}
    for word, subjects in sorted(frequent.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
        print(f"  '{word}' - {len(subjects)} occurrences")
        for subj in subjects[:2]:
            print(f"    - {subj}")
        print()

    print(f"\n4. TRULY UNMATCHED: {len(truly_unmatched)} threads")
    print("-" * 60)
    for item in truly_unmatched[:15]:
        print(f"  {item['subject'][:70]}")
    if len(truly_unmatched) > 15:
        print(f"  ... and {len(truly_unmatched) - 15} more")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    total_unmatched = len(unmatched)
    recoverable = len(matched_by_escrow) + len(matched_by_body_address)
    print(f"""
Original unmatched:        {total_unmatched} threads
Recoverable by escrow#:    {len(matched_by_escrow)} threads
Recoverable by body addr:  {len(matched_by_body_address)} threads
─────────────────────────────────────
Total recoverable:         {recoverable} threads ({recoverable/total_unmatched*100:.1f}%)
Still unmatched:           {len(truly_unmatched)} threads ({len(truly_unmatched)/total_unmatched*100:.1f}%)

Potential nickname patterns: {len(frequent)} (could recover more with manual mapping)
""")

if __name__ == '__main__':
    main()

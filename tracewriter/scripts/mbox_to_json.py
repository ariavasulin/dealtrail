#!/usr/bin/env python3
"""
Convert MBOX file to JSON format for TraceWriter.

Usage:
    python mbox_to_json.py <input.mbox> <output.json>

Example:
    python mbox_to_json.py "../Mail/Transaction Coordinator Emails.mbox" threads.json
"""

import mailbox
import email
import json
import sys
import re
import html
from email.utils import parsedate_to_datetime
from collections import defaultdict
from pathlib import Path


def get_header(msg, name, default=''):
    """Extract and decode email header."""
    value = msg.get(name, default)
    if value:
        # Handle encoded headers (=?utf-8?Q?...?=)
        try:
            decoded_parts = email.header.decode_header(value)
            decoded = ''
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    decoded += part.decode(charset or 'utf-8', errors='replace')
                else:
                    decoded += part
            return decoded.strip()
        except:
            return str(value).strip()
    return default


def extract_body(msg):
    """Extract plain text body from email message."""
    body = ''

    if msg.is_multipart():
        # Walk through all parts
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))

            # Skip attachments
            if 'attachment' in content_disposition:
                continue

            # Prefer plain text
            if content_type == 'text/plain':
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    break
                except:
                    continue

            # Fall back to HTML if no plain text found
            elif content_type == 'text/html' and not body:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    html_body = payload.decode(charset, errors='replace')
                    body = html_to_text(html_body)
                except:
                    continue
    else:
        # Simple message
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                content_type = msg.get_content_type()
                text = payload.decode(charset, errors='replace')

                if content_type == 'text/html':
                    body = html_to_text(text)
                else:
                    body = text
        except:
            body = str(msg.get_payload())

    return clean_body(body)


def html_to_text(html_content):
    """Convert HTML to plain text."""
    # Remove style and script tags
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Convert common tags
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<div[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '', text, flags=re.IGNORECASE)

    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    text = html.unescape(text)

    return text


def clean_body(body):
    """Clean up email body text."""
    if not body:
        return '[No body content]'

    # Normalize line endings
    body = body.replace('\r\n', '\n').replace('\r', '\n')

    # Remove [image: ...] placeholders
    body = re.sub(r'\[image:[^\]]*\]', '', body)

    # Remove quoted reply chains (lines starting with >)
    lines = body.split('\n')
    cleaned_lines = []
    in_quote_block = False

    for line in lines:
        # Detect "On ... wrote:" pattern that starts a quote block
        if re.match(r'^On .+ wrote:?\s*$', line, re.IGNORECASE):
            in_quote_block = True
            continue
        # Lines starting with > are quotes
        if line.strip().startswith('>'):
            in_quote_block = True
            continue
        # Empty line after quote might end the block, but be conservative
        if in_quote_block and line.strip() == '':
            continue
        # Non-quote, non-empty line - we're out of the quote block
        if line.strip():
            in_quote_block = False
        cleaned_lines.append(line)

    body = '\n'.join(cleaned_lines)

    # Remove signature blocks (detect common patterns)
    # THE*AGENCY* signature pattern
    body = re.sub(r'THE\s*\*?\s*AGENCY\s*\*?.*', '', body, flags=re.DOTALL | re.IGNORECASE)

    # Common signature separators
    body = re.sub(r'\n--\s*\n.*', '', body, flags=re.DOTALL)
    body = re.sub(r'\n_{3,}\n.*', '', body, flags=re.DOTALL)

    # Phone number blocks at end (often in signatures)
    # Only remove if near end of message
    lines = body.rstrip().split('\n')
    while lines and re.match(r'^[\s\d\(\)\-\.\+]+$', lines[-1].strip()):
        lines.pop()
    body = '\n'.join(lines)

    # Remove excessive blank lines (more than 2 in a row)
    body = re.sub(r'\n{4,}', '\n\n\n', body)

    # Strip leading/trailing whitespace
    body = body.strip()

    return body if body else '[No body content]'


# Property nickname map (discovered from data analysis)
PROPERTY_NICKNAME_MAP = {
    'holly': '5693 holly oak',
    'franklin': '7250 franklin',
    'shetland': '12233 shetland',
    'cherokee': '746 n cherokee',
    'gretna': '321 s gretna green',
    'doheny': '818 n doheny',
    'century': '1 w century',
    'olympic': '8844 olympic',
    'magnolia': '11675 magnolia',
    'bosque': '16908 bosque',
    'kings': '118 n kings',
    'columbus': '4730 columbus',
    'sunnyslope': '4740 sunnyslope',
    'knowlton': '7127 knowlton',
    'hilldale': '1222 hilldale',
    'tower': '1571 tower',
    'castle': '435 castle',
    'newcastle': '5339 newcastle',
    'rimpau': '242 s rimpau',
    'coldwater': '3506 coldwater',
    'marina': '13700 marina',
    'loma': '5330 loma linda',
    'vicente': '1007 n san vicente',
    'lucerne': 'lucerne',
    'alta': '611 n alta',
}


def normalize_address(address):
    """
    Normalize address string for consistent matching.
    Handles: Ave/Avenue, Dr/Drive, Unit/#/Apt, whitespace, periods after abbreviations, etc.
    """
    if not address:
        return ''

    addr = address.lower().strip()

    # Remove periods after common abbreviations (N. -> N, S. -> S, etc.)
    addr = re.sub(r'\b([nsew])\.\s*', r'\1 ', addr)

    # Normalize street type abbreviations
    replacements = [
        (r'\bavenue\b', 'ave'),
        (r'\bave\.?\b', 'ave'),
        (r'\bdrive\b', 'dr'),
        (r'\bdr\.?\b', 'dr'),
        (r'\bstreet\b', 'st'),
        (r'\bst\.?\b', 'st'),
        (r'\bboulevard\b', 'blvd'),
        (r'\bblvd\.?\b', 'blvd'),
        (r'\blade\b', 'ln'),
        (r'\blane\b', 'ln'),
        (r'\bln\.?\b', 'ln'),
        (r'\broad\b', 'rd'),
        (r'\brd\.?\b', 'rd'),
        (r'\bcourt\b', 'ct'),
        (r'\bct\.?\b', 'ct'),
        (r'\bplace\b', 'pl'),
        (r'\bpl\.?\b', 'pl'),
        (r'\bway\b', 'way'),
        (r'\bnorth\b', 'n'),
        (r'\bsouth\b', 's'),
        (r'\beast\b', 'e'),
        (r'\bwest\b', 'w'),
    ]

    for pattern, replacement in replacements:
        addr = re.sub(pattern, replacement, addr)

    # Remove unit/apartment designations for grouping purposes
    addr = re.sub(r'\s*(unit|apt|#|suite|ste)\s*\d*\w*', '', addr)

    # Remove street type suffix for grouping (1222 Hilldale Ave == 1222 Hilldale)
    addr = re.sub(r'\s+(ave|dr|st|blvd|ln|rd|ct|pl|way|cir)$', '', addr)

    # Collapse whitespace
    addr = re.sub(r'\s+', ' ', addr)

    # Remove trailing punctuation
    addr = addr.rstrip('.,;:')

    return addr.strip()


def extract_property_from_text(text):
    """
    Extract property address from text (subject or body).
    Returns normalized address if found, None otherwise.
    """
    if not text:
        return None

    text_lower = text.lower()

    # Pattern for street addresses: number + optional direction + street name + REQUIRED street type
    # e.g., "7250 Franklin Ave", "321 S Gretna Green Way", "818 N. Doheny Dr"
    # Require street type suffix to avoid false positives like "2023 At" or "500 Credit"
    address_pattern = r'\b(\d{2,5}\s+(?:[nsew]\.?\s+)?[a-z][a-z]+(?:\s+[a-z]+)*\s+(?:ave|avenue|dr|drive|st|street|blvd|boulevard|ln|lane|rd|road|ct|court|pl|place|way|cir|circle))\b'

    matches = re.findall(address_pattern, text_lower)

    if matches:
        for match in matches:
            normalized = normalize_address(match)
            # Verify it looks like a real address (number + name + type)
            if re.match(r'\d+\s+[a-z]+.*\s+(ave|dr|st|blvd|ln|rd|ct|pl|way|cir)', normalized):
                return normalized

    return None


def extract_property(msg, body_text):
    """
    Extract property address from email.
    Checks: subject → body → nickname map
    Returns normalized property key or None.
    """
    subject = get_header(msg, 'Subject', '')

    # 1. Try subject line first (most reliable)
    prop = extract_property_from_text(subject)
    if prop:
        return prop

    # 2. Try body text
    prop = extract_property_from_text(body_text)
    if prop:
        return prop

    # 3. Try nickname matching in subject
    subject_lower = subject.lower()
    for nickname, full_address in PROPERTY_NICKNAME_MAP.items():
        # Match as whole word
        if re.search(r'\b' + re.escape(nickname) + r'\b', subject_lower):
            return normalize_address(full_address)

    # 4. Try nickname matching in body (first 500 chars for performance)
    body_preview = body_text[:500].lower() if body_text else ''
    for nickname, full_address in PROPERTY_NICKNAME_MAP.items():
        if re.search(r'\b' + re.escape(nickname) + r'\b', body_preview):
            return normalize_address(full_address)

    return None


def get_thread_id(msg):
    """
    Extract or generate thread ID.
    Uses In-Reply-To or References header to group messages.
    Falls back to subject-based threading.
    """
    # Try Message-ID based threading
    references = msg.get('References', '')
    in_reply_to = msg.get('In-Reply-To', '')

    # Get the root message ID from references (first one)
    if references:
        ref_ids = references.split()
        if ref_ids:
            return ref_ids[0].strip('<>').replace('@', '_at_')

    if in_reply_to:
        return in_reply_to.strip('<>').replace('@', '_at_')

    # Fall back to subject-based threading
    subject = get_header(msg, 'Subject', '').lower()
    # Remove Re:, Fwd:, etc.
    subject = re.sub(r'^(re|fwd|fw):\s*', '', subject, flags=re.IGNORECASE)
    subject = re.sub(r'\s+', '_', subject.strip())

    return f"subj_{subject[:50]}" if subject else None


def parse_date(msg):
    """Parse email date to ISO format."""
    date_str = msg.get('Date', '')
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except:
            pass
    return None


def format_date_display(iso_date):
    """Format date for display (e.g., 'Dec 12, 2:34 PM')."""
    if not iso_date:
        return 'Unknown date'
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %I:%M %p')
    except:
        return iso_date


def convert_mbox_to_json(mbox_path, output_path, min_emails=10):
    """Convert MBOX file to TraceWriter JSON format using property-based grouping.

    Args:
        mbox_path: Path to input MBOX file
        output_path: Path to output JSON file
        min_emails: Minimum number of emails required to include a transaction (default 10)
    """
    print(f"Reading MBOX file: {mbox_path}")
    print(f"Minimum emails per transaction: {min_emails}")

    mbox = mailbox.mbox(mbox_path)

    # Group messages by property address (not email threading)
    properties = defaultdict(list)
    unmatched = []

    for i, msg in enumerate(mbox):
        if i % 100 == 0:
            print(f"  Processing message {i}...")

        message_id = msg.get('Message-ID', f'msg_{i}').strip('<>')
        body_text = extract_body(msg)

        # Extract property address from email
        property_key = extract_property(msg, body_text)

        email_data = {
            'id': message_id.replace('@', '_at_'),
            'from': get_header(msg, 'From'),
            'to': get_header(msg, 'To'),
            'date': parse_date(msg),
            'subject': get_header(msg, 'Subject', 'No Subject'),
            'body': body_text,
        }

        if property_key:
            properties[property_key].append(email_data)
        else:
            # Email doesn't match any property - likely administrative
            unmatched.append(email_data)

    print(f"  Found {len(properties)} property transactions and {len(unmatched)} unmatched emails")

    # Filter to only include transactions with enough emails
    filtered_properties = {k: v for k, v in properties.items() if len(v) >= min_emails}
    skipped_count = len(properties) - len(filtered_properties)
    skipped_emails = sum(len(v) for k, v in properties.items() if len(v) < min_emails)

    print(f"  Filtered to {len(filtered_properties)} transactions with {min_emails}+ emails")
    print(f"  Skipped {skipped_count} small transactions ({skipped_emails} emails)")

    # Convert to output format
    output = []

    # Process property-grouped emails as transaction timelines
    for property_key, messages in filtered_properties.items():
        # Sort chronologically within each transaction
        messages.sort(key=lambda m: m['date'] or '')

        # Create a readable property name from the key
        property_name = property_key.title()

        output.append({
            'id': f"prop_{property_key.replace(' ', '_')}",
            'subject': property_name,
            'property': property_key,
            'emails': [
                {
                    'id': m['id'],
                    'from': m['from'],
                    'to': m['to'],
                    'date': m['date'],
                    'dateDisplay': format_date_display(m['date']),
                    'subject': m['subject'],  # Keep individual email subjects
                    'body': m['body'],
                }
                for m in messages
            ]
        })

    # Skip unmatched emails - they're single emails not useful for annotation

    # Sort transactions by date of first email
    output.sort(key=lambda t: t['emails'][0]['date'] or '')

    print(f"Writing {len(output)} transactions to: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Done!")
    print(f"  Transactions included: {len(output)}")
    print(f"  Total emails: {sum(len(t['emails']) for t in output)}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    mbox_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not mbox_path.exists():
        print(f"Error: MBOX file not found: {mbox_path}")
        sys.exit(1)

    convert_mbox_to_json(mbox_path, output_path)

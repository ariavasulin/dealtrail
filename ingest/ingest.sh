#!/bin/bash
# Convert MBOX email export to TraceWriter JSON format
#
# Usage:
#   ./ingest.sh <input.mbox> [output.json]
#
# Example:
#   ./ingest.sh "Transaction Coordinator Emails.mbox"
#   ./ingest.sh ~/Mail/emails.mbox threads.json

set -e

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: $0 <input.mbox> [output.json]"
    echo ""
    echo "Converts MBOX email export to TraceWriter JSON format."
    echo ""
    echo "Arguments:"
    echo "  input.mbox   Path to MBOX file (required)"
    echo "  output.json  Path to output JSON file (default: threads.json)"
    echo ""
    echo "Example:"
    echo "  $0 'Transaction Coordinator Emails.mbox'"
    echo "  $0 ~/Mail/emails.mbox custom_output.json"
    exit 0
fi

# Check for required argument
if [ -z "$1" ]; then
    echo "Error: Input MBOX file required"
    echo "Usage: $0 <input.mbox> [output.json]"
    echo "Use -h for help"
    exit 1
fi

INPUT_MBOX="$1"
OUTPUT_JSON="${2:-threads.json}"

# Get script directory to find the Python script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../tracewriter/scripts/mbox_to_json.py"

# Verify input file exists
if [ ! -f "$INPUT_MBOX" ]; then
    echo "Error: Input file not found: $INPUT_MBOX"
    exit 1
fi

# Verify Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Run conversion
echo "Converting MBOX to JSON..."
echo "  Input:  $INPUT_MBOX"
echo "  Output: $OUTPUT_JSON"
echo ""

python3 "$PYTHON_SCRIPT" "$INPUT_MBOX" "$OUTPUT_JSON"

echo ""
echo "Success! Import the file in TraceWriter:"
echo "  cd tracewriter && npm run dev"
echo "  Then use the Import button to load: $OUTPUT_JSON"

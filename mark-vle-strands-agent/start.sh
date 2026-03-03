#!/bin/bash
# Start mark-vle-strands-agent with AWS credentials

set -e
cd "$(dirname "$0")"

echo "Starting Mark Vle Strands Agent..."

# Export AWS credentials
eval $(aws configure export-credentials --profile zuberua-Admin --format env 2>&1)
[ -z "$AWS_ACCESS_KEY_ID" ] && echo "✗ Failed to export AWS credentials" && exit 1
echo "✓ AWS credentials exported"

# Activate venv
[ ! -d "venv" ] && echo "✗ Virtual environment not found. Run: python3.13 -m venv venv" && exit 1
source venv/bin/activate
echo "✓ Virtual environment activated"

# Test AWS access
echo "Testing AWS access..."
python test_aws_access.py || exit 1

# Start Flask
echo ""
echo "Starting Flask on http://localhost:5001"
echo "Press Ctrl+C to stop"
echo ""
python flask_app.py

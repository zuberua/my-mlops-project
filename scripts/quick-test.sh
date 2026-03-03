#!/bin/bash
#
# Quick test to verify deployment script exists
#

set -e

echo "Testing deployment script location..."

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEPLOY_SCRIPT="$SCRIPT_DIR/../mark-vle-strands-agent/scripts/deploy_to_agentcore.py"

echo "Script directory: $SCRIPT_DIR"
echo "Looking for: $DEPLOY_SCRIPT"

if [ -f "$DEPLOY_SCRIPT" ]; then
    echo "✓ Deployment script found!"
    echo "  Location: $DEPLOY_SCRIPT"
    
    # Show first few lines
    echo ""
    echo "Script header:"
    head -5 "$DEPLOY_SCRIPT"
    
    # Check for boto3 client
    if grep -q "bedrock-agentcore-control" "$DEPLOY_SCRIPT"; then
        echo ""
        echo "✓ Uses correct boto3 client: bedrock-agentcore-control"
    fi
else
    echo "✗ Deployment script not found!"
    echo "  Expected: $DEPLOY_SCRIPT"
    exit 1
fi

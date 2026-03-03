#!/bin/bash

echo "=========================================="
echo "Mark Vle Strands Agent Setup"
echo "=========================================="

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Test locally
echo ""
echo "Testing agent locally..."
python3 agent.py

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To use the agent:"
echo "  python3 agent.py"
echo ""
echo "Or import in your code:"
echo "  from agent import agent"
echo "  response = agent('What is TNH-SPEED-1?')"
echo "=========================================="

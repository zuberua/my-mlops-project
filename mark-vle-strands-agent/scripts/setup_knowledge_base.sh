#!/bin/bash

set -e

echo "=========================================="
echo "Mark Vle Knowledge Base Setup"
echo "=========================================="

# Load environment variables
if [ -f config/.env ]; then
    export $(cat config/.env | grep -v '^#' | xargs)
fi

BUCKET_NAME=${S3_BUCKET_NAME:-mark-vie-s3-rag}
AWS_REGION=${AWS_REGION:-us-west-2}

echo "S3 Bucket: $BUCKET_NAME"
echo "AWS Region: $AWS_REGION"
echo "=========================================="

# Check if bucket exists
echo ""
echo "Step 1: Checking S3 bucket..."
aws s3 ls s3://$BUCKET_NAME 2>/dev/null || {
    echo "Creating bucket: $BUCKET_NAME"
    aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION
}

# Generate embeddings
echo ""
echo "Step 2: Generating embeddings..."
python3 scripts/generate_embeddings.py

echo ""
echo "=========================================="
echo "Knowledge Base Setup Complete!"
echo "=========================================="
echo "Bucket: s3://$BUCKET_NAME/embeddings/"
echo ""
echo "You can now test the agent:"
echo "  bash scripts/run_ui.sh"
echo "=========================================="

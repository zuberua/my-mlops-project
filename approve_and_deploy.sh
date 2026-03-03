#!/bin/bash

# Approve the model
echo "Approving model..."
aws sagemaker update-model-package \
  --model-package-arn "arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1" \
  --model-approval-status Approved \
  --approval-description "Manually approved for deployment"

echo "✓ Model approved!"
echo ""
echo "Now you can:"
echo "1. Push code to trigger deployment workflow automatically"
echo "2. Or manually trigger deployment workflow in GitHub Actions"

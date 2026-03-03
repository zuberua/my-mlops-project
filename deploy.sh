#!/bin/bash

# Deploy SageMaker Endpoint
# Usage: ./deploy.sh

set -e

echo "🚀 Deploying mlops-demo-staging endpoint..."
echo ""

# Set environment variable
export SAGEMAKER_EXECUTION_ROLE_ARN="arn:aws:iam::138720056246:role/mlops-demo-sagemaker-execution-role"

# Deploy endpoint
python3 deployment/deploy_endpoint.py \
  --model-package-arn "arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1" \
  --endpoint-name mlops-demo-staging \
  --instance-type ml.m5.xlarge \
  --instance-count 1 \
  --region us-east-1

echo ""
echo "⏳ Waiting for endpoint to be ready (this takes ~8-10 minutes)..."
echo ""

# Wait for endpoint
python3 deployment/wait_endpoint.py \
  --endpoint-name mlops-demo-staging \
  --region us-east-1 \
  --timeout 900

echo ""
echo "✅ Endpoint deployed successfully!"
echo "📍 Endpoint name: mlops-demo-staging"
echo "🔗 Console: https://console.aws.amazon.com/sagemaker/home?region=us-east-1#/endpoints/mlops-demo-staging"

#!/bin/bash

MODEL_ARN="arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1"

echo "Deploying staging endpoint..."
python3 deployment/deploy_endpoint.py \
  --model-package-arn "$MODEL_ARN" \
  --endpoint-name mlops-demo-staging \
  --instance-type ml.m5.xlarge \
  --instance-count 1 \
  --region us-east-1

echo ""
echo "Waiting for endpoint to be ready..."
python3 deployment/wait_endpoint.py \
  --endpoint-name mlops-demo-staging \
  --region us-east-1 \
  --timeout 900

echo ""
echo "✓ Staging endpoint deployed!"
echo "Endpoint name: mlops-demo-staging"

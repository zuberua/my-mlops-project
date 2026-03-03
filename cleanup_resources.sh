#!/bin/bash

# MLOps Project - AWS Resources Cleanup Script
# This script will delete all AWS resources created by the MLOps project

set -e

echo "=========================================="
echo "MLOps Project - AWS Resources Cleanup"
echo "=========================================="
echo ""

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS credentials not configured"
    echo "Please configure AWS credentials first:"
    echo "  aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Confirm deletion
read -p "⚠️  This will DELETE all MLOps project resources. Are you sure? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# 1. Delete SageMaker Endpoints (if any)
echo "1. Checking for SageMaker endpoints..."
ENDPOINTS=$(aws sagemaker list-endpoints --region $REGION --query "Endpoints[?contains(EndpointName, 'mlops-demo')].EndpointName" --output text)
if [ -n "$ENDPOINTS" ]; then
    for endpoint in $ENDPOINTS; do
        echo "   Deleting endpoint: $endpoint"
        aws sagemaker delete-endpoint --endpoint-name "$endpoint" --region $REGION || true
    done
else
    echo "   No endpoints found"
fi

# 2. Delete SageMaker Endpoint Configs (if any)
echo "2. Checking for SageMaker endpoint configs..."
ENDPOINT_CONFIGS=$(aws sagemaker list-endpoint-configs --region $REGION --query "EndpointConfigs[?contains(EndpointConfigName, 'mlops-demo')].EndpointConfigName" --output text)
if [ -n "$ENDPOINT_CONFIGS" ]; then
    for config in $ENDPOINT_CONFIGS; do
        echo "   Deleting endpoint config: $config"
        aws sagemaker delete-endpoint-config --endpoint-config-name "$config" --region $REGION || true
    done
else
    echo "   No endpoint configs found"
fi

# 3. Delete SageMaker Models (if any)
echo "3. Checking for SageMaker models..."
MODELS=$(aws sagemaker list-models --region $REGION --query "Models[?contains(ModelName, 'mlops-demo')].ModelName" --output text)
if [ -n "$MODELS" ]; then
    for model in $MODELS; do
        echo "   Deleting model: $model"
        aws sagemaker delete-model --model-name "$model" --region $REGION || true
    done
else
    echo "   No models found"
fi

# 4. Delete SageMaker Pipelines (if any)
echo "4. Checking for SageMaker pipelines..."
PIPELINES=$(aws sagemaker list-pipelines --region $REGION --query "PipelineSummaries[?contains(PipelineName, 'mlops-demo')].PipelineName" --output text)
if [ -n "$PIPELINES" ]; then
    for pipeline in $PIPELINES; do
        echo "   Deleting pipeline: $pipeline"
        aws sagemaker delete-pipeline --pipeline-name "$pipeline" --region $REGION || true
    done
else
    echo "   No pipelines found"
fi

# 5. Empty and delete S3 bucket
echo "5. Deleting S3 bucket..."
BUCKET_NAME="sagemaker-mlops-demo-$ACCOUNT_ID"
if aws s3 ls "s3://$BUCKET_NAME" 2>/dev/null; then
    echo "   Emptying bucket: $BUCKET_NAME"
    aws s3 rm "s3://$BUCKET_NAME" --recursive --region $REGION
    echo "   Deleting bucket: $BUCKET_NAME"
    aws s3 rb "s3://$BUCKET_NAME" --region $REGION
else
    echo "   Bucket not found: $BUCKET_NAME"
fi

# 6. Use Terraform to destroy remaining resources
echo "6. Running Terraform destroy..."
cd terraform
if [ -f "terraform.tfstate" ]; then
    terraform destroy -auto-approve
    echo "   ✓ Terraform resources destroyed"
else
    echo "   No terraform state found, skipping"
fi
cd ..

echo ""
echo "=========================================="
echo "✓ Cleanup completed successfully!"
echo "=========================================="
echo ""
echo "Deleted resources:"
echo "  - SageMaker endpoints, configs, models, pipelines"
echo "  - S3 bucket: $BUCKET_NAME"
echo "  - IAM roles: mlops-demo-github-actions-role, mlops-demo-sagemaker-execution-role"
echo "  - SageMaker Model Package Group: mlops-demo-model-group"
echo ""

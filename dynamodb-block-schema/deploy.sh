#!/bin/bash
set -e

# Configuration
STACK_NAME="${STACK_NAME:-markvie-kb-resources-poc}"
REGION="${AWS_REGION:-us-west-2}"
PROFILE_ARG=""
if [ -n "$AWS_PROFILE" ]; then
    PROFILE_ARG="--profile $AWS_PROFILE"
fi
ENVIRONMENT="${ENVIRONMENT:-poc}"
APP_PREFIX="${APP_PREFIX:-markvie-kb}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== GT Copilot Pin Ingestion Pipeline Deployment ==="
echo "Stack:       $STACK_NAME"
echo "Region:      $REGION"
echo "Environment: $ENVIRONMENT"
echo "Prefix:      $APP_PREFIX"
echo "Flow:        S3 -> EventBridge -> Step Functions -> Lambda -> DynamoDB"
echo ""

# Step 1: Deploy CloudFormation stack
echo "1. Deploying CloudFormation stack..."
aws cloudformation deploy \
    --stack-name "$STACK_NAME" \
    --template-file "$SCRIPT_DIR/cloudformation/table.yaml" \
    --parameter-overrides \
        AppPrefix="$APP_PREFIX" \
        Environment="$ENVIRONMENT" \
    --region "$REGION" \
    $PROFILE_ARG \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset

echo "   Done"

# Step 2: Get Lambda function name from stack outputs
FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    $PROFILE_ARG \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' \
    --output text)

echo "2. Packaging Lambda code..."
LAMBDA_DIR="$SCRIPT_DIR/lambda/csv_processor"
ZIP_FILE="/tmp/csv_processor.zip"

rm -f "$ZIP_FILE"
cd "$LAMBDA_DIR"
zip -r "$ZIP_FILE" handler.py
cd "$SCRIPT_DIR"

echo "   Packaged: $ZIP_FILE"

# Step 3: Update Lambda code
echo "3. Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$REGION" \
    $PROFILE_ARG \
    --output text --query 'FunctionName'

echo "   Lambda code updated"

# Step 4: Get outputs
echo ""
echo "=== Deployment Complete ==="
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    $PROFILE_ARG \
    --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
    --output text)

TABLE_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    $PROFILE_ARG \
    --query 'Stacks[0].Outputs[?OutputKey==`TableName`].OutputValue' \
    --output text)

SFN_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    $PROFILE_ARG \
    --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
    --output text)

echo "S3 Bucket:       $BUCKET_NAME"
echo "DynamoDB:        $TABLE_NAME"
echo "Lambda:          $FUNCTION_NAME"
echo "State Machine:   $SFN_ARN"
echo ""
echo "Upload a CSV to trigger the ingestion workflow:"
echo "  aws s3 cp data/sample_pins.csv s3://$BUCKET_NAME/knowledgebase/sample_pins.csv $PROFILE_ARG --region $REGION"

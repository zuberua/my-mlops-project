#!/bin/bash
#
# Deploy Mark Vle Agent using AWS CodeBuild
# This script creates a CodeBuild project and triggers a build
# Use this when Docker Desktop is not available locally
#

set -e

echo "=========================================="
echo "Mark Vle Agent - CodeBuild Deployment"
echo "=========================================="

cd "$(dirname "$0")"

# Load configuration
if [ ! -f config/.env ]; then
    echo "✗ config/.env not found"
    exit 1
fi

export $(cat config/.env | grep -v '^#' | grep -v '^$' | xargs)

# Configuration
PROJECT_NAME="${AGENTCORE_AGENT_NAME:-mark-vle-agent}-build"
ECR_REPO_NAME="${AGENTCORE_ECR_REPO:-bedrock-agentcore-mcp_server}"
AWS_REGION="${AGENTCORE_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo ""
echo "Configuration:"
echo "  Project Name:     $PROJECT_NAME"
echo "  ECR Repository:   $ECR_REPO_NAME"
echo "  AWS Region:       $AWS_REGION"
echo "  AWS Account:      $AWS_ACCOUNT_ID"
echo ""

# Step 1: Create S3 bucket for source code (if needed)
echo "=========================================="
echo "Step 1: Preparing source code"
echo "=========================================="

SOURCE_BUCKET="${PROJECT_NAME}-source-${AWS_ACCOUNT_ID}"
SOURCE_KEY="source.zip"

# Check if bucket exists, create if not
if aws s3 ls "s3://${SOURCE_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: $SOURCE_BUCKET"
    aws s3 mb "s3://${SOURCE_BUCKET}" --region $AWS_REGION
else
    echo "✓ S3 bucket exists: $SOURCE_BUCKET"
fi

# Create source zip
echo "Creating source archive..."
zip -r /tmp/source.zip \
    agent.py \
    agentcore_app.py \
    plc_diagram_generator.py \
    config/ \
    requirements.txt \
    Dockerfile \
    buildspec.yml \
    -x "*.pyc" "*__pycache__*" "*.git*"

# Upload to S3
echo "Uploading source to S3..."
aws s3 cp /tmp/source.zip "s3://${SOURCE_BUCKET}/${SOURCE_KEY}"
echo "✓ Source uploaded"

# Step 2: Create IAM role for CodeBuild (if needed)
echo ""
echo "=========================================="
echo "Step 2: Setting up IAM role"
echo "=========================================="

ROLE_NAME="${PROJECT_NAME}-role"

if aws iam get-role --role-name $ROLE_NAME &>/dev/null; then
    echo "✓ IAM role exists: $ROLE_NAME"
else
    echo "Creating IAM role: $ROLE_NAME"
    
    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create role
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json

    # Attach policies
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

    # Create inline policy for S3 and logs
    cat > /tmp/inline-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/codebuild/${PROJECT_NAME}*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::${SOURCE_BUCKET}/*"
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name CodeBuildPolicy \
        --policy-document file:///tmp/inline-policy.json

    echo "✓ IAM role created"
    echo "Waiting 10 seconds for IAM propagation..."
    sleep 10
fi

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"

# Step 3: Create CodeBuild project
echo ""
echo "=========================================="
echo "Step 3: Creating CodeBuild project"
echo "=========================================="

if aws codebuild batch-get-projects --names $PROJECT_NAME --region $AWS_REGION | grep -q $PROJECT_NAME; then
    echo "✓ CodeBuild project exists: $PROJECT_NAME"
    echo "Updating project..."
    
    aws codebuild update-project \
        --name $PROJECT_NAME \
        --region $AWS_REGION \
        --source type=S3,location="${SOURCE_BUCKET}/${SOURCE_KEY}" \
        --artifacts type=NO_ARTIFACTS \
        --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true,environmentVariables="[{name=AWS_DEFAULT_REGION,value=${AWS_REGION}},{name=AWS_ACCOUNT_ID,value=${AWS_ACCOUNT_ID}},{name=IMAGE_REPO_NAME,value=${ECR_REPO_NAME}}]" \
        --service-role $ROLE_ARN
else
    echo "Creating CodeBuild project: $PROJECT_NAME"
    
    aws codebuild create-project \
        --name $PROJECT_NAME \
        --region $AWS_REGION \
        --source type=S3,location="${SOURCE_BUCKET}/${SOURCE_KEY}" \
        --artifacts type=NO_ARTIFACTS \
        --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true,environmentVariables="[{name=AWS_DEFAULT_REGION,value=${AWS_REGION}},{name=AWS_ACCOUNT_ID,value=${AWS_ACCOUNT_ID}},{name=IMAGE_REPO_NAME,value=${ECR_REPO_NAME}}]" \
        --service-role $ROLE_ARN
fi

echo "✓ CodeBuild project ready"

# Step 4: Start build
echo ""
echo "=========================================="
echo "Step 4: Starting build"
echo "=========================================="

BUILD_ID=$(aws codebuild start-build \
    --project-name $PROJECT_NAME \
    --region $AWS_REGION \
    --query 'build.id' \
    --output text)

echo "✓ Build started: $BUILD_ID"
echo ""
echo "Monitoring build progress..."
echo "Press Ctrl+C to stop monitoring (build will continue)"
echo ""

# Monitor build
while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds \
        --ids $BUILD_ID \
        --region $AWS_REGION \
        --query 'builds[0].buildStatus' \
        --output text)
    
    if [ "$BUILD_STATUS" = "IN_PROGRESS" ]; then
        echo -n "."
        sleep 5
    elif [ "$BUILD_STATUS" = "SUCCEEDED" ]; then
        echo ""
        echo "✓ Build succeeded!"
        break
    else
        echo ""
        echo "✗ Build failed with status: $BUILD_STATUS"
        echo ""
        echo "View logs:"
        echo "  aws codebuild batch-get-builds --ids $BUILD_ID --region $AWS_REGION"
        exit 1
    fi
done

# Get image URI
IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:latest"

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Image URI: $IMAGE_URI"
echo ""
echo "Next Steps:"
echo "1. Update your AgentCore agent with this image URI"
echo "2. Configure environment variables:"
echo "   - AWS_REGION=us-west-2"
echo "   - S3_BUCKET_NAME=mark-vie-kb-138720056246"
echo ""
echo "View build logs:"
echo "  aws codebuild batch-get-builds --ids $BUILD_ID --region $AWS_REGION"
echo ""
echo "=========================================="

# Save deployment info
cat > deployment-info.txt <<EOF
Mark Vle Agent Deployment (CodeBuild)
======================================
Deployment Date: $(date)
Build ID: $BUILD_ID
Project Name: $PROJECT_NAME
AWS Region: $AWS_REGION
AWS Account: $AWS_ACCOUNT_ID
ECR Repository: $ECR_REPO_NAME
Image URI: $IMAGE_URI

View Build Logs:
aws codebuild batch-get-builds --ids $BUILD_ID --region $AWS_REGION

Update AgentCore Agent:
- Image URI: $IMAGE_URI
- Environment Variables:
  * AWS_REGION=us-west-2
  * S3_BUCKET_NAME=mark-vie-kb-138720056246
EOF

echo "✓ Deployment info saved to: deployment-info.txt"

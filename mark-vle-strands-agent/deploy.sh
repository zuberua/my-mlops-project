#!/bin/bash
#
# Mark Vle Strands Agent - Complete Deployment to AgentCore
# Builds Docker image and pushes to ECR
#

set -e

echo "=========================================="
echo "Mark Vle Agent - AgentCore Deployment"
echo "=========================================="

# Change to script directory
cd "$(dirname "$0")"

# Check prerequisites
echo ""
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "✗ Docker not found. Install Docker first."
    exit 1
fi
echo "✓ Docker installed"

if ! command -v aws &> /dev/null; then
    echo "✗ AWS CLI not found. Install AWS CLI first."
    exit 1
fi
echo "✓ AWS CLI installed"

if [ ! -f config/.env ]; then
    echo "✗ config/.env not found"
    exit 1
fi
echo "✓ config/.env found"

# Load environment variables
echo ""
echo "Loading configuration..."
export $(cat config/.env | grep -v '^#' | grep -v '^$' | xargs)

# Configuration - Use environment variables or defaults
AGENT_NAME="${AGENTCORE_AGENT_NAME:-mark-vle-agent}"
ECR_REPO_NAME="${AGENTCORE_ECR_REPO:-bedrock-agentcore-mcp_server}"
AWS_REGION="${AGENTCORE_REGION:-us-east-1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Get AWS account ID
echo "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "✗ Failed to get AWS account ID. Check AWS credentials."
    exit 1
fi

ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo ""
echo "=========================================="
echo "Configuration"
echo "=========================================="
echo "Agent Name:       $AGENT_NAME"
echo "AWS Region:       $AWS_REGION"
echo "AWS Account:      $AWS_ACCOUNT_ID"
echo "ECR Repository:   $ECR_REPO_NAME"
echo "Full ECR URI:     $ECR_REPO"
echo "Image Tag:        $IMAGE_TAG"
echo "S3 Bucket:        $S3_BUCKET_NAME"
echo "=========================================="

# Confirm deployment
echo ""
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Step 1: Verify ECR repository exists
echo ""
echo "=========================================="
echo "Step 1: Verifying ECR repository"
echo "=========================================="

if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION &>/dev/null; then
    echo "✓ ECR repository exists: $ECR_REPO_NAME"
else
    echo "✗ ECR repository not found: $ECR_REPO_NAME"
    echo "Please create the repository first or check the name."
    exit 1
fi

# Step 2: Build Docker image
echo ""
echo "=========================================="
echo "Step 2: Building Docker image"
echo "=========================================="

echo "Building image: $AGENT_NAME:$IMAGE_TAG"
docker build -t $AGENT_NAME:$IMAGE_TAG .

if [ $? -eq 0 ]; then
    echo "✓ Docker image built successfully"
else
    echo "✗ Docker build failed"
    exit 1
fi

# Step 3: Login to ECR
echo ""
echo "=========================================="
echo "Step 3: Logging in to ECR"
echo "=========================================="

aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

if [ $? -eq 0 ]; then
    echo "✓ Logged in to ECR"
else
    echo "✗ ECR login failed"
    exit 1
fi

# Step 4: Tag image
echo ""
echo "=========================================="
echo "Step 4: Tagging Docker image"
echo "=========================================="

docker tag $AGENT_NAME:$IMAGE_TAG $ECR_REPO:$IMAGE_TAG

if [ $? -eq 0 ]; then
    echo "✓ Image tagged: $ECR_REPO:$IMAGE_TAG"
else
    echo "✗ Image tagging failed"
    exit 1
fi

# Step 5: Push to ECR
echo ""
echo "=========================================="
echo "Step 5: Pushing image to ECR"
echo "=========================================="

echo "Pushing to: $ECR_REPO:$IMAGE_TAG"
docker push $ECR_REPO:$IMAGE_TAG

if [ $? -eq 0 ]; then
    echo "✓ Image pushed successfully"
else
    echo "✗ Image push failed"
    exit 1
fi

# Step 6: Get image digest
echo ""
echo "Getting image digest..."
IMAGE_DIGEST=$(aws ecr describe-images \
    --repository-name $ECR_REPO_NAME \
    --image-ids imageTag=$IMAGE_TAG \
    --region $AWS_REGION \
    --query 'imageDetails[0].imageDigest' \
    --output text)

echo "✓ Image digest: $IMAGE_DIGEST"

# Summary
echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Docker Image Details:"
echo "  Repository: $ECR_REPO_NAME"
echo "  Tag:        $IMAGE_TAG"
echo "  Digest:     $IMAGE_DIGEST"
echo "  URI:        $ECR_REPO:$IMAGE_TAG"
echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Test locally:"
echo "   docker run -p 8080:8080 \\"
echo "     -e AWS_REGION=$AWS_REGION \\"
echo "     -e S3_BUCKET_NAME=$S3_BUCKET_NAME \\"
echo "     -e AWS_ACCESS_KEY_ID=\$AWS_ACCESS_KEY_ID \\"
echo "     -e AWS_SECRET_ACCESS_KEY=\$AWS_SECRET_ACCESS_KEY \\"
echo "     -e AWS_SESSION_TOKEN=\$AWS_SESSION_TOKEN \\"
echo "     $ECR_REPO:$IMAGE_TAG"
echo ""
echo "2. Update AgentCore agent configuration:"
echo "   - Agent name: $AGENT_NAME"
echo "   - Image URI: $ECR_REPO:$IMAGE_TAG"
echo "   - Region: $AWS_REGION"
echo ""
echo "3. Required IAM permissions for agent:"
echo "   - s3:GetObject on $S3_BUCKET_NAME/*"
echo "   - s3:ListBucket on $S3_BUCKET_NAME"
echo "   - bedrock:InvokeModel"
echo ""
echo "=========================================="
echo ""

# Save deployment info
DEPLOY_INFO_FILE="deployment-info.txt"
cat > $DEPLOY_INFO_FILE <<EOF
Mark Vle Agent Deployment Information
======================================
Deployment Date: $(date)
Agent Name: $AGENT_NAME
AWS Region: $AWS_REGION
AWS Account: $AWS_ACCOUNT_ID
ECR Repository: $ECR_REPO_NAME
Image Tag: $IMAGE_TAG
Image Digest: $IMAGE_DIGEST
Image URI: $ECR_REPO:$IMAGE_TAG
S3 Bucket: $S3_BUCKET_NAME

Test Command:
docker run -p 8080:8080 \\
  -e AWS_REGION=$AWS_REGION \\
  -e S3_BUCKET_NAME=$S3_BUCKET_NAME \\
  -e AWS_ACCESS_KEY_ID=\$AWS_ACCESS_KEY_ID \\
  -e AWS_SECRET_ACCESS_KEY=\$AWS_SECRET_ACCESS_KEY \\
  -e AWS_SESSION_TOKEN=\$AWS_SESSION_TOKEN \\
  $ECR_REPO:$IMAGE_TAG

AgentCore Configuration:
- Agent Name: $AGENT_NAME
- Image URI: $ECR_REPO:$IMAGE_TAG
- Region: $AWS_REGION
EOF

echo "✓ Deployment info saved to: $DEPLOY_INFO_FILE"
echo ""

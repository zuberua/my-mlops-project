#!/bin/bash

set -e

echo "=========================================="
echo "Mark Vle Strands Agent - AgentCore Deploy"
echo "=========================================="

# Check if .env file exists
if [ ! -f config/.env ]; then
    echo "Error: config/.env file not found"
    exit 1
fi

# Load environment variables
export $(cat config/.env | grep -v '^#' | xargs)

# Configuration
AGENT_NAME="mark-vle-agent"
AWS_REGION="${AWS_REGION:-us-west-2}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${AGENT_NAME}"

echo ""
echo "Configuration:"
echo "  Agent Name: $AGENT_NAME"
echo "  AWS Region: $AWS_REGION"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  ECR Repository: $ECR_REPO"
echo "  Identity: ${AGENT_IDENTITY_NAME:-Not set}"
echo "  S3 Bucket: $S3_BUCKET_NAME"
echo "=========================================="

# Step 1: Create ECR repository if it doesn't exist
echo ""
echo "Step 1: Creating ECR repository..."
aws ecr describe-repositories --repository-names $AGENT_NAME --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $AGENT_NAME --region $AWS_REGION

# Step 2: Build Docker image
echo ""
echo "Step 2: Building Docker image..."
docker build -t $AGENT_NAME:latest .

# Step 3: Login to ECR
echo ""
echo "Step 3: Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Step 4: Tag and push image
echo ""
echo "Step 4: Pushing image to ECR..."
docker tag $AGENT_NAME:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Step 5: Deploy to AgentCore
echo ""
echo "Step 5: Deploying to AgentCore..."

if [ -z "$AGENT_IDENTITY_NAME" ]; then
    echo "Warning: AGENT_IDENTITY_NAME not set in config/.env"
    echo "Skipping AgentCore deployment. Image is available at: $ECR_REPO:latest"
else
    # Check if AgentCore CLI is available
    if command -v bedrock-agentcore &> /dev/null; then
        echo "Using bedrock-agentcore CLI..."
        bedrock-agentcore deploy \
            --image $ECR_REPO:latest \
            --name $AGENT_NAME \
            --region $AWS_REGION \
            --identity $AGENT_IDENTITY_NAME \
            --scopes ${AGENT_IDENTITY_SCOPES:-read,write}
    else
        echo "bedrock-agentcore CLI not found."
        echo ""
        echo "Install with: pip install bedrock-agentcore"
        echo ""
        echo "Or deploy manually using AWS Console/API"
        echo "Image available at: $ECR_REPO:latest"
    fi
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Docker Image: $ECR_REPO:latest"
echo "Agent Name: $AGENT_NAME"
echo ""
echo "To test locally:"
echo "  docker run -p 8080:8080 \\"
echo "    -e AWS_REGION=$AWS_REGION \\"
echo "    -e S3_BUCKET_NAME=$S3_BUCKET_NAME \\"
echo "    $ECR_REPO:latest"
echo ""
echo "To invoke via AgentCore:"
echo "  aws bedrock-agent-runtime invoke-agent \\"
echo "    --agent-id YOUR_AGENT_ID \\"
echo "    --agent-alias-id YOUR_ALIAS_ID \\"
echo "    --session-id \$(uuidgen) \\"
echo "    --input-text 'What is TNH-SPEED-1?' \\"
echo "    --region $AWS_REGION"
echo "=========================================="


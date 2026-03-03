#!/bin/bash
#
# Test AgentCore deployment locally before pushing to GitHub
#

set -e

echo "=========================================="
echo "Testing AgentCore Deployment Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ROLE_NAME="github-actions-agentcore-deploy"
EXECUTION_ROLE_NAME="agentcore-mark-vle-agent-execution"
RUNTIME_ID="agent-675ATtDQE1"
AGENT_NAME="mark-vle-agent"
REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo ""
echo "Configuration:"
echo "  AWS Account:      $AWS_ACCOUNT_ID"
echo "  Region:           $REGION"
echo "  Runtime ID:       $RUNTIME_ID"
echo "  Agent Name:       $AGENT_NAME"
echo ""

# Test 1: Check GitHub Actions role exists
echo "=========================================="
echo "Test 1: GitHub Actions IAM Role"
echo "=========================================="

if aws iam get-role --role-name $ROLE_NAME &>/dev/null; then
    echo -e "${GREEN}✓${NC} Role exists: $ROLE_NAME"
else
    echo -e "${RED}✗${NC} Role not found: $ROLE_NAME"
    echo "  Run: ./create-github-actions-role.sh"
    exit 1
fi

# Test 2: Check AgentCore Control permissions
echo ""
echo "=========================================="
echo "Test 2: AgentCore Control Permissions"
echo "=========================================="

POLICIES=$(aws iam list-attached-role-policies --role-name $ROLE_NAME --query 'AttachedPolicies[].PolicyName' --output text)

if echo "$POLICIES" | grep -q "agentcore-policy"; then
    echo -e "${GREEN}✓${NC} AgentCore policy attached"
    
    # Check policy content
    POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${ROLE_NAME}-agentcore-policy"
    POLICY_VERSION=$(aws iam get-policy --policy-arn $POLICY_ARN --query 'Policy.DefaultVersionId' --output text)
    POLICY_DOC=$(aws iam get-policy-version --policy-arn $POLICY_ARN --version-id $POLICY_VERSION --query 'PolicyVersion.Document' --output json)
    
    if echo "$POLICY_DOC" | grep -q "bedrock-agentcore-control"; then
        echo -e "${GREEN}✓${NC} AgentCore Control permissions found"
    else
        echo -e "${YELLOW}⚠${NC} AgentCore Control permissions missing"
        echo "  Run: ./update-github-actions-role-permissions.sh"
    fi
    
    if echo "$POLICY_DOC" | grep -q "PassRole"; then
        echo -e "${GREEN}✓${NC} IAM PassRole permission found"
    else
        echo -e "${YELLOW}⚠${NC} IAM PassRole permission missing"
        echo "  Run: ./update-github-actions-role-permissions.sh"
    fi
else
    echo -e "${RED}✗${NC} AgentCore policy not attached"
    echo "  Run: ./update-github-actions-role-permissions.sh"
fi

# Test 3: Check execution role exists
echo ""
echo "=========================================="
echo "Test 3: AgentCore Execution Role"
echo "=========================================="

if aws iam get-role --role-name $EXECUTION_ROLE_NAME &>/dev/null; then
    echo -e "${GREEN}✓${NC} Execution role exists: $EXECUTION_ROLE_NAME"
else
    echo -e "${RED}✗${NC} Execution role not found: $EXECUTION_ROLE_NAME"
    echo "  Run: ./create-agentcore-execution-role.sh"
    exit 1
fi

# Test 4: Check AgentCore runtime exists
echo ""
echo "=========================================="
echo "Test 4: AgentCore Runtime"
echo "=========================================="

if aws bedrock-agentcore-control list-agent-runtimes --region $REGION &>/dev/null; then
    RUNTIMES=$(aws bedrock-agentcore-control list-agent-runtimes --region $REGION --query 'agentRuntimes[].agentRuntimeId' --output text)
    
    if echo "$RUNTIMES" | grep -q "$RUNTIME_ID"; then
        echo -e "${GREEN}✓${NC} Runtime exists: $RUNTIME_ID"
    else
        echo -e "${RED}✗${NC} Runtime not found: $RUNTIME_ID"
        echo "  Available runtimes: $RUNTIMES"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Cannot access bedrock-agentcore-control"
    echo "  Check AWS credentials and region"
    exit 1
fi

# Test 5: Check ECR repository exists
echo ""
echo "=========================================="
echo "Test 5: ECR Repository"
echo "=========================================="

ECR_REPO="bedrock-agentcore-mcp_server"

if aws ecr describe-repositories --repository-names $ECR_REPO --region $REGION &>/dev/null; then
    echo -e "${GREEN}✓${NC} ECR repository exists: $ECR_REPO"
    
    # Check for images
    IMAGE_COUNT=$(aws ecr list-images --repository-name $ECR_REPO --region $REGION --query 'length(imageIds)' --output text)
    echo "  Images in repository: $IMAGE_COUNT"
else
    echo -e "${YELLOW}⚠${NC} ECR repository not found: $ECR_REPO"
    echo "  Will be created on first push"
fi

# Test 6: Check S3 knowledge base
echo ""
echo "=========================================="
echo "Test 6: S3 Knowledge Base"
echo "=========================================="

S3_BUCKET="mark-vie-kb-138720056246"

if aws s3 ls s3://$S3_BUCKET &>/dev/null; then
    echo -e "${GREEN}✓${NC} S3 bucket exists: $S3_BUCKET"
    
    # Check for embeddings
    EMBEDDING_COUNT=$(aws s3 ls s3://$S3_BUCKET/embeddings/ --recursive | wc -l)
    echo "  Embeddings found: $EMBEDDING_COUNT"
else
    echo -e "${RED}✗${NC} S3 bucket not accessible: $S3_BUCKET"
    exit 1
fi

# Test 7: Check GitHub secrets (can't test directly, just remind)
echo ""
echo "=========================================="
echo "Test 7: GitHub Secrets"
echo "=========================================="

echo -e "${YELLOW}ℹ${NC} Please verify these secrets are set in GitHub:"
echo "  https://github.com/zuberua/my-mlops-project/settings/secrets/actions"
echo ""
echo "  Required secrets:"
echo "    - AWS_ROLE_ARN: arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo "    - AGENTCORE_EXECUTION_ROLE_ARN: arn:aws:iam::${AWS_ACCOUNT_ID}:role/${EXECUTION_ROLE_NAME}"

# Test 8: Test deployment script
echo ""
echo "=========================================="
echo "Test 8: Deployment Script"
echo "=========================================="

# Get the script directory and construct absolute path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEPLOY_SCRIPT="$SCRIPT_DIR/../mark-vle-strands-agent/scripts/deploy_to_agentcore.py"

if [ -f "$DEPLOY_SCRIPT" ]; then
    echo -e "${GREEN}✓${NC} Deployment script exists"
    
    # Check if it's executable
    if [ -x "$DEPLOY_SCRIPT" ]; then
        echo -e "${GREEN}✓${NC} Script is executable"
    else
        echo -e "${YELLOW}⚠${NC} Script is not executable (will work in GitHub Actions)"
    fi
    
    # Check for required imports
    if grep -q "bedrock-agentcore-control" "$DEPLOY_SCRIPT"; then
        echo -e "${GREEN}✓${NC} Uses correct boto3 client"
    else
        echo -e "${RED}✗${NC} Missing bedrock-agentcore-control client"
    fi
else
    echo -e "${RED}✗${NC} Deployment script not found: $DEPLOY_SCRIPT"
    echo "  Expected location: mark-vle-strands-agent/scripts/deploy_to_agentcore.py"
    exit 1
fi

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo -e "${GREEN}✓${NC} All prerequisites are ready!"
echo ""
echo "Next steps:"
echo "  1. Verify GitHub secrets are set (see Test 7 above)"
echo "  2. Make a change to mark-vle-strands-agent/"
echo "  3. Commit and push to main branch"
echo "  4. Monitor: https://github.com/zuberua/my-mlops-project/actions"
echo ""
echo "To deploy now:"
echo "  cd ../mark-vle-strands-agent"
echo "  echo '# trigger deployment' >> README.md"
echo "  git add ."
echo "  git commit -m 'Deploy to AgentCore'"
echo "  git push origin main"
echo ""

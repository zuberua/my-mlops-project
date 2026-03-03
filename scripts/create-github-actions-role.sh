#!/bin/bash
#
# Create IAM Role for GitHub Actions to deploy to AgentCore
#

set -e

echo "=========================================="
echo "Creating GitHub Actions IAM Role"
echo "=========================================="

# Configuration
ROLE_NAME="github-actions-agentcore-deploy"
GITHUB_ORG="zuberua"
GITHUB_REPO="my-mlops-project"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"

echo ""
echo "Configuration:"
echo "  Role Name:     $ROLE_NAME"
echo "  GitHub Repo:   $GITHUB_ORG/$GITHUB_REPO"
echo "  AWS Account:   $AWS_ACCOUNT_ID"
echo "  AWS Region:    $AWS_REGION"
echo ""

# Step 1: Create OIDC Provider (if not exists)
echo "=========================================="
echo "Step 1: Setting up GitHub OIDC Provider"
echo "=========================================="

OIDC_PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn $OIDC_PROVIDER_ARN 2>/dev/null; then
    echo "✓ OIDC provider already exists"
else
    echo "Creating OIDC provider..."
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
        --thumbprint-list 1c58a3a8518e8759bf075b76b750d4f2df264fcd
    echo "✓ OIDC provider created"
fi

# Step 2: Create Trust Policy
echo ""
echo "=========================================="
echo "Step 2: Creating Trust Policy"
echo "=========================================="

cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${OIDC_PROVIDER_ARN}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

echo "✓ Trust policy created"

# Step 3: Create IAM Role
echo ""
echo "=========================================="
echo "Step 3: Creating IAM Role"
echo "=========================================="

if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "✓ Role already exists, updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name $ROLE_NAME \
        --policy-document file:///tmp/trust-policy.json
else
    echo "Creating role..."
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Role for GitHub Actions to deploy to AgentCore via ECR"
    echo "✓ Role created"
fi

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"

# Step 4: Create ECR Policy
echo ""
echo "=========================================="
echo "Step 4: Creating ECR Policy"
echo "=========================================="

cat > /tmp/ecr-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRPushPull",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:DescribeImages",
        "ecr:ListImages"
      ],
      "Resource": "*"
    }
  ]
}
EOF

POLICY_NAME="${ROLE_NAME}-ecr-policy"
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws iam get-policy --policy-arn $POLICY_ARN 2>/dev/null; then
    echo "✓ ECR policy already exists"
    
    # Create new version
    echo "Creating new policy version..."
    aws iam create-policy-version \
        --policy-arn $POLICY_ARN \
        --policy-document file:///tmp/ecr-policy.json \
        --set-as-default
else
    echo "Creating ECR policy..."
    aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document file:///tmp/ecr-policy.json \
        --description "ECR permissions for GitHub Actions"
    echo "✓ ECR policy created"
fi

# Step 5: Attach Policy to Role
echo ""
echo "=========================================="
echo "Step 5: Attaching Policy to Role"
echo "=========================================="

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN

echo "✓ Policy attached"

# Step 6: Add S3, Bedrock, and AgentCore Control permissions
echo ""
echo "=========================================="
echo "Step 6: Adding S3, Bedrock, and AgentCore Permissions"
echo "=========================================="

cat > /tmp/agentcore-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::mark-vie-kb-138720056246",
        "arn:aws:s3:::mark-vie-kb-138720056246/*"
      ]
    },
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v2:0",
        "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
      ]
    },
    {
      "Sid": "AgentCoreControl",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassRoleToAgentCore",
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/agentcore-mark-vle-agent-execution",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "bedrock-agentcore.amazonaws.com"
        }
      }
    }
  ]
}
EOF

AGENTCORE_POLICY_NAME="${ROLE_NAME}-agentcore-policy"
AGENTCORE_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${AGENTCORE_POLICY_NAME}"

if aws iam get-policy --policy-arn $AGENTCORE_POLICY_ARN 2>/dev/null; then
    echo "✓ AgentCore policy already exists"
    
    # Create new version
    echo "Creating new policy version..."
    aws iam create-policy-version \
        --policy-arn $AGENTCORE_POLICY_ARN \
        --policy-document file:///tmp/agentcore-policy.json \
        --set-as-default
else
    echo "Creating AgentCore policy..."
    aws iam create-policy \
        --policy-name $AGENTCORE_POLICY_NAME \
        --policy-document file:///tmp/agentcore-policy.json \
        --description "S3 and Bedrock permissions for AgentCore runtime"
    echo "✓ AgentCore policy created"
fi

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $AGENTCORE_POLICY_ARN

echo "✓ AgentCore policy attached"

# Summary
echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Role ARN: $ROLE_ARN"
echo ""
echo "Next Steps:"
echo "1. Add this secret to GitHub repository:"
echo "   - Go to: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/secrets/actions"
echo "   - Click 'New repository secret'"
echo "   - Name: AWS_ROLE_ARN"
echo "   - Value: $ROLE_ARN"
echo ""
echo "2. The role has permissions for:"
echo "   ✓ ECR (push/pull images)"
echo "   ✓ S3 (read from mark-vie-kb-138720056246)"
echo "   ✓ Bedrock (invoke models)"
echo "   ✓ AgentCore Control (create/update agents)"
echo "   ✓ IAM PassRole (for AgentCore execution role)"
echo ""
echo "3. Run your GitHub Actions workflow!"
echo ""
echo "=========================================="

# Save role ARN to file
echo $ROLE_ARN > github-actions-role-arn.txt
echo "✓ Role ARN saved to: github-actions-role-arn.txt"

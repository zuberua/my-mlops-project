#!/bin/bash
#
# Update GitHub Actions IAM Role with AgentCore Control permissions
#

set -e

echo "=========================================="
echo "Updating GitHub Actions Role Permissions"
echo "=========================================="

ROLE_NAME="github-actions-agentcore-deploy"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo ""
echo "Configuration:"
echo "  Role Name:     $ROLE_NAME"
echo "  AWS Account:   $AWS_ACCOUNT_ID"
echo ""

# Check if role exists
if ! aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "Error: Role $ROLE_NAME does not exist"
    echo "Please run create-github-actions-role.sh first"
    exit 1
fi

echo "✓ Role exists"

# Create updated policy with AgentCore Control permissions
echo ""
echo "Creating updated policy with AgentCore Control permissions..."

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

# Check if policy exists
if aws iam get-policy --policy-arn $AGENTCORE_POLICY_ARN 2>/dev/null; then
    echo "✓ Policy exists, creating new version..."
    
    # Delete old non-default versions if we're at the limit (5 versions max)
    VERSIONS=$(aws iam list-policy-versions --policy-arn $AGENTCORE_POLICY_ARN --query 'Versions[?!IsDefaultVersion].VersionId' --output text)
    VERSION_COUNT=$(echo "$VERSIONS" | wc -w)
    
    if [ "$VERSION_COUNT" -ge 4 ]; then
        echo "Deleting old policy versions..."
        OLDEST_VERSION=$(echo "$VERSIONS" | awk '{print $1}')
        aws iam delete-policy-version \
            --policy-arn $AGENTCORE_POLICY_ARN \
            --version-id $OLDEST_VERSION
        echo "✓ Deleted version $OLDEST_VERSION"
    fi
    
    # Create new version
    aws iam create-policy-version \
        --policy-arn $AGENTCORE_POLICY_ARN \
        --policy-document file:///tmp/agentcore-policy.json \
        --set-as-default
    
    echo "✓ Policy updated with new version"
else
    echo "Creating new policy..."
    aws iam create-policy \
        --policy-name $AGENTCORE_POLICY_NAME \
        --policy-document file:///tmp/agentcore-policy.json \
        --description "S3, Bedrock, and AgentCore Control permissions"
    
    echo "✓ Policy created"
fi

# Attach policy to role (idempotent)
echo ""
echo "Attaching policy to role..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $AGENTCORE_POLICY_ARN 2>/dev/null || echo "✓ Policy already attached"

echo ""
echo "=========================================="
echo "✓ Update Complete!"
echo "=========================================="
echo ""
echo "Role: $ROLE_NAME"
echo "Policy: $AGENTCORE_POLICY_NAME"
echo ""
echo "The role now has permissions for:"
echo "  ✓ ECR (push/pull images)"
echo "  ✓ S3 (read from mark-vie-kb-138720056246)"
echo "  ✓ Bedrock (invoke models)"
echo "  ✓ AgentCore Control (create/update agents)"
echo "  ✓ IAM PassRole (for AgentCore execution role)"
echo ""
echo "You can now deploy agents to AgentCore via GitHub Actions!"
echo ""

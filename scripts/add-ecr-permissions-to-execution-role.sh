#!/bin/bash
#
# Add ECR permissions to AgentCore execution role
#

set -e

echo "=========================================="
echo "Adding ECR Permissions to Execution Role"
echo "=========================================="

ROLE_NAME="agentcore-mark-vle-agent-execution"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo ""
echo "Configuration:"
echo "  Role Name:     $ROLE_NAME"
echo "  AWS Account:   $AWS_ACCOUNT_ID"
echo ""

# Create ECR policy
cat > /tmp/ecr-execution-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
EOF

POLICY_NAME="${ROLE_NAME}-ecr-policy"
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws iam get-policy --policy-arn $POLICY_ARN 2>/dev/null; then
    echo "✓ ECR policy already exists, updating..."
    
    # Delete old non-default versions if at limit
    VERSIONS=$(aws iam list-policy-versions --policy-arn $POLICY_ARN --query 'Versions[?!IsDefaultVersion].VersionId' --output text)
    VERSION_COUNT=$(echo "$VERSIONS" | wc -w)
    
    if [ "$VERSION_COUNT" -ge 4 ]; then
        echo "Deleting old policy versions..."
        OLDEST_VERSION=$(echo "$VERSIONS" | awk '{print $1}')
        aws iam delete-policy-version \
            --policy-arn $POLICY_ARN \
            --version-id $OLDEST_VERSION
        echo "✓ Deleted version $OLDEST_VERSION"
    fi
    
    # Create new version
    aws iam create-policy-version \
        --policy-arn $POLICY_ARN \
        --policy-document file:///tmp/ecr-execution-policy.json \
        --set-as-default
    
    echo "✓ Policy updated"
else
    echo "Creating ECR policy..."
    aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document file:///tmp/ecr-execution-policy.json \
        --description "ECR access for AgentCore agent to pull container images"
    echo "✓ ECR policy created"
fi

# Attach policy to role
echo ""
echo "Attaching policy to role..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN 2>/dev/null || echo "✓ Policy already attached"

echo ""
echo "=========================================="
echo "✓ Update Complete!"
echo "=========================================="
echo ""
echo "The execution role now has ECR permissions:"
echo "  ✓ ecr:GetAuthorizationToken"
echo "  ✓ ecr:BatchCheckLayerAvailability"
echo "  ✓ ecr:GetDownloadUrlForLayer"
echo "  ✓ ecr:BatchGetImage"
echo ""
echo "AgentCore can now pull the Docker image from ECR!"
echo ""

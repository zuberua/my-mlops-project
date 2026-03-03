#!/bin/bash
#
# Add Bedrock Agent permissions to GitHub Actions role
#

set -e

ROLE_NAME="github-actions-agentcore-deploy"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Adding Bedrock Agent permissions to: $ROLE_NAME"

# Create Bedrock Agent policy
cat > /tmp/bedrock-agent-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAgentManagement",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListAgents",
        "bedrock:GetAgent",
        "bedrock:CreateAgent",
        "bedrock:UpdateAgent",
        "bedrock:DeleteAgent",
        "bedrock:ListAgentAliases",
        "bedrock:CreateAgentAlias",
        "bedrock:UpdateAgentAlias",
        "bedrock:PrepareAgent"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMPassRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/agentcore-mark-vle-agent-execution",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "bedrock.amazonaws.com"
        }
      }
    }
  ]
}
EOF

POLICY_NAME="${ROLE_NAME}-bedrock-agent-policy"
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws iam get-policy --policy-arn $POLICY_ARN 2>/dev/null; then
    echo "✓ Policy exists, creating new version..."
    aws iam create-policy-version \
        --policy-arn $POLICY_ARN \
        --policy-document file:///tmp/bedrock-agent-policy.json \
        --set-as-default
else
    echo "Creating policy..."
    aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document file:///tmp/bedrock-agent-policy.json \
        --description "Bedrock Agent management permissions"
fi

# Attach policy to role
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN

echo "✓ Bedrock Agent permissions added"
echo ""
echo "The role can now:"
echo "  - List, create, update agents"
echo "  - Pass the execution role to Bedrock"

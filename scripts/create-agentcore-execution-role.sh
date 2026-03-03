#!/bin/bash
#
# Create IAM Role for AgentCore Agent Runtime Execution
# This role is used BY the agent when it runs (not by GitHub Actions)
#

set -e

echo "=========================================="
echo "Creating AgentCore Execution Role"
echo "=========================================="

# Configuration
ROLE_NAME="agentcore-mark-vle-agent-execution"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"

echo ""
echo "Configuration:"
echo "  Role Name:     $ROLE_NAME"
echo "  AWS Account:   $AWS_ACCOUNT_ID"
echo "  AWS Region:    $AWS_REGION"
echo ""

# Step 1: Create Trust Policy (trust Bedrock service)
echo "=========================================="
echo "Step 1: Creating Trust Policy"
echo "=========================================="

cat > /tmp/agentcore-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "${AWS_ACCOUNT_ID}"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:agent/*"
        }
      }
    }
  ]
}
EOF

echo "✓ Trust policy created"

# Step 2: Create IAM Role
echo ""
echo "=========================================="
echo "Step 2: Creating IAM Role"
echo "=========================================="

if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "✓ Role already exists, updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name $ROLE_NAME \
        --policy-document file:///tmp/agentcore-trust-policy.json
else
    echo "Creating role..."
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/agentcore-trust-policy.json \
        --description "Execution role for AgentCore Mark Vle Agent runtime"
    echo "✓ Role created"
fi

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"

# Step 3: Create S3 Access Policy
echo ""
echo "=========================================="
echo "Step 3: Creating S3 Access Policy"
echo "=========================================="

cat > /tmp/s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::mark-vie-kb-138720056246",
        "arn:aws:s3:::mark-vie-kb-138720056246/*"
      ]
    }
  ]
}
EOF

POLICY_NAME="${ROLE_NAME}-s3-policy"
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws iam get-policy --policy-arn $POLICY_ARN 2>/dev/null; then
    echo "✓ S3 policy already exists"
    
    # Create new version
    echo "Creating new policy version..."
    aws iam create-policy-version \
        --policy-arn $POLICY_ARN \
        --policy-document file:///tmp/s3-policy.json \
        --set-as-default
else
    echo "Creating S3 policy..."
    aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document file:///tmp/s3-policy.json \
        --description "S3 read access for Mark Vle knowledge base"
    echo "✓ S3 policy created"
fi

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN

echo "✓ S3 policy attached"

# Step 4: Create Bedrock Access Policy
echo ""
echo "=========================================="
echo "Step 4: Creating Bedrock Access Policy"
echo "=========================================="

cat > /tmp/bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v2:0",
        "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
        "arn:aws:bedrock:*::foundation-model/*"
      ]
    }
  ]
}
EOF

BEDROCK_POLICY_NAME="${ROLE_NAME}-bedrock-policy"
BEDROCK_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${BEDROCK_POLICY_NAME}"

if aws iam get-policy --policy-arn $BEDROCK_POLICY_ARN 2>/dev/null; then
    echo "✓ Bedrock policy already exists"
    
    # Create new version
    echo "Creating new policy version..."
    aws iam create-policy-version \
        --policy-arn $BEDROCK_POLICY_ARN \
        --policy-document file:///tmp/bedrock-policy.json \
        --set-as-default
else
    echo "Creating Bedrock policy..."
    aws iam create-policy \
        --policy-name $BEDROCK_POLICY_NAME \
        --policy-document file:///tmp/bedrock-policy.json \
        --description "Bedrock model invocation for Mark Vle agent"
    echo "✓ Bedrock policy created"
fi

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $BEDROCK_POLICY_ARN

echo "✓ Bedrock policy attached"

# Step 5: Add CloudWatch Logs permissions
echo ""
echo "=========================================="
echo "Step 5: Adding CloudWatch Logs Policy"
echo "=========================================="

cat > /tmp/logs-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:${AWS_ACCOUNT_ID}:log-group:/aws/bedrock/*"
    }
  ]
}
EOF

LOGS_POLICY_NAME="${ROLE_NAME}-logs-policy"
LOGS_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${LOGS_POLICY_NAME}"

if aws iam get-policy --policy-arn $LOGS_POLICY_ARN 2>/dev/null; then
    echo "✓ Logs policy already exists"
    
    # Create new version
    echo "Creating new policy version..."
    aws iam create-policy-version \
        --policy-arn $LOGS_POLICY_ARN \
        --policy-document file:///tmp/logs-policy.json \
        --set-as-default
else
    echo "Creating Logs policy..."
    aws iam create-policy \
        --policy-name $LOGS_POLICY_NAME \
        --policy-document file:///tmp/logs-policy.json \
        --description "CloudWatch Logs for AgentCore agent"
    echo "✓ Logs policy created"
fi

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $LOGS_POLICY_ARN

echo "✓ Logs policy attached"

# Summary
echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Role ARN: $ROLE_ARN"
echo ""
echo "This role has permissions for:"
echo "  ✓ S3 read access (mark-vie-kb-138720056246)"
echo "  ✓ Bedrock model invocation"
echo "  ✓ CloudWatch Logs"
echo ""
echo "Next Steps:"
echo "1. Add this secret to GitHub repository:"
echo "   - Go to: https://github.com/zuberua/my-mlops-project/settings/secrets/actions"
echo "   - Click 'New repository secret'"
echo "   - Name: AGENTCORE_EXECUTION_ROLE_ARN"
echo "   - Value: $ROLE_ARN"
echo ""
echo "2. This role will be used BY the AgentCore agent at runtime"
echo "   (different from the GitHub Actions role)"
echo ""
echo "=========================================="

# Save role ARN to file
echo $ROLE_ARN > agentcore-execution-role-arn.txt
echo "✓ Role ARN saved to: agentcore-execution-role-arn.txt"

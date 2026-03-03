#!/bin/bash
#
# Fix trust policy for GitHub Actions role
#

set -e

ROLE_NAME="github-actions-agentcore-deploy"
GITHUB_ORG="zuberua"
GITHUB_REPO="my-mlops-project"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Fixing trust policy for: $ROLE_NAME"
echo "GitHub Repo: $GITHUB_ORG/$GITHUB_REPO"
echo ""

# Create trust policy
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
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

echo "Updating trust policy..."
aws iam update-assume-role-policy \
    --role-name $ROLE_NAME \
    --policy-document file:///tmp/trust-policy.json

echo "✓ Trust policy updated"
echo ""
echo "Current trust policy:"
aws iam get-role --role-name $ROLE_NAME --query 'Role.AssumeRolePolicyDocument'

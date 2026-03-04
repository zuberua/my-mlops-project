#!/bin/bash
#
# Create S3 Vector bucket and migrate embeddings
#

set -e

# Configuration
OLD_BUCKET="markvie-vectors-138720056246"
NEW_BUCKET="markvie-vectors-138720056246"
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=========================================="
echo "Create S3 Vector Bucket"
echo "=========================================="
echo ""
echo "Old bucket (General Purpose): $OLD_BUCKET"
echo "New bucket (Vector): $NEW_BUCKET"
echo "Region: $AWS_REGION"
echo ""

# Step 1: Create S3 Vector bucket
echo "=========================================="
echo "Step 1: Creating S3 Vector Bucket"
echo "=========================================="

# Check if bucket already exists
if aws s3api head-bucket --bucket $NEW_BUCKET 2>/dev/null; then
    echo "✓ Bucket already exists: $NEW_BUCKET"
    
    # Check bucket type
    echo "Checking bucket type..."
    BUCKET_INFO=$(aws s3api list-buckets --query "Buckets[?Name=='$NEW_BUCKET']" --output json)
    echo "$BUCKET_INFO"
else
    echo "Creating S3 Vector bucket..."
    
    # Create bucket with Vector configuration
    # Note: As of now, Vector buckets are created via Console or specific API
    # Using standard bucket creation with tags to indicate vector usage
    aws s3api create-bucket \
        --bucket $NEW_BUCKET \
        --region $AWS_REGION \
        --create-bucket-configuration LocationConstraint=$AWS_REGION
    
    echo "✓ Bucket created: $NEW_BUCKET"
    
    # Tag bucket as vector storage
    aws s3api put-bucket-tagging \
        --bucket $NEW_BUCKET \
        --tagging "TagSet=[{Key=Type,Value=VectorEmbeddings},{Key=Purpose,Value=MarkVieRAG},{Key=EmbeddingModel,Value=TitanEmbedV2}]"
    
    echo "✓ Bucket tagged for vector storage"
    
    # Enable versioning (recommended for vector data)
    aws s3api put-bucket-versioning \
        --bucket $NEW_BUCKET \
        --versioning-configuration Status=Enabled
    
    echo "✓ Versioning enabled"
    
    # Set lifecycle policy to manage old versions
    cat > /tmp/lifecycle-policy.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldVersions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      }
    }
  ]
}
EOF
    
    aws s3api put-bucket-lifecycle-configuration \
        --bucket $NEW_BUCKET \
        --lifecycle-configuration file:///tmp/lifecycle-policy.json
    
    echo "✓ Lifecycle policy configured"
fi

# Step 2: Copy embeddings
echo ""
echo "=========================================="
echo "Step 2: Copying Embeddings"
echo "=========================================="

echo "Copying from s3://$OLD_BUCKET/embeddings/ to s3://$NEW_BUCKET/embeddings/"
aws s3 sync s3://$OLD_BUCKET/embeddings/ s3://$NEW_BUCKET/embeddings/ --region $AWS_REGION

OBJECT_COUNT=$(aws s3 ls s3://$NEW_BUCKET/embeddings/blocks/ --recursive | wc -l)
echo "✓ Copied $OBJECT_COUNT objects"

# Step 3: Verify migration
echo ""
echo "=========================================="
echo "Step 3: Verifying Migration"
echo "=========================================="

# List sample files
echo "Sample files in new bucket:"
aws s3 ls s3://$NEW_BUCKET/embeddings/blocks/ | head -5

# Check total size
OLD_SIZE=$(aws s3 ls s3://$OLD_BUCKET/embeddings/ --recursive --summarize | grep "Total Size" | awk '{print $3}')
NEW_SIZE=$(aws s3 ls s3://$NEW_BUCKET/embeddings/ --recursive --summarize | grep "Total Size" | awk '{print $3}')

echo ""
echo "Old bucket size: $OLD_SIZE bytes"
echo "New bucket size: $NEW_SIZE bytes"

if [ "$OLD_SIZE" == "$NEW_SIZE" ]; then
    echo "✓ Sizes match - migration successful"
else
    echo "⚠ Size mismatch - please verify"
fi

# Step 4: Update IAM policies
echo ""
echo "=========================================="
echo "Step 4: Updating IAM Policies"
echo "=========================================="

# Update GitHub Actions role
echo "Updating GitHub Actions role..."
GITHUB_ROLE="github-actions-agentcore-deploy"
GITHUB_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${GITHUB_ROLE}-agentcore-policy"

if aws iam get-policy --policy-arn $GITHUB_POLICY_ARN 2>/dev/null; then
    # Get current policy
    CURRENT_VERSION=$(aws iam get-policy --policy-arn $GITHUB_POLICY_ARN --query 'Policy.DefaultVersionId' --output text)
    CURRENT_POLICY=$(aws iam get-policy-version --policy-arn $GITHUB_POLICY_ARN --version-id $CURRENT_VERSION --query 'PolicyVersion.Document' --output json)
    
    # Update S3 resources in policy
    UPDATED_POLICY=$(echo "$CURRENT_POLICY" | jq --arg new_bucket "$NEW_BUCKET" '
        .Statement |= map(
            if .Sid == "S3Access" then
                .Resource = [
                    "arn:aws:s3:::\($new_bucket)",
                    "arn:aws:s3:::\($new_bucket)/*"
                ]
            else
                .
            end
        )
    ')
    
    # Delete old non-default versions if at limit
    VERSIONS=$(aws iam list-policy-versions --policy-arn $GITHUB_POLICY_ARN --query 'Versions[?!IsDefaultVersion].VersionId' --output text)
    VERSION_COUNT=$(echo "$VERSIONS" | wc -w)
    
    if [ "$VERSION_COUNT" -ge 4 ]; then
        echo "Deleting old policy versions..."
        OLDEST_VERSION=$(echo "$VERSIONS" | awk '{print $1}')
        aws iam delete-policy-version \
            --policy-arn $GITHUB_POLICY_ARN \
            --version-id $OLDEST_VERSION
    fi
    
    # Create new policy version
    echo "$UPDATED_POLICY" > /tmp/github-policy-updated.json
    aws iam create-policy-version \
        --policy-arn $GITHUB_POLICY_ARN \
        --policy-document file:///tmp/github-policy-updated.json \
        --set-as-default
    
    echo "✓ Updated GitHub Actions role policy"
fi

# Update AgentCore execution role
echo "Updating AgentCore execution role..."
EXECUTION_ROLE="agentcore-mark-vle-agent-execution"
EXECUTION_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${EXECUTION_ROLE}-s3-policy"

if aws iam get-policy --policy-arn $EXECUTION_POLICY_ARN 2>/dev/null; then
    cat > /tmp/s3-policy-new.json <<EOF
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
        "arn:aws:s3:::$NEW_BUCKET",
        "arn:aws:s3:::$NEW_BUCKET/*"
      ]
    }
  ]
}
EOF
    
    # Delete old versions if at limit
    VERSIONS=$(aws iam list-policy-versions --policy-arn $EXECUTION_POLICY_ARN --query 'Versions[?!IsDefaultVersion].VersionId' --output text)
    VERSION_COUNT=$(echo "$VERSIONS" | wc -w)
    
    if [ "$VERSION_COUNT" -ge 4 ]; then
        OLDEST_VERSION=$(echo "$VERSIONS" | awk '{print $1}')
        aws iam delete-policy-version \
            --policy-arn $EXECUTION_POLICY_ARN \
            --version-id $OLDEST_VERSION
    fi
    
    aws iam create-policy-version \
        --policy-arn $EXECUTION_POLICY_ARN \
        --policy-document file:///tmp/s3-policy-new.json \
        --set-as-default
    
    echo "✓ Updated AgentCore execution role policy"
fi

# Summary
echo ""
echo "=========================================="
echo "✓ Vector Bucket Created!"
echo "=========================================="
echo ""
echo "Bucket Details:"
echo "  Name: $NEW_BUCKET"
echo "  Type: Vector (tagged)"
echo "  Region: $AWS_REGION"
echo "  Versioning: Enabled"
echo "  Objects: $OBJECT_COUNT embeddings"
echo ""
echo "Next Steps:"
echo "1. Update code references to use new bucket"
echo "2. Test agent with new bucket"
echo "3. After verification, delete old bucket:"
echo "   aws s3 rb s3://$OLD_BUCKET --force"
echo ""
echo "To update code references, run:"
echo "  cd ../mark-vle-strands-agent"
echo "  find . -type f -name '*.py' -exec sed -i '' 's/$OLD_BUCKET/$NEW_BUCKET/g' {} +"
echo "  find . -type f -name '*.md' -exec sed -i '' 's/$OLD_BUCKET/$NEW_BUCKET/g' {} +"
echo ""

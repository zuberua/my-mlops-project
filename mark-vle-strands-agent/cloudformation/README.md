# CloudFormation Templates

This directory contains CloudFormation templates for deploying Mark Vle Agent infrastructure.

## Overview

This setup uses AWS CloudFormation to create a proper S3 Vector Bucket and automatically configures the agent to use it. The bucket name is automatically retrieved from CloudFormation stack outputs and used to update all configuration files.

## What's Automated

### 1. Infrastructure Creation
- Creates AWS::S3Vectors::VectorBucket resource (proper vector bucket, not just tagged)
- Parameterized bucket name with automatic account ID suffix
- Environment tagging for organization
- Exports bucket name, ARN, and creation time

### 2. Configuration Management
- Automatically updates `config/config.py` with bucket name from stack outputs
- Creates/updates `config/.env` with full configuration
- No manual configuration needed

### 3. Knowledge Base Processing
- Processes block library JSON and generates embeddings
- Uploads embeddings to the newly created bucket
- Verifies embeddings are accessible

## vector-bucket.yaml

Creates an S3 Vector Bucket optimized for storing vector embeddings.

### Parameters

- **VectorBucketName** (String, Default: `markvie-vectors`)
  - Base name for the S3 Vector Bucket
  - Account ID will be automatically appended
  - Must be lowercase, 3-63 characters
  - Can only contain letters, numbers, and hyphens

- **Environment** (String, Default: `production`)
  - Environment tag for the bucket
  - Allowed values: `development`, `staging`, `production`

### Resources Created

- **AWS::S3Vectors::VectorBucket**: Specialized S3 bucket optimized for vector storage
  - Automatically named: `{VectorBucketName}-{AccountId}`
  - Tagged with Purpose, Type, Environment, ManagedBy, and Project

### Outputs

- **VectorBucketName**: Full name of the created bucket
- **VectorBucketArn**: ARN of the vector bucket
- **VectorBucketCreationTime**: Timestamp when bucket was created

### Usage

#### Using AWS CLI

```bash
# Create stack
aws cloudformation create-stack \
  --stack-name mark-vle-vector-bucket \
  --template-body file://vector-bucket.yaml \
  --parameters \
    ParameterKey=VectorBucketName,ParameterValue=markvie-vectors \
    ParameterKey=Environment,ParameterValue=production \
  --region us-west-2 \
  --profile your-profile

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name mark-vle-vector-bucket \
  --region us-west-2 \
  --profile your-profile

# Get outputs
aws cloudformation describe-stacks \
  --stack-name mark-vle-vector-bucket \
  --region us-west-2 \
  --profile your-profile \
  --query 'Stacks[0].Outputs'

# Update stack
aws cloudformation update-stack \
  --stack-name mark-vle-vector-bucket \
  --template-body file://vector-bucket.yaml \
  --parameters \
    ParameterKey=VectorBucketName,ParameterValue=markvie-vectors \
    ParameterKey=Environment,ParameterValue=staging \
  --region us-west-2 \
  --profile your-profile

# Delete stack (bucket must be empty first)
aws s3 rm s3://markvie-vectors-123456789012 --recursive
aws cloudformation delete-stack \
  --stack-name mark-vle-vector-bucket \
  --region us-west-2 \
  --profile your-profile
```

#### Using Automated Script (Recommended)

The easiest way to deploy is using the automated setup script:

```bash
cd ..
./scripts/setup_vector_bucket_and_kb.sh
```

**What the script does:**
1. Prompts for AWS profile, region, and bucket name
2. Creates the CloudFormation stack
3. Waits for stack creation to complete
4. **Automatically retrieves bucket name from stack outputs**
5. **Updates config.py with the bucket name**
6. **Creates/updates .env file with full configuration**
7. Processes the knowledge base and uploads embeddings
8. Displays summary with next steps

**Configuration Flow:**
```
CloudFormation Stack
    ↓ (creates bucket)
Stack Outputs
    ↓ (retrieves name)
config.py + .env
    ↓ (uses bucket)
Agent Runtime
```

The bucket name flows automatically from CloudFormation → config.py → .env → agent runtime, ensuring consistency across all components.

### IAM Permissions Required

To deploy this stack, you need the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "s3vectors:CreateVectorBucket",
        "s3vectors:GetVectorBucket",
        "s3vectors:DeleteVectorBucket",
        "s3vectors:ListVectorBuckets"
      ],
      "Resource": "*"
    }
  ]
}
```

### Stack Exports

The stack exports the following values for use by other stacks:

- `{StackName}-VectorBucketName`
- `{StackName}-VectorBucketArn`
- `{StackName}-VectorBucketCreationTime`

### Notes

- Vector buckets are specialized S3 buckets optimized for storing and retrieving vector embeddings
- The bucket name must be globally unique across all AWS accounts
- Account ID is automatically appended to ensure uniqueness
- Bucket can only be deleted when empty
- DeletionPolicy is not set, so bucket will be deleted when stack is deleted (if empty)

### Troubleshooting

**Error: Bucket name already exists**
- Change the `VectorBucketName` parameter to a unique value
- The full bucket name is `{VectorBucketName}-{AccountId}`

**Error: Stack already exists**
- Use `update-stack` instead of `create-stack`
- Or delete the existing stack first

**Error: Cannot delete stack - bucket not empty**
- Empty the bucket first: `aws s3 rm s3://bucket-name --recursive`
- Then delete the stack

**Error: No updates to be performed**
- The stack is already up to date
- No changes needed

### Best Practices

1. Use descriptive bucket names that indicate purpose
2. Tag resources appropriately for cost tracking
3. Use different bucket names for different environments
4. Keep CloudFormation templates in version control
5. Test in development environment before production
6. Document any custom configurations
7. Set up CloudWatch alarms for bucket metrics
8. Enable versioning for important data
9. Configure lifecycle policies for cost optimization
10. Regularly review and update IAM permissions


## Verification

After running the setup script, verify everything is configured correctly:

```bash
./scripts/verify_setup.sh
```

This checks:
- ✓ AWS CLI and credentials
- ✓ CloudFormation stack status
- ✓ S3 bucket access and embeddings count
- ✓ Configuration files (config.py and .env)
- ✓ Knowledge base JSON validity
- ✓ Python dependencies
- ✓ Bedrock access

## Configuration Management

### Automatic Updates

The setup script automatically updates:

1. **config/config.py** - Updates the default value:
   ```python
   S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME', 'markvie-vectors-138720056246')
   ```

2. **config/.env** - Creates/updates with:
   ```bash
   AWS_REGION=us-west-2
   S3_BUCKET_NAME=markvie-vectors-138720056246
   EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
   AGENT_TEMPERATURE=0.7
   AGENT_MAX_TOKENS=2000
   RAG_MAX_RESULTS=3
   RAG_SIMILARITY_THRESHOLD=0.5
   ```

### Environment Variable Precedence

The agent uses this precedence:

1. **Environment Variables** (highest priority) - Set in shell or .env file
2. **Config.py Defaults** (fallback) - Updated by setup script
3. **Hardcoded Values** (last resort) - Only if both above are missing

### Manual Override

If you need to use a different bucket:

**Option 1: Environment Variable**
```bash
export S3_BUCKET_NAME=my-custom-bucket
python3 flask_app.py
```

**Option 2: Update .env**
```bash
echo "S3_BUCKET_NAME=my-custom-bucket" >> config/.env
```

**Option 3: Update config.py**
```python
S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME', 'my-custom-bucket')
```

## Key Features

### ✓ Fully Parameterized
```yaml
Parameters:
  VectorBucketName:
    Type: String
    Default: markvie-vectors
  Environment:
    Type: String
    Default: production
```

### ✓ Automatic Bucket Naming
- Format: `{VectorBucketName}-{AWS::AccountId}`
- Example: `markvie-vectors-138720056246`
- Ensures global uniqueness
- No manual account ID entry needed

### ✓ Stack Outputs Integration
```yaml
Outputs:
  VectorBucketName:
    Value: !Sub '${VectorBucketName}-${AWS::AccountId}'
  VectorBucketArn:
    Value: !GetAtt MarkVleVectorBucket.VectorBucketArn
```

### ✓ Idempotent Operations
- Script detects existing stack and updates instead of failing
- Config updates are safe to run multiple times
- Handles both new and existing .env files

## Complete Setup Example

```bash
# 1. Run automated setup
cd my-mlops-project/mark-vle-strands-agent
./scripts/setup_vector_bucket_and_kb.sh

# When prompted, enter:
# - AWS Profile: zuberua-Admin
# - AWS Region: us-west-2
# - Bucket Name: markvie-vectors
# - Environment: production

# 2. Verify setup
./scripts/verify_setup.sh

# 3. Test locally
source venv/bin/activate
python3 flask_app.py

# 4. Test API
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the inputs of the TIMER block?"}'
```

## Integration with AgentCore

After CloudFormation setup, the agent is ready for AgentCore deployment:

1. **Bucket Created**: S3 Vector Bucket with embeddings
2. **Config Updated**: Agent knows which bucket to use
3. **IAM Roles**: Update execution role to access bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::markvie-vectors-*",
        "arn:aws:s3:::markvie-vectors-*/embeddings/*"
      ]
    }
  ]
}
```

See [../docs/AGENTCORE_DEPLOYMENT.md](../docs/AGENTCORE_DEPLOYMENT.md) for deployment steps.

## Related Documentation

- [Setup Guide](../SETUP_GUIDE.md) - Complete setup instructions
- [Main README](../README.md) - Project overview
- [AgentCore Deployment](../docs/AGENTCORE_DEPLOYMENT.md) - Deployment guide
- [Knowledge Base Guide](../knowledge-base/README.md) - KB documentation

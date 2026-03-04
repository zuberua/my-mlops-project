# Mark Vle Agent Setup Guide

Complete guide for setting up the Mark Vle Strands Agent with S3 Vector Bucket.

## Prerequisites

- AWS CLI installed and configured
- Python 3.9 or higher
- AWS account with appropriate permissions
- Git (for AgentCore deployment)

## Quick Setup (Automated)

The easiest way to set up everything:

```bash
cd my-mlops-project/mark-vle-strands-agent
./scripts/setup_vector_bucket_and_kb.sh
```

This single script will:
1. ✓ Create S3 Vector Bucket via CloudFormation
2. ✓ Update config.py with bucket name
3. ✓ Create/update .env file with configuration
4. ✓ Process block library JSON
5. ✓ Generate embeddings using Titan Embed v2
6. ✓ Upload embeddings to S3

### What the Script Prompts For

- **AWS Profile**: Your AWS CLI profile (default: `default`)
- **AWS Region**: Region for resources (default: `us-west-2`)
- **Bucket Name**: Base name without account ID (default: `markvie-vectors`)
- **Environment**: Tag for the bucket (default: `production`)

### What Gets Created

1. **CloudFormation Stack**: `mark-vle-vector-bucket`
   - S3 Vector Bucket: `{bucket-name}-{account-id}`
   - Tags for organization and tracking

2. **Configuration Files**:
   - `config/config.py`: Updated with bucket name
   - `config/.env`: Created with all settings

3. **Knowledge Base**:
   - 206 block embeddings in S3
   - Path: `s3://{bucket-name}/embeddings/blocks/`

## Manual Setup

If you prefer step-by-step control:

### Step 1: Create S3 Vector Bucket

```bash
cd my-mlops-project/mark-vle-strands-agent

# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name mark-vle-vector-bucket \
  --template-body file://cloudformation/vector-bucket.yaml \
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

# Get bucket name
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name mark-vle-vector-bucket \
  --region us-west-2 \
  --profile your-profile \
  --query 'Stacks[0].Outputs[?OutputKey==`VectorBucketName`].OutputValue' \
  --output text)

echo "Bucket created: $BUCKET_NAME"
```

### Step 2: Configure Environment

Create `config/.env`:

```bash
cat > config/.env << EOF
# AWS Configuration
AWS_REGION=us-west-2
S3_BUCKET_NAME=$BUCKET_NAME

# Embedding Model
EMBEDDING_MODEL=amazon.titan-embed-text-v2:0

# Agent Configuration
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=2000

# RAG Configuration
RAG_MAX_RESULTS=3
RAG_SIMILARITY_THRESHOLD=0.5
EOF
```

### Step 3: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Process Knowledge Base

```bash
# Set environment variables
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
export S3_BUCKET_NAME=$BUCKET_NAME

# Run processing script
cd scripts
python3 process_block_library.py
```

### Step 5: Test Locally

```bash
cd ..
python3 flask_app.py
```

Visit http://localhost:5000

## Configuration Reference

### Environment Variables

The agent uses these environment variables (set in `config/.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for S3 and Bedrock | `us-west-2` |
| `S3_BUCKET_NAME` | S3 vector bucket name | Auto-set by script |
| `EMBEDDING_MODEL` | Bedrock embedding model | `amazon.titan-embed-text-v2:0` |
| `AGENT_TEMPERATURE` | Model temperature | `0.7` |
| `AGENT_MAX_TOKENS` | Max tokens per response | `2000` |
| `RAG_MAX_RESULTS` | Max RAG search results | `3` |
| `RAG_SIMILARITY_THRESHOLD` | Minimum similarity score | `0.5` |

### Optional: LiteLLM Proxy

To use LiteLLM proxy for model inference:

```bash
# Add to config/.env
LITELLM_PROXY_URL=http://localhost:4000
LITELLM_API_KEY=your-api-key
LITELLM_MODEL=litellm_proxy/bedrock-claude-sonnet-4.5
```

### Optional: AgentCore Identity

For AgentCore deployment with identity:

```bash
# Add to config/.env
AGENT_IDENTITY_NAME=your-identity-name
AGENT_IDENTITY_SCOPES=read,write
```

## Verification

### Check CloudFormation Stack

```bash
aws cloudformation describe-stacks \
  --stack-name mark-vle-vector-bucket \
  --region us-west-2 \
  --profile your-profile
```

### Check S3 Bucket

```bash
# List embeddings
aws s3 ls s3://$BUCKET_NAME/embeddings/blocks/ \
  --profile your-profile

# Count embeddings
aws s3 ls s3://$BUCKET_NAME/embeddings/blocks/ \
  --profile your-profile | wc -l
```

### Test Agent Locally

```bash
# Start Flask app
python3 flask_app.py

# In another terminal, test API
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the inputs of the TIMER block?"}'
```

## Troubleshooting

### Issue: CloudFormation stack creation fails

**Solution**: Check IAM permissions. You need:
- `cloudformation:CreateStack`
- `s3vectors:CreateVectorBucket`
- `s3vectors:GetVectorBucket`

### Issue: Bucket name already exists

**Solution**: Change the bucket name parameter:
```bash
# Use a different base name
./scripts/setup_vector_bucket_and_kb.sh
# When prompted, enter a unique name like: markvie-vectors-dev
```

### Issue: Cannot access S3 bucket

**Solution**: Check AWS credentials:
```bash
# Verify credentials
aws sts get-caller-identity --profile your-profile

# Test S3 access
aws s3 ls s3://$BUCKET_NAME --profile your-profile
```

### Issue: Embeddings not uploading

**Solution**: Check the JSON file:
```bash
# Verify JSON is valid
python3 -c "import json; json.load(open('knowledge-base/markvie_block_library.json'))"

# Check file size
ls -lh knowledge-base/markvie_block_library.json
```

### Issue: Agent can't find embeddings

**Solution**: Verify bucket name in config:
```bash
# Check config
cat config/.env | grep S3_BUCKET_NAME

# Verify embeddings exist
aws s3 ls s3://$BUCKET_NAME/embeddings/blocks/ --profile your-profile
```

## Cleanup

To remove all resources:

```bash
# 1. Empty the S3 bucket
aws s3 rm s3://$BUCKET_NAME --recursive \
  --region us-west-2 \
  --profile your-profile

# 2. Delete CloudFormation stack
aws cloudformation delete-stack \
  --stack-name mark-vle-vector-bucket \
  --region us-west-2 \
  --profile your-profile

# 3. Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name mark-vle-vector-bucket \
  --region us-west-2 \
  --profile your-profile
```

## Next Steps

After setup is complete:

1. **Test Locally**: Run `python3 flask_app.py` and test queries
2. **Update IAM Roles**: Grant access to the vector bucket for production
3. **Deploy to AgentCore**: See [docs/AGENTCORE_DEPLOYMENT.md](docs/AGENTCORE_DEPLOYMENT.md)
4. **Monitor Usage**: Set up CloudWatch alarms for S3 and Bedrock

## Additional Resources

- [CloudFormation Template Documentation](cloudformation/README.md)
- [API Documentation](docs/API.md)
- [AgentCore Deployment Guide](docs/AGENTCORE_DEPLOYMENT.md)
- [Knowledge Base Guide](knowledge-base/README.md)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review CloudFormation stack events for errors
3. Check CloudWatch logs for runtime errors
4. Verify AWS credentials and permissions

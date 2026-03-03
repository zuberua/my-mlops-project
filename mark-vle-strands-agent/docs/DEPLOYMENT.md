# AgentCore Deployment Guide

## Quick Deploy

```bash
./deploy.sh
```

This single script will:
1. ✓ Verify prerequisites (Docker, AWS CLI)
2. ✓ Build Docker image
3. ✓ Login to ECR
4. ✓ Tag and push image to ECR
5. ✓ Save deployment info

## Configuration

Edit `config/.env` to set deployment parameters:

```bash
# AgentCore Deployment Configuration
AGENTCORE_AGENT_NAME=mark-vle-agent
AGENTCORE_ECR_REPO=bedrock-agentcore-mcp_server
AGENTCORE_REGION=us-east-1
```

## Prerequisites

- Docker installed and running
- AWS CLI configured with credentials
- Access to ECR repository: `bedrock-agentcore-mcp_server`
- AgentCore runtime already deployed in `us-east-1`

## Deployment Steps

### 1. Build and Push

```bash
cd mark-vle-strands-agent
./deploy.sh
```

The script will prompt for confirmation before deploying.

### 2. Update AgentCore Agent

After the image is pushed, update your AgentCore agent configuration:

**Image URI**: `<account-id>.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-mcp_server:latest`

**Environment Variables**:
- `AWS_REGION=us-west-2` (for S3 bucket access)
- `S3_BUCKET_NAME=mark-vie-kb-138720056246`
- `EMBEDDING_MODEL=amazon.titan-embed-text-v2:0`

**IAM Permissions Required**:
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
        "arn:aws:s3:::mark-vie-kb-138720056246",
        "arn:aws:s3:::mark-vie-kb-138720056246/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v2:0",
        "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
      ]
    }
  ]
}
```

### 3. Test Deployment

After updating AgentCore, test the agent:

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id <your-agent-id> \
  --agent-alias-id <your-alias-id> \
  --session-id $(uuidgen) \
  --input-text "What is TNH-SPEED-1?" \
  --region us-east-1
```

## Local Testing

Test the Docker image locally before deploying:

```bash
# Export AWS credentials
eval $(aws configure export-credentials --profile zuberua-Admin --format env)

# Run container
docker run -p 8080:8080 \
  -e AWS_REGION=us-west-2 \
  -e S3_BUCKET_NAME=mark-vie-kb-138720056246 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
  mark-vle-agent:latest

# Test in another terminal
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "What is TNH-SPEED-1?"}'
```

## Troubleshooting

### Error: ECR repository not found

Make sure the repository exists:
```bash
aws ecr describe-repositories \
  --repository-names bedrock-agentcore-mcp_server \
  --region us-east-1
```

### Error: Docker build failed

Check Dockerfile and ensure all required files exist:
- `agent.py`
- `agentcore_app.py`
- `plc_diagram_generator.py`
- `config/`
- `requirements.txt`

### Error: Permission denied

Ensure your AWS credentials have permissions to:
- Push to ECR
- Access S3 bucket
- Invoke Bedrock models

## Deployment Info

After deployment, check `deployment-info.txt` for:
- Image URI
- Image digest
- Test commands
- AgentCore configuration details

# AgentCore Deployment Guide

This document explains how the Mark Vle Strands Agent is deployed to AWS Bedrock AgentCore using GitHub Actions.

## Architecture

```
GitHub Push → GitHub Actions → Build Docker → Push to ECR → Deploy to AgentCore
```

## Components

### 1. Docker Container
- **Dockerfile**: Builds Python 3.13 container with agent code
- **Entry Point**: `agentcore_app.py` wraps the Strands agent for AgentCore
- **Base Image**: `python:3.13-slim`
- **Port**: 8080 (AgentCore standard)

### 2. ECR Repository
- **Name**: `bedrock-agentcore-mcp_server`
- **Region**: us-east-1
- **Account**: 138720056246
- **URI**: `138720056246.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-mcp_server`

### 3. AgentCore Runtime
- **Runtime ID**: `agent-675ATtDQE1`
- **Runtime ARN**: `arn:aws:bedrock-agentcore:us-east-1:138720056246:runtime/agent-675ATtDQE1`
- **Agent Name**: `mark-vle-agent`
- **Region**: us-east-1

### 4. IAM Roles

#### GitHub Actions Role
- **Name**: `github-actions-agentcore-deploy`
- **Purpose**: Allows GitHub Actions to build, push to ECR, and deploy to AgentCore
- **Permissions**:
  - ECR: Push/pull images
  - AgentCore Control: Create/update agents
  - IAM: PassRole to execution role
  - S3: Read from knowledge base bucket
  - Bedrock: Invoke models

#### AgentCore Execution Role
- **Name**: `agentcore-mark-vle-agent-execution`
- **Purpose**: Runtime permissions for the agent
- **Permissions**:
  - S3: Read embeddings from `mark-vie-kb-138720056246`
  - Bedrock: Invoke Claude and Titan models
  - CloudWatch: Write logs

## GitHub Actions Workflow

### Trigger
- Push to `main` branch with changes in `mark-vle-strands-agent/**`
- Manual trigger via `workflow_dispatch`

### Jobs

#### 1. build-and-push
1. Checkout code
2. Configure AWS credentials (OIDC)
3. Login to ECR
4. Build Docker image
5. Tag with commit SHA and `latest`
6. Push to ECR
7. Output image URI

#### 2. deploy-to-agentcore
1. Checkout code
2. Setup Python 3.11
3. Install boto3
4. Configure AWS credentials
5. Run `deploy_to_agentcore.py` script
6. Create/update agent in AgentCore runtime
7. Generate deployment summary

## Deployment Script

The `scripts/deploy_to_agentcore.py` script uses boto3 `bedrock-agentcore-control` client:

```python
client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')

# Check if agent exists
agents = client.list_agent_runtimes()

# Create or update
if agent_exists:
    client.update_agent_runtime(...)
else:
    client.create_agent_runtime(...)
```

## Setup Instructions

### 1. Create IAM Roles

```bash
# Create GitHub Actions role with all permissions
cd my-mlops-project/scripts
./create-github-actions-role.sh

# Create AgentCore execution role
./create-agentcore-execution-role.sh
```

### 2. Configure GitHub Secrets

Go to: https://github.com/zuberua/my-mlops-project/settings/secrets/actions

Add these secrets:
- `AWS_ROLE_ARN`: Output from `create-github-actions-role.sh`
- `AGENTCORE_EXECUTION_ROLE_ARN`: Output from `create-agentcore-execution-role.sh`

### 3. Trigger Deployment

```bash
# Make a change to agent code
cd mark-vle-strands-agent
echo "# trigger" >> agent.py

# Commit and push
git add .
git commit -m "Deploy agent to AgentCore"
git push origin main
```

### 4. Monitor Deployment

- GitHub Actions: https://github.com/zuberua/my-mlops-project/actions
- AWS Console: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agentcore

## Testing the Deployed Agent

### Using boto3

```python
import boto3

client = boto3.client('bedrock-agentcore-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentName='mark-vle-agent',
    inputText='Generate a PLC diagram for COMPARE_50'
)

print(response['output'])
```

### Using AWS CLI

```bash
aws bedrock-agentcore-runtime invoke-agent \
  --agent-name mark-vle-agent \
  --input-text "Generate a PLC diagram for COMPARE_50" \
  --region us-east-1
```

## Troubleshooting

### AccessDenied on bedrock-agentcore-control

**Problem**: GitHub Actions can't create/update agents

**Solution**: Run `create-github-actions-role.sh` to add AgentCore Control permissions

### Agent not found in runtime

**Problem**: `list_agent_runtimes()` doesn't show the agent

**Solution**: Check runtime ID is correct: `agent-675ATtDQE1`

### Container fails to start

**Problem**: Agent crashes on startup

**Solution**: 
1. Check CloudWatch logs
2. Verify execution role has S3 and Bedrock permissions
3. Test container locally: `docker run -p 8080:8080 <image>`

### OIDC authentication fails

**Problem**: "Could not assume role with OIDC"

**Solution**:
1. Verify OIDC provider exists in IAM
2. Check trust policy allows repo: `zuberua/my-mlops-project`
3. Verify GitHub secret `AWS_ROLE_ARN` is set correctly

## References

- [AWS Blog: Deploy AI Agents on Amazon Bedrock AgentCore using GitHub Actions](https://aws.amazon.com/blogs/machine-learning/deploy-ai-agents-on-amazon-bedrock-agentcore-using-github-actions/)
- [Strands AgentCore Documentation](https://github.com/awslabs/strands)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)

## Architecture Diagram

```
┌─────────────────┐
│  GitHub Repo    │
│  (main branch)  │
└────────┬────────┘
         │ push
         ▼
┌─────────────────┐
│ GitHub Actions  │
│  Workflow       │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌──────────────────┐
│  Build Docker   │  │  Configure AWS   │
│  Image          │  │  (OIDC)          │
└────────┬────────┘  └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Push to ECR    │
│  us-east-1      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Deploy to AgentCore            │
│  - Runtime: agent-675ATtDQE1    │
│  - Agent: mark-vle-agent        │
│  - Region: us-east-1            │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Agent Running in AgentCore     │
│  - Accesses S3 (us-west-2)      │
│  - Invokes Bedrock models       │
│  - Generates PLC diagrams       │
└─────────────────────────────────┘
```

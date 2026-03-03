# 🚀 AgentCore Deployment - Ready to Deploy!

## Summary

The Mark Vle Strands Agent is now configured for automated deployment to AWS Bedrock AgentCore via GitHub Actions.

## What Was Done

### 1. GitHub Actions Workflow Updated
✅ **File:** `.github/workflows/deploy-mark-vle-agent.yml`

**Changes:**
- Added Python 3.11 setup
- Added boto3 installation
- Integrated automated deployment to AgentCore
- Uses `deploy_to_agentcore.py` script with boto3 `bedrock-agentcore-control` client
- Generates deployment summary with agent details

**Jobs:**
1. `build-and-push`: Builds Docker image and pushes to ECR
2. `deploy-to-agentcore`: Deploys agent to AgentCore runtime

### 2. IAM Role Scripts Enhanced
✅ **File:** `scripts/create-github-actions-role.sh`

**Added permissions:**
- `bedrock-agentcore-control:*` - Create/update agents
- `iam:PassRole` - Pass execution role to AgentCore

✅ **File:** `scripts/update-github-actions-role-permissions.sh` (NEW)

**Purpose:** Update existing role with new permissions without recreating

### 3. Deployment Script Ready
✅ **File:** `mark-vle-strands-agent/scripts/deploy_to_agentcore.py`

**Features:**
- Uses boto3 `bedrock-agentcore-control` client
- Handles create/update logic automatically
- Saves deployment info to file
- Proper error handling

### 4. Testing Script Created
✅ **File:** `scripts/test-agentcore-deployment.sh` (NEW)

**Tests:**
- IAM roles exist
- Permissions are correct
- AgentCore runtime exists
- ECR repository exists
- S3 knowledge base accessible
- Deployment script validation

### 5. Documentation Added
✅ **Files:**
- `mark-vle-strands-agent/AGENTCORE_DEPLOYMENT.md` - Complete technical guide
- `DEPLOYMENT_CHECKLIST.md` - Step-by-step checklist
- `scripts/README.md` - Scripts documentation
- `DEPLOYMENT_READY.md` - This file

## Next Steps

### Step 1: Update IAM Role Permissions

The GitHub Actions role needs AgentCore Control permissions:

```bash
cd my-mlops-project/scripts

# If role exists, update it:
./update-github-actions-role-permissions.sh

# If role doesn't exist, create it:
./create-github-actions-role.sh
```

### Step 2: Verify GitHub Secrets

Go to: https://github.com/zuberua/my-mlops-project/settings/secrets/actions

Ensure these secrets are set:
- `AWS_ROLE_ARN`: arn:aws:iam::138720056246:role/github-actions-agentcore-deploy
- `AGENTCORE_EXECUTION_ROLE_ARN`: arn:aws:iam::138720056246:role/agentcore-mark-vle-agent-execution

### Step 3: Test Prerequisites

```bash
cd my-mlops-project/scripts
./test-agentcore-deployment.sh
```

This validates all prerequisites are ready.

### Step 4: Deploy!

```bash
cd my-mlops-project/mark-vle-strands-agent

# Make a small change to trigger deployment
echo "# deployment ready" >> README.md

# Commit and push
git add .
git commit -m "Deploy Mark Vle Agent to AgentCore"
git push origin main
```

### Step 5: Monitor Deployment

Watch the workflow:
- GitHub Actions: https://github.com/zuberua/my-mlops-project/actions
- Workflow: "Deploy Mark Vle Agent to ECR"

Expected timeline:
- Build and push: ~3-5 minutes
- Deploy to AgentCore: ~1-2 minutes
- Total: ~5-7 minutes

### Step 6: Verify Deployment

```bash
# Check agent is deployed
aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='mark-vle-agent']"
```

### Step 7: Test Agent

```python
import boto3

client = boto3.client('bedrock-agentcore-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentName='mark-vle-agent',
    inputText='Generate a PLC diagram for COMPARE_50'
)

print(response['output'])
```

## Configuration

### AWS Resources
- **Account:** 138720056246
- **Region (AgentCore):** us-east-1
- **Region (S3/Bedrock):** us-west-2
- **Runtime ID:** agent-675ATtDQE1
- **Agent Name:** mark-vle-agent
- **ECR Repository:** bedrock-agentcore-mcp_server
- **S3 Bucket:** mark-vie-kb-138720056246

### GitHub
- **Repository:** zuberua/my-mlops-project
- **Branch:** main
- **Trigger Path:** mark-vle-strands-agent/**

## Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     GitHub Repository                         │
│                   zuberua/my-mlops-project                    │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Push to main
                            │ (mark-vle-strands-agent/**)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    GitHub Actions Workflow                    │
│              .github/workflows/deploy-mark-vle-agent.yml      │
├──────────────────────────────────────────────────────────────┤
│  Job 1: build-and-push                                       │
│    1. Checkout code                                          │
│    2. Configure AWS (OIDC)                                   │
│    3. Login to ECR                                           │
│    4. Build Docker image                                     │
│    5. Push to ECR (commit SHA + latest)                      │
│    6. Output IMAGE_URI                                       │
├──────────────────────────────────────────────────────────────┤
│  Job 2: deploy-to-agentcore                                  │
│    1. Checkout code                                          │
│    2. Setup Python 3.11                                      │
│    3. Install boto3                                          │
│    4. Configure AWS (OIDC)                                   │
│    5. Run deploy_to_agentcore.py                             │
│       - Uses bedrock-agentcore-control client                │
│       - Creates or updates agent                             │
│    6. Generate deployment summary                            │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    Amazon ECR (us-east-1)                     │
│           bedrock-agentcore-mcp_server:latest                 │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              AWS Bedrock AgentCore (us-east-1)                │
│                Runtime: agent-675ATtDQE1                      │
│                 Agent: mark-vle-agent                         │
├──────────────────────────────────────────────────────────────┤
│  Runtime Capabilities:                                       │
│    • Identity (OAuth, Cognito, IAM)                          │
│    • Memory (conversation history)                           │
│    • Observability (CloudWatch, OTEL)                        │
│    • Tool execution (async, secure)                          │
│    • Long-running tasks (up to 8 hours)                      │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Agent accesses:
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│  S3 Bucket   │  │  Bedrock Models  │  │  CloudWatch  │
│  (us-west-2) │  │   (us-west-2)    │  │  (us-east-1) │
├──────────────┤  ├──────────────────┤  ├──────────────┤
│ mark-vie-kb  │  │ Claude 3.5 Haiku │  │     Logs     │
│ /embeddings/ │  │ Titan Embed v2   │  │   Metrics    │
└──────────────┘  └──────────────────┘  └──────────────┘
```

## Key Features

### Automated Deployment
- Push to main → automatic build and deploy
- No manual steps required
- Full CI/CD pipeline

### Smart Agent Management
- Automatically detects if agent exists
- Creates new agent or updates existing
- No conflicts or duplicates

### Security
- OIDC authentication (no static credentials)
- Least privilege IAM roles
- Separate execution role for runtime

### Observability
- GitHub Actions logs
- CloudWatch logs for agent
- Deployment summaries in GitHub

## Troubleshooting

### Issue: AccessDenied on bedrock-agentcore-control

**Solution:**
```bash
cd my-mlops-project/scripts
./update-github-actions-role-permissions.sh
```

### Issue: OIDC authentication fails

**Solution:**
1. Verify OIDC provider exists
2. Check trust policy
3. Verify GitHub secret `AWS_ROLE_ARN`

See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for detailed troubleshooting.

## Success Criteria

- ✅ GitHub Actions workflow completes without errors
- ✅ Agent appears in `list_agent_runtimes()` output
- ✅ Agent responds to test invocations
- ✅ PLC diagram generation works
- ✅ Knowledge base search returns results
- ✅ No errors in CloudWatch logs

## References

- [AWS Blog: Deploy AI Agents on Amazon Bedrock AgentCore using GitHub Actions](https://aws.amazon.com/blogs/machine-learning/deploy-ai-agents-on-amazon-bedrock-agentcore-using-github-actions/)
- [Strands Documentation](https://github.com/awslabs/strands)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)

---

**Status:** ✅ Ready to Deploy

**Last Updated:** March 3, 2026

**Deployment Method:** GitHub Actions with boto3 bedrock-agentcore-control client

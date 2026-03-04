# Deployment Scripts

Scripts for setting up and deploying the Mark Vle Strands Agent to AWS Bedrock AgentCore.

## Setup Scripts

### create-github-actions-role.sh
Creates the IAM role for GitHub Actions with all necessary permissions.

**Permissions included:**
- ECR: Push/pull Docker images
- S3: Read from knowledge base bucket
- Bedrock: Invoke models
- AgentCore Control: Create/update agents
- IAM: PassRole to execution role

**Usage:**
```bash
./create-github-actions-role.sh
```

**Output:**
- Creates role: `github-actions-agentcore-deploy`
- Saves ARN to: `github-actions-role-arn.txt`

### create-agentcore-execution-role.sh
Creates the IAM role for AgentCore runtime execution.

**Permissions included:**
- S3: Read embeddings from knowledge base
- Bedrock: Invoke Claude and Titan models
- CloudWatch: Write logs

**Usage:**
```bash
./create-agentcore-execution-role.sh
```

**Output:**
- Creates role: `agentcore-mark-vle-agent-execution`
- Saves ARN to: `agentcore-execution-role-arn.txt`

### update-github-actions-role-permissions.sh
Updates existing GitHub Actions role with latest permissions.

Use this if you already created the role but need to add AgentCore Control permissions.

**Usage:**
```bash
./update-github-actions-role-permissions.sh
```

**What it does:**
- Checks if role exists
- Creates new policy version with AgentCore permissions
- Handles policy version limits (max 5 versions)
- Attaches policy to role

## Testing Scripts

### test-agentcore-deployment.sh
Validates all prerequisites before deploying to AgentCore.

**Tests performed:**
1. GitHub Actions IAM role exists
2. AgentCore Control permissions are attached
3. AgentCore execution role exists
4. AgentCore runtime exists
5. ECR repository exists
6. S3 knowledge base is accessible
7. GitHub secrets reminder
8. Deployment script validation

**Usage:**
```bash
./test-agentcore-deployment.sh
```

**Output:**
- ✓ Green checkmarks for passing tests
- ✗ Red X for failing tests
- ⚠ Yellow warnings for optional items

## Deployment Flow

```
1. Setup (one-time)
   ├── create-github-actions-role.sh
   ├── create-agentcore-execution-role.sh
   └── Configure GitHub secrets

2. Validation (before each deployment)
   └── test-agentcore-deployment.sh

3. Deployment (automatic via GitHub Actions)
   ├── Push to main branch
   ├── GitHub Actions builds Docker image
   ├── Push to ECR
   └── Deploy to AgentCore using deploy_to_agentcore.py
```

## GitHub Secrets Required

After running setup scripts, add these secrets to GitHub:

**Repository:** https://github.com/zuberua/my-mlops-project/settings/secrets/actions

**Secrets:**
- `AWS_ROLE_ARN`: Output from `create-github-actions-role.sh`
- `AGENTCORE_EXECUTION_ROLE_ARN`: Output from `create-agentcore-execution-role.sh`

## Troubleshooting

### Role already exists
If you get "role already exists" error:
```bash
# Update permissions instead
./update-github-actions-role-permissions.sh
```

### AccessDenied on bedrock-agentcore-control
```bash
# Add missing permissions
./update-github-actions-role-permissions.sh
```

### OIDC authentication fails
1. Check OIDC provider exists:
   ```bash
   aws iam get-open-id-connect-provider \
     --open-id-connect-provider-arn arn:aws:iam::138720056246:oidc-provider/token.actions.githubusercontent.com
   ```

2. Verify trust policy:
   ```bash
   aws iam get-role --role-name github-actions-agentcore-deploy \
     --query 'Role.AssumeRolePolicyDocument'
   ```

### Policy version limit reached
The script automatically handles this by deleting the oldest non-default version.

## Configuration

All scripts use these defaults:

```bash
AWS_ACCOUNT_ID=138720056246
AWS_REGION=us-east-1
GITHUB_ORG=zuberua
GITHUB_REPO=my-mlops-project
RUNTIME_ID=agent-675ATtDQE1
AGENT_NAME=mark-vle-agent
S3_BUCKET=markvie-vectors-138720056246
ECR_REPOSITORY=bedrock-agentcore-mcp_server
```

To change these, edit the scripts directly.

## Related Documentation

- [DEPLOYMENT_CHECKLIST.md](../DEPLOYMENT_CHECKLIST.md) - Step-by-step deployment guide
- [mark-vle-strands-agent/AGENTCORE_DEPLOYMENT.md](../mark-vle-strands-agent/AGENTCORE_DEPLOYMENT.md) - Architecture and technical details
- [.github/workflows/deploy-mark-vle-agent.yml](../.github/workflows/deploy-mark-vle-agent.yml) - GitHub Actions workflow

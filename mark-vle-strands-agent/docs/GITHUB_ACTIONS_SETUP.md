# GitHub Actions Deployment Setup

This guide shows how to deploy the Mark Vle Agent to ECR using GitHub Actions.

## Setup Steps

### 1. Add AWS Credentials to GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

**Required Secrets:**
- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key
- `AWS_SESSION_TOKEN` - Your AWS session token (if using temporary credentials)

**How to get credentials:**
```bash
aws configure export-credentials --profile zuberua-Admin --format env
```

Copy the values and add them as GitHub secrets.

### 2. Workflow Configuration

The workflow is located at: `.github/workflows/deploy-mark-vle-agent.yml`

**Triggers:**
- Automatically on push to `main` branch when files in `mark-vle-strands-agent/` change
- Manually via "Actions" tab → "Deploy Mark Vle Agent to ECR" → "Run workflow"

**Configuration:**
```yaml
env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: bedrock-agentcore-mcp_server
  IMAGE_TAG: latest
```

### 3. Deploy

**Option A: Automatic (on push)**
```bash
cd my-mls-project
git add mark-vle-strands-agent/
git commit -m "Deploy Mark Vle Agent"
git push origin main
```

**Option B: Manual trigger**
1. Go to GitHub repository
2. Click "Actions" tab
3. Select "Deploy Mark Vle Agent to ECR"
4. Click "Run workflow"
5. Select branch (main)
6. Click "Run workflow"

### 4. Monitor Deployment

1. Go to "Actions" tab in GitHub
2. Click on the running workflow
3. Watch the build progress
4. Check the output for the image URI

### 5. Update AgentCore

After successful deployment, update your AgentCore agent with:

**Image URI:** `<account-id>.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-mcp_server:latest`

## Multiple Workflows

Yes, you can have multiple workflows! Each workflow is a separate `.yml` file in `.github/workflows/`.

Example structure:
```
.github/
  workflows/
    deploy-mark-vle-agent.yml       # This agent
    deploy-another-agent.yml        # Another agent
    run-tests.yml                   # Tests
    deploy-infrastructure.yml       # Infrastructure
```

Each workflow runs independently based on its triggers.

## Workflow Features

- ✓ Builds Docker image in GitHub's cloud runners
- ✓ Pushes to your ECR repository
- ✓ Tags with both commit SHA and 'latest'
- ✓ Only triggers when mark-vle-strands-agent files change
- ✓ Can be manually triggered anytime

## Troubleshooting

### Error: AWS credentials not configured

Make sure you added all three secrets:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_SESSION_TOKEN

### Error: ECR repository not found

Verify the repository name in the workflow matches your ECR repo:
```yaml
ECR_REPOSITORY: bedrock-agentcore-mcp_server
```

### Error: Permission denied

Ensure your AWS credentials have permissions to:
- Push to ECR
- Login to ECR

### Workflow not triggering

Check the `paths` filter in the workflow:
```yaml
paths:
  - 'mark-vle-strands-agent/**'
```

Only changes to files in this directory will trigger the workflow.

## Security Notes

- Never commit AWS credentials to the repository
- Use GitHub Secrets for all sensitive data
- Rotate credentials regularly
- Use temporary credentials (session tokens) when possible

## Example: Adding Another Agent

To add another agent deployment workflow:

1. Create `.github/workflows/deploy-another-agent.yml`
2. Copy the existing workflow
3. Update the paths and working directory:
```yaml
paths:
  - 'another-agent/**'

working-directory: ./another-agent
```

Both workflows will run independently!

# AgentCore Deployment Checklist

## Prerequisites

- [x] AWS Account: 138720056246
- [x] GitHub Repository: zuberua/my-mlops-project
- [x] AgentCore Runtime: agent-675ATtDQE1 (us-east-1)
- [x] ECR Repository: bedrock-agentcore-mcp_server (us-east-1)
- [x] S3 Knowledge Base: mark-vie-kb-138720056246 (us-west-2)

## Setup Steps

### 1. Update IAM Role Permissions

The GitHub Actions role needs AgentCore Control permissions to deploy agents.

```bash
cd my-mlops-project/scripts

# If role doesn't exist, create it:
./create-github-actions-role.sh

# If role exists, update permissions:
./update-github-actions-role-permissions.sh
```

This adds:
- `bedrock-agentcore-control:*` permissions
- `iam:PassRole` for AgentCore execution role

### 2. Verify GitHub Secrets

Go to: https://github.com/zuberua/my-mlops-project/settings/secrets/actions

Required secrets:
- `AWS_ROLE_ARN`: arn:aws:iam::138720056246:role/github-actions-agentcore-deploy
- `AGENTCORE_EXECUTION_ROLE_ARN`: arn:aws:iam::138720056246:role/agentcore-mark-vle-agent-execution

### 3. Test Deployment

```bash
# Make a small change to trigger workflow
cd my-mlops-project/mark-vle-strands-agent
echo "# deployment test" >> README.md

# Commit and push
git add .
git commit -m "Test AgentCore deployment"
git push origin main
```

### 4. Monitor Workflow

Watch the deployment:
- GitHub Actions: https://github.com/zuberua/my-mlops-project/actions
- Workflow: "Deploy Mark Vle Agent to ECR"

Expected jobs:
1. **build-and-push**: Builds Docker image and pushes to ECR (~3-5 min)
2. **deploy-to-agentcore**: Deploys to AgentCore runtime (~1-2 min)

### 5. Verify Deployment

Check agent is running:

```bash
# Using AWS CLI
aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='mark-vle-agent']"

# Using Python
python3 << EOF
import boto3
client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
agents = client.list_agent_runtimes()
for agent in agents['agentRuntimes']:
    if agent['agentRuntimeName'] == 'mark-vle-agent':
        print(f"✓ Agent deployed: {agent['agentRuntimeArn']}")
EOF
```

### 6. Test Agent

```python
import boto3

client = boto3.client('bedrock-agentcore-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentName='mark-vle-agent',
    inputText='Generate a PLC diagram for COMPARE_50'
)

print(response['output'])
```

## Troubleshooting

### Issue: AccessDenied on bedrock-agentcore-control

**Symptom**: 
```
User: arn:aws:sts::138720056246:assumed-role/github-actions-agentcore-deploy/GitHubActions-AgentCoreDeploy 
is not authorized to perform: bedrock-agentcore-control:ListAgentRuntimes
```

**Solution**:
```bash
cd my-mlops-project/scripts
./update-github-actions-role-permissions.sh
```

### Issue: Could not assume role with OIDC

**Symptom**:
```
Error: Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

**Solution**:
1. Verify OIDC provider exists:
   ```bash
   aws iam get-open-id-connect-provider \
     --open-id-connect-provider-arn arn:aws:iam::138720056246:oidc-provider/token.actions.githubusercontent.com
   ```

2. Check trust policy allows your repo:
   ```bash
   aws iam get-role --role-name github-actions-agentcore-deploy \
     --query 'Role.AssumeRolePolicyDocument'
   ```

3. Verify GitHub secret `AWS_ROLE_ARN` is set correctly

### Issue: Agent not found in runtime

**Symptom**: `list_agent_runtimes()` doesn't show the agent

**Solution**: 
- Verify runtime ID: `agent-675ATtDQE1`
- Check region: `us-east-1`
- Look for errors in GitHub Actions logs

### Issue: Container fails to start

**Symptom**: Agent crashes on startup

**Solution**:
1. Check CloudWatch logs:
   ```bash
   aws logs tail /aws/bedrock-agentcore/mark-vle-agent --follow
   ```

2. Verify execution role has permissions:
   ```bash
   aws iam get-role --role-name agentcore-mark-vle-agent-execution
   ```

3. Test container locally:
   ```bash
   docker run -p 8080:8080 \
     -e AWS_REGION=us-west-2 \
     -e S3_BUCKET_NAME=mark-vie-kb-138720056246 \
     138720056246.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-mcp_server:latest
   ```

## Files Modified

### GitHub Actions Workflow
- `.github/workflows/deploy-mark-vle-agent.yml`
  - Added Python setup
  - Added boto3 installation
  - Added automated deployment step
  - Integrated `deploy_to_agentcore.py` script

### IAM Role Scripts
- `scripts/create-github-actions-role.sh`
  - Added AgentCore Control permissions
  - Added IAM PassRole permission
  
- `scripts/update-github-actions-role-permissions.sh` (NEW)
  - Updates existing role with new permissions
  - Handles policy version limits

### Deployment Script
- `mark-vle-strands-agent/scripts/deploy_to_agentcore.py`
  - Uses boto3 `bedrock-agentcore-control` client
  - Handles create/update logic
  - Saves deployment info

### Documentation
- `mark-vle-strands-agent/AGENTCORE_DEPLOYMENT.md` (NEW)
  - Complete deployment guide
  - Architecture diagrams
  - Testing instructions

## Next Steps

After successful deployment:

1. **Monitor Performance**: Check CloudWatch metrics for agent invocations
2. **Test Functionality**: Verify all tools work (search_knowledge_base, generate_diagram, export_xml)
3. **Update Documentation**: Document any environment-specific configurations
4. **Set Up Alerts**: Create CloudWatch alarms for errors and latency
5. **Plan Rollback**: Document rollback procedure if needed

## Success Criteria

- [x] GitHub Actions workflow completes successfully
- [x] Agent appears in `list_agent_runtimes()` output
- [x] Agent responds to test invocations
- [x] PLC diagram generation works
- [x] Knowledge base search returns results
- [x] No errors in CloudWatch logs

## Reference

- AWS Blog: https://aws.amazon.com/blogs/machine-learning/deploy-ai-agents-on-amazon-bedrock-agentcore-using-github-actions/
- Strands Documentation: https://github.com/awslabs/strands
- AgentCore API: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_Operations_Amazon_Bedrock_AgentCore.html

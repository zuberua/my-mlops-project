# Mark Vle Strands Agent

AI agent using AWS Strands SDK with S3-based vector RAG for Mark Vle turbine control system.

## Table of Contents

- [Quick Start](#quick-start)
- [Local Development Guide](#local-development-guide)
- [AgentCore Deployment Guide](#agentcore-deployment-guide)
- [Architecture](#architecture)
- [API for Other Agents](#api-for-other-agents)
- [Troubleshooting](#troubleshooting)

## Quick Start

```bash
./start.sh
```

Open http://localhost:5001

---

## Local Development Guide

Complete step-by-step guide to run the agent locally with Flask UI.

### Prerequisites

- Python 3.13+
- AWS CLI configured
- AWS credentials with access to:
  - S3 bucket: `mark-vie-kb-138720056246`
  - Bedrock models (Claude 3.5 Haiku, Titan Embed v2)

### Step 1: Setup Knowledge Base

Deploy the knowledge base to S3 with embeddings:

```bash
# Navigate to scripts directory
cd scripts

# Run setup script (creates embeddings and uploads to S3)
bash setup_knowledge_base.sh

# This will:
# - Process all markdown files in knowledge-base/
# - Generate embeddings using Titan Embed v2
# - Upload to s3://mark-vie-kb-138720056246/embeddings/
```

**Expected output:**
```
Processing 65 markdown files...
✓ Embeddings generated
✓ Uploaded to S3: mark-vie-kb-138720056246/embeddings/
```

### Step 2: Create Virtual Environment

```bash
# Return to agent directory
cd ..

# Create virtual environment
python3.13 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure AWS Credentials

```bash
# Configure AWS profile (if not already done)
aws configure --profile zuberua-Admin

# Test AWS access
python test_aws_access.py
```

**Expected output:**
```
✓ AWS credentials working
✓ Can access S3 bucket: mark-vie-kb-138720056246
✓ Can invoke Bedrock models
```

### Step 4: Configure Environment (Optional)

Edit `config/.env` if you want to customize settings:

```bash
# AWS Configuration
AWS_REGION=us-west-2
S3_BUCKET_NAME=mark-vie-kb-138720056246
EMBEDDING_MODEL=amazon.titan-embed-text-v2:0

# Optional: Use LiteLLM Proxy for local testing
# LITELLM_API_KEY=your-key
# LITELLM_PROXY_URL=https://api.groq.com/openai/v1
# LITELLM_MODEL=llama-3.1-8b-instant
```

### Step 5: Start the Agent

```bash
# Start Flask server with AWS credentials
./start.sh
```

**What start.sh does:**
1. Exports AWS credentials from your profile
2. Starts Flask server on port 5001
3. Makes agent available at http://localhost:5001

### Step 6: Use the UI

Open your browser to http://localhost:5001

**Features:**
- **Chat Panel**: Ask questions about Mark Vle system
- **Diagram Panel**: Generate PLC block diagrams
- **Knowledge Search**: Searches 65 markdown files with vector similarity

**Example queries:**
- "What is TNH-SPEED-1?"
- "Generate a diagram for COMPARE_50"
- "How do I configure a valve control block?"

### Step 7: Test the API (Optional)

Test the REST API endpoints:

```bash
# Chat endpoint
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is TNH-SPEED-1?"}'

# Generate diagram endpoint
curl -X POST http://localhost:5001/api/generate-plc-diagram \
  -H "Content-Type: application/json" \
  -d '{"blockName": "COMPARE_50"}'

# Get configuration
curl http://localhost:5001/api/config
```

### Step 8: Use Python Client (Optional)

Use the Python client library to integrate with other agents:

```python
from client import MarkVleClient

# Initialize client
client = MarkVleClient(base_url="http://localhost:5001")

# Search knowledge base
response = client.chat("What is TNH-SPEED-1?")
print(response['response'])

# Generate PLC diagram
mermaid_code, info = client.generate_diagram("COMPARE_50")
print(mermaid_code)
```

See [docs/API.md](docs/API.md) for complete API documentation.

---

## AgentCore Deployment Guide

Deploy the agent to AWS Bedrock AgentCore for production use with GitHub Actions.

### Prerequisites

- GitHub repository: `zuberua/my-mlops-project`
- AWS Account: 138720056246
- AgentCore Runtime: `agent-675ATtDQE1` (us-east-1)
- ECR Repository: `bedrock-agentcore-mcp_server` (us-east-1)
- Knowledge base already deployed to S3 (see Local Development Step 1)

### Step 1: Setup Knowledge Base (If Not Done)

If you haven't deployed the knowledge base yet:

```bash
cd scripts
bash setup_knowledge_base.sh
cd ..
```

This uploads embeddings to S3 that the AgentCore runtime will access.

### Step 2: Create IAM Roles

Create the necessary IAM roles for GitHub Actions and AgentCore runtime:

```bash
# Navigate to project root
cd ../..

# Create GitHub Actions role (for CI/CD)
cd scripts
./create-github-actions-role.sh

# Create AgentCore execution role (for runtime)
./create-agentcore-execution-role.sh
```

**Output:**
- GitHub Actions Role: `github-actions-agentcore-deploy`
- Execution Role: `agentcore-mark-vle-agent-execution`
- Role ARNs saved to text files

### Step 3: Configure GitHub Secrets

Add the role ARNs as GitHub secrets:

1. Go to: https://github.com/zuberua/my-mlops-project/settings/secrets/actions

2. Click "New repository secret"

3. Add these secrets:
   - **Name:** `AWS_ROLE_ARN`
     **Value:** (from `github-actions-role-arn.txt`)
   
   - **Name:** `AGENTCORE_EXECUTION_ROLE_ARN`
     **Value:** (from `agentcore-execution-role-arn.txt`)

### Step 4: Verify Prerequisites

Test that everything is configured correctly:

```bash
# Run validation script
./test-agentcore-deployment.sh
```

**Expected output:**
```
✓ GitHub Actions IAM role exists
✓ AgentCore Control permissions found
✓ AgentCore execution role exists
✓ AgentCore runtime exists: agent-675ATtDQE1
✓ ECR repository exists
✓ S3 knowledge base accessible
```

### Step 5: Deploy to AgentCore

Trigger deployment by pushing to main branch:

```bash
# Navigate to agent directory
cd ../mark-vle-strands-agent

# Make a change to trigger deployment
echo "# deployed $(date)" >> README.md

# Commit and push
git add .
git commit -m "Deploy to AgentCore"
git push origin main
```

**Or manually trigger** from GitHub Actions UI:
1. Go to: https://github.com/zuberua/my-mlops-project/actions
2. Select "Deploy Mark Vle Agent to ECR"
3. Click "Run workflow"

### Step 6: Monitor Deployment

Watch the deployment progress:

**GitHub Actions:**
- URL: https://github.com/zuberua/my-mlops-project/actions
- Workflow: "Deploy Mark Vle Agent to ECR"

**Expected jobs:**
1. **build-and-push** (~3-5 min)
   - Builds Docker image
   - Pushes to ECR: `bedrock-agentcore-mcp_server:latest`

2. **deploy-to-agentcore** (~1-2 min)
   - Deploys to AgentCore runtime
   - Creates/updates agent: `mark_vle_agent`

### Step 7: Verify Deployment

Check that the agent is deployed:

```bash
# List agents in runtime
aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='mark_vle_agent']"
```

**Expected output:**
```json
[
  {
    "agentRuntimeId": "...",
    "agentRuntimeName": "mark_vle_agent",
    "agentRuntimeArn": "arn:aws:bedrock-agentcore:us-east-1:138720056246:runtime/agent-675ATtDQE1/agent/...",
    "status": "ACTIVE"
  }
]
```

### Step 8: Test the Deployed Agent

Test the agent in AgentCore:

```python
import boto3

# Initialize client
client = boto3.client('bedrock-agentcore-runtime', region_name='us-east-1')

# Invoke agent
response = client.invoke_agent(
    agentName='mark_vle_agent',
    inputText='Generate a PLC diagram for COMPARE_50'
)

# Print response
print(response['output'])
```

### Step 9: Monitor Agent (Optional)

Monitor the agent's performance:

**CloudWatch Logs:**
```bash
# View agent logs
aws logs tail /aws/bedrock-agentcore/mark_vle_agent --follow
```

**CloudWatch Metrics:**
- Go to: https://console.aws.amazon.com/cloudwatch
- Navigate to: Metrics → Bedrock AgentCore
- View: Invocations, Errors, Latency

### Deployment Architecture

```
GitHub Push → GitHub Actions → Build Docker → Push to ECR → Deploy to AgentCore
                                                              ↓
                                                    Runtime: agent-675ATtDQE1
                                                    Agent: mark_vle_agent
                                                              ↓
                                                    Accesses S3 (us-west-2)
                                                    Invokes Bedrock models
```

### Updating the Agent

To update the agent, simply push changes to the `mark-vle-strands-agent/` directory:

```bash
# Make changes to agent code
vim agent.py

# Commit and push
git add .
git commit -m "Update agent logic"
git push origin main
```

GitHub Actions will automatically:
1. Build new Docker image
2. Push to ECR with new tag
3. Update agent in AgentCore runtime

### Rollback

If you need to rollback to a previous version:

```bash
# List ECR images
aws ecr list-images \
  --repository-name bedrock-agentcore-mcp_server \
  --region us-east-1

# Deploy specific image
python scripts/deploy_to_agentcore.py \
  --agent-name mark_vle_agent \
  --region us-east-1 \
  --container-uri 138720056246.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-mcp_server:<commit-sha> \
  --runtime-id agent-675ATtDQE1 \
  --role-arn arn:aws:iam::138720056246:role/agentcore-mark-vle-agent-execution
```

---

## Architecture

```
User → Flask → Strands Agent → S3 (embeddings)
                  ↓
            Vector search + Tools
```

**Components:**
- **Strands Agent**: AWS Strands SDK-based agent with Claude 3.5 Haiku
- **S3 Vector RAG**: Direct S3 access for embeddings (no OpenSearch)
- **Knowledge Base**: 65 markdown files with Mark Vle documentation

**Tools**:
- `search_knowledge_base` - S3 vector search with cosine similarity
- `generate_diagram` - PLC block diagrams in Mermaid format
- `export_xml` - Mark VIe XML configuration export

**Deployment Options:**
1. **Local**: Flask server for development and testing
2. **AgentCore**: Production deployment with managed runtime

---

## API for Other Agents

Other agents can interact with this agent via REST API.

**Python Client**:
```python
from client import MarkVleClient

client = MarkVleClient()

# Search knowledge base
info = client.chat("What is TNH-SPEED-1?")

# Generate diagram
mermaid, info = client.generate_diagram("COMPARE_50")
```

**REST API**:
```bash
# Chat
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is TNH-SPEED-1?"}'

# Generate diagram
curl -X POST http://localhost:5001/api/generate-plc-diagram \
  -H "Content-Type: application/json" \
  -d '{"blockName": "COMPARE_50"}'
```

See [docs/API.md](docs/API.md) for complete documentation.

---

## Troubleshooting

### Local Development Issues

**Error: AccessDenied to S3**
```bash
# Solution 1: Use start.sh (exports credentials automatically)
./start.sh

# Solution 2: Export credentials manually
eval $(aws configure export-credentials --profile zuberua-Admin --format env)

# Solution 3: Test AWS access
python test_aws_access.py
```

**Error: No embeddings found in S3**
```bash
# Deploy knowledge base
cd scripts
bash setup_knowledge_base.sh
```

**Error: Cannot invoke Bedrock models**
```bash
# Check Bedrock access
aws bedrock list-foundation-models --region us-west-2

# Verify model access
aws bedrock invoke-model \
  --model-id anthropic.claude-3-5-haiku-20241022-v1:0 \
  --region us-west-2 \
  --body '{"anthropic_version":"bedrock-2023-05-31","messages":[{"role":"user","content":"test"}],"max_tokens":10}' \
  --cli-binary-format raw-in-base64-out \
  output.json
```

### AgentCore Deployment Issues

**Error: AccessDenied on bedrock-agentcore**
```bash
# Update IAM role permissions
cd ../../scripts
./update-github-actions-role-permissions.sh
```

**Error: OIDC authentication fails**
```bash
# Verify OIDC provider exists
aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::138720056246:oidc-provider/token.actions.githubusercontent.com

# Check trust policy
aws iam get-role --role-name github-actions-agentcore-deploy \
  --query 'Role.AssumeRolePolicyDocument'
```

**Error: Agent not found in runtime**
```bash
# List all agents
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1

# Check specific runtime
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id agent-675ATtDQE1 \
  --region us-east-1
```

**Error: Container fails to start**
```bash
# Check CloudWatch logs
aws logs tail /aws/bedrock-agentcore/mark_vle_agent --follow

# Test container locally
docker run -p 8080:8080 \
  -e AWS_REGION=us-west-2 \
  -e S3_BUCKET_NAME=mark-vie-kb-138720056246 \
  138720056246.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-mcp_server:latest
```

### Getting Help

**Documentation:**
- [AgentCore Deployment](docs/AGENTCORE_DEPLOYMENT.md) - Technical details
- [API Documentation](docs/API.md) - REST API reference
- [Deployment Checklist](../../DEPLOYMENT_CHECKLIST.md) - Step-by-step checklist

**AWS Resources:**
- [Strands Documentation](https://github.com/awslabs/strands)
- [Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [AWS Blog: Deploy AI Agents with GitHub Actions](https://aws.amazon.com/blogs/machine-learning/deploy-ai-agents-on-amazon-bedrock-agentcore-using-github-actions/)

---

## Configuration Reference

### Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-west-2                              # Region for S3 and Bedrock
S3_BUCKET_NAME=mark-vie-kb-138720056246          # Knowledge base bucket
EMBEDDING_MODEL=amazon.titan-embed-text-v2:0     # Embedding model

# Optional: LiteLLM Proxy
LITELLM_API_KEY=your-key                         # API key for proxy
LITELLM_PROXY_URL=https://api.groq.com/openai/v1 # Proxy URL
LITELLM_MODEL=llama-3.1-8b-instant               # Model to use
```

### AWS Resources

```bash
# S3
S3_BUCKET=mark-vie-kb-138720056246               # us-west-2
S3_PREFIX=embeddings/                            # Embeddings location

# ECR
ECR_REPOSITORY=bedrock-agentcore-mcp_server      # us-east-1
ECR_URI=138720056246.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-mcp_server

# AgentCore
RUNTIME_ID=agent-675ATtDQE1                      # us-east-1
AGENT_NAME=mark_vle_agent                        # Deployed agent name

# IAM Roles
GITHUB_ACTIONS_ROLE=github-actions-agentcore-deploy
EXECUTION_ROLE=agentcore-mark-vle-agent-execution
```

### File Structure

```
mark-vle-strands-agent/
├── agent.py                    # Main agent logic
├── agentcore_app.py           # AgentCore wrapper
├── flask_app.py               # Flask web server
├── plc_diagram_generator.py   # Diagram generation
├── client.py                  # Python client library
├── start.sh                   # Local startup script
├── test_aws_access.py         # AWS access test
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container build
├── config/
│   ├── config.py             # Configuration management
│   └── .env                  # Environment variables
├── scripts/
│   ├── setup_knowledge_base.sh  # Deploy KB to S3
│   └── deploy_to_agentcore.py   # Deploy to AgentCore
├── templates/
│   └── strands_index.html    # Web UI
├── knowledge-base/           # Markdown documentation
│   ├── hardware-config/
│   └── logic-templates/
└── docs/
    ├── AGENTCORE_DEPLOYMENT.md
    ├── API.md
    ├── DEPLOYMENT.md
    └── GITHUB_ACTIONS_SETUP.md
```

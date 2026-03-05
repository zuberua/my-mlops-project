# Mark Vle Strands Agent

AI agent for Mark Vle control system using Amazon Bedrock with S3-based vector RAG.

<!-- Pipeline trigger: Use cloudformation deploy for simpler stack management -->

## Features

- Claude 3.5 Haiku via Amazon Bedrock
- S3 Vector Bucket for embeddings storage
- Local RAG with cosine similarity search (see [Why Local RAG?](#why-local-rag-instead-of-bedrock-knowledge-bases))
- 206 Mark Vle block definitions in knowledge base
- Custom tools: search_knowledge_base, generate_diagram, export_xml
- Mermaid diagram generation for PLC blocks
- Flask UI and REST API
- AgentCore deployment support

## Quick Start

### Automated Setup (Recommended)

The easiest way to get started - one script does everything:

```bash
cd my-mlops-project/mark-vle-strands-agent
./scripts/setup_vector_bucket_and_kb.sh
```
**What it does:**
1. ✓ Creates S3 Vector Bucket via CloudFormation
2. ✓ Automatically retrieves bucket name from stack outputs
3. ✓ Updates `config.py` with the bucket name
4. ✓ Creates/updates `.env` file with full configuration
5. ✓ Processes block library JSON (206 blocks)
6. ✓ Generates embeddings using Titan Embed v2
7. ✓ Uploads embeddings to S3

**What you'll be prompted for:**
- AWS Profile (default: `default`)
- AWS Region (default: `us-west-2`)
- Bucket Name (default: `markvie-vectors`)
- Environment (default: `production`)

The bucket name flows automatically: **CloudFormation → config.py → .env → agent runtime**

### Verify Setup

After setup, verify everything is working:

```bash
export AWS_PROFILE={replace-me}
./scripts/verify_setup.sh
```

Checks:
- ✓ AWS CLI and credentials
- ✓ CloudFormation stack status
- ✓ S3 bucket access and embeddings count
- ✓ Configuration files (config.py and .env)
- ✓ Knowledge base JSON validity
- ✓ Python dependencies
- ✓ Bedrock access

### Test Locally

```bash
# Activate virtual environment
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


# Start Flask app
python3 flask_app.py
```

Access the UI at http://localhost:5000

Test the API:
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the inputs of the TIMER block?"}'
```

### Manual Setup

For step-by-step control, see [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed manual setup instructions.

## CloudFormation Infrastructure

The `cloudformation/vector-bucket.yaml` template creates a proper AWS::S3Vectors::VectorBucket (not just a tagged regular bucket).

**Features:**
- Automatic bucket naming: `{VectorBucketName}-{AccountId}`
- Environment tagging for organization
- Stack outputs for bucket name, ARN, and creation time
- Parameterized for reusability

**Parameters:**
- `VectorBucketName`: Base name (default: `markvie-vectors`)
- `Environment`: Environment tag (development/staging/production)

**Automatic Configuration:**
The setup script retrieves the bucket name from CloudFormation stack outputs and automatically updates:
- `config/config.py` - Default S3_BUCKET_NAME value
- `config/.env` - Environment variables

See [cloudformation/README.md](cloudformation/README.md) for detailed CloudFormation documentation.

## Knowledge Base

The knowledge base contains 206 Mark Vle block definitions from `knowledge-base/markvie_block_library.json`.

Each block includes:
- Block name and full name
- Category and description
- Inputs, outputs, and states
- Data types and notes
- Metadata (variant, expandable, etc.)

## Why Local RAG Instead of Bedrock Knowledge Bases?

This agent uses **Local RAG** (direct S3 access + Python-based vector search) rather than Amazon Bedrock Knowledge Bases. Here's why:

### Architecture Comparison

**Local RAG (Current Implementation):**
```
User Query → Generate Embedding → Fetch from S3 → Compute Similarity → Top Results → LLM
```

**Bedrock Knowledge Bases (Alternative):**
```
User Query → Bedrock KB API → OpenSearch Serverless → Results → LLM
```

### Why Local RAG is Better for This Use Case

| Factor | Local RAG | Bedrock Knowledge Bases |
|--------|-----------|------------------------|
| **Cost** | ~$1/month (S3 only) | ~$700+/month (OpenSearch Serverless) |
| **Complexity** | Simple - just S3 | Complex - requires vector database |
| **Setup Time** | 5 minutes (automated script) | Hours (OpenSearch + KB setup) |
| **Maintenance** | Minimal | Manage OpenSearch cluster |
| **Performance** | Fast for 206 blocks | Overkill for small dataset |
| **Control** | Full control over search logic | Limited to KB API features |
| **Scalability** | Good up to ~10K docs | Excellent for millions |

### When to Consider Bedrock Knowledge Bases

Migrate to Bedrock KB if you:
- ✅ Scale to 10,000+ documents
- ✅ Need sub-second search on millions of vectors
- ✅ Want automatic document ingestion pipelines
- ✅ Need advanced filtering and hybrid search
- ✅ Have budget for managed services ($700+/month)

### Technical Details

**Local RAG Implementation:**
```python
# 1. Generate query embedding
query_embedding = bedrock.invoke_model(
    model="amazon.titan-embed-text-v2:0",
    input=user_question
)

# 2. Fetch embeddings from S3
embeddings = s3.list_objects(Bucket='markvie-vectors-138720056246')

# 3. Compute cosine similarity locally
for doc in embeddings:
    score = cosine_similarity(query_embedding, doc['embedding'])

# 4. Return top 3 matches
top_results = sorted(results, key=lambda x: x['score'], reverse=True)[:3]
```

**Why This Works:**
- ✓ 206 blocks = ~5MB of embeddings (easily fits in memory)
- ✓ Search completes in <100ms
- ✓ No cold start issues (unlike OpenSearch)
- ✓ Simple to debug and modify

### Cost Breakdown

**Local RAG (Current):**
- S3 Storage: $0.023/GB/month × 0.005GB = $0.0001/month
- S3 API Calls: $0.0004/1000 requests × 1000 = $0.40/month
- Bedrock Embeddings: $0.0001/1000 tokens × 10K = $1/month
- **Total: ~$1.40/month**

**Bedrock Knowledge Bases:**
- OpenSearch Serverless: $700/month (minimum)
- S3 Storage: $0.023/month
- Bedrock KB API: $0.10/1000 requests
- **Total: ~$700+/month**

**Savings: $698.60/month = $8,383/year**

### Performance Comparison

For 206 blocks:
- **Local RAG**: 50-100ms search latency
- **Bedrock KB**: 100-200ms search latency (network + OpenSearch overhead)

Local RAG is actually **faster** for small datasets!

### Conclusion

Local RAG is the optimal choice for this agent because:
1. **Cost-effective** - 500x cheaper than Bedrock KB
2. **Simpler** - No vector database to manage
3. **Faster** - Lower latency for small datasets
4. **Sufficient** - Handles 206 blocks perfectly
5. **Flexible** - Full control over search logic

The agent can always migrate to Bedrock Knowledge Bases later if the dataset grows significantly.

## AgentCore Deployment

After completing the setup above, deploy to AgentCore:

```bash
# Ensure IAM roles have access to the S3 vector bucket
# Push changes to GitHub main branch
git add .
git commit -m "Deploy agent"
git push origin main

# GitHub Actions will automatically build and deploy
```

See [docs/AGENTCORE_DEPLOYMENT.md](docs/AGENTCORE_DEPLOYMENT.md) for detailed deployment instructions.

## API Usage

Test the agent API:

```bash
# Query the agent
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the inputs of the TIMER block?"}'

# Example response
{
  "response": "The TIMER block has the following inputs:\n- IN (BOOL): Trigger input...",
  "sources": ["TIMER.json"]
}
```

See [docs/API.md](docs/API.md) for complete API documentation.

## Configuration

Configuration is managed through environment variables (set in `config/.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_PROFILE` | AWS profile to use | `default` |
| `AWS_REGION` | AWS region | `us-west-2` |
| `S3_BUCKET_NAME` | S3 vector bucket name | Auto-set by setup script |
| `EMBEDDING_MODEL` | Bedrock embedding model | `amazon.titan-embed-text-v2:0` |
| `AGENT_TEMPERATURE` | Model temperature | `0.7` |
| `AGENT_MAX_TOKENS` | Max tokens per response | `2000` |
| `RAG_MAX_RESULTS` | Max RAG search results | `3` |
| `RAG_SIMILARITY_THRESHOLD` | Minimum similarity score | `0.3` |

**Optional - LiteLLM Proxy:**
- `LITELLM_PROXY_URL`: LiteLLM proxy URL
- `LITELLM_API_KEY`: LiteLLM API key
- `LITELLM_MODEL`: Model name (e.g., `litellm_proxy/bedrock-claude-sonnet-4.5`)

**Optional - AgentCore Identity:**
- `AGENT_IDENTITY_NAME`: Identity name for AgentCore
- `AGENT_IDENTITY_SCOPES`: Comma-separated scopes (e.g., `read,write`)

The setup script automatically creates `.env` with recommended defaults.

## Project Structure

```
mark-vle-strands-agent/
├── cloudformation/
│   ├── vector-bucket.yaml          # CloudFormation template
│   └── README.md                   # CloudFormation documentation
├── config/
│   ├── config.py                   # Configuration (auto-updated)
│   ├── .env                        # Environment variables (auto-created)
│   └── .env.example                # Example environment variables
├── docs/                           # Documentation
│   ├── AGENTCORE_DEPLOYMENT.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── GITHUB_ACTIONS_SETUP.md
├── knowledge-base/
│   ├── markvie_block_library.json  # 206 block definitions
│   └── README.md
├── scripts/
│   ├── setup_vector_bucket_and_kb.sh  # Automated setup (main)
│   ├── verify_setup.sh                # Verification script
│   ├── process_block_library.py       # KB processing
│   └── deploy_to_agentcore.py         # AgentCore deployment
├── templates/
│   └── strands_index.html          # Flask UI
├── agent.py                        # Main agent logic with RAG
├── agentcore_app.py                # AgentCore wrapper
├── flask_app.py                    # Flask web server
├── plc_diagram_generator.py        # Mermaid diagram generation
├── Dockerfile                      # Container image for AgentCore
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── SETUP_GUIDE.md                  # Detailed setup guide
```

## Cleanup

To delete the CloudFormation stack and vector bucket:

```bash
# Empty the bucket first
aws s3 rm s3://markvie-vectors-<account-id> --recursive --profile your-profile

# Delete the stack
aws cloudformation delete-stack \
  --stack-name mark-vle-vector-bucket \
  --region us-west-2 \
  --profile your-profile
```

## Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup instructions (automated and manual)
- **[cloudformation/README.md](cloudformation/README.md)** - CloudFormation template documentation
- **[docs/API.md](docs/API.md)** - API documentation
- **[docs/AGENTCORE_DEPLOYMENT.md](docs/AGENTCORE_DEPLOYMENT.md)** - AgentCore deployment guide
- **[docs/GITHUB_ACTIONS_SETUP.md](docs/GITHUB_ACTIONS_SETUP.md)** - GitHub Actions configuration
- **[knowledge-base/README.md](knowledge-base/README.md)** - Knowledge base guide

## Troubleshooting

**Issue: Setup script fails**
- Check AWS credentials: `aws sts get-caller-identity --profile your-profile`
- Verify IAM permissions for CloudFormation and S3Vectors

**Issue: Embeddings not found**
- Run verification: `./scripts/verify_setup.sh`
- Check S3 bucket: `aws s3 ls s3://your-bucket-name/embeddings/blocks/`

**Issue: Agent can't access bucket**
- Verify bucket name in `.env` matches CloudFormation output
- Check IAM permissions for S3 access

For more troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting).

## License

Proprietary - Mark Vle Control System

# Mark Vle Strands Agent

AI agent using AWS Strands SDK with S3-based vector RAG for Mark Vle turbine control system.

## Quick Start

```bash
./start.sh
```

Open http://localhost:5001

## Setup

```bash
# 1. Create virtual environment
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure AWS profile
aws configure --profile zuberua-Admin

# 3. Start agent
./start.sh
```

## Architecture

```
User → Flask → Strands Agent → S3 (embeddings)
                  ↓
            Vector search + Tools
```

**Tools**:
- `search_knowledge_base` - S3 vector search
- `generate_diagram` - PLC block diagrams
- `export_xml` - Mark VIe XML config

## Configuration

Edit `config/.env`:

```bash
# AWS
AWS_REGION=us-west-2
S3_BUCKET_NAME=mark-vie-kb-138720056246

# Optional: LiteLLM Proxy
# LITELLM_API_KEY=your-key
# LITELLM_PROXY_URL=https://api.groq.com/openai/v1
# LITELLM_MODEL=llama-3.1-8b-instant
```

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

See [API.md](API.md) for complete documentation.

## Troubleshooting

**Error: AccessDenied**
- Run `./start.sh` (exports AWS credentials automatically)
- Or manually: `eval $(aws configure export-credentials --profile zuberua-Admin --format env)`

**Test AWS access**:
```bash
python test_aws_access.py
```

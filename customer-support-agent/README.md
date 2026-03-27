# Mark VIe Programming Agent

AI-powered GE Mark VIe controller programming assistant with IEC 61131-3 FBD generation.
Uses Strands SDK `@tool` decorators, FastAPI backend, and React + TypeScript frontend.
Pin dependency tracing powered by DynamoDB GSI3 (ConnectionIndex) queries.

## Project Structure

```
customer-support-agent/
├── agent/
│   ├── __init__.py
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── app.py               # FastAPI server (chat, uploads, block search)
│   │   ├── config.py            # Env-based configuration
│   │   ├── session_store.py     # In-memory session storage
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── tools.py         # 9 Strands @tool functions
│   │       ├── dynamodb_kb.py   # DynamoDB GSI3 pin dependency tracer
│   │       └── kb.py            # Block catalog loader (GEI-100682)
│   └── frontend/                # React + TypeScript UI
│       ├── src/
│       │   ├── App.tsx          # Main app: setup wizard, chat, file uploads
│       │   ├── FBDCanvas.tsx    # SVG FBD diagram renderer (draggable blocks)
│       │   ├── useChat.ts       # Chat hook (fetch /chat endpoint)
│       │   ├── types.ts         # TypeScript interfaces
│       │   ├── App.css          # Dark theme styles
│       │   └── index.tsx        # React entry point
│       ├── public/index.html
│       ├── package.json
│       └── tsconfig.json
├── data/                        # Sample CSV data
│   ├── sample_coding_practice_report.csv
│   ├── sample_io_variable_report.csv
│   └── sample_pins.csv
├── docs/
│   └── FBD_DIAGRAM_FLOW.md
├── output/
│   └── progress.json            # GEI-100682 block library data
├── requirements.txt
├── start.sh                     # Launches backend (:8001) + frontend (:3000)
└── README.md
```

## Tools (Strands @tool)

| Tool | Description |
|------|-------------|
| `list_categories` | List all block categories in GEI-100682 library |
| `search_blocks` | Keyword search with alias expansion (relay→latch, ladder→and/or, etc.) |
| `get_block_detail` | Full pin spec (inputs/outputs/types) for a block |
| `io_context_summary` | Summary of uploaded I/O report in session |
| `io_find_connected_variable` | Map device tag → connected variable |
| `io_find_device_tag` | Map connected variable → device tag |
| `io_list_unwritten_variables` | List unresolved d_/a_ variables from CodingPracticeReport |
| `io_get_unwritten_variable_detail` | Detail for a specific unresolved variable |
| `dep_trace` | BFS signal chain trace via DynamoDB GSI3 (ConnectionIndex) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + block count |
| POST | `/chat` | Send message, get agent response |
| POST | `/chat/stream` | SSE streaming chat |
| POST | `/session/io-report` | Upload IO report + unwritten vars to session |
| GET | `/blocks/categories` | List block categories |
| GET | `/blocks/search?q=&category=` | Search blocks |
| GET | `/blocks/{name}` | Get block detail |

## Quick Start (Local)

### Prerequisites

- Python 3.13+
- Node.js 18+
- AWS credentials configured (for Bedrock model access + DynamoDB)

### Option A: start.sh (recommended)

```bash
cd customer-support-agent
./start.sh
# Starts backend on :8001 and frontend on :3000
```

### Option B: Manual

```bash
# Backend
cd customer-support-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH="$(pwd)" uvicorn agent.backend.app:app --reload --port 8001

# Frontend (separate terminal)
cd customer-support-agent/agent/frontend
npm install
REACT_APP_API_URL=http://localhost:8001 npm start
```

### Block Library Data

Place your `progress.json` (GEI-100682 block library) in `output/progress.json`.
Format: `{ "blocks": { "BLOCK_NAME": { "category": "...", "description": "...", "inputs": [...], "outputs": [...] } } }`

## Frontend Workflow

1. Select an enhancement path (Custom Logic, Hot List, Early Feature, New Custom)
2. Upload I/O Variable Report CSV (Device Tag + Connected Variable columns)
3. (Custom Logic only) Upload CodingPracticeReport CSV for unresolved variable extraction
4. Select a variable and click "Assign Logic" — agent traces dependencies via DynamoDB and generates FBD
5. View/drag blocks in the FBD Workspace panel
6. Ask follow-up questions or modify the diagram in chat
7. Export to Excel (TaskList + create_blocks sheets)

## Error Handling

- When DynamoDB/AWS credentials expire, the agent falls back to block catalog knowledge
- Source badges in the UI indicate whether the FBD came from DynamoDB KB or Agent Knowledge
- Error banners show DynamoDB connection issues without blocking the chat

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LITELLM_MODEL` | `us.anthropic.claude-sonnet-4-20250514-v1:0` | Bedrock model ID |
| `AGENT_TEMPERATURE` | `0.2` | Model temperature |
| `AGENT_MAX_TOKENS` | `8192` | Max output tokens |
| `DYNAMODB_TABLE_NAME` | `markvie-kb-poc` | DynamoDB pin knowledge base table |
| `AWS_REGION` | `us-west-2` | AWS region |
| `REACT_APP_API_URL` | `http://localhost:8001` | Backend URL (frontend) |

# Mark Vle Strands Agent API

REST API for other agents to interact with the Mark Vle knowledge base and generate PLC diagrams.

## Base URL

```
http://localhost:5001
```

## Endpoints

### 1. Chat with Agent

Send a natural language query to the agent.

**Endpoint**: `POST /api/chat`

**Request**:
```json
{
  "message": "What is TNH-SPEED-1?"
}
```

**Response**:
```json
{
  "response": "TNH-SPEED-1 is a critical analog input in the turbine control system..."
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is TNH-SPEED-1?"}'
```

**Example (Python)**:
```python
import requests

response = requests.post(
    'http://localhost:5001/api/chat',
    json={'message': 'What is TNH-SPEED-1?'}
)
print(response.json()['response'])
```

---

### 2. Generate PLC Block Diagram

Generate a Mermaid diagram for a specific PLC block.

**Endpoint**: `POST /api/generate-plc-diagram`

**Request**:
```json
{
  "blockName": "COMPARE_50"
}
```

**Response**:
```json
{
  "mermaid": "flowchart LR\n    IN1[Input 1] --> COMPARE[COMPARE_50]\n    ...",
  "blockInfo": "Found 1 relevant documents:\n\n--- Document 1: COMPARE_50 Block..."
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:5001/api/generate-plc-diagram \
  -H "Content-Type: application/json" \
  -d '{"blockName": "COMPARE_50"}'
```

**Example (Python)**:
```python
import requests

response = requests.post(
    'http://localhost:5001/api/generate-plc-diagram',
    json={'blockName': 'COMPARE_50'}
)

data = response.json()
mermaid_code = data['mermaid']
block_info = data['blockInfo']

print("Mermaid Diagram:")
print(mermaid_code)
print("\nBlock Information:")
print(block_info)
```

---

### 3. Get Configuration

Get current agent configuration.

**Endpoint**: `GET /api/config`

**Response**:
```json
{
  "agentIdentity": "Not configured",
  "litellmProxy": "Not configured",
  "litellmModel": "litellm_proxy/bedrock-claude-sonnet-4.5",
  "awsRegion": "us-west-2",
  "s3Bucket": "mark-vie-kb-138720056246",
  "embeddingModel": "amazon.titan-embed-text-v2:0"
}
```

**Example (curl)**:
```bash
curl http://localhost:5001/api/config
```

---

## Use Cases for Other Agents

### Use Case 1: Search Knowledge Base

An agent wants to find information about a specific I/O point or PLC block.

```python
import requests

def search_mark_vle_kb(query: str) -> str:
    """Search Mark Vle knowledge base"""
    response = requests.post(
        'http://localhost:5001/api/chat',
        json={'message': query}
    )
    return response.json()['response']

# Example usage
info = search_mark_vle_kb("What is TNH-SPEED-1?")
print(info)
```

### Use Case 2: Generate PLC Diagram

An agent wants to generate a diagram for a PLC block.

```python
import requests

def generate_plc_diagram(block_name: str) -> dict:
    """Generate PLC block diagram"""
    response = requests.post(
        'http://localhost:5001/api/generate-plc-diagram',
        json={'blockName': block_name}
    )
    return response.json()

# Example usage
result = generate_plc_diagram("COMPARE_50")
mermaid_code = result['mermaid']
block_info = result['blockInfo']

# Save diagram to file
with open('compare_50.mmd', 'w') as f:
    f.write(mermaid_code)

print(f"Diagram saved to compare_50.mmd")
print(f"Block info: {block_info}")
```

### Use Case 3: Multi-Step Workflow

An agent wants to:
1. Search for block information
2. Generate a diagram
3. Process the results

```python
import requests

class MarkVleClient:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
    
    def chat(self, message: str) -> str:
        """Send message to agent"""
        response = requests.post(
            f'{self.base_url}/api/chat',
            json={'message': message}
        )
        return response.json()['response']
    
    def generate_diagram(self, block_name: str) -> dict:
        """Generate PLC diagram"""
        response = requests.post(
            f'{self.base_url}/api/generate-plc-diagram',
            json={'blockName': block_name}
        )
        return response.json()
    
    def get_config(self) -> dict:
        """Get agent configuration"""
        response = requests.get(f'{self.base_url}/api/config')
        return response.json()

# Example workflow
client = MarkVleClient()

# Step 1: Search for block
info = client.chat("Tell me about COMPARE_50")
print("Block Information:")
print(info)

# Step 2: Generate diagram
diagram = client.generate_diagram("COMPARE_50")
print("\nMermaid Diagram:")
print(diagram['mermaid'])

# Step 3: Check configuration
config = client.get_config()
print(f"\nUsing S3 bucket: {config['s3Bucket']}")
```

---

## Supported Block Names

Common PLC blocks in the knowledge base:
- `COMPARE_50` - Comparison block
- `MOVE_150` - Move/transfer block
- `TNH-SPEED-1` - Speed sensor input
- `FSV-MAIN-SOL` - Fuel solenoid valve
- `FUEL-VALVE-CMD` - Fuel valve command

To find available blocks, ask the agent:
```python
response = client.chat("List all available PLC blocks")
```

---

## Error Handling

All endpoints return standard HTTP status codes:
- `200` - Success
- `400` - Bad request (missing parameters)
- `500` - Server error

**Error Response Format**:
```json
{
  "error": "Error message with details"
}
```

**Example Error Handling**:
```python
import requests

try:
    response = requests.post(
        'http://localhost:5001/api/generate-plc-diagram',
        json={'blockName': 'INVALID_BLOCK'}
    )
    response.raise_for_status()
    data = response.json()
    
    if 'error' in data:
        print(f"Error: {data['error']}")
    else:
        print(f"Success: {data['mermaid']}")
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

---

## Agent Integration Example

Complete example for another agent to use this API:

```python
#!/usr/bin/env python3
"""
Example: Another agent using Mark Vle Strands Agent API
"""

import requests
import json

class MarkVleIntegration:
    """Integration with Mark Vle Strands Agent"""
    
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify agent is running"""
        try:
            response = requests.get(f'{self.base_url}/api/config', timeout=5)
            response.raise_for_status()
            print("✓ Connected to Mark Vle Strands Agent")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to agent: {e}")
    
    def ask(self, question: str) -> str:
        """Ask agent a question"""
        response = requests.post(
            f'{self.base_url}/api/chat',
            json={'message': question}
        )
        response.raise_for_status()
        return response.json()['response']
    
    def get_diagram(self, block_name: str) -> tuple[str, str]:
        """Get PLC diagram and block info"""
        response = requests.post(
            f'{self.base_url}/api/generate-plc-diagram',
            json={'blockName': block_name}
        )
        response.raise_for_status()
        data = response.json()
        return data['mermaid'], data['blockInfo']

# Usage
if __name__ == '__main__':
    agent = MarkVleIntegration()
    
    # Example 1: Ask about a component
    print("Question: What is TNH-SPEED-1?")
    answer = agent.ask("What is TNH-SPEED-1?")
    print(f"Answer: {answer}\n")
    
    # Example 2: Generate diagram
    print("Generating diagram for COMPARE_50...")
    mermaid, info = agent.get_diagram("COMPARE_50")
    print(f"Mermaid code:\n{mermaid}\n")
    print(f"Block info:\n{info}")
```

---

## Notes

- The agent must be running (`./start.sh`) before making API calls
- AWS credentials must be properly configured for S3 access
- The agent performs vector search on S3 embeddings for accurate results
- Diagram generation uses the knowledge base to create accurate PLC-style diagrams

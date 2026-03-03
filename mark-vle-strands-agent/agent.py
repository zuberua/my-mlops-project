#!/usr/bin/env python3
"""
Mark Vle Strands Agent with S3 Vector RAG
Uses Strands Agents SDK with custom tools for knowledge base search
"""

from strands import Agent, tool
import boto3
import json
import numpy as np
from typing import List, Dict
from config.config import Config
import os

# Load and validate configuration
Config.print_config()

# Don't create clients at import time - create them lazily
_session = None
_bedrock = None
_s3 = None
BUCKET_NAME = Config.S3_BUCKET_NAME

def get_aws_clients():
    """Get or create AWS clients with proper credentials"""
    global _session, _bedrock, _s3
    
    if _session is None:
        try:
            if os.environ.get('AWS_ACCESS_KEY_ID'):
                _session = boto3.Session(region_name=Config.AWS_REGION)
            else:
                _session = boto3.Session(profile_name='zuberua-Admin', region_name=Config.AWS_REGION)
            
            _bedrock = _session.client('bedrock-runtime')
            _s3 = _session.client('s3')
            
            # Test access
            sts = _session.client('sts')
            identity = sts.get_caller_identity()
            print(f"[AWS] ✓ {identity['Arn']}")
            
            _s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='embeddings/', MaxKeys=1)
            print(f"[AWS] ✓ S3: {BUCKET_NAME}")
            
        except Exception as e:
            print(f"[AWS] ✗ {e}")
            print("[AWS] Run: ./start.sh")
            raise
    
    return _bedrock, _s3

# Set AWS region as environment variable for Strands SDK
os.environ['AWS_DEFAULT_REGION'] = Config.AWS_REGION
os.environ['AWS_REGION'] = Config.AWS_REGION

def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Amazon Titan"""
    bedrock, _ = get_aws_clients()
    response = bedrock.invoke_model(
        modelId=Config.EMBEDDING_MODEL,
        body=json.dumps({"inputText": text})
    )
    result = json.loads(response['body'].read())
    return result['embedding']

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

@tool
def search_knowledge_base(query: str, max_results: int = 3) -> str:
    """
    Search the Mark Vle knowledge base for information about I/O points, 
    PLC blocks, control logic, and system configuration.
    
    Args:
        query: The search query (e.g., "TNH-SPEED-1", "COMPARE_50", "fuel valve")
        max_results: Maximum number of results to return (default from config)
    
    Returns:
        Relevant documentation from the knowledge base
    """
    if max_results is None:
        max_results = Config.RAG_MAX_RESULTS
    print(f"[Tool] Searching knowledge base for: {query}")
    
    try:
        # Get AWS clients
        _, s3 = get_aws_clients()
        
        # Generate query embedding
        query_embedding = generate_embedding(query)
        
        # List all embedding files
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='embeddings/')
        
        if 'Contents' not in response:
            return "No documents found in knowledge base."
        
        # Score each document chunk
        scored_chunks = []
        
        for obj in response['Contents']:
            key = obj['Key']
            
            if key == 'embeddings/index.json' or not key.endswith('.json'):
                continue
            
            try:
                doc_response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                doc_data = json.loads(doc_response['Body'].read().decode('utf-8'))
                
                # Calculate similarity for each chunk
                for chunk in doc_data.get('chunks', []):
                    similarity = cosine_similarity(query_embedding, chunk['embedding'])
                    
                    if similarity > Config.RAG_SIMILARITY_THRESHOLD:
                        scored_chunks.append({
                            'filename': doc_data['filename'],
                            'title': doc_data['title'],
                            'chunk_text': chunk['text'],
                            'full_content': doc_data['full_content'],
                            'similarity': similarity
                        })
            except Exception as e:
                print(f"[Tool] Error processing {key}: {e}")
                continue
        
        # Sort and deduplicate
        scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
        
        seen_files = set()
        unique_docs = []
        
        for chunk in scored_chunks:
            if chunk['filename'] not in seen_files:
                seen_files.add(chunk['filename'])
                unique_docs.append(chunk)
                if len(unique_docs) >= max_results:
                    break
        
        if not unique_docs:
            return f"No relevant information found for: {query}"
        
        # Format results
        result = f"Found {len(unique_docs)} relevant documents:\n\n"
        for i, doc in enumerate(unique_docs, 1):
            result += f"--- Document {i}: {doc['title']} (similarity: {doc['similarity']:.2f}) ---\n"
            result += doc['full_content']
            result += "\n\n"
        
        return result
    
    except Exception as e:
        error_msg = f"Error accessing knowledge base: {str(e)}"
        print(f"[Tool] {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg

@tool
def generate_diagram(block_name: str) -> str:
    """
    REQUIRED TOOL: Generate a PLC-style Function Block Diagram (FBD) based on knowledge base information.
    
    ALWAYS use this tool when the user asks to:
    - "generate a diagram"
    - "draw a diagram" 
    - "create a diagram"
    - "show a diagram"
    - "visualize"
    - "FBD"
    - "PLC block diagram"
    
    This tool retrieves block information from the knowledge base and creates a PLC-style FBD.
    
    Args:
        block_name: Name of the block or I/O tag (e.g., "MOVE_150", "COMPARE_50", "TNH-SPEED-1")
    
    Returns:
        Mermaid diagram code for PLC-style FBD
    """
    print(f"[Tool] Generating PLC FBD diagram for: {block_name}")
    
    # Get detailed information from knowledge base
    info = search_knowledge_base(block_name, max_results=1)
    
    # Generate PLC-style Mermaid diagram
    from plc_diagram_generator import generate_plc_block_from_rag
    
    mermaid_code = generate_plc_block_from_rag(info)
    
    result = f"""```mermaid
{mermaid_code}
```

**Block Information from Knowledge Base:**

{info}
"""
    
    return result

@tool
def export_xml(block_name: str) -> str:
    """
    Export Mark VIe XML configuration for a PLC function block.
    Uses information from the knowledge base to generate accurate XML.
    
    Args:
        block_name: Name of the block (e.g., "MOVE_150", "COMPARE_50")
    
    Returns:
        XML configuration string based on knowledge base information
    """
    print(f"[Tool] Exporting XML for: {block_name}")
    
    # Get block information from knowledge base
    block_info = search_knowledge_base(block_name, max_results=1)
    
    # Return the information and let the agent generate the XML
    return f"""Based on the knowledge base information:

{block_info}

Please generate a Mark VIe XML configuration for this block using the standard format with:
- FunctionBlock root element with name, type, version
- Properties section (BlockType, Instance, StatusCode, ExecutionOrder)
- Inputs section with all input pins
- Outputs section with all output pins
- Logic section with Structured Text code"""

# Create the Strands agent with LiteLLM proxy support
model_config = Config.get_model_config()

# Check if LiteLLM is configured
if Config.LITELLM_PROXY_URL and Config.LITELLM_API_KEY:
    # Use LiteLLM model
    from strands.models import LiteLLMModel
    
    model = LiteLLMModel(
        client_args={
            "api_key": Config.LITELLM_API_KEY,
            "base_url": Config.LITELLM_PROXY_URL
        },
        model_id=Config.LITELLM_MODEL,
        params={
            "temperature": Config.AGENT_TEMPERATURE,
            "max_tokens": Config.AGENT_MAX_TOKENS
        }
    )
    
    print(f"✓ Using LiteLLM Model")
    print(f"  Proxy: {Config.LITELLM_PROXY_URL}")
    print(f"  Model: {Config.LITELLM_MODEL}")
else:
    # Use default Bedrock model
    model = model_config['model']
    print(f"✓ Using Bedrock Model: {model}")

# Build agent kwargs
agent_kwargs = {
    'model': model,
    'system_prompt': """You are an expert assistant for the Mark Vle turbine control system.

CRITICAL INSTRUCTION: When a user asks you to generate, draw, create, or show a DIAGRAM, you MUST call the generate_diagram tool. Do NOT just describe the diagram - actually call the tool to create it.

You have access to a knowledge base containing:
- I/O point specifications (analog inputs, digital outputs, etc.)
- PLC function blocks (MOVE_150, COMPARE_50)
- Control logic and interlocks
- System configuration guides

Your tools and when to use them:

1. search_knowledge_base - Use for questions about specifications, details, explanations
   Example: "What is TNH-SPEED-1?" → search_knowledge_base("TNH-SPEED-1")

2. generate_diagram - MANDATORY for any diagram request
   Example: "Generate diagram for MOVE_150" → generate_diagram("MOVE_150")
   Example: "Draw FBD for COMPARE_50" → generate_diagram("COMPARE_50")
   Example: "Show diagram of TNH-SPEED-1" → generate_diagram("TNH-SPEED-1")

3. export_xml - Use when user wants XML configuration
   Example: "Export XML for MOVE_150" → export_xml("MOVE_150")

REMEMBER: If the user's message contains words like "diagram", "draw", "generate", "visualize", "FBD", "show" combined with a block name, you MUST call generate_diagram. Do not just explain - create the actual diagram!""",
    'tools': [search_knowledge_base, generate_diagram, export_xml]
}

# Add access token if available
if 'access_token' in model_config:
    agent_kwargs['access_token'] = model_config['access_token']

agent = Agent(**agent_kwargs)

# Example usage
if __name__ == "__main__":
    print("="*60)
    print("Mark Vle Strands Agent")
    print("="*60)
    
    # Test queries
    queries = [
        "What is TNH-SPEED-1?",
        "Show me the COMPARE_50 block",
        "Generate a PLC diagram for MOVE_150",
        "Export XML for COMPARE_50"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        print("-"*60)
        response = agent(query)
        print(response)
        print()

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
_embeddings_cache = None  # Cache for all embeddings
BUCKET_NAME = Config.S3_BUCKET_NAME

def load_all_embeddings():
    """Load all embeddings from S3 into memory cache (one-time operation)"""
    global _embeddings_cache
    
    if _embeddings_cache is not None:
        return _embeddings_cache
    
    print("[Cache] Loading all embeddings from S3...")
    import time
    start_time = time.time()
    
    _, s3 = get_aws_clients()
    
    _embeddings_cache = []
    
    # List all embedding files
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='embeddings/blocks/')
    
    if 'Contents' not in response:
        print("[Cache] No embeddings found")
        return []
    
    # Get list of keys
    keys = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.json')]
    
    # Fetch embeddings in parallel using ThreadPoolExecutor
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def fetch_embedding(key):
        try:
            doc_response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            doc_data = json.loads(doc_response['Body'].read().decode('utf-8'))
            
            if 'embedding' in doc_data:
                return {
                    'filename': doc_data.get('file', key),
                    'text': doc_data.get('text', ''),
                    'metadata': doc_data.get('metadata', {}),
                    'embedding': doc_data['embedding']
                }
        except Exception as e:
            print(f"[Cache] Error loading {key}: {e}")
            return None
    
    # Use 20 parallel threads for faster loading
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_embedding, key): key for key in keys}
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                _embeddings_cache.append(result)
    
    elapsed = time.time() - start_time
    print(f"[Cache] ✓ Loaded {len(_embeddings_cache)} embeddings in {elapsed:.2f}s")
    return _embeddings_cache

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
    """Generate embedding using Amazon Titan (via LiteLLM or direct Bedrock)"""
    
    # Check if using LiteLLM proxy
    if Config.LITELLM_PROXY_URL and Config.LITELLM_API_KEY:
        # Use LiteLLM proxy for embeddings
        import requests
        
        response = requests.post(
            f"{Config.LITELLM_PROXY_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {Config.LITELLM_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "litellm_proxy/bedrock-titan-embed-text-v2",
                "input": text
            }
        )
        response.raise_for_status()
        result = response.json()
        return result['data'][0]['embedding']
    else:
        # Use direct Bedrock
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
        query: The search query (e.g., "TIMER", "ANALOG_ALARM", "array blocks")
        max_results: Maximum number of results to return (default from config)
    
    Returns:
        Relevant documentation from the knowledge base
    """
    if max_results is None:
        max_results = Config.RAG_MAX_RESULTS
    print(f"[Tool] Searching knowledge base for: {query}")
    
    try:
        # Load embeddings cache (one-time operation)
        embeddings = load_all_embeddings()
        
        if not embeddings:
            return "No documents found in knowledge base."
        
        # Generate query embedding
        query_embedding = generate_embedding(query)
        
        # Score each document from cache
        scored_docs = []
        
        for doc in embeddings:
            try:
                # Calculate similarity
                similarity = cosine_similarity(query_embedding, doc['embedding'])
                
                if similarity > Config.RAG_SIMILARITY_THRESHOLD:
                    scored_docs.append({
                        'filename': doc['filename'],
                        'text': doc['text'],
                        'metadata': doc['metadata'],
                        'similarity': similarity
                    })
            except Exception as e:
                print(f"[Tool] Error processing document: {e}")
                continue
        
        # Sort by similarity
        scored_docs.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Take top results
        top_docs = scored_docs[:max_results]
        
        if not top_docs:
            return f"No relevant information found for: {query}"
        
        # Format results
        result = f"Found {len(top_docs)} relevant documents:\n\n"
        for i, doc in enumerate(top_docs, 1):
            result += f"--- Document {i} (similarity: {doc['similarity']:.2f}) ---\n"
            result += doc['text']
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
        block_name: Name of the block or I/O tag (e.g., "TIMER", "ANALOG_ALARM", "ADD")
    
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
        block_name: Name of the block (e.g., "TIMER", "ANALOG_ALARM")
    
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
    'system_prompt': """You are an expert assistant for the Mark Vle control system.

You have access to a knowledge base containing 206 Mark Vle block definitions with their inputs, outputs, states, and descriptions.

Your tools and when to use them:

1. search_knowledge_base - Use for questions about block specifications, inputs, outputs, descriptions
   - "What are the inputs of TIMER?" → search_knowledge_base("TIMER inputs outputs")
   - "Explain ANALOG_ALARM" → search_knowledge_base("ANALOG_ALARM")
   - "What blocks handle arrays?" → search_knowledge_base("array blocks")

2. generate_diagram - ONLY use when explicitly asked to generate/create/draw a diagram
   - "Generate diagram for TIMER" → generate_diagram("TIMER")
   - "Draw FBD for ANALOG_ALARM" → generate_diagram("ANALOG_ALARM")
   - "Show me a diagram of ADD" → generate_diagram("ADD")
   - DO NOT use for simple questions about inputs/outputs

3. export_xml - Use when user wants XML configuration
   - "Export XML for TIMER" → export_xml("TIMER")

IMPORTANT: 
- For questions about inputs, outputs, or block details, use search_knowledge_base ONLY
- Only use generate_diagram when the user explicitly requests a visual diagram
- Answer based on the knowledge base search results
- If no information is found, say so clearly""",
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
        "What are the inputs of the TIMER block?",
        "Explain the ANALOG_ALARM block",
        "Generate a diagram for TIMER",
        "What blocks handle arrays?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        print("-"*60)
        response = agent(query)
        print(response)
        print()

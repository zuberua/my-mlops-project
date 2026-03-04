#!/usr/bin/env python3
"""
Process Mark VIe Block Library JSON and add to RAG system
Converts JSON blocks into searchable text format with embeddings
"""

import json
import boto3
import os
from pathlib import Path

# Configuration - can be overridden by environment variables
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'markvie-vectors-138720056246')
S3_PREFIX = "embeddings/"
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
JSON_FILE = "../knowledge-base/markvie_block_library.json"

def block_to_text(block_name, block_data):
    """Convert a block JSON object to searchable text"""
    
    text_parts = [
        f"# {block_name} - {block_data.get('full_name', 'N/A')}",
        f"\n**Category:** {block_data.get('category', 'N/A')}",
        f"\n**Description:** {block_data.get('description', 'N/A')}",
    ]
    
    # Add inputs
    inputs = block_data.get('inputs', [])
    if inputs:
        text_parts.append("\n\n## Inputs")
        for inp in inputs:
            text_parts.append(f"\n- **{inp.get('name', 'N/A')}** ({inp.get('data_type', 'N/A')}): {inp.get('description', 'N/A')}")
    else:
        text_parts.append("\n\n## Inputs\nNone")
    
    # Add outputs
    outputs = block_data.get('outputs', [])
    if outputs:
        text_parts.append("\n\n## Outputs")
        for out in outputs:
            text_parts.append(f"\n- **{out.get('name', 'N/A')}** ({out.get('data_type', 'N/A')}): {out.get('description', 'N/A')}")
    else:
        text_parts.append("\n\n## Outputs\nNone")
    
    # Add states
    states = block_data.get('states', [])
    if states:
        text_parts.append("\n\n## States")
        for state in states:
            text_parts.append(f"\n- **{state.get('name', 'N/A')}** ({state.get('data_type', 'N/A')}): {state.get('description', 'N/A')}")
    
    # Add notes
    notes = block_data.get('notes', [])
    if notes:
        text_parts.append("\n\n## Notes")
        for note in notes:
            text_parts.append(f"\n- {note}")
    
    # Add metadata
    text_parts.append(f"\n\n## Metadata")
    text_parts.append(f"\n- **Variant Block:** {block_data.get('is_variant_block', False)}")
    text_parts.append(f"\n- **Expandable:** {block_data.get('is_expandable', False)}")
    if block_data.get('max_inputs'):
        text_parts.append(f"\n- **Max Inputs:** {block_data.get('max_inputs')}")
    if block_data.get('supported_data_types'):
        text_parts.append(f"\n- **Supported Data Types:** {', '.join(block_data.get('supported_data_types', []))}")
    
    return ''.join(text_parts)

def generate_embedding(text, bedrock_client=None):
    """Generate embedding using Titan Embed v2 (via LiteLLM or direct Bedrock)"""
    
    # Check if using LiteLLM proxy
    litellm_url = os.getenv('LITELLM_PROXY_URL')
    litellm_key = os.getenv('LITELLM_API_KEY')
    
    if litellm_url and litellm_key:
        # Use LiteLLM proxy for embeddings
        import requests
        
        response = requests.post(
            f"{litellm_url}/embeddings",
            headers={
                "Authorization": f"Bearer {litellm_key}",
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
        response = bedrock_client.invoke_model(
            modelId=EMBEDDING_MODEL,
            body=json.dumps({
                "inputText": text,
                "dimensions": 1024,
                "normalize": True
            })
        )
        
        result = json.loads(response['body'].read())
        return result['embedding']

def process_block_library():
    """Main function to process block library and upload to S3"""
    
    print("="*60)
    print("Processing Mark VIe Block Library for RAG")
    print("="*60)
    
    # Load JSON file
    json_path = Path(__file__).parent / JSON_FILE
    print(f"\nLoading: {json_path}")
    
    if not json_path.exists():
        print(f"Error: File not found: {json_path}")
        return
    
    # Check if file is empty
    if json_path.stat().st_size == 0:
        print(f"\n❌ Error: The JSON file is empty!")
        print(f"\nPlease add your block library JSON content to:")
        print(f"  {json_path}")
        print(f"\nExpected format:")
        print("""  {
    "BLOCK_NAME": {
      "block_name": "BLOCK_NAME",
      "full_name": "Full Block Name",
      "category": "Category",
      "description": "Block description",
      "inputs": [...],
      "outputs": [...],
      ...
    },
    ...
  }""")
        return
    
    try:
        with open(json_path, 'r') as f:
            blocks = json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON format!")
        print(f"  {str(e)}")
        print(f"\nPlease check the JSON syntax in:")
        print(f"  {json_path}")
        return
    
    print(f"✓ Loaded {len(blocks)} blocks")
    
    # Initialize AWS clients
    litellm_url = os.getenv('LITELLM_PROXY_URL')
    litellm_key = os.getenv('LITELLM_API_KEY')
    
    if litellm_url and litellm_key:
        print(f"\nUsing LiteLLM Proxy: {litellm_url}")
        print("✓ LiteLLM configured for embeddings")
        bedrock = None  # Not needed when using LiteLLM
    else:
        print(f"\nInitializing AWS clients (region: {AWS_REGION})...")
        bedrock = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        print("✓ AWS Bedrock client initialized")
    
    s3 = boto3.client('s3', region_name=AWS_REGION)
    print("✓ S3 client initialized")
    
    # Process each block
    print(f"\nProcessing blocks and generating embeddings...")
    processed = 0
    errors = []
    
    for block_name, block_data in blocks.items():
        try:
            # Convert to text
            text = block_to_text(block_name, block_data)
            
            # Generate embedding
            embedding = generate_embedding(text, bedrock)
            
            # Create embedding object
            embedding_obj = {
                "file": f"blocks/{block_name}.json",
                "text": text,
                "embedding": embedding,
                "metadata": {
                    "block_name": block_name,
                    "full_name": block_data.get('full_name', ''),
                    "category": block_data.get('category', ''),
                    "source": "markvie_block_library.json",
                    "type": "block_definition"
                }
            }
            
            # Upload to S3
            s3_key = f"{S3_PREFIX}blocks/{block_name}.json"
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=json.dumps(embedding_obj),
                ContentType='application/json'
            )
            
            processed += 1
            if processed % 10 == 0:
                print(f"  Processed {processed}/{len(blocks)} blocks...")
        
        except Exception as e:
            errors.append(f"{block_name}: {str(e)}")
            print(f"  Error processing {block_name}: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"\n✓ Successfully processed: {processed}/{len(blocks)} blocks")
    print(f"✓ Uploaded to: s3://{S3_BUCKET}/{S3_PREFIX}blocks/")
    
    if errors:
        print(f"\n⚠ Errors encountered: {len(errors)}")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    print("\nThe block library is now searchable via the agent's RAG system!")
    print("\nExample queries:")
    print("  - 'What are the inputs and outputs of the TIMER block?'")
    print("  - 'Show me all blocks in the Controls category'")
    print("  - 'What does the TRAN_DLY block do?'")
    print()

if __name__ == "__main__":
    process_block_library()

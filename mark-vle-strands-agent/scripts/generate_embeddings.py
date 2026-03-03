#!/usr/bin/env python3
"""
Generate embeddings for knowledge base documents and upload to S3
"""

import json
import boto3
import os
import glob
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import Config

# AWS clients
s3 = boto3.client('s3', region_name=Config.AWS_REGION)
bedrock = boto3.client('bedrock-runtime', region_name=Config.AWS_REGION)

BUCKET_NAME = Config.S3_BUCKET_NAME
EMBEDDING_MODEL = Config.EMBEDDING_MODEL
DOCS_DIR = 'knowledge-base'

def generate_embedding(text: str) -> list:
    """Generate embedding using Bedrock Titan"""
    request_body = {"inputText": text}
    
    response = bedrock.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        if chunk.strip():
            chunks.append({
                'text': chunk,
                'start': start,
                'end': end
            })
        
        start += (chunk_size - overlap)
    
    return chunks

def process_document(filepath: str) -> dict:
    """Process a single document and generate embeddings"""
    print(f"Processing: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract title
    title = os.path.basename(filepath)
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line[2:].strip()
            break
    
    # Chunk the document
    chunks = chunk_text(content)
    
    # Generate embeddings for each chunk
    chunk_embeddings = []
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}/{len(chunks)}")
        embedding = generate_embedding(chunk['text'])
        chunk_embeddings.append({
            'chunk_id': i,
            'text': chunk['text'],
            'start': chunk['start'],
            'end': chunk['end'],
            'embedding': embedding
        })
    
    return {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'title': title,
        'full_content': content,
        'chunks': chunk_embeddings,
        'embedding_model': EMBEDDING_MODEL,
        'embedding_dimension': len(chunk_embeddings[0]['embedding']) if chunk_embeddings else 0
    }

def upload_to_s3(doc_data: dict, bucket: str):
    """Upload document with embeddings to S3"""
    filename = doc_data['filename']
    key = f"embeddings/{filename}.json"
    
    # Upload full document data with embeddings
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(doc_data),
        ContentType='application/json'
    )
    
    print(f"  Uploaded to s3://{bucket}/{key}")

def main():
    """Main function"""
    print("="*60)
    print("Generating Embeddings for Mark Vle Knowledge Base")
    print("="*60)
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Region: {Config.AWS_REGION}")
    print(f"Embedding Model: {EMBEDDING_MODEL}")
    print("="*60)
    
    # Check if bucket exists
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"✓ Using bucket: {BUCKET_NAME}")
    except Exception as e:
        print(f"Warning: Could not verify bucket access: {e}")
        print(f"Continuing anyway with bucket: {BUCKET_NAME}")
        # Don't return - continue anyway
    
    # Find all markdown files
    md_files = glob.glob(os.path.join(DOCS_DIR, '**/*.md'), recursive=True)
    print(f"Found {len(md_files)} markdown files")
    
    if len(md_files) == 0:
        print(f"No markdown files found in {DOCS_DIR}")
        return
    
    # Process each document
    for i, filepath in enumerate(md_files, 1):
        print(f"\n[{i}/{len(md_files)}] {filepath}")
        
        try:
            doc_data = process_document(filepath)
            upload_to_s3(doc_data, BUCKET_NAME)
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Create index file
    print("\nCreating index file...")
    index_data = {
        'total_documents': len(md_files),
        'embedding_model': EMBEDDING_MODEL,
        'bucket': BUCKET_NAME,
        'documents': []
    }
    
    # List all embeddings
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='embeddings/')
    if 'Contents' in response:
        for obj in response['Contents']:
            if obj['Key'] != 'embeddings/index.json':
                index_data['documents'].append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
    
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key='embeddings/index.json',
        Body=json.dumps(index_data, indent=2),
        ContentType='application/json'
    )
    
    print("="*60)
    print("Complete!")
    print(f"Total documents processed: {len(md_files)}")
    print(f"S3 Bucket: {BUCKET_NAME}")
    print(f"Embeddings: s3://{BUCKET_NAME}/embeddings/")
    print("="*60)

if __name__ == '__main__':
    main()

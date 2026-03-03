#!/usr/bin/env python3
"""
Mark Vle Strands Agent - Flask Web UI
Web interface with Mermaid diagram support
"""

import os

# CRITICAL: Set AWS profile BEFORE any imports that use boto3
if not os.environ.get('AWS_PROFILE'):
    os.environ['AWS_PROFILE'] = 'zuberua-Admin'

# Now import everything else
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from agent import agent
from config.config import Config
from plc_diagram_generator import generate_plc_block_from_rag
import traceback

app = Flask(__name__)
CORS(app)

# Load configuration
Config.print_config()

@app.route('/')
def index():
    """Render main UI"""
    return render_template('strands_index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat with Strands agent"""
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Call agent
        result = agent(message)
        
        # Extract text from AgentResult
        if hasattr(result, 'text'):
            response = result.text
        elif hasattr(result, 'content'):
            response = result.content
        elif isinstance(result, str):
            response = result
        else:
            response = str(result)
        
        return jsonify({
            'response': response
        })
    
    except Exception as e:
        error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
        return jsonify({'error': error_msg}), 500

@app.route('/api/generate-plc-diagram', methods=['POST'])
def generate_plc_diagram():
    """Generate PLC block diagram from block name"""
    try:
        data = request.json
        block_name = data.get('blockName', '')
        
        if not block_name:
            return jsonify({'error': 'Block name is required'}), 400
        
        # Use agent's generate_diagram tool
        from agent import search_knowledge_base
        
        # Get block info from knowledge base
        info = search_knowledge_base(block_name, max_results=1)
        
        # Generate Mermaid diagram
        mermaid_code = generate_plc_block_from_rag(info)
        
        return jsonify({
            'mermaid': mermaid_code,
            'blockInfo': info
        })
    
    except Exception as e:
        error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
        return jsonify({'error': error_msg}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify({
        'agentIdentity': Config.AGENT_IDENTITY_NAME or 'Not configured',
        'litellmProxy': Config.LITELLM_PROXY_URL or 'Not configured',
        'litellmModel': Config.LITELLM_MODEL,
        'awsRegion': Config.AWS_REGION,
        's3Bucket': Config.S3_BUCKET_NAME,
        'embeddingModel': Config.EMBEDDING_MODEL
    })

if __name__ == '__main__':
    print("="*60)
    print("Starting Mark Vle Strands Agent Flask UI")
    print("="*60)
    print("Open http://localhost:5001 in your browser")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=True)

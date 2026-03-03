#!/usr/bin/env python3
"""
Mark Vle Strands Agent Client
Simple Python client for other agents to use
"""

import requests
from typing import Optional, Dict, Tuple

class MarkVleClient:
    """Client for Mark Vle Strands Agent API"""
    
    def __init__(self, base_url: str = 'http://localhost:5001', timeout: int = 30):
        """
        Initialize client
        
        Args:
            base_url: Agent API base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify agent is running"""
        try:
            response = requests.get(
                f'{self.base_url}/api/config',
                timeout=5
            )
            response.raise_for_status()
            print(f"✓ Connected to Mark Vle Agent at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Cannot connect to Mark Vle Agent at {self.base_url}. "
                f"Make sure the agent is running (./start.sh). Error: {e}"
            )
    
    def chat(self, message: str) -> str:
        """
        Send a message to the agent
        
        Args:
            message: Natural language query
            
        Returns:
            Agent's response text
            
        Example:
            >>> client = MarkVleClient()
            >>> response = client.chat("What is TNH-SPEED-1?")
            >>> print(response)
        """
        response = requests.post(
            f'{self.base_url}/api/chat',
            json={'message': message},
            timeout=self.timeout
        )
        response.raise_for_status()
        
        data = response.json()
        if 'error' in data:
            raise RuntimeError(f"Agent error: {data['error']}")
        
        return data['response']
    
    def generate_diagram(self, block_name: str) -> Tuple[str, str]:
        """
        Generate PLC block diagram
        
        Args:
            block_name: Name of PLC block (e.g., "COMPARE_50", "MOVE_150")
            
        Returns:
            Tuple of (mermaid_code, block_info)
            
        Example:
            >>> client = MarkVleClient()
            >>> mermaid, info = client.generate_diagram("COMPARE_50")
            >>> print(mermaid)
            >>> print(info)
        """
        response = requests.post(
            f'{self.base_url}/api/generate-plc-diagram',
            json={'blockName': block_name},
            timeout=self.timeout
        )
        response.raise_for_status()
        
        data = response.json()
        if 'error' in data:
            raise RuntimeError(f"Diagram generation error: {data['error']}")
        
        return data['mermaid'], data['blockInfo']
    
    def get_config(self) -> Dict:
        """
        Get agent configuration
        
        Returns:
            Configuration dictionary
            
        Example:
            >>> client = MarkVleClient()
            >>> config = client.get_config()
            >>> print(config['s3Bucket'])
        """
        response = requests.get(
            f'{self.base_url}/api/config',
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def search_knowledge_base(self, query: str) -> str:
        """
        Search the Mark Vle knowledge base
        
        Args:
            query: Search query (I/O point, block name, etc.)
            
        Returns:
            Search results from knowledge base
            
        Example:
            >>> client = MarkVleClient()
            >>> results = client.search_knowledge_base("TNH-SPEED-1")
            >>> print(results)
        """
        return self.chat(query)
    
    def save_diagram(self, block_name: str, output_file: str) -> str:
        """
        Generate diagram and save to file
        
        Args:
            block_name: Name of PLC block
            output_file: Output file path (e.g., "diagram.mmd")
            
        Returns:
            Block information text
            
        Example:
            >>> client = MarkVleClient()
            >>> info = client.save_diagram("COMPARE_50", "compare_50.mmd")
            >>> print(f"Diagram saved. Info: {info}")
        """
        mermaid, info = self.generate_diagram(block_name)
        
        with open(output_file, 'w') as f:
            f.write(mermaid)
        
        print(f"✓ Diagram saved to {output_file}")
        return info


# Example usage
if __name__ == '__main__':
    # Create client
    client = MarkVleClient()
    
    # Example 1: Ask a question
    print("\n" + "="*60)
    print("Example 1: Ask about TNH-SPEED-1")
    print("="*60)
    response = client.chat("What is TNH-SPEED-1?")
    print(response[:200] + "...")
    
    # Example 2: Generate diagram
    print("\n" + "="*60)
    print("Example 2: Generate COMPARE_50 diagram")
    print("="*60)
    mermaid, info = client.generate_diagram("COMPARE_50")
    print(f"Mermaid code length: {len(mermaid)} characters")
    print(f"Block info length: {len(info)} characters")
    
    # Example 3: Save diagram to file
    print("\n" + "="*60)
    print("Example 3: Save MOVE_150 diagram to file")
    print("="*60)
    info = client.save_diagram("MOVE_150", "/tmp/move_150.mmd")
    print(f"Info: {info[:100]}...")
    
    # Example 4: Get configuration
    print("\n" + "="*60)
    print("Example 4: Get agent configuration")
    print("="*60)
    config = client.get_config()
    print(f"S3 Bucket: {config['s3Bucket']}")
    print(f"AWS Region: {config['awsRegion']}")
    print(f"Embedding Model: {config['embeddingModel']}")

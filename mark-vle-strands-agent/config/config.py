"""
Configuration for Mark Vle Strands Agent
Supports LiteLLM proxy for model inference and AgentCore identity
"""

import os
from typing import Optional

class Config:
    """Configuration class for agent settings"""
    
    # LiteLLM Proxy Configuration
    LITELLM_API_KEY: Optional[str] = os.getenv('LITELLM_API_KEY')
    LITELLM_PROXY_URL: Optional[str] = os.getenv('LITELLM_PROXY_URL')
    LITELLM_MODEL: str = os.getenv('LITELLM_MODEL', 'litellm_proxy/bedrock-claude-sonnet-4.5')
    
    # AgentCore Identity Configuration
    AGENT_IDENTITY_NAME: Optional[str] = os.getenv('AGENT_IDENTITY_NAME')
    AGENT_IDENTITY_SCOPES: str = os.getenv('AGENT_IDENTITY_SCOPES', 'read,write')
    
    # AWS Configuration (for S3 and embeddings)
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-west-2')
    S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME', 'mark-vie-kb-138720056246')
    
    # Embedding Model Configuration
    EMBEDDING_MODEL: str = os.getenv('EMBEDDING_MODEL', 'amazon.titan-embed-text-v2:0')
    
    # Agent Configuration
    AGENT_TEMPERATURE: float = float(os.getenv('AGENT_TEMPERATURE', '0.7'))
    AGENT_MAX_TOKENS: int = int(os.getenv('AGENT_MAX_TOKENS', '2000'))
    
    # RAG Configuration
    RAG_MAX_RESULTS: int = int(os.getenv('RAG_MAX_RESULTS', '3'))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv('RAG_SIMILARITY_THRESHOLD', '0.5'))
    
    @classmethod
    def requires_auth(cls) -> bool:
        """Check if agent requires authentication"""
        return cls.AGENT_IDENTITY_NAME is not None
    
    @classmethod
    def load_agent_access_token(cls) -> Optional[str]:
        """
        Load agent access token from AgentCore identity
        Returns None if no identity is configured
        """
        if not cls.AGENT_IDENTITY_NAME:
            return None
        
        try:
            from strands.agentcore.identity import require_access_token
            
            # Parse scopes from comma-separated string
            scopes = cls.AGENT_IDENTITY_SCOPES.split(',') if cls.AGENT_IDENTITY_SCOPES else []
            
            # Require access token with M2M auth flow
            token = require_access_token(
                provider_name=cls.AGENT_IDENTITY_NAME,
                scopes=scopes,
                auth_flow="M2M"
            )
            
            print(f"Loaded access token for identity: {cls.AGENT_IDENTITY_NAME}")
            print(f"Scopes: {scopes}")
            print(f"Auth flow: M2M")
            return token
        except ImportError:
            print("Warning: strands.agentcore.identity not available")
            return None
        except Exception as e:
            print(f"Error loading access token: {e}")
            return None
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        # Check identity configuration
        if cls.AGENT_IDENTITY_NAME:
            print(f"AgentCore Identity: {cls.AGENT_IDENTITY_NAME}")
            token = cls.load_agent_access_token()
            if not token:
                print("Warning: Could not load access token")
        
        # Check LiteLLM configuration
        if cls.LITELLM_PROXY_URL:
            # Using LiteLLM proxy
            if not cls.LITELLM_API_KEY:
                print("Warning: LITELLM_API_KEY not set")
                return False
            print(f"Using LiteLLM Proxy: {cls.LITELLM_PROXY_URL}")
            print(f"Model: {cls.LITELLM_MODEL}")
            return True
        else:
            # Using direct Bedrock
            print("Using direct AWS Bedrock")
            return True
    
    @classmethod
    def get_model_config(cls) -> dict:
        """Get model configuration for Strands agent"""
        config = {}
        
        if cls.LITELLM_PROXY_URL and cls.LITELLM_API_KEY:
            # LiteLLM proxy configuration
            # For Strands SDK, we need to use the model name that includes the proxy prefix
            # and the SDK will route it through LiteLLM
            config['model'] = cls.LITELLM_MODEL
            
            # Set environment variables that LiteLLM SDK uses
            import os
            os.environ['LITELLM_API_BASE'] = cls.LITELLM_PROXY_URL
            os.environ['LITELLM_API_KEY'] = cls.LITELLM_API_KEY
            
            print(f"✓ LiteLLM configured: {cls.LITELLM_PROXY_URL}")
            print(f"✓ Model: {cls.LITELLM_MODEL}")
        else:
            # Direct Bedrock configuration
            config['model'] = 'anthropic.claude-3-5-haiku-20241022-v1:0'
            print(f"✓ Using direct Bedrock model")
        
        # Add access token if using AgentCore identity
        if cls.AGENT_IDENTITY_NAME:
            access_token = cls.load_agent_access_token()
            if access_token:
                config['access_token'] = access_token
        
        return config
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        print("="*60)
        print("Mark Vle Strands Agent Configuration")
        print("="*60)
        print(f"AgentCore Identity: {cls.AGENT_IDENTITY_NAME or 'Not configured'}")
        print(f"AgentCore Scopes: {cls.AGENT_IDENTITY_SCOPES}")
        print(f"LiteLLM Proxy URL: {cls.LITELLM_PROXY_URL or 'Not configured'}")
        print(f"LiteLLM Model: {cls.LITELLM_MODEL}")
        print(f"LiteLLM API Key: {'Set' if cls.LITELLM_API_KEY else 'Not set'}")
        print(f"AWS Region: {cls.AWS_REGION}")
        print(f"S3 Bucket: {cls.S3_BUCKET_NAME}")
        print(f"Embedding Model: {cls.EMBEDDING_MODEL}")
        print(f"Temperature: {cls.AGENT_TEMPERATURE}")
        print(f"Max Tokens: {cls.AGENT_MAX_TOKENS}")
        print(f"RAG Max Results: {cls.RAG_MAX_RESULTS}")
        print(f"RAG Similarity Threshold: {cls.RAG_SIMILARITY_THRESHOLD}")
        print(f"Requires Auth: {cls.requires_auth()}")
        print("="*60)

# Validate configuration on import
Config.validate()

#!/usr/bin/env python3
"""
Mark Vle Strands Agent - AgentCore Deployment
Wraps the Strands agent for Amazon Bedrock AgentCore
"""

from strands.agentcore import BedrockAgentCoreApp
from agent import agent
from config.config import Config

# Wrap the Strands agent for AgentCore deployment
app = BedrockAgentCoreApp(agent)

# AgentCore will handle:
# - Identity (OAuth, Cognito, IAM)
# - Memory (conversation history)
# - Observability (CloudWatch, OTEL)
# - Tool execution (async, secure)
# - Long-running tasks (up to 8 hours)

if __name__ == "__main__":
    print("="*60)
    print("Mark Vle Strands Agent - AgentCore Deployment")
    print("="*60)
    Config.print_config()
    print("\nAgent wrapped for AgentCore deployment")
    print("Use 'bedrock-agentcore deploy' to deploy")
    print("="*60)

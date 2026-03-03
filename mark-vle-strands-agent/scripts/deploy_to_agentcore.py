#!/usr/bin/env python3
"""
Deploy Mark Vle Agent to AWS Bedrock AgentCore Runtime
"""

import logging
import sys
import os
from argparse import ArgumentParser
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def deploy_agent(agent_name, region, container_uri, runtime_id, role_arn):
    """Deploy agent to AgentCore Runtime"""
    
    logger.info(f"Deploying agent: {agent_name}")
    logger.info(f"Runtime ID: {runtime_id}")
    logger.info(f"Container URI: {container_uri}")
    logger.info(f"Execution Role: {role_arn}")
    
    # Initialize AgentCore client
    client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    try:
        # Check if agent already exists in runtime
        existing_agents = client.list_agent_runtimes()
        agent_exists = False
        existing_agent_id = None
        
        for agent in existing_agents.get('agentRuntimes', []):
            if agent['agentRuntimeName'] == agent_name:
                agent_exists = True
                existing_agent_id = agent['agentRuntimeId']
                logger.info(f"Found existing agent: {existing_agent_id}")
                break
        
        if agent_exists:
            # Update existing agent
            logger.info("Updating existing agent...")
            response = client.update_agent_runtime(
                agentRuntimeId=existing_agent_id,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': container_uri
                    }
                },
                networkConfiguration={'networkMode': 'PUBLIC'},
                roleArn=role_arn
            )
        else:
            # Create new agent
            logger.info("Creating new agent...")
            response = client.create_agent_runtime(
                agentRuntimeName=agent_name,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': container_uri
                    }
                },
                networkConfiguration={'networkMode': 'PUBLIC'},
                roleArn=role_arn
            )
        
        agent_arn = response['agentRuntimeArn']
        agent_id = response['agentRuntimeId']
        
        logger.info("✓ Agent deployed successfully!")
        logger.info(f"Agent ARN: {agent_arn}")
        logger.info(f"Agent ID: {agent_id}")
        
        # Save deployment info
        with open("deployment_info.txt", "w") as f:
            f.write(f"agent_arn={agent_arn}\n")
            f.write(f"agent_id={agent_id}\n")
            f.write(f"container_uri={container_uri}\n")
        
        return {
            'agent_arn': agent_arn,
            'agent_id': agent_id,
            'container_uri': container_uri
        }
        
    except ClientError as e:
        logger.error(f"Deployment failed: {e}")
        sys.exit(1)

def main():
    parser = ArgumentParser(description="Deploy agent to AgentCore Runtime")
    parser.add_argument("--agent-name", required=True, help="Agent name")
    parser.add_argument("--region", required=True, help="AWS region")
    parser.add_argument("--container-uri", required=True, help="ECR container URI")
    parser.add_argument("--runtime-id", required=True, help="AgentCore Runtime ID")
    parser.add_argument("--role-arn", required=True, help="Execution role ARN")
    
    args = parser.parse_args()
    
    deploy_agent(
        args.agent_name,
        args.region,
        args.container_uri,
        args.runtime_id,
        args.role_arn
    )

if __name__ == "__main__":
    main()

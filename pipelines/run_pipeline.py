#!/usr/bin/env python3
"""Start SageMaker Pipeline execution."""

import argparse
import boto3


def run_pipeline(pipeline_name, region):
    """Start pipeline execution."""
    
    sm_client = boto3.client("sagemaker", region_name=region)
    
    response = sm_client.start_pipeline_execution(
        PipelineName=pipeline_name,
        PipelineExecutionDisplayName=f"github-actions-{boto3.client('sts').get_caller_identity()['Account']}",
    )
    
    execution_arn = response["PipelineExecutionArn"]
    
    # Save execution ARN
    with open("execution_arn.txt", "w") as f:
        f.write(execution_arn)
    
    print(f"Pipeline execution started: {execution_arn}")
    
    return execution_arn


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-name", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    
    args = parser.parse_args()
    
    run_pipeline(args.pipeline_name, args.region)

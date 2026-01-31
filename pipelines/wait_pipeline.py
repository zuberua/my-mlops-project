#!/usr/bin/env python3
"""Wait for SageMaker Pipeline execution to complete."""

import argparse
import time
import boto3


def wait_pipeline(execution_arn, region, timeout=3600):
    """Wait for pipeline execution to complete."""
    
    sm_client = boto3.client("sagemaker", region_name=region)
    
    start_time = time.time()
    
    while True:
        response = sm_client.describe_pipeline_execution(
            PipelineExecutionArn=execution_arn
        )
        
        status = response["PipelineExecutionStatus"]
        
        print(f"Pipeline status: {status}")
        
        if status in ["Succeeded", "Failed", "Stopped"]:
            print(f"Pipeline execution completed with status: {status}")
            
            if status != "Succeeded":
                raise Exception(f"Pipeline execution failed with status: {status}")
            
            return status
        
        if time.time() - start_time > timeout:
            raise Exception(f"Pipeline execution timed out after {timeout} seconds")
        
        time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-arn", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    parser.add_argument("--timeout", type=int, default=3600)
    
    args = parser.parse_args()
    
    wait_pipeline(args.execution_arn, args.region, args.timeout)

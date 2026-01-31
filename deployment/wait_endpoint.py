#!/usr/bin/env python3
"""Wait for SageMaker endpoint to be in service."""

import argparse
import time
import boto3


def wait_endpoint(endpoint_name, region, timeout=900):
    """Wait for endpoint to be in service."""
    
    sm_client = boto3.client("sagemaker", region_name=region)
    
    start_time = time.time()
    
    while True:
        response = sm_client.describe_endpoint(EndpointName=endpoint_name)
        
        status = response["EndpointStatus"]
        
        print(f"Endpoint status: {status}")
        
        if status == "InService":
            print(f"Endpoint is in service: {endpoint_name}")
            return status
        
        if status == "Failed":
            failure_reason = response.get("FailureReason", "Unknown")
            raise Exception(f"Endpoint deployment failed: {failure_reason}")
        
        if time.time() - start_time > timeout:
            raise Exception(f"Endpoint deployment timed out after {timeout} seconds")
        
        time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    parser.add_argument("--timeout", type=int, default=900)
    
    args = parser.parse_args()
    
    wait_endpoint(args.endpoint_name, args.region, args.timeout)

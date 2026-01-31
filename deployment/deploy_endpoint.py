#!/usr/bin/env python3
"""Deploy SageMaker endpoint."""

import argparse
import boto3
import time


def deploy_endpoint(
    model_package_arn,
    endpoint_name,
    instance_type,
    instance_count,
    region,
    enable_autoscaling=False,
    min_capacity=1,
    max_capacity=10,
):
    """Deploy SageMaker endpoint."""
    
    sm_client = boto3.client("sagemaker", region_name=region)
    
    # Create model from model package
    model_name = f"{endpoint_name}-model-{int(time.time())}"
    
    print(f"Creating model: {model_name}")
    sm_client.create_model(
        ModelName=model_name,
        Containers=[
            {
                "ModelPackageName": model_package_arn
            }
        ],
        ExecutionRoleArn=get_execution_role(region),
    )
    
    # Create endpoint configuration
    endpoint_config_name = f"{endpoint_name}-config-{int(time.time())}"
    
    print(f"Creating endpoint configuration: {endpoint_config_name}")
    sm_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": model_name,
                "InstanceType": instance_type,
                "InitialInstanceCount": instance_count,
                "InitialVariantWeight": 1.0,
            }
        ],
        DataCaptureConfig={
            "EnableCapture": True,
            "InitialSamplingPercentage": 100,
            "DestinationS3Uri": f"s3://sagemaker-{region}-{boto3.client('sts').get_caller_identity()['Account']}/data-capture/{endpoint_name}",
            "CaptureOptions": [
                {"CaptureMode": "Input"},
                {"CaptureMode": "Output"},
            ],
        },
    )
    
    # Create or update endpoint
    try:
        print(f"Checking if endpoint exists: {endpoint_name}")
        sm_client.describe_endpoint(EndpointName=endpoint_name)
        
        print(f"Updating existing endpoint: {endpoint_name}")
        sm_client.update_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name,
        )
    except sm_client.exceptions.ClientError:
        print(f"Creating new endpoint: {endpoint_name}")
        sm_client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name,
        )
    
    # Enable autoscaling if requested
    if enable_autoscaling:
        print(f"Configuring autoscaling for endpoint: {endpoint_name}")
        autoscaling_client = boto3.client("application-autoscaling", region_name=region)
        
        resource_id = f"endpoint/{endpoint_name}/variant/AllTraffic"
        
        autoscaling_client.register_scalable_target(
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            MinCapacity=min_capacity,
            MaxCapacity=max_capacity,
        )
        
        autoscaling_client.put_scaling_policy(
            PolicyName=f"{endpoint_name}-scaling-policy",
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            PolicyType="TargetTrackingScaling",
            TargetTrackingScalingPolicyConfiguration={
                "TargetValue": 70.0,
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
                },
                "ScaleInCooldown": 300,
                "ScaleOutCooldown": 60,
            },
        )
    
    # Save endpoint name
    with open("endpoint_name.txt", "w") as f:
        f.write(endpoint_name)
    
    print(f"Endpoint deployment initiated: {endpoint_name}")
    
    return endpoint_name


def get_execution_role(region):
    """Get SageMaker execution role."""
    sts_client = boto3.client("sts")
    account_id = sts_client.get_caller_identity()["Account"]
    
    # Try to get role from environment or use default
    import os
    role_arn = os.environ.get("SAGEMAKER_EXECUTION_ROLE_ARN")
    
    if not role_arn:
        role_arn = f"arn:aws:iam::{account_id}:role/SageMakerExecutionRole"
    
    return role_arn


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-package-arn", type=str, required=True)
    parser.add_argument("--endpoint-name", type=str, required=True)
    parser.add_argument("--instance-type", type=str, default="ml.m5.xlarge")
    parser.add_argument("--instance-count", type=int, default=1)
    parser.add_argument("--region", type=str, required=True)
    parser.add_argument("--enable-autoscaling", action="store_true")
    parser.add_argument("--min-capacity", type=int, default=1)
    parser.add_argument("--max-capacity", type=int, default=10)
    
    args = parser.parse_args()
    
    deploy_endpoint(
        model_package_arn=args.model_package_arn,
        endpoint_name=args.endpoint_name,
        instance_type=args.instance_type,
        instance_count=args.instance_count,
        region=args.region,
        enable_autoscaling=args.enable_autoscaling,
        min_capacity=args.min_capacity,
        max_capacity=args.max_capacity,
    )

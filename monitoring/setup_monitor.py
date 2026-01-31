#!/usr/bin/env python3
"""Setup SageMaker Model Monitor for endpoint."""

import argparse
import boto3
from datetime import datetime


def setup_monitor(endpoint_name, region):
    """Setup Model Monitor for endpoint."""
    
    sm_client = boto3.client("sagemaker", region_name=region)
    sts_client = boto3.client("sts")
    
    account_id = sts_client.get_caller_identity()["Account"]
    
    # Get endpoint details
    endpoint = sm_client.describe_endpoint(EndpointName=endpoint_name)
    
    print(f"Setting up Model Monitor for endpoint: {endpoint_name}")
    
    # Data capture is already enabled in endpoint config
    # Now create monitoring schedule
    
    monitoring_schedule_name = f"{endpoint_name}-monitor"
    
    # S3 paths
    baseline_uri = f"s3://sagemaker-{region}-{account_id}/monitoring/{endpoint_name}/baseline"
    output_uri = f"s3://sagemaker-{region}-{account_id}/monitoring/{endpoint_name}/results"
    
    try:
        # Check if monitoring schedule exists
        sm_client.describe_monitoring_schedule(
            MonitoringScheduleName=monitoring_schedule_name
        )
        print(f"Monitoring schedule already exists: {monitoring_schedule_name}")
        return
    except sm_client.exceptions.ResourceNotFound:
        pass
    
    # Create monitoring schedule
    print(f"Creating monitoring schedule: {monitoring_schedule_name}")
    
    sm_client.create_monitoring_schedule(
        MonitoringScheduleName=monitoring_schedule_name,
        MonitoringScheduleConfig={
            "ScheduleConfig": {
                "ScheduleExpression": "cron(0 * * * ? *)"  # Hourly
            },
            "MonitoringJobDefinition": {
                "MonitoringInputs": [
                    {
                        "EndpointInput": {
                            "EndpointName": endpoint_name,
                            "LocalPath": "/opt/ml/processing/input/endpoint"
                        }
                    }
                ],
                "MonitoringOutputConfig": {
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "S3Uri": output_uri,
                                "LocalPath": "/opt/ml/processing/output"
                            }
                        }
                    ]
                },
                "MonitoringResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": "ml.m5.xlarge",
                        "VolumeSizeInGB": 20
                    }
                },
                "MonitoringAppSpecification": {
                    "ImageUri": f"156813124566.dkr.ecr.{region}.amazonaws.com/sagemaker-model-monitor-analyzer"
                },
                "RoleArn": f"arn:aws:iam::{account_id}:role/SageMakerExecutionRole",
                "Environment": {
                    "dataset_format": '{"sagemakerCaptureJson": {"captureIndexNames": ["endpointInput", "endpointOutput"]}}',
                    "dataset_source": "/opt/ml/processing/input/endpoint",
                    "output_path": "/opt/ml/processing/output",
                    "publish_cloudwatch_metrics": "Enabled"
                }
            }
        }
    )
    
    print(f"✅ Model Monitor enabled for {endpoint_name}")
    print(f"   Schedule: Hourly")
    print(f"   Output: {output_uri}")
    print(f"   CloudWatch metrics: Enabled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    
    args = parser.parse_args()
    
    setup_monitor(args.endpoint_name, args.region)

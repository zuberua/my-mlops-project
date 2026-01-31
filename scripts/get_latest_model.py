#!/usr/bin/env python3
"""Get latest approved model from Model Registry."""

import argparse
import boto3


def get_latest_model(project_name, region, status="Approved"):
    """Get latest model with specified status."""
    
    sm_client = boto3.client("sagemaker", region_name=region)
    
    model_package_group_name = f"{project_name}-model-group"
    
    # List model packages
    response = sm_client.list_model_packages(
        ModelPackageGroupName=model_package_group_name,
        ModelApprovalStatus=status,
        SortBy="CreationTime",
        SortOrder="Descending",
        MaxResults=1,
    )
    
    if not response["ModelPackageSummaryList"]:
        raise Exception(f"No {status} models found in {model_package_group_name}")
    
    model_package_arn = response["ModelPackageSummaryList"][0]["ModelPackageArn"]
    
    # Save model package ARN
    with open("model_package_arn.txt", "w") as f:
        f.write(model_package_arn)
    
    print(f"Latest {status} model: {model_package_arn}")
    
    return model_package_arn


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-name", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    parser.add_argument("--status", type=str, default="Approved")
    
    args = parser.parse_args()
    
    get_latest_model(args.project_name, args.region, args.status)

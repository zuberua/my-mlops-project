#!/usr/bin/env python3
"""Approve model in Model Registry."""

import argparse
import json
import boto3


def approve_model(results_file, region, min_accuracy=0.8):
    """Approve model if it meets criteria."""
    
    sm_client = boto3.client("sagemaker", region_name=region)
    
    # Load results
    with open(results_file, "r") as f:
        results = json.load(f)
    
    if "model_package_arn" not in results:
        print("No model package found in results")
        return
    
    model_package_arn = results["model_package_arn"]
    accuracy = results.get("accuracy", 0)
    
    print(f"Model Package: {model_package_arn}")
    print(f"Accuracy: {accuracy}")
    
    # Check if accuracy meets threshold
    if isinstance(accuracy, (int, float)) and accuracy >= min_accuracy:
        print(f"Approving model (accuracy {accuracy} >= {min_accuracy})")
        
        sm_client.update_model_package(
            ModelPackageArn=model_package_arn,
            ModelApprovalStatus="Approved",
            ApprovalDescription=f"Automatically approved by GitHub Actions. Accuracy: {accuracy}",
        )
        
        print(f"Model approved: {model_package_arn}")
    else:
        print(f"Model does not meet approval criteria (accuracy {accuracy} < {min_accuracy})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-file", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    parser.add_argument("--min-accuracy", type=float, default=0.8)
    
    args = parser.parse_args()
    
    approve_model(args.results_file, args.region, args.min_accuracy)

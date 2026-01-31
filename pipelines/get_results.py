#!/usr/bin/env python3
"""Get SageMaker Pipeline execution results."""

import argparse
import json
import boto3


def get_results(execution_arn, region):
    """Get pipeline execution results."""
    
    sm_client = boto3.client("sagemaker", region_name=region)
    
    # Get execution details
    response = sm_client.describe_pipeline_execution(
        PipelineExecutionArn=execution_arn
    )
    
    status = response["PipelineExecutionStatus"]
    
    # Get pipeline steps
    steps_response = sm_client.list_pipeline_execution_steps(
        PipelineExecutionArn=execution_arn
    )
    
    results = {
        "status": status,
        "execution_arn": execution_arn,
        "steps": []
    }
    
    # Extract model package ARN if registered
    for step in steps_response["PipelineExecutionSteps"]:
        step_info = {
            "name": step["StepName"],
            "status": step["StepStatus"]
        }
        
        if step["StepName"] == "RegisterModel" and step["StepStatus"] == "Succeeded":
            metadata = step.get("Metadata", {})
            register_model = metadata.get("RegisterModel", {})
            step_info["model_package_arn"] = register_model.get("Arn")
            results["model_package_arn"] = register_model.get("Arn")
        
        if step["StepName"] == "EvaluateModel" and step["StepStatus"] == "Succeeded":
            # Try to get evaluation metrics
            metadata = step.get("Metadata", {})
            processing = metadata.get("ProcessingJob", {})
            if processing:
                step_info["processing_job_name"] = processing.get("Arn", "").split("/")[-1]
        
        results["steps"].append(step_info)
    
    # Try to get evaluation metrics from S3
    if "model_package_arn" in results:
        try:
            # Get model package details
            model_response = sm_client.describe_model_package(
                ModelPackageName=results["model_package_arn"]
            )
            
            metrics = model_response.get("ModelMetrics", {})
            if metrics:
                results["metrics"] = metrics
                
                # Extract accuracy if available
                model_stats = metrics.get("ModelQuality", {}).get("Statistics", {})
                if model_stats:
                    s3_uri = model_stats.get("S3Uri")
                    if s3_uri:
                        # Parse S3 URI and download
                        import re
                        match = re.match(r"s3://([^/]+)/(.+)", s3_uri)
                        if match:
                            bucket, key = match.groups()
                            s3_client = boto3.client("s3", region_name=region)
                            obj = s3_client.get_object(Bucket=bucket, Key=key)
                            eval_data = json.loads(obj["Body"].read())
                            
                            if "classification_metrics" in eval_data:
                                results["accuracy"] = eval_data["classification_metrics"]["accuracy"]["value"]
        except Exception as e:
            print(f"Could not retrieve model metrics: {e}")
            results["accuracy"] = "N/A"
    
    # Save results
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(json.dumps(results, indent=2))
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-arn", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    
    args = parser.parse_args()
    
    get_results(args.execution_arn, args.region)

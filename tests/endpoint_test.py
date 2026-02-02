#!/usr/bin/env python3
"""Test SageMaker endpoint."""

import argparse
import json
import time
import boto3
import numpy as np


def test_endpoint(endpoint_name, test_data_file, region):
    """Test endpoint with sample data."""
    
    runtime_client = boto3.client("sagemaker-runtime", region_name=region)
    
    # Load test data
    with open(test_data_file, "r") as f:
        test_data = json.load(f)
    
    results = {
        "success": True,
        "total_tests": len(test_data["samples"]),
        "passed": 0,
        "failed": 0,
        "latencies": [],
        "predictions": [],
    }
    
    print(f"Testing endpoint: {endpoint_name}")
    print(f"Running {results['total_tests']} test cases...")
    
    for i, sample in enumerate(test_data["samples"]):
        try:
            # Prepare payload
            payload = sample["input"]
            expected = sample.get("expected")
            
            # Invoke endpoint
            start_time = time.time()
            response = runtime_client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType="text/csv",
                Body=payload,
            )
            latency = (time.time() - start_time) * 1000  # ms
            
            # Parse response
            prediction = response["Body"].read().decode("utf-8").strip()
            
            results["latencies"].append(latency)
            results["predictions"].append({
                "input": payload,
                "prediction": prediction,
                "expected": expected,
                "latency_ms": latency,
            })
            
            # Check if prediction matches expected (if provided)
            if expected is not None:
                if str(prediction) == str(expected):
                    results["passed"] += 1
                    print(f"  ✅ Test {i+1}: PASS (latency: {latency:.2f}ms)")
                else:
                    results["failed"] += 1
                    results["success"] = False
                    print(f"  ❌ Test {i+1}: FAIL - Expected {expected}, got {prediction}")
            else:
                results["passed"] += 1
                print(f"  ✅ Test {i+1}: PASS (latency: {latency:.2f}ms, prediction: {prediction})")
        
        except Exception as e:
            results["failed"] += 1
            results["success"] = False
            print(f"  ❌ Test {i+1}: ERROR - {str(e)}")
    
    # Calculate statistics
    if results["latencies"]:
        results["avg_latency_ms"] = np.mean(results["latencies"])
        results["p50_latency_ms"] = np.percentile(results["latencies"], 50)
        results["p95_latency_ms"] = np.percentile(results["latencies"], 95)
        results["p99_latency_ms"] = np.percentile(results["latencies"], 99)
    
    results["accuracy"] = results["passed"] / results["total_tests"] if results["total_tests"] > 0 else 0
    
    # Save results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*50)
    print("Test Summary:")
    print(f"  Total: {results['total_tests']}")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Accuracy: {results['accuracy']:.2%}")
    if results["latencies"]:
        print(f"  Avg Latency: {results['avg_latency_ms']:.2f}ms")
        print(f"  P95 Latency: {results['p95_latency_ms']:.2f}ms")
    print("="*50)
    
    if not results["success"]:
        raise Exception("Some tests failed")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", type=str, required=True)
    parser.add_argument("--test-data", type=str, required=True)
    parser.add_argument("--region", type=str, required=True)
    
    args = parser.parse_args()
    
    test_endpoint(args.endpoint_name, args.test_data, args.region)

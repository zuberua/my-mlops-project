#!/usr/bin/env python3
"""Validate test results before production deployment."""

import argparse
import json
import sys


def validate_tests(test_results_file, min_accuracy=0.85):
    """Validate test results."""
    
    with open(test_results_file, "r") as f:
        results = json.load(f)
    
    print(f"Test Results: {json.dumps(results, indent=2)}")
    
    # Check if tests passed
    if not results.get("success", False):
        print("❌ Tests failed")
        sys.exit(1)
    
    # Check accuracy
    accuracy = results.get("accuracy", 0)
    if accuracy < min_accuracy:
        print(f"❌ Accuracy {accuracy} is below threshold {min_accuracy}")
        sys.exit(1)
    
    # Check latency
    latency = results.get("avg_latency_ms", 0)
    if latency > 1000:
        print(f"⚠️  Warning: High latency detected ({latency}ms)")
    
    print(f"✅ All validation checks passed")
    print(f"   Accuracy: {accuracy}")
    print(f"   Latency: {latency}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-results", type=str, required=True)
    parser.add_argument("--min-accuracy", type=float, default=0.85)
    
    args = parser.parse_args()
    
    validate_tests(args.test_results, args.min_accuracy)

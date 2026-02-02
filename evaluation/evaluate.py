#!/usr/bin/env python3
"""Model evaluation script for SageMaker Pipeline."""

import argparse
import json
import os
import sys
import subprocess
import tarfile

# Install xgboost compatible with the container's pandas 1.1.3
print("Installing xgboost compatible with container environment...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost==1.3.3", "-q"])

import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def evaluate(model_path, test_path, output_path):
    """Evaluate model on test data."""
    
    print("Loading model...")
    
    # Extract model
    model_tar = os.path.join(model_path, "model.tar.gz")
    with tarfile.open(model_tar, "r:gz") as tar:
        tar.extractall(path="/tmp/model")
    
    # Load XGBoost model
    model = xgb.Booster()
    model.load_model("/tmp/model/xgboost-model")
    
    print("Loading test data...")
    
    # Load test data
    test_data = pd.read_csv(
        os.path.join(test_path, "test.csv"),
        header=None
    )
    
    # Split features and target
    y_test = test_data.iloc[:, 0]
    X_test = test_data.iloc[:, 1:]
    
    # Convert to DMatrix
    dtest = xgb.DMatrix(X_test)
    
    print("Making predictions...")
    
    # Get predictions
    y_pred_proba = model.predict(dtest)
    y_pred = (y_pred_proba > 0.5).astype(int)
    
    print("Calculating metrics...")
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="binary")
    recall = recall_score(y_test, y_pred, average="binary")
    f1 = f1_score(y_test, y_pred, average="binary")
    
    try:
        auc = roc_auc_score(y_test, y_pred_proba)
    except:
        auc = 0.0
    
    cm = confusion_matrix(y_test, y_pred)
    
    # Create evaluation report
    report = {
        "classification_metrics": {
            "accuracy": {
                "value": float(accuracy),
                "standard_deviation": 0.0
            },
            "precision": {
                "value": float(precision),
                "standard_deviation": 0.0
            },
            "recall": {
                "value": float(recall),
                "standard_deviation": 0.0
            },
            "f1_score": {
                "value": float(f1),
                "standard_deviation": 0.0
            },
            "auc": {
                "value": float(auc),
                "standard_deviation": 0.0
            }
        },
        "confusion_matrix": {
            "true_negatives": int(cm[0][0]),
            "false_positives": int(cm[0][1]),
            "false_negatives": int(cm[1][0]),
            "true_positives": int(cm[1][1])
        }
    }
    
    # Save evaluation report
    os.makedirs(output_path, exist_ok=True)
    
    with open(os.path.join(output_path, "evaluation.json"), "w") as f:
        json.dump(report, f, indent=2)
    
    print("\nEvaluation Results:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  AUC:       {auc:.4f}")
    print("\nConfusion Matrix:")
    print(f"  TN: {cm[0][0]}, FP: {cm[0][1]}")
    print(f"  FN: {cm[1][0]}, TP: {cm[1][1]}")
    print("\nEvaluation complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, default="/opt/ml/processing/model")
    parser.add_argument("--test-path", type=str, default="/opt/ml/processing/test")
    parser.add_argument("--output-path", type=str, default="/opt/ml/processing/evaluation")
    
    args = parser.parse_args()
    
    evaluate(args.model_path, args.test_path, args.output_path)

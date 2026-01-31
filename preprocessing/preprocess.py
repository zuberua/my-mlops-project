#!/usr/bin/env python3
"""Data preprocessing script for SageMaker Pipeline."""

import argparse
import os
import pandas as pd
from sklearn.model_selection import train_test_split


def preprocess(input_path, output_path):
    """Preprocess data and split into train/validation/test sets."""
    
    print(f"Reading data from {input_path}")
    
    # Read input data
    df = pd.read_csv(os.path.join(input_path, "data.csv"))
    
    print(f"Data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Basic preprocessing
    # TODO: Add your preprocessing logic here
    # - Handle missing values
    # - Feature engineering
    # - Encoding categorical variables
    # - Scaling/normalization
    
    # Example: Drop rows with missing values
    df = df.dropna()
    
    # Split features and target
    # Assuming last column is target
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]
    
    # Split data: 70% train, 15% validation, 15% test
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    # Combine features and target
    train_data = pd.concat([y_train, X_train], axis=1)
    val_data = pd.concat([y_val, X_val], axis=1)
    test_data = pd.concat([y_test, X_test], axis=1)
    
    # Save processed data
    train_output = os.path.join(output_path, "train")
    val_output = os.path.join(output_path, "validation")
    test_output = os.path.join(output_path, "test")
    
    os.makedirs(train_output, exist_ok=True)
    os.makedirs(val_output, exist_ok=True)
    os.makedirs(test_output, exist_ok=True)
    
    train_data.to_csv(os.path.join(train_output, "train.csv"), index=False, header=False)
    val_data.to_csv(os.path.join(val_output, "validation.csv"), index=False, header=False)
    test_data.to_csv(os.path.join(test_output, "test.csv"), index=False, header=False)
    
    print(f"Train set: {train_data.shape}")
    print(f"Validation set: {val_data.shape}")
    print(f"Test set: {test_data.shape}")
    print("Preprocessing complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", type=str, default="/opt/ml/processing/input")
    parser.add_argument("--output-path", type=str, default="/opt/ml/processing")
    
    args = parser.parse_args()
    
    preprocess(args.input_path, args.output_path)

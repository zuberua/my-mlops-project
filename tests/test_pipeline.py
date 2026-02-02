#!/usr/bin/env python3
"""Unit tests for pipeline code."""

import pytest
import os


def test_imports():
    """Test that required packages can be imported."""
    import boto3
    import sagemaker
    assert boto3.__version__
    # SageMaker doesn't have __version__, just check it imports
    assert sagemaker is not None


def test_environment_variables():
    """Test that we can access environment variables."""
    # These should be set by GitHub Actions
    assert os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')


def test_pipeline_files_exist():
    """Test that pipeline files exist."""
    import os
    
    # Check if pipeline files exist
    assert os.path.exists('pipelines/create_pipeline.py')
    assert os.path.exists('pipelines/run_pipeline.py')
    assert os.path.exists('pipelines/wait_pipeline.py')
    assert os.path.exists('pipelines/get_results.py')


def test_sample_data_format():
    """Test that sample data has correct format."""
    import pandas as pd
    
    # Check if sample data exists
    assert os.path.exists('sample_data.csv')
    
    # Load and validate
    df = pd.read_csv('sample_data.csv')
    
    # Should have at least one row
    assert len(df) > 0
    
    # Should have target column
    assert 'target' in df.columns
    
    # Target should be binary (0 or 1)
    assert df['target'].isin([0, 1]).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

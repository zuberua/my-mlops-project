#!/usr/bin/env python3
import boto3

bucket_name = "sagemaker-mlops-demo-138720056246"
region = "us-east-1"

s3 = boto3.client('s3', region_name=region)

print(f"Deleting all versions from bucket: {bucket_name}")

# Delete all object versions
paginator = s3.get_paginator('list_object_versions')
for page in paginator.paginate(Bucket=bucket_name):
    # Delete versions
    if 'Versions' in page:
        for version in page['Versions']:
            print(f"Deleting version: {version['Key']} (VersionId: {version['VersionId']})")
            s3.delete_object(Bucket=bucket_name, Key=version['Key'], VersionId=version['VersionId'])
    
    # Delete delete markers
    if 'DeleteMarkers' in page:
        for marker in page['DeleteMarkers']:
            print(f"Deleting delete marker: {marker['Key']} (VersionId: {marker['VersionId']})")
            s3.delete_object(Bucket=bucket_name, Key=marker['Key'], VersionId=marker['VersionId'])

print(f"✓ All versions deleted from {bucket_name}")

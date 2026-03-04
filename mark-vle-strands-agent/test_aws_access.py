#!/usr/bin/env python3
"""Test AWS access for mark-vle-strands-agent"""

import boto3
import os
import sys

def test_aws_access():
    print("\nTesting AWS Access")
    print("="*60)
    
    # Create session
    try:
        if os.environ.get('AWS_ACCESS_KEY_ID'):
            session = boto3.Session(region_name='us-west-2')
            print("✓ Using environment credentials")
        else:
            session = boto3.Session(profile_name='zuberua-Admin', region_name='us-west-2')
            print("✓ Using profile: zuberua-Admin")
    except Exception as e:
        print(f"✗ Failed to create session: {e}")
        return False
    
    # Test STS
    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"✓ Identity: {identity['Arn']}")
    except Exception as e:
        print(f"✗ STS failed: {e}")
        return False
    
    # Test S3
    try:
        s3 = session.client('s3')
        response = s3.list_objects_v2(
            Bucket='markvie-vectors-138720056246',
            Prefix='embeddings/',
            MaxKeys=3
        )
        if 'Contents' in response:
            print(f"✓ S3 access: markvie-vectors-138720056246 ({response['KeyCount']} objects)")
        else:
            print("✗ No objects found in S3")
            return False
    except Exception as e:
        print(f"✗ S3 failed: {e}")
        return False
    
    # Test Bedrock
    try:
        session.client('bedrock-runtime')
        print("✓ Bedrock client created")
    except Exception as e:
        print(f"✗ Bedrock failed: {e}")
        return False
    
    print("="*60)
    print("✓ All tests passed!\n")
    return True

if __name__ == '__main__':
    sys.exit(0 if test_aws_access() else 1)

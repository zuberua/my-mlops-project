#!/usr/bin/env python3
"""
Load Mark Vle block pin data into DynamoDB (local CLI tool).

Usage:
    python load_data.py --file data/sample_pins.csv --dry-run
    python load_data.py --file data/sample_pins.csv --table MarkvleBlockPins-production
"""

import argparse
import csv
import sys
import os

# Add lambda dir to path so we can reuse build_item
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'csv_processor'))
from handler import build_item

import boto3


def load_csv(filepath):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description='Load block pin data into DynamoDB')
    parser.add_argument('--file', default='data/sample_pins.csv', help='CSV file path')
    parser.add_argument('--table', default='MarkvleBlockPins-production', help='DynamoDB table name')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    parser.add_argument('--profile', default=None, help='AWS profile')
    parser.add_argument('--dry-run', action='store_true', help='Print items without writing')
    args = parser.parse_args()

    rows = load_csv(args.file)
    items = [build_item(row) for row in rows]
    print(f'Loaded {len(rows)} rows → {len(items)} items')

    if args.dry_run:
        for item in items[:3]:
            print(f"\n  PK: {item['PK']}")
            print(f"  SK: {item['SK']}")
            print(f"  GSI1PK: {item['GSI1PK']}")
            print(f"  GSI1SK: {item['GSI1SK']}")
        print(f'\n  ... and {len(items) - 3} more')
        return

    session_kwargs = {'region_name': args.region}
    if args.profile:
        session_kwargs['profile_name'] = args.profile

    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(args.table)

    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    print(f'Successfully wrote {len(items)} items to {args.table}')


if __name__ == '__main__':
    main()

"""
Lambda handler: S3 CSV upload → DynamoDB block pin ingestion.

Triggered by S3 PutObject events on the uploads/ prefix.
Downloads the CSV, parses it, and batch-writes pin items
to the DynamoDB table using the new key design:

PK: SYS#{System}|DEV#{Device}|PG#{ProgramGroup}|PROG#{Program}|TASK#{Task}
SK: BEX#{BlockExecution}|BLK#{Block}|PIN#{Pin}|USE#{Usage}
"""

import csv
import io
import os
import re
import urllib.parse

import boto3

TABLE_NAME = os.environ.get('TABLE_NAME', '')

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None


def parse_locator(locator):
    """Extract System, Device, ProgramGroup from Locator string.

    Locator format:
    System:TVA CUMBERLAND|Device:G1|ProgramGroup:Custom|Program:Custom|Block:...|PinVariable:...
    """
    parts = {}
    for segment in locator.split('|'):
        if ':' in segment:
            key, value = segment.split(':', 1)
            # Only take the first occurrence of each key
            if key not in parts:
                parts[key] = value
    return parts


def build_pk(row, locator_parts):
    """Build partition key from hierarchy fields."""
    system = locator_parts.get('System', 'UNKNOWN')
    device = locator_parts.get('Device', 'UNKNOWN')
    prog_group = locator_parts.get('ProgramGroup', 'UNKNOWN')
    program = row.get('Program', '').strip() or locator_parts.get('Program', 'UNKNOWN')
    task = row.get('Task', '').strip() or 'UNKNOWN'

    return f'SYS#{system}|DEV#{device}|PG#{prog_group}|PROG#{program}|TASK#{task}'


def build_sk(row):
    """Build sort key: execution order → block → pin → usage."""
    block_exec = int(row['BlockExecution'].strip())
    block = row['Block'].strip()
    pin = row['Pin'].strip()
    usage = row['Usage'].strip()

    return f'BEX#{block_exec:04d}|BLK#{block}|PIN#{pin}|USE#{usage}'


def build_item(row):
    """Build a DynamoDB item from a CSV row."""
    locator = row.get('Locator', '').strip()
    locator_parts = parse_locator(locator)

    pk = build_pk(row, locator_parts)
    sk = build_sk(row)

    block = row['Block'].strip()
    pin = row['Pin'].strip()
    block_type = row['BlockType'].strip()
    usage = row['Usage'].strip()
    system = locator_parts.get('System', 'UNKNOWN')
    device = locator_parts.get('Device', 'UNKNOWN')

    return {
        # Primary key
        'PK': pk,
        'SK': sk,
        # GSI1 — BlockTypeIndex (cross-project queries by type)
        'GSI1PK': f'TYPE#{block_type}',
        'GSI1SK': f'USE#{usage}|SYS#{system}|DEV#{device}|BLK#{block}|PIN#{pin}',
        # GSI2 — LocatorIndex (globally unique lookup)
        'GSI2PK': f'LOC#{locator}',
        'GSI2SK': '-',
        # Attributes
        'Pin': pin,
        'PinDescription': row.get('PinDescription', '').strip(),
        'Block': block,
        'BlockDescription': row.get('BlockDescription', '').strip(),
        'Task': row.get('Task', '').strip(),
        'Program': row.get('Program', '').strip(),
        'BlockExecution': int(row['BlockExecution'].strip()),
        'BlockType': block_type,
        'Connection': row.get('Connection', '').strip(),
        'DataType': row.get('DataType', '').strip(),
        'EntryNo': int(row['EntryNo'].strip()),
        'IsCritical': row.get('IsCritical', 'FALSE').strip().upper() == 'TRUE',
        'ProgramExecution': int(row.get('ProgramExecution', '0').strip()),
        'Usage': usage,
        'Locator': locator,
        'System': system,
        'Device': device,
        'ProgramGroup': locator_parts.get('ProgramGroup', ''),
    }


def parse_csv(body_bytes):
    """Parse CSV bytes into list of dicts."""
    text = body_bytes.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def handler(event, context):
    """Lambda entry point — triggered by S3 event."""
    results = []

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])

        print(f'Processing s3://{bucket}/{key}')

        # Download CSV from S3
        response = s3.get_object(Bucket=bucket, Key=key)
        rows = parse_csv(response['Body'].read())
        print(f'Parsed {len(rows)} rows')

        # Build and write items
        items = [build_item(row) for row in rows]
        print(f'Writing {len(items)} items to {TABLE_NAME}')

        written = 0
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
                written += 1

        # Move processed file to processed/ prefix
        processed_key = key.replace('uploads/', 'processed/', 1)
        s3.copy_object(
            Bucket=bucket,
            CopySource={'Bucket': bucket, 'Key': key},
            Key=processed_key,
        )
        s3.delete_object(Bucket=bucket, Key=key)
        print(f'Moved {key} → {processed_key}')

        results.append({
            'file': key,
            'rows_parsed': len(rows),
            'items_written': written,
        })

    return {
        'statusCode': 200,
        'body': results,
    }

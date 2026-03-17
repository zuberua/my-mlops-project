"""
Lambda handler: CSV pin report → DynamoDB block pin ingestion.

Invoked by Step Functions with payload:
  {"bucket": "bucket-name", "key": "uploads/file.csv"}

Also supports direct S3 event trigger (legacy) for backward compatibility.

Downloads the CSV, parses it, and batch-writes pin items to DynamoDB
using the pin-level key design:

PK: SYS#{System}|DEV#{Device}|PG#{ProgramGroup}|PROG#{Program}|TASK#{Task}
SK: BEX#{BlockExecution}|BLK#{Block}|PIN#{Pin}|USE#{Usage}
"""

import csv
import io
import os
import urllib.parse

import boto3

TABLE_NAME = os.environ.get('TABLE_NAME', '')

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None


def parse_locator(locator):
    """Extract System, Device, ProgramGroup from Locator string."""
    parts = {}
    for segment in locator.split('|'):
        if ':' in segment:
            key, value = segment.split(':', 1)
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


def build_item(row, source_file='', upload_id=''):
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
    connection = row.get('Connection', '').strip()

    return {
        'PK': pk,
        'SK': sk,
        'GSI3PK': f'CONN#{connection}' if connection else 'CONN#NONE',
        'GSI3SK': f'USE#{usage}|BLK#{block}|PIN#{pin}',
        'Pin': pin,
        'PinDescription': row.get('PinDescription', '').strip(),
        'Block': block,
        'BlockDescription': row.get('BlockDescription', '').strip(),
        'Task': row.get('Task', '').strip(),
        'Program': row.get('Program', '').strip(),
        'BlockExecution': int(row['BlockExecution'].strip()),
        'BlockType': block_type,
        'Connection': connection,
        'DataType': row.get('DataType', '').strip(),
        'EntryNo': int(row['EntryNo'].strip()),
        'IsCritical': row.get('IsCritical', 'FALSE').strip().upper() == 'TRUE',
        'ProgramExecution': int(row.get('ProgramExecution', '0').strip()),
        'Usage': usage,
        'Locator': locator,
        'System': system,
        'Device': device,
        'ProgramGroup': locator_parts.get('ProgramGroup', ''),
        'SourceFile': source_file,
        'UploadId': upload_id,
    }


def parse_csv(body_bytes):
    """Parse CSV bytes into list of dicts."""
    text = body_bytes.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _extract_bucket_key(event):
    """Extract bucket and key from Step Functions payload or S3 event.

    Step Functions payload format:
      {"bucket": "bucket-name", "key": "uploads/file.csv"}

    S3 event format (legacy):
      {"Records": [{"s3": {"bucket": {"name": "..."}, "object": {"key": "..."}}}]}
    """
    # Step Functions payload (primary)
    if 'bucket' in event and 'key' in event:
        return event['bucket'], event['key']

    # S3 event record (legacy/backward compat)
    if 'Records' in event:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        return bucket, key

    raise ValueError(f'Unrecognized event format: {list(event.keys())}')


def process_file(bucket, key, upload_id=''):
    """Download CSV from S3, parse, and write items to DynamoDB.

    Returns processing result including project/task context extracted
    from the CSV data (unique systems and tasks found in the file).
    """
    print(f'Processing s3://{bucket}/{key}')

    response = s3.get_object(Bucket=bucket, Key=key)
    rows = parse_csv(response['Body'].read())
    print(f'Parsed {len(rows)} rows')

    source_file = key.split('/')[-1]
    items = [build_item(row, source_file=source_file, upload_id=upload_id) for row in rows]
    print(f'Writing {len(items)} items to {TABLE_NAME}')

    written = 0
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
            written += 1

    # Extract project and task context from processed items
    systems = sorted(set(item.get('System', 'UNKNOWN') for item in items))
    tasks = sorted(set(item.get('Task', 'UNKNOWN') for item in items))
    project_context = ' | '.join(systems)
    task_context = ' | '.join(tasks)
    print(f'Project context: {project_context}')
    print(f'Task context: {task_context}')

    # Delete processed file from knowledgebase/ to avoid re-triggering EventBridge
    s3.delete_object(Bucket=bucket, Key=key)
    print(f'Deleted {key} after processing')

    return {
        'file': key,
        'rows_parsed': len(rows),
        'items_written': written,
        'project_context': project_context,
        'task_context': task_context,
    }


def handler(event, context):
    """Lambda entry point — invoked by Step Functions or S3 event."""
    bucket, key = _extract_bucket_key(event)
    upload_id = event.get('uploadId', '')
    result = process_file(bucket, key, upload_id=upload_id)

    return {
        'statusCode': 200,
        'body': result,
    }

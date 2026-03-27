"""DynamoDB Stream → SQS producer.

Reads pin table stream events, extracts unique (project, task) PKs,
and sends one SQS message per unique PK to the summary queue.
SQS FIFO deduplication prevents duplicate messages within the 5-min window.
"""

import hashlib
import json
import os

import boto3

QUEUE_URL = os.environ.get("SUMMARY_QUEUE_URL", "")

sqs = boto3.client("sqs")


def _safe_dedup_id(pk):
    """Hash the PK to produce a valid SQS MessageDeduplicationId."""
    return hashlib.sha256(pk.encode("utf-8")).hexdigest()[:128]


def _safe_group_id(pk):
    """Hash the PK to produce a valid SQS MessageGroupId."""
    return hashlib.sha256(pk.encode("utf-8")).hexdigest()[:128]


def handler(event, context):
    """Process DynamoDB Stream records and enqueue unique PKs."""
    if not QUEUE_URL:
        raise ValueError("SUMMARY_QUEUE_URL environment variable is required")

    # Extract unique PKs from stream records
    unique_pks = {}
    for record in event.get("Records", []):
        if record["eventName"] not in ("INSERT", "MODIFY"):
            continue

        new_image = record["dynamodb"].get("NewImage", {})
        pk = new_image.get("PK", {}).get("S", "")
        if not pk:
            continue

        # Only process once per PK in this batch
        if pk in unique_pks:
            continue

        # Extract metadata from the PK
        # PK format: SYS#{sys}|DEV#{dev}|PG#{pg}|PROG#{prog}|TASK#{task}
        parts = {}
        for segment in pk.split("|"):
            if "#" in segment:
                prefix, value = segment.split("#", 1)
                parts[prefix] = value

        system = parts.get("SYS", "UNKNOWN")
        device = parts.get("DEV", "UNKNOWN")
        task = parts.get("TASK", "UNKNOWN")
        program = parts.get("PROG", "UNKNOWN")
        project_id = f"{system}_{device}".replace(" ", "_")

        unique_pks[pk] = {
            "pk": pk,
            "project_id": project_id,
            "task": task,
            "program": program,
        }

    # Send one SQS message per unique PK
    sent = 0
    for pk, payload in unique_pks.items():
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(payload),
            MessageGroupId=_safe_group_id(pk),
            MessageDeduplicationId=_safe_dedup_id(pk),
        )
        sent += 1

    print(f"Processed {len(event.get('Records', []))} stream records, "
          f"enqueued {sent} unique PKs")

    return {"records_processed": len(event.get("Records", [])), "messages_sent": sent}

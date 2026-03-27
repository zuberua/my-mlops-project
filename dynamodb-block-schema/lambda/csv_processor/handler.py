"""Lambda handler: S3 CSV upload -> DynamoDB block pin ingestion.

Triggered by EventBridge on S3 PutObject events (files_to_be_processed/ prefix),
or directly by Step Functions payload.

Downloads the CSV, parses it, and batch-writes pin items to DynamoDB.
After successful processing, moves the file to files_already_processed/.

PK: SYS#{System}|DEV#{Device}|PG#{ProgramGroup}|PROG#{Program}|TASK#{Task}
SK: BEX#{BlockExecution}|BLK#{Block}|PIN#{Pin}|USE#{Usage}

GSI indexes:
  ConnectionIndex (GSI3) - trace signal chains by connection name
"""

import csv
import io
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import PurePosixPath

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "")
TRACKER_TABLE_NAME = os.environ.get("TRACKER_TABLE_NAME", "")

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None


def utc_timestamp():
    """Return compact UTC timestamp for deterministic S3 object names."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def move_s3_object(bucket, source_key, dest_key):
    """Move an S3 object by copy+delete."""
    s3.copy_object(
        Bucket=bucket,
        CopySource={"Bucket": bucket, "Key": source_key},
        Key=dest_key,
    )
    s3.delete_object(Bucket=bucket, Key=source_key)


def unsupported_key_for(key):
    """Build destination key for unsupported files."""
    stem = PurePosixPath(key).name
    return f"failed/unsupported/{utc_timestamp()}-{stem}"


def flagged_report_key_for(key, upload_id):
    """Build destination key for skipped-row reports."""
    del upload_id  # kept for compatibility with existing callsites
    return f"skipped_records/{PurePosixPath(key).name}"


def parse_locator(locator):
    """Extract System, Device, ProgramGroup from Locator string.

    Locator format:
      System:TVA CUMBERLAND|Device:G1|ProgramGroup:Custom|Program:Custom|...
    """
    parts = {}
    for segment in locator.split("|"):
        if ":" in segment:
            key, value = segment.split(":", 1)
            if key not in parts:
                parts[key] = value
    return parts


def build_pk(row, locator_parts):
    """Build partition key from hierarchy fields."""
    system = locator_parts.get("System", "UNKNOWN")
    device = locator_parts.get("Device", "UNKNOWN")
    prog_group = locator_parts.get("ProgramGroup", "UNKNOWN")
    program = row.get("Program", "").strip() or locator_parts.get("Program", "UNKNOWN")
    task = row.get("Task", "").strip() or "UNKNOWN"
    return f"SYS#{system}|DEV#{device}|PG#{prog_group}|PROG#{program}|TASK#{task}"


def build_sk(row):
    """Build sort key: execution order -> block -> pin -> usage."""
    block_exec = int(row["BlockExecution"].strip())
    block = row["Block"].strip()
    pin = row["Pin"].strip()
    usage = row["Usage"].strip()
    return f"BEX#{block_exec:04d}|BLK#{block}|PIN#{pin}|USE#{usage}"


def build_item(row, source_key):
    """Build a DynamoDB item from a CSV row."""
    locator = row.get("Locator", "").strip()
    locator_parts = parse_locator(locator)
    source_file_name = PurePosixPath(source_key).name

    pk = build_pk(row, locator_parts)
    sk = build_sk(row)

    block = row["Block"].strip()
    pin = row["Pin"].strip()
    block_type = row["BlockType"].strip()
    usage = row["Usage"].strip()
    system = locator_parts.get("System", "UNKNOWN")
    device = locator_parts.get("Device", "UNKNOWN")
    connection = row.get("Connection", "").strip()

    return {
        "PK": pk,
        "SK": sk,
        "GSI3PK": f"CONN#{connection}" if connection else "CONN#NONE",
        "GSI3SK": f"USE#{usage}|BLK#{block}|PIN#{pin}",
        "Pin": pin,
        "PinDescription": row.get("PinDescription", "").strip(),
        "Block": block,
        "BlockDescription": row.get("BlockDescription", "").strip(),
        "Task": row.get("Task", "").strip(),
        "Program": row.get("Program", "").strip(),
        "BlockExecution": int(row["BlockExecution"].strip()),
        "BlockType": block_type,
        "Connection": connection,
        "DataType": row.get("DataType", "").strip(),
        "EntryNo": int(row["EntryNo"].strip()),
        "IsCritical": row.get("IsCritical", "FALSE").strip().upper() == "TRUE",
        "ProgramExecution": int(row.get("ProgramExecution", "0").strip()),
        "Usage": usage,
        "Locator": locator,
        "System": system,
        "Device": device,
        "ProgramGroup": locator_parts.get("ProgramGroup", ""),
        "SourceS3Key": source_key,
        "SourceFileName": source_file_name,
    }


def parse_csv(body_bytes):
    """Parse CSV bytes into list of dicts.

    Handles multiple encodings, skips metadata/title rows before the header,
    and normalizes space-separated column names to camelCase.
    """
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "iso-8859-1"):
        try:
            text = body_bytes.decode(encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        raise ValueError(
            "Unable to decode CSV. Supported encodings: utf-8-sig, utf-16, cp1252, iso-8859-1"
        )

    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        first_field = line.split(",")[0].strip().lstrip("\ufeff")
        if first_field == "Pin":
            start = i
            break

    if start is None:
        raise ValueError("CSV header row not found; expected first column 'Pin'")

    body = "\n".join(lines[start:])

    _HEADER_MAP = {
        "Pin Description":   "PinDescription",
        "Block Description": "BlockDescription",
        "Block Execution":   "BlockExecution",
        "Block Type":        "BlockType",
        "Data Type":         "DataType",
        "Entry No":          "EntryNo",
        "Is Critical":       "IsCritical",
        "Program Execution": "ProgramExecution",
    }

    reader = csv.DictReader(io.StringIO(body))
    rows = []
    for row in reader:
        rows.append({_HEADER_MAP.get(k, k): v for k, v in row.items()})
    return rows


def iter_targets(event):
    """Normalize either S3 or Step Functions payloads into bucket/key targets."""
    if "Records" in event:
        for record in event["Records"]:
            yield {
                "bucket": record["s3"]["bucket"]["name"],
                "key": urllib.parse.unquote_plus(record["s3"]["object"]["key"]),
                "upload_id": "",
            }
        return

    bucket = event.get("bucket")
    key = event.get("key")
    if bucket and key:
        yield {
            "bucket": bucket,
            "key": urllib.parse.unquote_plus(key),
            "upload_id": event.get("uploadId", ""),
        }
        return

    raise ValueError("Event must contain either S3 Records or bucket/key fields")


def build_context(rows):
    """Derive lightweight context strings for Step Functions tracking."""
    if not rows:
        return {"project_context": "UNKNOWN", "task_context": "UNKNOWN"}

    first_row = rows[0]
    locator_parts = parse_locator(first_row.get("Locator", "").strip())
    program_group = locator_parts.get("ProgramGroup", "UNKNOWN")
    program = (
        first_row.get("Program", "").strip()
        or locator_parts.get("Program", "UNKNOWN")
    )
    task = first_row.get("Task", "").strip() or "UNKNOWN"

    return {
        "project_context": f"ProgramGroup:{program_group}|Program:{program}",
        "task_context": f"Task:{task}",
    }


def processed_key_for(key):
    """Compute the processed/ destination key for a source file."""
    if key.startswith("files_to_be_processed/"):
        return key.replace("files_to_be_processed/", "files_already_processed/", 1)
    return f"files_already_processed/{PurePosixPath(key).name}"


def handler(event, context):
    """Lambda entry point for either S3 events or Step Functions payloads."""
    if not table:
        raise ValueError("TABLE_NAME environment variable is required")

    results = []
    for target in iter_targets(event):
        bucket = target["bucket"]
        key = target["key"]
        upload_id = target["upload_id"]

        print(f"Processing s3://{bucket}/{key}")

        try:
            # Reject non-CSV files early
            if not key.lower().endswith(".csv"):
                unsupported_key = unsupported_key_for(key)
                move_s3_object(bucket, key, unsupported_key)
                raise ValueError(
                    f"Unsupported file type for {key}. Moved to {unsupported_key}"
                )

            # Download and parse CSV
            response = s3.get_object(Bucket=bucket, Key=key)
            try:
                rows = parse_csv(response["Body"].read())
            except ValueError as parse_err:
                unsupported_key = unsupported_key_for(key)
                move_s3_object(bucket, key, unsupported_key)
                raise ValueError(
                    f"{parse_err}. Moved to {unsupported_key}"
                ) from parse_err

            print(f"Parsed {len(rows)} rows")

            # Build items, skipping malformed rows
            items = []
            skipped = 0
            skipped_rows = []
            for i, row in enumerate(rows):
                try:
                    items.append(build_item(row, key))
                except Exception as row_err:
                    print(f"ERROR: skipping row {i} in {key}: {row_err}")
                    skipped += 1
                    skipped_rows.append({
                        "row_number": i + 2,
                        "error": str(row_err),
                        "row_data": row,
                    })

            print(f"Writing {len(items)} items to {TABLE_NAME} ({skipped} rows skipped)")

            written = 0
            with table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
                    written += 1

            context_info = build_context(rows)

            # Write skipped rows report to S3
            flagged_report_key = ""
            if skipped_rows:
                flagged_report_key = flagged_report_key_for(key, upload_id)
                dynamic_fields = set()
                for skipped_row in skipped_rows:
                    dynamic_fields.update(
                        (skipped_row.get("row_data") or {}).keys()
                    )
                fieldnames = ["row_number", "error"] + sorted(dynamic_fields)

                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=fieldnames)
                writer.writeheader()
                for skipped_row in skipped_rows:
                    out_row = {
                        "row_number": skipped_row["row_number"],
                        "error": skipped_row["error"],
                    }
                    out_row.update(skipped_row.get("row_data") or {})
                    writer.writerow(out_row)

                s3.put_object(
                    Bucket=bucket,
                    Key=flagged_report_key,
                    Body=buffer.getvalue().encode("utf-8"),
                    ContentType="text/csv",
                )
                print(f"Wrote skipped rows to s3://{bucket}/{flagged_report_key}")

            # Move processed file
            processed_key = processed_key_for(key)
            move_s3_object(bucket, key, processed_key)
            print(f"Moved {key} -> {processed_key}")

            # Collect unique (project, task) scopes for summary generation
            unique_pks = sorted(set(item["PK"] for item in items))
            unique_tasks = []
            for pk in unique_pks:
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
                unique_tasks.append({
                    "pk": pk,
                    "project_id": project_id,
                    "task": task,
                    "program": program,
                })

            results.append({
                "file": key,
                "upload_id": upload_id,
                "rows_parsed": len(rows),
                "items_written": written,
                "rows_skipped": skipped,
                "flagged_report_key": flagged_report_key,
                "project_context": context_info["project_context"],
                "task_context": context_info["task_context"],
                "processed_key": processed_key,
                "tracker_table_name": TRACKER_TABLE_NAME,
                "unique_tasks": unique_tasks,
            })

        except Exception as e:
            print(f"ERROR: failed to process s3://{bucket}/{key}: {e}")
            raise

    body = results[0] if "Records" not in event and len(results) == 1 else results
    return {
        "statusCode": 200,
        "body": body,
    }

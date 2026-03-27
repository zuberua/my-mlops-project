"""Agent tools for task logic summary generation.

These tools allow the AgentCore agent to query pin data from DynamoDB
and write task summaries back, enabling the agent to build knowledge
about the control logic during ingestion.
"""

import json
import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from strands import tool

# Table names from environment (set in AgentCore deployment)
_PINS_TABLE = os.environ.get("PINS_TABLE_NAME", "markvie-kb-poc")
_SUMMARY_TABLE = os.environ.get("TASK_SUMMARY_TABLE_NAME", "markvie-kb-task-summaries-poc")
_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")

_dynamodb = None


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=_REGION)
    return _dynamodb


@tool
def query_task_pins(pk: str, table_name: str = "") -> str:
    """Query all pins for a (project, task) partition key from the pins DynamoDB table.

    Args:
        pk: The partition key, e.g. SYS#TVA CUMBERLAND|DEV#G1|PG#Custom|PROG#Custom|TASK#TempMonitor
        table_name: Optional table name override. Defaults to PINS_TABLE_NAME env var.

    Returns:
        JSON with pins list, signals_in, signals_out, block_types_used, and row_count.
    """
    tbl_name = table_name or _PINS_TABLE
    table = _get_dynamodb().Table(tbl_name)

    items = []
    response = table.query(KeyConditionExpression=Key("PK").eq(pk))
    items.extend(response["Items"])
    while response.get("LastEvaluatedKey"):
        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response["Items"])

    # Extract metadata
    signals_in = set()
    signals_out = set()
    block_types = set()

    for pin in items:
        usage = pin.get("Usage", "")
        connection = pin.get("Connection", "")
        block_type = pin.get("BlockType", "")

        if block_type:
            block_types.add(block_type)
        if usage == "Input" and connection:
            signals_in.add(connection)
        elif usage == "Output" and connection:
            signals_out.add(connection)

    # Build compact pin list for the agent to analyze
    pins_compact = [
        {
            "Pin": p.get("Pin", ""),
            "Block": p.get("Block", ""),
            "BlockType": p.get("BlockType", ""),
            "Usage": p.get("Usage", ""),
            "Connection": p.get("Connection", ""),
            "DataType": p.get("DataType", ""),
            "BlockExecution": str(p.get("BlockExecution", "")),
        }
        for p in items[:100]  # Cap at 100 for prompt size
    ]

    return json.dumps({
        "pk": pk,
        "row_count": len(items),
        "signals_in": sorted(signals_in),
        "signals_out": sorted(signals_out),
        "block_types_used": sorted(block_types),
        "pins_sample": pins_compact,
        "total_pins_returned": len(pins_compact),
    }, default=str)


@tool
def write_task_summary(
    pk: str,
    project_id: str,
    task: str,
    program: str,
    signals_in: list,
    signals_out: list,
    block_types_used: list,
    logic_summary: str,
    row_count: int,
    table_name: str = "",
) -> str:
    """Write a task logic summary to the task-summaries DynamoDB table.

    Args:
        pk: Summary partition key, e.g. PROJECT#TVA_CUMBERLAND_G1#TASK#TempMonitor
        project_id: Project identifier, e.g. TVA_CUMBERLAND_G1
        task: Task name, e.g. TempMonitor
        program: Program name, e.g. Custom
        signals_in: List of unique input connection strings
        signals_out: List of unique output connection strings
        block_types_used: List of unique block type values
        logic_summary: Engineering description of the task logic
        row_count: Total pin rows in the task
        table_name: Optional table name override. Defaults to TASK_SUMMARY_TABLE_NAME env var.

    Returns:
        JSON confirmation with the pk written.
    """
    tbl_name = table_name or _SUMMARY_TABLE
    table = _get_dynamodb().Table(tbl_name)

    now = datetime.now(timezone.utc).isoformat()

    item = {
        "pk": pk,
        "project_id": project_id,
        "task": task,
        "program": program,
        "signals_in": signals_in,
        "signals_out": signals_out,
        "block_types_used": block_types_used,
        "logic_summary": logic_summary,
        "row_count": row_count,
        "computed_at": now,
    }

    table.put_item(Item=item)

    return json.dumps({
        "status": "written",
        "pk": pk,
        "computed_at": now,
        "row_count": row_count,
    })

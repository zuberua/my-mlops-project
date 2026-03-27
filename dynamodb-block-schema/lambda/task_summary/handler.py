"""SQS → AgentCore bridge Lambda.

Triggered by SQS. Receives a (project, task) PK and invokes the AgentCore
agent to generate and store the task logic summary. All logic (querying pins,
generating summary, writing to DynamoDB) is handled by the agent's tools.
"""

import json
import os

import boto3

AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
AGENT_REGION = os.environ.get("AGENT_REGION", "us-east-1")
PINS_TABLE = os.environ.get("TABLE_NAME", "")
SUMMARY_TABLE = os.environ.get("TASK_SUMMARY_TABLE_NAME", "")


def handler(event, context):
    """Process SQS messages and invoke AgentCore agent for each."""
    client = boto3.client("bedrock-agentcore", region_name=AGENT_REGION)

    results = []
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        pk = body["pk"]
        project_id = body["project_id"]
        task = body["task"]
        program = body["program"]

        print(f"Invoking AgentCore for {pk}")

        prompt = (
            f"Generate a task logic summary for the following Mark VIe controller task.\n\n"
            f"Use the query_task_pins tool to retrieve all pins for PK: {pk}\n"
            f"Then analyze the signal flow and block types.\n"
            f"Finally, use the write_task_summary tool to store the summary with:\n"
            f"  - pk: PROJECT#{project_id}#TASK#{task}\n"
            f"  - project_id: {project_id}\n"
            f"  - task: {task}\n"
            f"  - program: {program}\n"
            f"  - pins_table: {PINS_TABLE}\n"
            f"  - summary_table: {SUMMARY_TABLE}\n"
            f"  - source_pk: {pk}\n\n"
            f"Include signals_in, signals_out, block_types_used, row_count, "
            f"and a concise engineering logic_summary describing the signal flow."
        )

        try:
            response = client.invoke_agent_runtime(
                agentRuntimeArn=AGENT_RUNTIME_ARN,
                payload=json.dumps({"prompt": prompt}).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )

            # Read streaming response
            body_bytes = b""
            event_stream = response.get("response")
            if event_stream:
                try:
                    for evt in event_stream:
                        if isinstance(evt, dict):
                            if "chunk" in evt:
                                chunk_data = evt["chunk"].get("bytes", b"")
                                if isinstance(chunk_data, str):
                                    chunk_data = chunk_data.encode("utf-8")
                                body_bytes += chunk_data
                        elif isinstance(evt, bytes):
                            body_bytes += evt
                except Exception as stream_err:
                    print(f"Stream read error for {pk}: {stream_err}")

            agent_response = body_bytes.decode("utf-8").strip() if body_bytes else "No response"
            print(f"Agent response for {pk}: {agent_response[:200]}...")
            results.append({"pk": pk, "status": "completed"})

        except Exception as e:
            print(f"AgentCore invocation failed for {pk}: {e}")
            results.append({"pk": pk, "status": "failed", "error": str(e)})
            # Don't raise — let SQS retry via visibility timeout

    return {"results": results}

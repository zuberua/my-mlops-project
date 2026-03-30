"""SQS → AgentCore bridge Lambda.

Triggered by SQS. Receives a (project, task) PK and invokes the AgentCore
agent to generate and store the task logic summary.
"""

import json
import os
import uuid

import boto3

AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
AGENT_REGION = os.environ.get("AGENT_REGION", "us-east-1")
PINS_TABLE = os.environ.get("TABLE_NAME", "")
SUMMARY_TABLE = os.environ.get("TASK_SUMMARY_TABLE_NAME", "")

agent_core_client = boto3.client("bedrock-agentcore", region_name=AGENT_REGION)


def handler(event, context):
    """Process SQS messages and invoke AgentCore agent for each."""
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
            f"  - program: {program}\n\n"
            f"Include signals_in, signals_out, block_types_used, row_count, "
            f"and a concise engineering logic_summary describing the signal flow."
        )

        payload = json.dumps({"prompt": prompt})
        session_id = str(uuid.uuid4())

        try:
            response = agent_core_client.invoke_agent_runtime(
                agentRuntimeArn=AGENT_RUNTIME_ARN,
                runtimeSessionId=session_id,
                payload=payload,
            )

            # Process response based on content type
            raw_response = ""
            content_type = response.get("contentType", "")

            if "text/event-stream" in content_type:
                content = []
                for line in response["response"].iter_lines(chunk_size=10):
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            line = line[6:]
                            content.append(line)
                raw_response = "\n".join(content)

            elif content_type == "application/json":
                content = []
                for chunk in response.get("response", []):
                    content.append(chunk.decode("utf-8"))
                raw_response = "".join(content)

            else:
                raw_response = str(response)

            print(f"Agent response for {pk}: {raw_response[:200]}...")
            results.append({"pk": pk, "status": "completed"})

        except Exception as e:
            print(f"AgentCore invocation failed for {pk}: {e}")
            results.append({"pk": pk, "status": "failed", "error": str(e)})

    return {"results": results}

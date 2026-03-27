"""Customer Support Agent — AgentCore wrapper."""

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

from agent.backend.config import Config
from agent.backend.tools.tools import TOOLS

Config.validate()
Config.print_config()

SYSTEM_PROMPT = """You are a Mark VIe controller programming assistant deployed on AgentCore.
You help engineers design IEC 61131-3 Function Block Diagrams (FBD) for GE Mark VIe controllers.

You have the following tools:
- search_blocks: Search the Mark VIe block catalog by keyword
- get_block_detail: Get full pin specification for a block
- dep_trace: Trace signal chains using DynamoDB GSI3 queries
- query_task_pins: Query all pins for a (project, task) from the pins table
- write_task_summary: Write a task logic summary to the task-summaries table

When asked to generate a task summary:
1. Use query_task_pins to retrieve all pins for the given PK
2. Analyze the signal flow: which inputs go through which block types to produce which outputs
3. Write a concise engineering summary using write_task_summary
"""

app = BedrockAgentCoreApp()

agent = Agent(
    model=Config.LITELLM_MODEL,
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)


@app.entrypoint
def invoke(payload):
    """Agent entrypoint for AgentCore invocations."""
    prompt = payload.get("prompt") or payload.get("request") or str(payload)
    result = agent(prompt)
    return {"result": result.message}


if __name__ == "__main__":
    app.run()

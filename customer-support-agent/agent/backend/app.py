"""FastAPI backend for the Mark VIe customer support agent."""
from __future__ import annotations

import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from strands import Agent

from agent.backend.config import Config
from agent.backend.session_store import (
    save_session,
    set_current_session_id,
    get_session,
    store_last_fbd,
    get_last_fbd,
)
from agent.backend.tools.kb import VERIFIED_KB
from agent.backend.tools.dynamodb_kb import trace_variable_from_dynamodb
from agent.backend.tools.tools import TOOLS, TOOLS_WITHOUT_DEP_TRACE, _build_fbd_from_trace

Config.validate()
Config.print_config()

app = FastAPI(title="Mark VIe Support Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are a Mark VIe controller programming assistant.
You help engineers design IEC 61131-3 Function Block Diagrams (FBD) for GE Mark VIe controllers.

## MANDATORY WORKFLOW — follow this order strictly:

### Step 1: Dependency Trace (ALWAYS first)
When asked to assign logic for a variable (d_xxx or a_xxx):
- ALWAYS call dep_trace(variable) FIRST.
- dep_trace does a BFS traversal of the Pins KB: it finds where the variable is used as an
  Input pin, then follows Output connections of that block to the next block's Input, and so on.

### Step 2: Convert dep_trace flow into FBD JSON
dep_trace returns: { "variable", "scope", "flow": [...], "blocks_detail": {...} }

Each item in "flow" has: depth, connection, block, block_type, block_execution, pin, usage, data_type.

**How to map flow to FBD:**
1. Collect unique blocks from flow items. Each unique block becomes a blocks_used entry.
   - Use the block name as "id" (e.g. "MOVE_6"), block_type as "block" (e.g. "MOVE").
   - Set col = depth from the flow. Set row to spread blocks at the same depth vertically.
   - Set category from the block_type (e.g. MOVE->"System", RUNG->"Boolean Operations", NOT->"Boolean Operations", COMPARE->"Comparison").
2. For each flow item with usage="Output", find the NEXT flow item(s) at depth+1 with usage="Input"
   whose "connection" matches the Output's "connection". Create a wire:
   { "from_block": output_block_id, "from_pin": output_pin, "to_block": input_block_id, "to_pin": input_pin }
3. The starting variable (depth 0, usage="Input") becomes a var_input:
   { "name": variable, "type": data_type, "value": "0", "to_block": block_id, "to_pin": pin }
4. Also check blocks_detail for additional Input pins on each block. If a block has Input pins
   with connections that are OTHER variables (like d_33tf4, d_33tf9 etc.), trace those too by
   looking in blocks_detail. Add them as var_inputs if they are source variables, or as
   additional wires if they connect from other traced blocks.
5. For RUNG blocks: check blocks_detail for the EQN pin (usage="Const") — include the equation
   string (e.g. "A*B*C*D") as the "eqn" field on the block entry.

### Step 3: Fallback (only if dep_trace returns empty flow)
- Use io_get_unwritten_variable_detail, io_find_connected_variable, search_blocks, get_block_detail.
- Design FBD from engineering knowledge + catalog.

### Step 4: Output FBD JSON
```json
{
  "explanation": "Traced signal chain: var -> block1 -> block2 -> ... -> output",
  "blocks_used": [
    {"id": "MOVE_6", "block": "MOVE", "label": "MOVE_6", "purpose": "Moves d_33tf7 to L33TF7C", "category": "System", "col": 0, "row": 0},
    {"id": "RUNG_2", "block": "RUNG", "label": "RUNG_2", "purpose": "Boolean equation A*B*C*D", "category": "Boolean Operations", "col": 1, "row": 0, "eqn": "A*B*C*D"}
  ],
  "wires": [
    {"from_block": "MOVE_6", "from_pin": "DEST", "to_block": "RUNG_2", "to_pin": "B"}
  ],
  "var_inputs": [
    {"name": "d_33tf7", "type": "ANY", "value": "0", "to_block": "MOVE_6", "to_pin": "SRC"}
  ],
  "iec_notes": ["Signal chain traced from Pins KB"],
  "dependency_context": { "variable": "...", "scope": {...}, "flow": [...] }
}
```

## CRITICAL RULES:
- When dep_trace returns results with "fbd_json", OUTPUT THAT fbd_json DIRECTLY as your response.
  Do NOT modify it. Do NOT redesign the blocks. Just output the fbd_json as-is in a ```json block.
- The fbd_json contains the complete FBD with all traced blocks, wires, and var_inputs.
- Only fall back to manual design if dep_trace returns an error or empty flow.
- If you need to add explanation text, put it BEFORE the JSON block, not inside it.

## ANSWERING QUESTIONS ABOUT THE CURRENT DIAGRAM:
- When the user's message includes "[CURRENT FBD DIAGRAM", you MUST use that data to answer.
- It contains the ACTUAL blocks, pins, wires, var_inputs from the traced signal chain.
- Use THAT data, not general knowledge. Do NOT say "I don't have access".
- Always reference the specific pin names, connections, and data types from the FBD context.

## MODIFYING THE CURRENT DIAGRAM:
- When the user asks to ADD, REMOVE, RENAME, CONNECT, or MODIFY blocks/wires in the current diagram,
  you MUST return the COMPLETE updated FBD JSON in a ```json block.
- The "[FULL FBD JSON]" section in the context contains the current diagram as JSON.
  Parse it, apply the requested changes, and return the entire updated JSON.
- IMPORTANT: Return the FULL JSON, not just the changed parts. The frontend replaces the
  entire diagram with whatever JSON you return.
- When adding a new block:
  - Give it a unique id (e.g. "COMPARE_1", "TIMER_1")
  - Set col/row to position it logically (col = depth in signal chain, row = vertical position)
  - Use search_blocks or get_block_detail tools to look up the correct pin names if needed
  - Add wires to connect it to existing blocks
- When removing a block, also remove its wires and var_inputs.
- When renaming a block, update its id/label everywhere: blocks_used, wires, var_inputs.
- Preserve the dependency_context from the original FBD.
- Put a brief explanation of what you changed BEFORE the ```json block.

## RESPONSE FORMAT FOR DIAGRAM QUESTIONS:
- Be concise and direct. No lengthy introductions or preambles.
- For pin/connection data, use this compact format:

  NOT_1:
    A (In) ← L3TFSTCK [BOOL]
    OUT_A (Out) → (none) [BOOL]
    NOT_A (Out) → L30TF_ALM [BOOL]

- Use ← for inputs and → for outputs. Show connection and data type in brackets.
- Keep explanations to 1-2 sentences max after the pin list.
- Do NOT use markdown tables — they don't render well in chat.
- Do NOT repeat information the user can already see in the diagram.
- Do NOT ask follow-up questions unless genuinely ambiguous.
- Do NOT offer numbered options or "Would you like me to..." suggestions.
"""


# ---- Agent factory ----

def _make_agent() -> Agent:
    """Create a Strands agent with all tools."""
    return Agent(
        model=Config.LITELLM_MODEL,
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
    )


def _make_agent_without_dep_trace() -> Agent:
    """Create a Strands agent without dep_trace (used when DynamoDB is down)."""
    return Agent(
        model=Config.LITELLM_MODEL,
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS_WITHOUT_DEP_TRACE,
    )


# ---- Request / Response models ----

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    enhancement_option: str | None = None


class IOReportUpload(BaseModel):
    session_id: str
    enhancement_option: str
    mappings: list[dict]
    unwritten_variables: list[dict] | None = None


# ---- Endpoints ----

@app.get("/health")
def health():
    return {"status": "ok", "blocks_loaded": len(VERIFIED_KB)}


@app.post("/chat")
async def chat(req: ChatRequest):
    """Non-streaming chat endpoint.

    If the message references a variable (d_xxx or a_xxx), run dep_trace
    directly and return the pre-built FBD JSON — bypassing the LLM for
    the diagram so it can't summarize or drop blocks.
    """
    import re
    sid = req.session_id or str(uuid.uuid4())
    set_current_session_id(sid)

    try:
        return _handle_chat(req, sid)
    except Exception as e:
        # Absolute last-resort catch — nothing should crash the endpoint
        print(f"[ERROR /chat] Unhandled exception: {e}")
        return {
            "session_id": sid,
            "response": "I encountered an internal error. Please try again.",
            "dynamodb_error": str(e),
        }


def _handle_chat(req, sid):
    """Inner chat handler — separated so the top-level try/except stays clean."""
    import re

    # Try to extract a variable name from the message
    # Only bypass to direct trace when the message is a trace/assign request,
    # not a general question about the diagram.
    # The proceedWithVariable message starts with "Assign logic for" — always bypass those.
    var_match = re.search(r'\b([da]_[A-Za-z0-9_]+)\b', req.message, re.IGNORECASE)
    is_assign = req.message.strip().lower().startswith("assign logic for")
    question_patterns = re.search(
        r'\b(what|why|how|explain|describe|tell me|can you|does|is it|which)\b',
        req.message[:60], re.IGNORECASE
    )
    is_question = question_patterns is not None and not is_assign

    dynamodb_error = None
    if var_match and not is_question:
        variable = var_match.group(1).lower()
        try:
            trace_result = trace_variable_from_dynamodb(variable)
        except Exception as e:
            trace_result = {'error': f'DynamoDB connection failed: {e}'}
        if "error" not in trace_result and trace_result.get("flow"):
            fbd = _build_fbd_from_trace(trace_result)
            if fbd and fbd.get("blocks_used"):
                # Store FBD in session for follow-up questions
                store_last_fbd(sid, fbd)
                print(f"[DEBUG /chat] BYPASS: stored FBD for sid={sid}, blocks={[b['id'] for b in fbd['blocks_used']]}")
                # Return the pre-built FBD directly — no LLM needed for the diagram
                fbd["source"] = "dynamodb"
                fbd_str = json.dumps(fbd, indent=2)
                return {
                    "session_id": sid,
                    "response": fbd_str,
                }
        # DynamoDB failed or returned empty — capture error for UI, fall through to LLM
        if "error" in trace_result:
            dynamodb_error = trace_result["error"]
            print(f"[DEBUG /chat] DynamoDB error: {dynamodb_error}, falling back to LLM")

    # Fallback: let the LLM agent handle it
    # Inject last FBD context so the agent can answer questions about the diagram
    last_fbd = get_last_fbd(sid)
    print(f"[DEBUG /chat] sid={sid}, last_fbd={'YES' if last_fbd else 'NONE'}, msg={req.message[:80]}")
    message = req.message
    if last_fbd:
        # Build a concise pin summary from the flow data
        flow = last_fbd.get("dependency_context", {}).get("flow", [])
        pin_summary_lines = []
        blocks_seen = set()
        for f in flow:
            b = f.get("block", "")
            if b not in blocks_seen:
                blocks_seen.add(b)
                block_pins = [
                    item for item in flow if item.get("block") == b
                ]
                btype = f.get("block_type", "")
                bexec = f.get("block_execution", "")
                pin_list = ", ".join(
                    f"{p['pin']}({p['usage']}, conn={p['connection']}, type={p['data_type']})"
                    for p in block_pins
                )
                pin_summary_lines.append(f"  {b} [type={btype}, execution={bexec}]: {pin_list}")

        pin_summary = "\n".join(pin_summary_lines)

        # Detect if user wants to modify the diagram
        modify_patterns = re.search(
            r'\b(add|remove|delete|rename|change|update|connect|disconnect|insert|move|replace)\b',
            req.message, re.IGNORECASE
        )

        # Always include the full FBD JSON so the LLM can return modified version
        fbd_json_str = json.dumps(last_fbd, indent=2)

        if modify_patterns:
            message = (
                f"[CURRENT FBD DIAGRAM — the user wants to MODIFY this diagram]\n"
                f"Blocks and their pins:\n{pin_summary}\n\n"
                f"[FULL FBD JSON — modify this and return the complete updated JSON]\n"
                f"```json\n{fbd_json_str}\n```\n\n"
                f"[USER REQUEST]\n{req.message}"
            )
        else:
            message = (
                f"[CURRENT FBD DIAGRAM — use this data to answer the user's question]\n"
                f"Blocks and their pins:\n{pin_summary}\n\n"
                f"Wires: {json.dumps(last_fbd.get('wires', []))}\n"
                f"Var inputs: {json.dumps(last_fbd.get('var_inputs', []))}\n"
                f"Explanation: {last_fbd.get('explanation', '')}\n\n"
                f"[USER QUESTION]\n{req.message}"
            )

    # When DynamoDB is down, tell the LLM to skip dep_trace and remove it
    # from the tool list so it can't call it and crash again.
    if dynamodb_error:
        message = (
            f"[IMPORTANT: The DynamoDB knowledge base is currently unavailable. "
            f"DO NOT call dep_trace — it will fail. Instead, use your block catalog "
            f"knowledge (search_blocks, get_block_detail) and the IO report tools to "
            f"design the FBD from engineering knowledge.]\n\n{message}"
        )
        agent = _make_agent_without_dep_trace()
    else:
        agent = _make_agent()

    try:
        result = agent(message)
        response_text = str(result)
    except Exception as e:
        err_str = str(e)
        print(f"[ERROR /chat] Agent/LLM call failed: {err_str}")
        # If the LLM itself can't be reached (e.g. same credential issue for Bedrock),
        # return a clear error — there's nothing to fall back to.
        response_data = {
            "session_id": sid,
            "response": (
                "Unable to reach the AI model. This is likely the same credential issue "
                "affecting DynamoDB. Please run `mwinit` to refresh your AWS credentials, "
                "then try again."
            ) if "credential" in err_str.lower() or "midway" in err_str.lower() else (
                f"The AI agent encountered an error: {err_str}"
            ),
        }
        if dynamodb_error:
            response_data["dynamodb_error"] = dynamodb_error
        return response_data

    # If the LLM response contains FBD JSON, store it for follow-up questions/modifications
    try:
        import re as _re
        json_match = _re.search(r'```json\s*([\s\S]*?)```', response_text)
        if json_match:
            parsed_fbd = json.loads(json_match.group(1))
        else:
            parsed_fbd = json.loads(response_text)
        if parsed_fbd.get("blocks_used"):
            parsed_fbd["source"] = "agent"
            store_last_fbd(sid, parsed_fbd)
            print(f"[DEBUG /chat] LLM returned FBD, stored for sid={sid}")
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass

    response_data = {
        "session_id": sid,
        "response": response_text,
    }
    if dynamodb_error:
        response_data["dynamodb_error"] = dynamodb_error
    return response_data


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming chat endpoint."""
    sid = req.session_id or str(uuid.uuid4())
    set_current_session_id(sid)

    async def event_generator():
        yield f"data: {json.dumps({'session_id': sid, 'type': 'start'})}\n\n"
        agent = _make_agent()
        try:
            result = agent(req.message)
            text = str(result)
            # Stream in chunks for responsiveness
            chunk_size = 80
            for i in range(0, len(text), chunk_size):
                chunk = text[i : i + chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/io/upload")
async def upload_io_report(data: IOReportUpload):
    """Upload parsed I/O report data into session memory."""
    save_session(
        session_id=data.session_id,
        enhancement_option=data.enhancement_option,
        mappings=data.mappings,
        unwritten_variables=data.unwritten_variables,
    )
    return {
        "session_id": data.session_id,
        "mappings_count": len(data.mappings),
        "unwritten_count": len(data.unwritten_variables or []),
    }


@app.post("/session/io-report")
async def session_io_report(data: IOReportUpload):
    """Frontend calls this to sync IO report + unwritten vars into session memory."""
    save_session(
        session_id=data.session_id,
        enhancement_option=data.enhancement_option,
        mappings=data.mappings,
        unwritten_variables=data.unwritten_variables,
    )
    return {
        "session_id": data.session_id,
        "mappings_count": len(data.mappings),
        "unwritten_count": len(data.unwritten_variables or []),
    }


@app.get("/blocks/categories")
def block_categories():
    """List block categories from the verified KB."""
    cats: dict[str, int] = {}
    for v in VERIFIED_KB.values():
        c = v.get("category", "Uncategorized")
        cats[c] = cats.get(c, 0) + 1
    return {"categories": cats, "total_blocks": len(VERIFIED_KB)}


@app.get("/blocks/search")
def block_search(q: str, category: str = ""):
    """Search blocks by keyword."""
    q_lower = q.lower()
    results = []
    for name, info in VERIFIED_KB.items():
        if category and info.get("category", "").lower() != category.lower():
            continue
        if q_lower in name.lower() or q_lower in info.get("description", "").lower():
            results.append({"name": name, **info})
    return {"results": results[:30], "total": len(results)}


@app.get("/blocks/{block_name}")
def block_detail(block_name: str):
    """Get full block detail."""
    info = VERIFIED_KB.get(block_name)
    if not info:
        raise HTTPException(404, f"Block '{block_name}' not found")
    return {"name": block_name, **info}

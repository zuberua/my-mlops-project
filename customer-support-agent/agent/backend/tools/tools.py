"""Strands tools for the Mark VIe FBD agent (with dependency tracing)."""
from __future__ import annotations

import json
from strands import tool

from agent.backend.tools.kb import VERIFIED_KB
from agent.backend.session_store import (
    get_mappings,
    get_enhancement_option,
    get_unwritten_variables,
    get_current_session_id,
)


@tool
def list_categories() -> str:
    """List all available block categories to guide search_blocks queries."""
    cats = sorted({b["category"] for b in VERIFIED_KB.values() if b["category"]})
    return json.dumps(cats)


_ALIASES: dict[str, list[str]] = {
    "relay":      ["latch", "and", "or", "not", "rung"],
    "ladder":     ["and", "or", "not", "latch", "rung"],
    "coil":       ["latch", "rung"],
    "contact":    ["and", "or", "not"],
    "seal":       ["latch"],
    "interlock":  ["and", "latch"],
    "permissive": ["and", "compare"],
    "trip":       ["compare", "latch"],
    "alarm":      ["compare", "latch"],
    "setpoint":   ["compare", "clamp"],
    "pid":        ["pid"],
    "ramp":       ["ratelim", "lag"],
    "delay":      ["timer", "tran_dly"],
    "count":      ["ctu", "ctd"],
    "average":    ["avrg"],
    "select":     ["select", "modsel"],
    "vote":       ["prevote", "median"],
}


@tool
def search_blocks(query: str, category: str = "") -> str:
    """Search the Mark VIe block catalog by keyword and optional category."""
    words = query.lower().split()
    expanded = set(words)
    for w in words:
        for alias, targets in _ALIASES.items():
            if alias in w:
                expanded.update(targets)
    cat = category.lower()
    results = []
    for name, block in VERIFIED_KB.items():
        haystack = f"{name} {block['category']} {block['description']}".lower()
        name_match = any(
            t == name.lower() or name.lower().startswith(t) for t in expanded
        )
        desc_match = any(t in haystack for t in expanded if len(t) > 3)
        if (name_match or desc_match) and (
            not cat or cat in block["category"].lower()
        ):
            results.append({
                "name": name,
                "category": block["category"],
                "description": block["description"],
            })
    return json.dumps(results[:20])


@tool
def get_block_detail(block_name: str) -> str:
    """Get the full input/output pin specification for a specific block."""
    block = VERIFIED_KB.get(block_name)
    if not block:
        return json.dumps({
            "error": f"Block '{block_name}' not found. Use search_blocks to find valid names."
        })
    return json.dumps({"name": block_name, **block})


@tool
def io_context_summary() -> str:
    """Summarize uploaded I/O report context available in current session memory."""
    mappings = get_mappings()
    option = get_enhancement_option()
    unwritten = get_unwritten_variables()
    return json.dumps({
        "enhancement_option": option,
        "mappings_count": len(mappings),
        "unwritten_variables_count": len(unwritten),
        "available": len(mappings) > 0,
    })


@tool
def io_find_connected_variable(device_tag: str) -> str:
    """Find connected variables for a given device tag from uploaded I/O report session memory."""
    query = device_tag.strip().lower()
    matches = []
    for m in get_mappings():
        tag = (m.get("device_tag") or "").strip()
        conn = (m.get("connected_variable") or "").strip()
        if not tag or not conn:
            continue
        if query in tag.lower():
            matches.append({"device_tag": tag, "connected_variable": conn})
    return json.dumps({"query": device_tag, "matches": matches[:100]})


@tool
def io_find_device_tag(connected_variable: str) -> str:
    """Find device tags for a given connected variable from uploaded I/O report session memory."""
    query = connected_variable.strip().lower()
    matches = []
    for m in get_mappings():
        tag = (m.get("device_tag") or "").strip()
        conn = (m.get("connected_variable") or "").strip()
        if not tag or not conn:
            continue
        if query in conn.lower():
            matches.append({"device_tag": tag, "connected_variable": conn})
    return json.dumps({"query": connected_variable, "matches": matches[:100]})


@tool
def io_list_unwritten_variables() -> str:
    """List unresolved variables extracted from CodingPracticeReport Unwritten Variables section."""
    vars_list = get_unwritten_variables()
    return json.dumps({"count": len(vars_list), "variables": vars_list[:500]})


@tool
def io_get_unwritten_variable_detail(variable: str) -> str:
    """Get details for specific unresolved variable (e.g., d_27es1 or a_xxx)."""
    q = variable.strip().lower()
    matches = []
    for item in get_unwritten_variables():
        key = (item.get("variable") or "").strip().lower()
        full_name = (item.get("full_variable") or "").strip().lower()
        if q == key or q in key or q in full_name:
            matches.append(item)
    return json.dumps({"query": variable, "matches": matches[:100]})


def _build_fbd_from_trace(trace_result: dict) -> dict:
    """Convert dep_trace output into a ready-to-render FBD JSON."""
    variable = trace_result.get("variable", "")
    flow = trace_result.get("flow", [])
    blocks_traversed = trace_result.get("blocks_traversed", [])

    if not flow:
        return {}

    # Group flow items by block
    block_pins: dict[str, list[dict]] = {}
    block_meta: dict[str, dict] = {}
    for item in flow:
        b = item["block"]
        block_pins.setdefault(b, []).append(item)
        if b not in block_meta:
            block_meta[b] = {
                "block_type": item["block_type"],
                "block_execution": item["block_execution"],
                "depth": item["depth"],
                "chain_order": item["chain_order"],
            }

    blocks_used = []
    row_at_depth: dict[int, int] = {}
    for block_name in blocks_traversed:
        meta = block_meta.get(block_name, {})
        bt = meta.get("block_type", "")
        depth = meta.get("depth", 0)
        row = row_at_depth.get(depth, 0)
        row_at_depth[depth] = row + 1

        # Find equation for RUNG blocks
        eqn = None
        for p in block_pins.get(block_name, []):
            if p["usage"] == "Const" and p["pin"] == "EQN":
                raw = p["connection"]
                eqn = raw.replace("N:", "") if raw.startswith("N:") else raw

        # Build purpose from pins
        inputs = [p for p in block_pins.get(block_name, []) if p["usage"] == "Input"]
        outputs = [p for p in block_pins.get(block_name, []) if p["usage"] == "Output"]
        in_conns = [p["connection"] for p in inputs if p["connection"]]
        out_conns = [p["connection"] for p in outputs if p["connection"]]
        purpose = f"{bt}: {', '.join(in_conns)} -> {', '.join(out_conns)}"

        # Look up category from block catalog, fall back to "System"
        kb_entry = VERIFIED_KB.get(bt, {})
        category = kb_entry.get("category", "System") if kb_entry else "System"

        entry: dict = {
            "id": block_name,
            "block": bt,
            "label": block_name,
            "purpose": purpose,
            "category": category,
            "col": depth,
            "row": row,
        }
        if eqn:
            entry["eqn"] = eqn
        blocks_used.append(entry)

    # Build wires: match Output connections to Input connections across blocks
    # output_map: connection_name -> (block_id, pin_name)
    output_map: dict[str, tuple[str, str]] = {}
    for block_name in blocks_traversed:
        for p in block_pins.get(block_name, []):
            if p["usage"] == "Output" and p["connection"]:
                output_map[p["connection"]] = (block_name, p["pin"])

    wires = []
    for block_name in blocks_traversed:
        for p in block_pins.get(block_name, []):
            if p["usage"] == "Input" and p["connection"]:
                conn = p["connection"]
                if conn in output_map:
                    src_block, src_pin = output_map[conn]
                    if src_block != block_name:
                        wires.append({
                            "from_block": src_block,
                            "from_pin": src_pin,
                            "to_block": block_name,
                            "to_pin": p["pin"],
                        })

    # Build var_inputs: Input pins whose connection is NOT from another traced block's output
    var_inputs = []
    seen_vars: set[str] = set()
    for block_name in blocks_traversed:
        for p in block_pins.get(block_name, []):
            if p["usage"] == "Input" and p["connection"]:
                conn = p["connection"]
                if conn not in output_map and not conn.startswith("N:") and not conn.startswith("E:"):
                    key = f"{conn}|{block_name}|{p['pin']}"
                    if key not in seen_vars:
                        seen_vars.add(key)
                        var_inputs.append({
                            "name": conn,
                            "type": p["data_type"] or "BOOL",
                            "value": "0",
                            "to_block": block_name,
                            "to_pin": p["pin"],
                        })

    return {
        "explanation": f"Signal chain traced from Pins KB for {variable}: {' -> '.join(blocks_traversed)}",
        "blocks_used": blocks_used,
        "wires": wires,
        "var_inputs": var_inputs,
        "iec_notes": [
            f"Traced {len(blocks_traversed)} blocks: {' -> '.join(blocks_traversed)}",
            "All blocks and wiring from verified Pins KB dependency trace",
        ],
        "dependency_context": {
            "variable": variable,
            "scope": trace_result.get("scope", {}),
            "flow": flow,
        },
    }


@tool
def dep_trace(variable: str) -> str:
    """Run scope-aware directional trace for 'variable' using DynamoDB GSI3 queries.
    Returns the trace data AND a pre-built FBD JSON ready for rendering.
    The agent should output the fbd_json directly as the response.
    """
    from agent.backend.tools.dynamodb_kb import trace_variable_from_dynamodb

    try:
        res = trace_variable_from_dynamodb(variable)
    except Exception as e:
        return json.dumps({'error': f'DynamoDB connection failed: {e}'})
    if 'error' in res:
        return json.dumps(res)
    fbd = _build_fbd_from_trace(res)
    res['fbd_json'] = fbd
    return json.dumps(res)


@tool
def query_task_pins(pk: str) -> str:
    """Query all pins for a (project, task) partition key from the pins DynamoDB table.

    Args:
        pk: The partition key, e.g. SYS#TVA CUMBERLAND|DEV#G1|PG#Custom|PROG#Custom|TASK#TempMonitor

    Returns:
        JSON with pins list, signals_in, signals_out, block_types_used, and row_count.
    """
    import boto3
    from boto3.dynamodb.conditions import Key as DKey
    from agent.backend.config import Config

    dynamodb = boto3.resource("dynamodb", region_name=Config.AWS_REGION)
    table = dynamodb.Table(Config.DYNAMODB_TABLE_NAME)

    items = []
    response = table.query(KeyConditionExpression=DKey("PK").eq(pk))
    items.extend(response["Items"])
    while response.get("LastEvaluatedKey"):
        response = table.query(
            KeyConditionExpression=DKey("PK").eq(pk),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response["Items"])

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
        for p in items[:100]
    ]

    return json.dumps({
        "pk": pk,
        "row_count": len(items),
        "signals_in": sorted(signals_in),
        "signals_out": sorted(signals_out),
        "block_types_used": sorted(block_types),
        "pins_sample": pins_compact,
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
) -> str:
    """Write a task logic summary to the task-summaries DynamoDB table.

    Args:
        pk: Summary partition key, e.g. PROJECT#TVA_CUMBERLAND_G1#TASK#TempMonitor
        project_id: Project identifier, e.g. TVA_CUMBERLAND_G1
        task: Task name
        program: Program name
        signals_in: List of unique input connection strings
        signals_out: List of unique output connection strings
        block_types_used: List of unique block type values
        logic_summary: Engineering description of the task logic
        row_count: Total pin rows in the task

    Returns:
        JSON confirmation.
    """
    import boto3
    from datetime import datetime, timezone
    from agent.backend.config import Config

    dynamodb = boto3.resource("dynamodb", region_name=Config.AWS_REGION)
    table = dynamodb.Table(Config.TASK_SUMMARY_TABLE_NAME)
    now = datetime.now(timezone.utc).isoformat()

    table.put_item(Item={
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
    })

    return json.dumps({"status": "written", "pk": pk, "computed_at": now})


TOOLS = [
    list_categories,
    search_blocks,
    get_block_detail,
    io_context_summary,
    io_find_connected_variable,
    io_find_device_tag,
    io_list_unwritten_variables,
    io_get_unwritten_variable_detail,
    dep_trace,
    query_task_pins,
    write_task_summary,
]

TOOLS_WITHOUT_DEP_TRACE = [
    list_categories,
    search_blocks,
    get_block_detail,
    io_context_summary,
    io_find_connected_variable,
    io_find_device_tag,
    io_list_unwritten_variables,
    io_get_unwritten_variable_detail,
    query_task_pins,
    write_task_summary,
]

"""DynamoDB-backed pin knowledge base for dependency tracing.

Queries the markvie-kb DynamoDB table using GSI3 (ConnectionIndex) for
efficient BFS tracing. Each hop costs ~0.5 RCU instead of a full table scan.

Adapted from: my-mlops-project/dynamodb-block-schema/scripts/trace_connection.py
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

from agent.backend.config import Config

_table = None


def _get_table():
    """Lazy-init DynamoDB table resource.

    Returns the table resource. Credential/connection errors will surface
    during actual queries and are caught by callers.
    """
    global _table
    if _table is None:
        try:
            dynamodb = boto3.resource('dynamodb', region_name=Config.AWS_REGION)
            _table = dynamodb.Table(Config.DYNAMODB_TABLE_NAME)
        except Exception as e:
            raise RuntimeError(f"Cannot init DynamoDB table '{Config.DYNAMODB_TABLE_NAME}': {e}") from e
    return _table


def _query_gsi3(table, connection: str, usage_prefix: str = None) -> List[Dict]:
    """Query ConnectionIndex GSI for pins matching a connection name."""
    kce = Key('GSI3PK').eq(f'CONN#{connection}')
    if usage_prefix:
        kce = kce & Key('GSI3SK').begins_with(f'USE#{usage_prefix}')

    items = []
    response = table.query(IndexName='ConnectionIndex', KeyConditionExpression=kce)
    items.extend(response['Items'])
    while response.get('LastEvaluatedKey'):
        response = table.query(
            IndexName='ConnectionIndex',
            KeyConditionExpression=kce,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response['Items'])
    return items


def _query_block_pins(table, pk: str, block_execution, block_name: str) -> List[Dict]:
    """Get ALL pins for a specific block by querying the base table."""
    prefix = f'BEX#{int(block_execution):04d}|BLK#{block_name}'
    response = table.query(
        KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(prefix)
    )
    return response['Items']


def trace_chain_gsi3(start_connection: str, max_depth: int = 10) -> Dict[str, List[Dict]]:
    """Trace the full signal chain using GSI3 queries (BFS per scope).

    1. Queries GSI3 to find all Input pins consuming the variable
    2. Groups by PK (project scope) — each scope traced independently
    3. BFS: fetches all pins per block, follows Output connections
    4. Returns {scope_pk: [chain_items]}
    """
    table = _get_table()
    results = {}

    # SEED — find where start_connection is consumed as Input
    seed_items = _query_gsi3(table, start_connection, usage_prefix='Input')
    if not seed_items:
        return results

    # Group by project scope (PK)
    scopes: Dict[str, List[Dict]] = {}
    for item in seed_items:
        scopes.setdefault(item['PK'], []).append(item)

    # BFS per scope
    for scope_pk, scope_seeds in scopes.items():
        visited_connections = {start_connection}
        visited_blocks = set()
        chain = []
        queue = [(start_connection, 0)]

        while queue:
            connection, depth = queue.pop(0)
            if depth > max_depth:
                continue

            input_items = _query_gsi3(table, connection, usage_prefix='Input')
            input_items = [i for i in input_items if i['PK'] == scope_pk]

            for item in input_items:
                block = item['Block']
                bex = item['BlockExecution']
                block_key = (scope_pk, bex, block)

                if block_key in visited_blocks:
                    continue
                visited_blocks.add(block_key)

                # Get ALL pins for this block
                block_pins = _query_block_pins(table, scope_pk, bex, block)

                for pin in block_pins:
                    chain.append({
                        'depth': depth,
                        'connection': pin.get('Connection', ''),
                        'block': pin['Block'],
                        'block_type': pin.get('BlockType', ''),
                        'block_execution': str(pin.get('BlockExecution', '')),
                        'pin': pin['Pin'],
                        'pin_description': pin.get('PinDescription', ''),
                        'usage': pin['Usage'],
                        'data_type': pin.get('DataType', ''),
                        'project_context': scope_pk,
                    })

                    if pin['Usage'] == 'Output':
                        out_conn = pin.get('Connection', '').strip()
                        if out_conn and out_conn not in visited_connections:
                            visited_connections.add(out_conn)
                            queue.append((out_conn, depth + 1))

        # Sort by depth then block execution order
        chain.sort(
            key=lambda x: (
                x['depth'],
                int(x['block_execution']) if x['block_execution'].isdigit() else 0,
            )
        )
        results[scope_pk] = chain

    return results


def trace_variable_from_dynamodb(variable: str) -> Dict[str, Any]:
    """Trace a variable using DynamoDB and return in the same format as
    trace_variable_from_session() so the FBD builder works unchanged.

    Returns:
        Dict with keys: variable, scope, flow, blocks_traversed
        Or dict with 'error' key on failure.
    """
    global _table

    if not Config.DYNAMODB_TABLE_NAME:
        return {'error': 'DYNAMODB_TABLE_NAME not configured'}

    try:
        results = trace_chain_gsi3(variable)
    except Exception as e:
        # Reset cached table so next call retries fresh credentials
        _table = None
        return {'error': f'DynamoDB query failed: {e}'}

    if not results:
        return {'error': f'No connections found for {variable} in DynamoDB'}

    # Use the first scope (most common case — single project)
    scope_pk = next(iter(results))
    chain = results[scope_pk]

    if not chain:
        return {'error': f'Empty chain for {variable}'}

    # Build ordered block list
    blocks_ordered: List[str] = []
    block_depth: Dict[str, int] = {}
    for item in chain:
        b = item['block']
        if b not in block_depth:
            block_depth[b] = item['depth']
            blocks_ordered.append(b)

    # Build flat flow in the same format as trace_variable_from_session
    flat_flow: List[Dict[str, Any]] = []
    for order, block_name in enumerate(blocks_ordered, 1):
        depth = block_depth[block_name]
        block_pins = [i for i in chain if i['block'] == block_name]
        for p in block_pins:
            flat_flow.append({
                'chain_order': order,
                'depth': depth,
                'traced_connection': variable,
                'pin': p['pin'],
                'pin_description': p['pin_description'],
                'block': block_name,
                'block_type': p['block_type'],
                'block_execution': p['block_execution'],
                'connection': p['connection'],
                'data_type': p['data_type'],
                'usage': p['usage'],
            })

    return {
        'variable': variable,
        'scope': {
            'project_context': scope_pk,
        },
        'flow': flat_flow,
        'blocks_traversed': blocks_ordered,
    }

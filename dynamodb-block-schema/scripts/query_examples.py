#!/usr/bin/env python3
"""
Example queries demonstrating all access patterns.

Usage:
    python query_examples.py --profile zuberua-Admin
"""

import argparse
import boto3
from boto3.dynamodb.conditions import Key


def setup(args):
    session_kwargs = {'region_name': args.region}
    if args.profile:
        session_kwargs['profile_name'] = args.profile
    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource('dynamodb')
    return dynamodb.Table(args.table)


SAMPLE_PK = 'SYS#TVA CUMBERLAND|DEV#G1|PG#Custom|PROG#Custom|TASK#ProjectSpecific'


def ap1_all_pins_in_task(table):
    """AP1: Get all pins in a task, returned in execution order."""
    print('\n--- AP1: All pins in task (execution order) ---')
    resp = table.query(KeyConditionExpression=Key('PK').eq(SAMPLE_PK))
    for item in resp['Items']:
        print(f"  BEX:{item['BlockExecution']:3d} | {item['Block']:15s}.{item['Pin']:10s} | {item['Usage']:6s} | {item['DataType']}")
    print(f'  Total: {resp["Count"]} items')


def ap2_pins_at_execution_step(table, step=2):
    """AP2: Get all pins at a specific execution step."""
    print(f'\n--- AP2: All pins at execution step {step} ---')
    resp = table.query(
        KeyConditionExpression=Key('PK').eq(SAMPLE_PK) & Key('SK').begins_with(f'BEX#{step:04d}')
    )
    for item in resp['Items']:
        print(f"  {item['Block']:15s}.{item['Pin']:10s} | {item['Usage']:6s} | {item.get('Connection', '')}")


def ap3_pins_for_block(table, block='MOVE_6', step=2):
    """AP3: Get all pins for a specific block."""
    print(f'\n--- AP3: All pins for {block} ---')
    resp = table.query(
        KeyConditionExpression=Key('PK').eq(SAMPLE_PK) & Key('SK').begins_with(f'BEX#{step:04d}|BLK#{block}')
    )
    for item in resp['Items']:
        print(f"  {item['Pin']:10s} | {item['Usage']:6s} | {item['DataType']:6s} | {item.get('Connection', '')}")


def ap5_blocks_by_type(table, block_type='MOVE'):
    """AP5: Find all blocks of a type across all projects."""
    print(f'\n--- AP5: All {block_type} blocks (cross-project) ---')
    resp = table.query(
        IndexName='BlockTypeIndex',
        KeyConditionExpression=Key('GSI1PK').eq(f'TYPE#{block_type}')
    )
    for item in resp['Items']:
        print(f"  {item.get('System', '?'):20s} | {item['Block']:15s}.{item['Pin']:10s} | {item['Usage']}")
    print(f'  Total: {resp["Count"]} items')


def ap6_inputs_by_type(table, block_type='MOVE', usage='Input'):
    """AP6: Find all input pins for a block type."""
    print(f'\n--- AP6: All {usage} pins for {block_type} blocks ---')
    resp = table.query(
        IndexName='BlockTypeIndex',
        KeyConditionExpression=Key('GSI1PK').eq(f'TYPE#{block_type}') & Key('GSI1SK').begins_with(f'USE#{usage}')
    )
    for item in resp['Items']:
        print(f"  {item['Block']:15s}.{item['Pin']:10s} | {item.get('Connection', '')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--table', default='MarkvleBlockPins-production')
    parser.add_argument('--region', default='us-west-2')
    parser.add_argument('--profile', default=None)
    args = parser.parse_args()

    table = setup(args)

    ap1_all_pins_in_task(table)
    ap2_pins_at_execution_step(table, step=2)
    ap3_pins_for_block(table, 'MOVE_6', step=2)
    ap5_blocks_by_type(table, 'MOVE')
    ap6_inputs_by_type(table, 'MOVE', 'Input')


if __name__ == '__main__':
    main()

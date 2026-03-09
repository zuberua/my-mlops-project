# DynamoDB Schema Design — Mark Vle Block Pin Configuration

## Data Entity Summary

Each record represents a **Pin** belonging to a **Block**, within a **System/Device/Program/Task** hierarchy.

| Field           | Example | Cardinality |
|-----------------|---------------------------------------|------------------------------|
| System          | TVA CUMBERLAND                        | Few (one per plant)          |
| Device          | G1                                    | Few persystem                | 
| ProgramGroup    | Custom                                | Few per device               |
| Program         | Custom                                | Few per program group        |
| Task            | ProjectSpecific                       | Few per program              |
| Block           | MOVE_6, RUNG_2, NOT_1, COMPARE_2      | Hundreds per task            |
| Pin             | SRC, ENABLE, DEST, EQN, OUT, A, B     | ~10-20 unique pin names.     |
| Block Type      | MOVE, RUNG, NOT, COMPARE, _COMMENT    | ~20-30 types                 |
| Block Execution | 2, 3, 4, 5...                         | Execution order within task  |
| Usage           | Input, Output, Const                  | 3 values                     |
| Data Type       | BOOL, ANY, STRING, REAL, INT          | ~5-10 types                  |
| Entry No        | 191, 192, 193...                      | Unique within a project file |
| Locator         | System:TVA CUMBERLAND\|Device:G1\|... | Unique per pin globally      |

## Multi-Project Support

Multiple projects (systems/devices) will upload data to the same table. `EntryNo` is NOT globally unique — it can repeat across projects. The `Locator` field is globally unique since it encodes the full hierarchy path.

The key design scopes data by project context (System + Device + ProgramGroup + Program + Task) in the partition key, ensuring complete data isolation between projects.

## Key Uniqueness — Composite Primary Key

DynamoDB uses a composite primary key (PK + SK). The PK alone does not need to be unique — it is the combination of PK and SK that uniquely identifies each item.

Multiple items share the same PK when they belong to the same program/task context. This creates an item collection that can be fetched in a single query.

For example, all pins in task `ProjectSpecific` under program `Custom` share the same PK but have distinct sort keys:

| PK | SK | Unique? |
|---|---|---|
| `SYS#TVA CUMBERLAND\|DEV#G1\|PG#Custom\|PROG#Custom\|TASK#ProjectSpecific` | `BEX#0002\|BLK#MOVE_6\|PIN#SRC\|USE#Input` | ✓ |
| `SYS#TVA CUMBERLAND\|DEV#G1\|PG#Custom\|PROG#Custom\|TASK#ProjectSpecific` | `BEX#0002\|BLK#MOVE_6\|PIN#ENABLE\|USE#Input` | ✓ |
| `SYS#TVA CUMBERLAND\|DEV#G1\|PG#Custom\|PROG#Custom\|TASK#ProjectSpecific` | `BEX#0002\|BLK#MOVE_6\|PIN#DEST\|USE#Output` | ✓ |

## Access Patterns

| # | Access Pattern | Key Condition |
|-----|--------------------------------------------|-----------------------------------------------------|
| AP1 | Get all pins in a task (execution order)   | PK = `SYS#...\|TASK#ProjectSpecific`                |
| AP2 | Get all pins at a specific execution step  | PK + SK `begins_with('BEX#0002')`                   |
| AP3 | Get all pins for a specific block          | PK + SK `begins_with('BEX#0002\|BLK#MOVE_6')`       |
| AP4 | Get a specific pin                         | PK + full SK                                        |
| AP5 | Find all blocks of a type across projects  | GSI1: PK = `TYPE#MOVE`                              |
| AP6 | Find all pins by usage across a block type | GSI1: PK = `TYPE#MOVE`, SK `begins_with('USE#Input'`|
| AP7 | Lookup by locator (globally unique)        | GSI2: PK = `LOC#{Locator}`                          |

## Table Design

### Primary Key

```
PK: SYS#{System}|DEV#{Device}|PG#{ProgramGroup}|PROG#{Program}|TASK#{Task}
SK: BEX#{BlockExecution_padded}|BLK#{Block}|PIN#{Pin}|USE#{Usage}
```

The PK groups all pins within a program/task context.
The SK orders by execution step, then block, then pin — so a query on PK returns items in the natural program execution order.

### GSI1 — BlockTypeIndex (cross-project queries by block type)

```
GSI1PK: TYPE#{BlockType}
GSI1SK: USE#{Usage}|SYS#{System}|DEV#{Device}|BLK#{Block}|PIN#{Pin}
```

Enables: "Find all MOVE blocks across all projects" or "Find all Input pins for COMPARE blocks."

### GSI2 — LocatorIndex (globally unique lookup)

```
GSI2PK: LOC#{Locator}
GSI2SK: -
```

Enables: Direct lookup by the full locator path, which is globally unique.

### Item Example

```json
{
  "PK": "SYS#TVA CUMBERLAND|DEV#G1|PG#Custom|PROG#Custom|TASK#ProjectSpecific",
  "SK": "BEX#0002|BLK#MOVE_6|PIN#SRC|USE#Input",
  "GSI1PK": "TYPE#MOVE",
  "GSI1SK": "USE#Input|SYS#TVA CUMBERLAND|DEV#G1|BLK#MOVE_6|PIN#SRC",
  "GSI2PK": "LOC#System:TVA CUMBERLAND|Device:G1|ProgramGroup:Custom|Program:Custom|Block:ProjectSpecific|Block:MOVE_6|PinVariable:SRC",
  "GSI2SK": "-",
  "Pin": "SRC",
  "PinDescription": "Source variable",
  "Block": "MOVE_6",
  "BlockType": "MOVE",
  "BlockExecution": 2,
  "Connection": "d_33tf7",
  "DataType": "ANY",
  "EntryNo": 191,
  "IsCritical": false,
  "Usage": "Input",
  "Locator": "System:TVA CUMBERLAND|Device:G1|ProgramGroup:Custom|Program:Custom|Block:ProjectSpecific|Block:MOVE_6|PinVariable:SRC"
}
```

## Capacity Estimation

Assuming ~10,000 blocks with avg 5 pins each = ~50,000 pin items per project.
With 10 projects: ~500,000 items. Average item size: ~600 bytes → ~300 MB total.
Well within DynamoDB on-demand pricing sweet spot.

## Indexes Summary

| Index | PK | SK | Projection |
|-----------------------|--------|--------|-----|
| Base Table            | PK     | SK     | ALL |
| GSI1 (BlockTypeIndex) | GSI1PK | GSI1SK | ALL |
| GSI2 (LocatorIndex)   | GSI2PK | GSI2SK | ALL |

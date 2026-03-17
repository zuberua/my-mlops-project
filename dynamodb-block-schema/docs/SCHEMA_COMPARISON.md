# DynamoDB Schema Comparison

Two schema designs for storing Mark VIe pin/block data in DynamoDB.

---

## 1. Pin-Level Schema (`dynamodb-block-schema`) — RECOMMENDED

### Definition

One DynamoDB item per CSV row. Each pin is a standalone item with all attributes
as top-level fields. Uses GSI3 (ConnectionIndex) to enable efficient connection
tracing across all project scopes.

### How Items Are Stored

```
CSV Input (e.g37 rows):
  Pin,Block,Task,System,Connection,Usage,...
  SRC,MOVE_1,TempMonitor,GREENLAND POWER,v_8a2x9,Input,...
  DEST,MOVE_1,TempMonitor,GREENLAND POWER,M_tmp_raw,Output,...
  ...

DynamoDB Output (37 items):

Item 1:
  PK: SYS#GREENLAND POWER|DEV#T1|PG#Logic|PROG#Logic|TASK#TempMonitor
  SK: BEX#0002|BLK#MOVE_1|PIN#SRC|USE#Input
  GSI3PK: CONN#v_8a2x9
  GSI3SK: USE#Input|BLK#MOVE_1|PIN#SRC
  Pin: SRC
  Block: MOVE_1
  Connection: v_8a2x9
  Usage: Input
  BlockType: MOVE
  DataType: ANY
  Task: TempMonitor
  System: GREENLAND POWER
  ...

Item 2:
  PK: SYS#GREENLAND POWER|DEV#T1|PG#Logic|PROG#Logic|TASK#TempMonitor
  SK: BEX#0002|BLK#MOVE_1|PIN#DEST|USE#Output
  GSI3PK: CONN#M_tmp_raw
  GSI3SK: USE#Output|BLK#MOVE_1|PIN#DEST
  Pin: DEST
  Block: MOVE_1
  Connection: M_tmp_raw
  Usage: Output
  ...
```

37 CSV rows = 37 DynamoDB items. Each item has GSI3PK/GSI3SK attributes
that DynamoDB automatically indexes in the ConnectionIndex GSI.

### How Querying Works

**Find all pins using connection `v_8a2x9` across all project scopes:**

```python
# Single GSI3 query — returns all matching pins from every scope
response = table.query(
    IndexName='ConnectionIndex',
    KeyConditionExpression=Key('GSI3PK').eq('CONN#v_8a2x9')
)

# Result: 5 items (one from each scope that uses v_8a2x9)
# GREENLAND POWER / TempMonitor / MOVE_1.SRC (Input)
# GREENLAND POWER / PressureCalc / ADD_5.IN1 (Input)
# NORDIC HYDRO / FlowBalance / MUL_8.A (Input)
# NORDIC HYDRO / VoltageGuard / SUB_6.IN1 (Input)
# PACIFIC WIND / SpeedRegulator / SCALE_9.SRC (Input)
```

**Find only Input pins for a connection:**

```python
response = table.query(
    IndexName='ConnectionIndex',
    KeyConditionExpression=(
        Key('GSI3PK').eq('CONN#v_8a2x9') &
        Key('GSI3SK').begins_with('USE#Input')
    )
)
```

**Get all pins within a scope (e.g. TempMonitor in GREENLAND POWER):**

```python
response = table.query(
    KeyConditionExpression=Key('PK').eq(
        'SYS#GREENLAND POWER|DEV#T1|PG#Logic|PROG#Logic|TASK#TempMonitor'
    )
)
# Returns all pins for that task, ordered by block execution
```

### How Trace Connection Works

BFS trace starting from `v_8a2x9`:

```
Step 1: Query GSI3 for CONN#v_8a2x9 (Input pins only)
        → Found in 5 scopes. For each scope, get the block, then
          fetch all pins for that block to find Output connections.

Step 2: GREENLAND POWER / TempMonitor scope:
        MOVE_1.SRC consumes v_8a2x9 (Input)
        MOVE_1.DEST produces M_tmp_raw (Output) → follow this

Step 3: Query GSI3 for CONN#M_tmp_raw (Input pins only)
        → AND_1.A consumes M_tmp_raw
        → AND_1.OUT produces M_tmp_alarm → follow this

Step 4: Query GSI3 for CONN#M_tmp_alarm
        → No consumers found → END OF CHAIN

Result for GREENLAND POWER / TempMonitor:
  v_8a2x9 → MOVE_1 → M_tmp_raw → AND_1 → M_tmp_alarm (end)
  3 GSI3 queries, 0 scans
```

Each scope is traced independently. Total for all 5 scopes: ~7 GSI3 queries.

### Performance at Scale (5M items)

```
Trace v_8a2x9 across 10 scopes, 3-block chain per scope:

Queries:        ~7 GSI3 queries (one per BFS hop)
Items read:     ~25 (only matching pins — 4,999,975 items untouched)
Data read:      ~12.5 KB
RCU cost:       ~4 RCU (eventually consistent)
Latency:        <100ms total
```

Performance is identical at 37 items or 5 million. GSI3 partitions by
connection ID and reads only matching items — table size is irrelevant.

### Cost at Scale (5M items, 1,000 traces/day)

```
Storage:        5M items × 500 bytes avg = ~2.5 GB
                + GSI3 replica = ~5 GB total
                Cost: ~$1.25/month ($0.25/GB)

Reads:          1,000 traces × ~4 RCU = ~4,000 RCU/day
                = ~120,000 RCU/month
                Cost: ~$0.04/month (on-demand @ $0.25/M RCU)

Writes:         Ingestion: 5M items × 2 WCU each (base + GSI3) = 10M WCU
                One-time cost: ~$12.50 (on-demand @ $1.25/M WCU)
                Incremental: per CSV upload, ~37 WCU per file

Total monthly:  ~$1.29/month (storage + reads, after initial ingestion)
```

### Pros

- Every pin is directly indexed by connection — GSI3 query returns exact matches
- Cross-scope tracing in one query (all scopes returned together)
- O(matches) cost — same performance at 100 items or 10 million items
- Each pin is independently updatable without touching other items
- Simple flat data model — no nested maps to navigate
- BFS trace uses only GSI3 queries, no scans

### Cons

- Item count equals CSV row count (37 rows = 37 items)
- Each write also writes to GSI3 (2 writes per row during ingestion)
- No built-in task-level grouping (need PK query to assemble a task's pins)

---

## 2. Task Schema (`dynamodb-task-schema`)

### Definition

Groups all pins by task into a single DynamoDB item. All pin data is stored
in a nested `pins` map attribute. Dramatically reduces item count but loses
the ability to index individual pins or connections.

### How Items Are Stored

```
CSV Input (37 rows):
  Same 37 rows as above, spanning 5 tasks

DynamoDB Output (5 items):

Item 1:
  PK: TempMonitor#GREENLAND POWER
  SK: v_8a2x9|M_tmp_raw|v_arm_temp       (first 3 unique connections)
  GSI3PK: CONN#v_8a2x9                   (first connection only)
  GSI3SK: TASK#TempMonitor#SYS#GREENLAND POWER
  Task: TempMonitor
  System: GREENLAND POWER
  PinCount: 6
  pins:
    pin_0:
      Pin: SRC
      Block: MOVE_1
      Connection: v_8a2x9
      Usage: Input
      DataType: ANY
    pin_1:
      Pin: ENABLE
      Block: MOVE_1
      Connection: ""
      Usage: Input
      DataType: BOOL
    ...
```

37 CSV rows = 5 DynamoDB items. All pins for a task are nested inside one item.

### How Querying Works

**Get all pins for a task (efficient):**

```python
# Single GetItem — returns the entire task with all pins
response = table.get_item(
    Key={'PK': 'TempMonitor#GREENLAND POWER', 'SK': 'v_8a2x9|M_tmp_raw|v_arm_temp'}
)
# Result: 1 item containing 6 pins in the pins map
```

**Find all pins using connection `v_8a2x9` across all scopes (problematic):**

```python
# GSI3 query — only finds tasks where v_8a2x9 is the FIRST connection
response = table.query(
    IndexName='ConnectionIndex',
    KeyConditionExpression=Key('GSI3PK').eq('CONN#v_8a2x9')
)
# Result: Maybe 2-3 tasks (not all 5 scopes)
# MISSING: Tasks where v_8a2x9 is the 2nd or 3rd connection

# Fallback: Full table scan + app-side filtering
response = table.scan()
for item in response['Items']:
    for pin_key, pin_data in item.get('pins', {}).items():
        if pin_data.get('Connection') == 'v_8a2x9':
            print(f"Found in {item['PK']}: {pin_data}")
# At 10K tasks: reads entire table, iterates every pin in every map
```

### How Trace Connection Works

BFS trace starting from `v_8a2x9`:

```
Step 1: Query GSI3 for CONN#v_8a2x9
        → Returns tasks where v_8a2x9 is the first connection
        → MISSES tasks where it's not first

Step 2: Fallback — scan entire table
        → Read all 5 items (or thousands at scale)
        → For each item, iterate through pins map
        → Check if any pin has Connection = v_8a2x9
        → Found in TempMonitor, PressureCalc, FlowBalance, VoltageGuard, SpeedRegulator

Step 3: Extract output connections from matched pins
        → But outputs are buried in the same pins map
        → More iteration needed to find them

Step 4: For each output connection (M_tmp_raw, M_prs_total, etc.)
        → Repeat full scan + filter for each one
        → Another full table scan per hop

Result for all scopes:
  4+ full table scans, iterate all pins maps each time
  At 10K tasks with ~50K pins total: seconds to minutes
```

### Performance at Scale (5M pins → ~100K task items)

```
Trace v_8a2x9 across 10 scopes, 3-block chain per scope:

Queries:        ~4 full table scans (one per BFS hop)
Items read:     ALL 100K items per scan = 400K items total
Data read:      100K × 2KB avg = ~200MB per scan × 4 = ~800MB
RCU cost:       ~50,000 RCU per scan × 4 = ~200,000 RCU per trace
Latency:        5-30 seconds per trace (sequential scans + app-side filtering)
```

Every trace reads the entire table multiple times. At 500K task items,
each scan costs 250K RCU. Performance degrades linearly with table size.

### Cost at Scale (5M pins → ~100K task items, 1,000 traces/day)

```
Storage:        100K items × 2KB avg = ~200 MB
                + GSI3 replica = ~400 MB total
                Cost: ~$0.10/month ($0.25/GB)

Reads:          1,000 traces × ~200,000 RCU = 200M RCU/day
                = ~6B RCU/month
                Cost: ~$1,500/month (on-demand @ $0.25/M RCU)

                With provisioned capacity (cheaper but requires planning):
                ~2,315 RCU sustained = ~$438/month

Writes:         Ingestion: 100K items × 1 WCU each = 100K WCU
                One-time cost: ~$0.13
                Incremental: ~5 WCU per CSV upload

Total monthly:  ~$438-$1,500/month (dominated by scan reads)
```

Storage is cheap ($0.10/month) but the scan-based reads destroy the savings.
At 1,000 traces/day the read cost alone is 1,000x more than Pin-Level.

### Pros

- Fewest items (37 rows → 5 items)
- Single GetItem returns all pins for a task — no assembly needed
- Lowest write cost during ingestion (5 PutItems vs 37)
- Natural task-level grouping

### Cons

- DynamoDB cannot index inside map attributes — pins are invisible to GSI3
- GSI3 only indexes the first connection per task — misses most connections
- Connection tracing requires full table scans at every BFS hop
- Does not scale — scan cost grows linearly with table size
- 400KB item size limit — large tasks with hundreds of pins may exceed this
- Updating one pin requires reading and rewriting the entire item
- App-side filtering needed for every connection lookup

---

## Summary

| | Pin-Level | Task |
|---|---|---|
| Items (37 rows) | 37 | 5 |
| GSI3 tracing | Full | Broken |
| Scan required | Never | Every hop |
| Query per trace hop | 1 GSI3 | 1 scan + filter |
| Scales to millions | Yes | No |
| Complexity | Simple | Simple |
| Best for | Connection tracing | Task-level reads only |

---

## Key Uniqueness

DynamoDB requires that the primary key (PK + SK for composite tables) is unique per item. If you write an item with the same PK + SK as an existing one, it silently overwrites it — no error, no duplicate.

In the Pin-Level schema, neither PK nor SK needs to be unique on its own:

- **PK is not unique** — all pins within the same task share the same PK. This is intentional. A shared PK creates an "item collection" — a group of related items stored in the same partition. Querying by PK returns all pins in that task with a single call.
- **SK is not unique globally** — two different tasks could have the same SK value (e.g., `BEX#0002|BLK#MOVE_1|PIN#IN|USE#Input`). That's fine because uniqueness is enforced on the combination.
- **PK + SK is always unique** — the combination of 5 PK fields (System, Device, ProgramGroup, Program, Task) and 4 SK fields (BlockExecution, Block, Pin, Usage) produces 9 total fields. A specific pin on a specific block at a specific execution order in a specific task/program/device/system is as granular as it gets in the Mark VIe hierarchy. No two CSV rows can produce the same PK + SK unless they represent the exact same pin.

```
PK (5 fields, shared per task):
  SYS#{System}|DEV#{Device}|PG#{ProgramGroup}|PROG#{Program}|TASK#{Task}

SK (4 fields, unique within a task):
  BEX#{BlockExecution}|BLK#{Block}|PIN#{Pin}|USE#{Usage}

Combined = unique per item in the entire table
```

This design follows DynamoDB best practices for one-to-many relationships: the PK groups related items for efficient queries, and the SK differentiates each item within the group. Making every PK unique would eliminate the ability to query related items together and require additional GSIs or scans to reassemble them.

---

## Recommendation for Your Use Case

### Your Use Case

You need to trace connection dependencies (e.g. `v_8a2x9`) across hundreds of
project scopes, with millions of pin items in the table. Given a connection ID,
the system must find every scope that uses it and walk the full signal chain
(Input → Block → Output → next Block) with minimal latency and cost.

### Winner: Pin-Level Schema (`dynamodb-block-schema`)

### Why Pin-Level Is the Right Choice

**1. GSI3 gives you instant cross-scope lookup**

Your primary query is "where is `v_8a2x9` used across all projects?" — this is
exactly what GSI3 (ConnectionIndex) was built for. One query returns every pin
that references that connection, from every project scope, in milliseconds.
Task schema cannot do this at all (maps are invisible to GSIs).

**2. Cost stays flat as you scale to millions**

With 5 million pin items in the table, a GSI3 query for `CONN#v_8a2x9` still
only reads the 5-20 items that match — not the other 4,999,980. You pay for
what you retrieve, not what's in the table. A typical 3-block trace across
5 scopes costs ~7 GSI3 queries (~3.5 RCU). Compare that to Task schema where
every trace hop scans the entire table — at 100K task items, that's ~12,500 RCU
per hop, and it gets worse linearly as you add projects.

```
Pin-Level at 5M items:  ~7 queries, ~3.5 RCU, <100ms
Task at 100K items:     ~4 scans, ~50,000 RCU, seconds to minutes
```

**3. Simplest data model = fewest bugs**

Each CSV row becomes one DynamoDB item. No nested maps to parse, no connection
index items to keep in sync. When you update a pin, you update one item. When
you delete a project scope, you delete items by PK prefix.

**4. Item count is not a problem — it's a feature**

The instinct to reduce item count comes from relational databases where row count
affects scan performance. DynamoDB is different: queries use indexes, not scans.
More items with proper indexes means more precise queries. Fewer items with nested
data means you lose the ability to index and must scan + filter instead.

```
More items + GSI3  →  precise O(matches) queries  →  scales forever
Fewer items + maps →  full table scans             →  breaks at scale
```

### When You Might Use Task Schema Instead

Task schema is only useful if your primary access pattern is "get all pins for
task X in system Y" and you never need cross-scope connection tracing. For example,
a dashboard that displays one task at a time. But since your core requirement is
dependency tracing by connection ID across project scopes, Task schema is not viable.

### Final Verdict

| Criteria | Pin-Level | Task |
|---|---|---|
| Cross-scope connection trace | ✅ Fast | ❌ Scan |
| Scales to millions of pins | ✅ Yes | ❌ No |
| Fewest items stored | ❌ 37 | ✅ 5 |
| Fewest queries per trace | ✅ ~7 | ❌ ~4 scans |
| Simplest to maintain | ✅ 1 item type | ✅ 1 item type |
| Single pin update cost | ✅ 1 write | ❌ Read-modify-write |

### Performance at 5 Million Items

Your production workload will have ~5M pin items from hundreds of projects.
Here's how each schema performs at that scale:

**Pin-Level — trace `v_8a2x9` across 10 scopes, 3-block chain per scope:**

```
GSI3 query: CONN#v_8a2x9 → reads only the ~15-20 matching items
The other 4,999,980 items are never touched.

Queries:        ~7 GSI3 queries × ~3-4 items each = ~25 items read
Data read:      ~25 items × 500 bytes = ~12.5 KB
RCU cost:       ~4 RCU (eventually consistent) or ~8 RCU (strongly consistent)
Latency:        <100ms total (single-digit ms per query)
Monthly cost:   At 1,000 traces/day → ~120,000 RCU/month → ~$0.04/month
```

The cost and latency are identical whether you have 37 items or 5 million.
GSI3 partitions by connection ID, so the query jumps directly to the matching
partition and reads only what matches.

**Task Schema at 5M pins (~100K task items):**

```
Each trace hop requires a full table scan.
Scan: reads ALL 100K items → filters in app code for matching connection.

Queries:        ~4 full scans per trace (one per BFS hop)
Data read:      100K items × 2KB avg = ~200MB per scan × 4 = ~800MB
RCU cost:       ~50,000 RCU per scan × 4 = ~200,000 RCU per trace
Latency:        5-30 seconds per trace (sequential scans)
Monthly cost:   At 1,000 traces/day → 200M RCU/month → ~$60/month just for reads
```

And it gets worse linearly — at 500K task items, each scan costs 250K RCU.

**Side-by-side at 5M pins:**

| Metric | Pin-Level | Task |
|---|---|---|
| Items stored | 5,000,000 | ~100,000 |
| GSI3 items | 5,000,000 | ~100,000 (broken) |
| RCU per trace | ~4 | ~200,000 |
| Latency per trace | <100ms | 5-30s |
| Data read per trace | ~12.5 KB | ~800 MB |
| Monthly read cost (1K/day) | ~$0.04 | ~$60 |
| Monthly read cost (provisioned) | ~$0.04 | ~$438 |
| Storage cost | ~$1.25/mo | ~$0.10/mo |
| Total monthly cost | ~$1.29/mo | ~$438-$1,500/mo |

Task schema saves on storage ($0.10 vs $1.25) but the read cost at scale
($438-$1,500/month) dwarfs any storage savings by 300-1,000x. Pin-level's
total cost of ownership is lower by orders of magnitude.

**Use Pin-Level Schema.** It is the only design that satisfies all your requirements:
fast cross-scope connection tracing, O(matches) query cost at any scale, simple
flat data model, and the fewest total items with full GSI3 coverage. Task schema
breaks your primary use case (connection tracing) and costs 1,000x more at scale.
At 5 million items, Pin-Level traces cost <100ms and ~4 RCU — the same as at 37 items.

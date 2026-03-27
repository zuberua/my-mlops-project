# FBD Diagram Generation & Modification Flow

## Overview

The Mark VIe Programming Agent generates IEC 61131-3 Function Block Diagrams (FBD)
from uploaded Pins Connectivity data. Users can ask questions about the diagram or
request modifications through natural language chat.

---

## 1. Diagram Generation (Bypass Path — No LLM)

### Trigger
User clicks **Assign Logic** on an unresolved variable (e.g. `d_33tf7`).

### Sequence

1. **Frontend** `proceedWithVariable()` sends message: "Assign logic for d_33tf7..."
2. **Backend** `/chat` endpoint detects `d_33tf7` via regex, `is_assign=true`
3. **Backend** calls `trace_variable_from_session(sid, "d_33tf7")`
4. **kb.py** runs BFS traversal on the uploaded Pins CSV:
   - Finds where `d_33tf7` is used as an Input pin (MOVE_6.SRC)
   - Follows MOVE_6's Output connections (DEST → L33TF7C)
   - Finds L33TF7C as Input on RUNG_2.B, follows RUNG_2 outputs
   - Continues until no more downstream blocks
   - Scoped to same System/Device/ProgramGroup/Program/Task
5. **Backend** `_build_fbd_from_trace()` converts trace into FBD JSON:
   - Groups flow items by block → `blocks_used` with col=depth, row=spread
   - Matches Output connections to Input connections → `wires`
   - Unmatched Input connections → `var_inputs`
   - Extracts EQN for RUNG blocks
   - Includes full `dependency_context.flow` (all pins per block)
6. **Backend** stores FBD via `store_last_fbd(sid, fbd)` for follow-ups
7. **Backend** returns FBD JSON directly (no LLM call — sub-second)
8. **Frontend** `useChat.ts` parses JSON, finds `blocks_used` → `setProgram()`
9. **Frontend** `FBDCanvas.tsx` renders blocks, pins, wires, labels

### Why It's Fast
No Bedrock/LLM call. Pure Python: regex match → BFS trace → JSON build → return.

---

## 2. Question Answering (LLM Path with Context)

### Trigger
User types a question: "what are the pins for MOVE_6?"

### Sequence

1. **Backend** `/chat` — no `d_xxx` match or `is_question=true` → LLM path
2. **Backend** retrieves stored FBD via `get_last_fbd(sid)`
3. **Backend** builds pin summary from `dependency_context.flow`:
   ```
   MOVE_6 [type=MOVE, execution=2]: SRC(Input, conn=d_33tf7, type=ANY), ...
   ```
4. **Backend** injects summary as context prefix to user message
5. **LLM** (Bedrock Claude) answers using actual pin data from the diagram
6. **Frontend** displays text response, diagram unchanged

### Question Detection
First 60 chars checked for: what, why, how, explain, describe, tell me, can you, does, is it, which.
Messages starting with "Assign logic for" always bypass to trace, never treated as questions.

---

## 3. Diagram Modification (LLM Path with Full JSON)

### Trigger
User types: "add a COMPARE block after NOT_1 and connect NOT_A to its input"

### Sequence

1. **Backend** `/chat` — detects modification word ("add") → modification path
2. **Backend** retrieves stored FBD via `get_last_fbd(sid)`
3. **Backend** injects FULL FBD JSON + pin summary as context:
   ```
   [CURRENT FBD DIAGRAM — the user wants to MODIFY this diagram]
   Blocks and their pins: ...
   [FULL FBD JSON — modify this and return the complete updated JSON]
   ```json
   { "blocks_used": [...], "wires": [...], ... }
   ```
   [USER REQUEST]
   add a COMPARE block after NOT_1...
   ```
4. **LLM** parses the FBD JSON, applies changes, returns complete updated JSON
5. **Backend** detects FBD JSON in LLM response → `store_last_fbd(sid, updated)`
6. **Frontend** `useChat.ts` parses JSON → `setProgram()` → canvas re-renders

### Modification Detection
Message checked for: add, remove, delete, rename, change, update, connect,
disconnect, insert, move, replace.

### Chaining
Each modification stores the updated FBD, so subsequent modifications build
on the latest version. Example:
- "add a COMPARE block" → updated FBD stored
- "now connect it to RUNG_2" → uses the FBD that already has COMPARE

---

## 4. Session Memory

All FBD state is stored in-memory per session_id:

| Store | Purpose | Lifetime |
|-------|---------|----------|
| `_last_fbd[sid]` | Current FBD JSON for follow-ups | Until server restart |
| `_pins_kb[sid]` | Uploaded Pins CSV rows | Until server restart |
| `_sessions[sid]` | IO report mappings, unwritten vars | Until server restart |

Note: Server restart or auto-reload (WatchFiles) clears all session state.
The user must re-generate the diagram after a restart for follow-ups to work.

---

## 5. File Reference

| File | Role |
|------|------|
| `agent/app.py` | /chat endpoint, bypass logic, context injection, LLM agent |
| `agent/session_store.py` | In-memory session state (FBD, pins, IO report) |
| `tools/kb.py` | Pins CSV parsing, BFS trace, scope detection |
| `tools/tools.py` | Strands @tool functions, `_build_fbd_from_trace()` |
| `frontend/src/useChat.ts` | Sends /chat requests, parses JSON from responses |
| `frontend/src/FBDCanvas.tsx` | SVG rendering of blocks, pins, wires |
| `frontend/src/App.tsx` | UI: setup, I/O review, chat, Assign Logic button |
| `frontend/src/types.ts` | TypeScript types: ProgramDef, BlockUsed, Wire, etc. |

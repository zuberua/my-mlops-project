# Mark VIe Knowledge Base

This directory contains the knowledge base for the Mark Vle Strands Agent.

## Contents

### Markdown Documentation
- `hardware-config/` - Hardware configuration guides
- `logic-templates/` - PLC logic block templates

### Block Library
- `markvie_block_library.json` - Complete Mark VIe block library with inputs/outputs

## Adding Block Library to RAG

The `markvie_block_library.json` file contains structured information about all Mark VIe blocks including:
- Block names and descriptions
- Input/output definitions with data types
- State variables
- Categories and metadata

### Process Block Library

To add the block library to the RAG system:

```bash
# Navigate to scripts directory
cd ../scripts

# Run the processing script
python3 process_block_library.py
```

**What it does:**
1. Reads `markvie_block_library.json`
2. Converts each block to searchable text format
3. Generates embeddings using Titan Embed v2
4. Uploads to S3: `s3://markvie-vectors-138720056246/embeddings/blocks/`

**Output:**
```
Processing Mark VIe Block Library for RAG
============================================================

Loading: ../knowledge-base/markvie_block_library.json
✓ Loaded 150 blocks

Initializing AWS clients (region: us-west-2)...
✓ AWS clients initialized

Processing blocks and generating embeddings...
  Processed 10/150 blocks...
  Processed 20/150 blocks...
  ...
  Processed 150/150 blocks...

============================================================
Processing Complete!
============================================================

✓ Successfully processed: 150/150 blocks
✓ Uploaded to: s3://markvie-vectors-138720056246/embeddings/blocks/

The block library is now searchable via the agent's RAG system!
```

### Text Format Example

Each block is converted to this format for embedding:

```markdown
# TIMER - Timer

**Category:** Time
**Description:** Timer functionality

## Inputs
None

## Outputs
- **AT_TIME** (BOOL): Timer completion indicator

## States
- **CURTIME** (DINT): Current time value

## Notes
- Updated MAX_TIME to MAXTIME
- Added Note to clarify when AT_TIME goes True

## Metadata
- **Variant Block:** False
- **Expandable:** False
```

## Querying Block Information

Once processed, users can query block information through the agent:

**Example queries:**
- "What are the inputs and outputs of the TIMER block?"
- "Show me all blocks in the Controls category"
- "What does the TRAN_DLY block do?"
- "Which blocks have BOOL inputs?"
- "List all expandable blocks"

## File Structure

```
knowledge-base/
├── README.md                          # This file
├── markvie_block_library.json        # Block library (add your JSON here)
├── hardware-config/
│   └── io-allocation-guide.md
└── logic-templates/
    ├── speed-sensor-template.md
    ├── temperature-sensor-template.md
    └── valve-control-template.md
```

## S3 Structure

After processing, the S3 bucket will have:

```
s3://markvie-vectors-138720056246/
└── embeddings/
    ├── blocks/                        # Block library embeddings
    │   ├── TIMER.json
    │   ├── TRAN_DLY.json
    │   ├── ANALOG_ALARM.json
    │   └── ...
    └── *.json                         # Markdown file embeddings
```

## Updating the Block Library

To update the block library:

1. Edit `markvie_block_library.json`
2. Run `python3 ../scripts/process_block_library.py`
3. The agent will automatically use the updated embeddings

## JSON Schema

Each block in `markvie_block_library.json` follows this schema:

```json
{
  "BLOCK_NAME": {
    "block_name": "string",
    "full_name": "string",
    "category": "string",
    "description": "string",
    "inputs": [
      {
        "name": "string",
        "data_type": "string",
        "description": "string"
      }
    ],
    "outputs": [
      {
        "name": "string",
        "data_type": "string",
        "description": "string"
      }
    ],
    "states": [
      {
        "name": "string",
        "data_type": "string",
        "description": "string"
      }
    ],
    "notes": ["string"],
    "is_variant_block": boolean,
    "supported_data_types": ["string"],
    "is_expandable": boolean,
    "max_inputs": number | null
  }
}
```

## Integration with Agent

The agent's `search_knowledge_base` tool will automatically search both:
1. Markdown documentation (existing)
2. Block library definitions (new)

The vector search uses cosine similarity to find the most relevant blocks based on the user's query.

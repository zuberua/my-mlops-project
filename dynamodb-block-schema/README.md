# DynamoDB Block Pin Ingestion Pipeline

S3 CSV upload → Lambda processing → DynamoDB single-table design for Mark Vle control system block/pin data.

## Architecture

```
CSV File → S3 (uploads/) → Lambda (csv_processor) → DynamoDB
                                    ↓
                            S3 (processed/)
```

## Deploy

```bash
export AWS_PROFILE=zuberua-Admin
export AWS_REGION=us-west-2

./deploy.sh
```

## Upload Data

```bash
aws s3 cp data/sample_pins.csv s3://markvle-block-pins-138720056246/uploads/sample_pins.csv \
  --profile zuberua-Admin --region us-west-2
```

## Query Examples (CLI)

Get all pins for a specific block (MOVE_6):

```bash
aws dynamodb query \
  --table-name MarkvleBlockPins-production \
  --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
  --expression-attribute-values '{
    ":pk":{"S":"SYS#TVA CUMBERLAND|DEV#G1|PG#Custom|PROG#Custom|TASK#ProjectSpecific"},
    ":sk":{"S":"BEX#0002|BLK#MOVE_6"}
  }' \
  --profile zuberua-Admin --region us-west-2
```

Get all pins at execution step 5 (RUNG_2):

```bash
aws dynamodb query \
  --table-name MarkvleBlockPins-production \
  --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
  --expression-attribute-values '{
    ":pk":{"S":"SYS#TVA CUMBERLAND|DEV#G1|PG#Custom|PROG#Custom|TASK#ProjectSpecific"},
    ":sk":{"S":"BEX#0005"}
  }' \
  --profile zuberua-Admin --region us-west-2
```

Get all pins in a task (full execution order):

```bash
aws dynamodb query \
  --table-name MarkvleBlockPins-production \
  --key-condition-expression "PK = :pk" \
  --expression-attribute-values '{
    ":pk":{"S":"SYS#TVA CUMBERLAND|DEV#G1|PG#Custom|PROG#Custom|TASK#ProjectSpecific"}
  }' \
  --profile zuberua-Admin --region us-west-2
```

Find all MOVE blocks across all projects (GSI1):

```bash
aws dynamodb query \
  --table-name MarkvleBlockPins-production \
  --index-name BlockTypeIndex \
  --key-condition-expression "GSI1PK = :type" \
  --expression-attribute-values '{
    ":type":{"S":"TYPE#MOVE"}
  }' \
  --profile zuberua-Admin --region us-west-2
```

Find all Input pins for MOVE blocks (GSI1):

```bash
aws dynamodb query \
  --table-name MarkvleBlockPins-production \
  --index-name BlockTypeIndex \
  --key-condition-expression "GSI1PK = :type AND begins_with(GSI1SK, :usage)" \
  --expression-attribute-values '{
    ":type":{"S":"TYPE#MOVE"},
    ":usage":{"S":"USE#Input"}
  }' \
  --profile zuberua-Admin --region us-west-2
```

Count total items:

```bash
aws dynamodb scan \
  --table-name MarkvleBlockPins-production \
  --select COUNT \
  --profile zuberua-Admin --region us-west-2
```

## Query Examples (Python)

```bash
python scripts/query_examples.py --profile zuberua-Admin
```

## Schema

See [docs/SCHEMA_DESIGN.md](docs/SCHEMA_DESIGN.md) for full access pattern analysis and key design.

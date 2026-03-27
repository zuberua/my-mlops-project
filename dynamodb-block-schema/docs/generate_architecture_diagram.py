"""Generate AWS architecture diagram for the Mark VIe pin ingestion pipeline.

Run:  pip install diagrams && python3 generate_architecture_diagram.py
"""
import os
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.integration import Eventbridge, StepFunctions
from diagrams.aws.compute import Lambda
from diagrams.aws.database import DynamodbTable

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "architecture")

graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "nodesep": "1.0",
    "ranksep": "1.2",
}

with Diagram(
    "Mark VIe Pin Ingestion Pipeline",
    filename=OUTPUT_PATH,
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    outformat="png",
):
    # --- Trigger ---
    csv_upload = S3("markvie-kb-138720056246\nfiles_to_be_processed/")
    eventbridge = Eventbridge("markvie-kb-rule-poc\nObject Created")

    # --- Step Functions workflow (simplified) ---
    with Cluster("markvie-kb-pin-ingestion-poc"):
        sfn = StepFunctions("Step Functions\nWorkflow")
        process = Lambda("markvie-kb-\nprocessor-poc")

    # --- DynamoDB ---
    pins_table = DynamodbTable("markvie-kb-poc\nGSI: ConnectionIndex")
    tracker_table = DynamodbTable("markvie-kb-upload-\ntracker-poc\nGSI: StatusIndex")

    # --- S3 outputs ---
    s3_processed = S3("files_already_processed/")
    s3_unsupported = S3("failed/unsupported/")
    s3_partial = S3("failed/partial/\n+ _errors.json")

    # === Main flow ===
    csv_upload >> Edge(label="Object Created") >> eventbridge
    eventbridge >> Edge(label="StartExecution") >> sfn
    sfn >> process

    # === Lambda writes ===
    process >> Edge(label="BatchWriteItem", style="dashed") >> pins_table
    process >> Edge(headlabel="success  ", style="dashed", color="green", labeldistance="2.5") >> s3_processed
    process >> Edge(headlabel="unsupported  ", style="dashed", color="orange", labeldistance="2.5") >> s3_unsupported
    process >> Edge(headlabel="skipped rows  ", style="dashed", color="orange", labeldistance="2.5") >> s3_partial

    # === Tracker updates (from Step Functions states) ===
    sfn >> Edge(label="RECEIVED /\nCOMPLETED /\nFAILED", style="dashed") >> tracker_table

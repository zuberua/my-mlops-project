"""Generate AWS architecture diagram for the pin ingestion pipeline."""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.integration import Eventbridge, StepFunctions
from diagrams.aws.compute import Lambda
from diagrams.aws.database import DynamodbTable
from diagrams.aws.security import IAMRole

graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "nodesep": "1.0",
    "ranksep": "1.2",
}

with Diagram(
    "Mark VIe Pin Ingestion Pipeline",
    filename="my-mlops-project/dynamodb-block-schema/docs/architecture",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    outformat="png",
):
    csv_upload = S3("S3 Bucket\nknowledgebase/*.csv")

    eventbridge = Eventbridge("EventBridge Rule\nObject Created")

    with Cluster("Step Functions Workflow"):
        record_received = DynamodbTable("Record Upload\nRECEIVED\n(UploadTracker)")
        process = Lambda("Process Pin Report\n(csv_processor)")
        record_completed = DynamodbTable("Record Upload\nCOMPLETED\n(UploadTracker)")
        record_failed = DynamodbTable("Record Upload\nFAILED\n(UploadTracker)")

    pins_table = DynamodbTable("MarkvleBlockPins\n(Pin Data)")
    tracker_table = DynamodbTable("MarkvleUploadTracker\n(Upload Tracking)")

    csv_upload >> Edge(label="Object Created") >> eventbridge
    eventbridge >> Edge(label="StartExecution") >> record_received
    record_received >> Edge(label="PutItem") >> tracker_table
    record_received >> process
    process >> Edge(label="BatchWriteItem") >> pins_table
    process >> Edge(label="success", color="green") >> record_completed
    process >> Edge(label="failure", color="red") >> record_failed
    record_completed >> Edge(label="UpdateItem") >> tracker_table
    record_failed >> Edge(label="UpdateItem") >> tracker_table

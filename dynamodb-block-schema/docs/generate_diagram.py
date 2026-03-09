#!/usr/bin/env python3
"""Generate AWS architecture diagram for the Mark Vle Block Pin Ingestion Pipeline."""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.compute import Lambda
from diagrams.aws.database import DynamodbTable
from diagrams.aws.security import IAMRole
from diagrams.aws.management import Cloudformation
from diagrams.aws.general import User

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

with Diagram(
    "Mark Vle Block Pin Ingestion Pipeline",
    filename="architecture",
    show=False,
    direction="LR",
    graph_attr={"fontsize": "14", "bgcolor": "white", "pad": "0.5"},
):
    user = User("Engineer\n(CSV Upload)")

    with Cluster("Infrastructure as Code"):
        cfn = Cloudformation("CloudFormation\ntable.yaml")
        deploy = User("deploy.sh")

    with Cluster("Ingestion Pipeline"):
        s3_upload = S3("S3 Bucket\nuploads/*.csv")
        s3_processed = S3("S3 Bucket\nprocessed/")
        lambda_fn = Lambda("csv_processor\nPython 3.12")

    with Cluster("Data Store"):
        dynamodb = DynamodbTable("MarkvleBlockPins\n(PAY_PER_REQUEST)")

    with Cluster("Security"):
        role = IAMRole("Lambda Role\nS3 + DynamoDB")

    # Data flow
    user >> Edge(label="aws s3 cp", color="darkgreen") >> s3_upload
    s3_upload >> Edge(label="S3 Event\nObjectCreated", color="orange") >> lambda_fn
    lambda_fn >> Edge(label="BatchWriteItem", color="blue") >> dynamodb
    lambda_fn >> Edge(label="Move processed", style="dashed", color="gray") >> s3_processed
    lambda_fn >> Edge(style="dashed", color="red") >> role

    # IaC flow
    deploy >> Edge(style="dotted", color="purple") >> cfn

print("Generated: architecture.png")
